"""WP3.5 — durable disposition receipts survive a node restart (pre-condition for WP4).

AA's WP3 D7 flag: `/audit/cylinders` + `/inference/receipts` read the in-memory compliance trail, which is
empty after a restart. WP3.5 persists each disposed act — a Port sanction, a breath-gate approve/deny — to the
append-only, hash-chained object registry (`_reg()`, the same durable store `open_crossing` uses) and projects
it onto the EXISTING `/inference/receipts` route.

These tests prove the restart-survival property WITHOUT touching a sealed primitive: a disposition is made on
one app instance, the in-memory singletons are dropped (`reset_node` + `reset_substrate` — a process restart),
a SECOND app instance is built against the SAME on-disk storage root, and the disposed act is STILL listable +
re-derivable there. No value is written (money-path OFF); the web surface is untouched (no agent POST here —
these are the owner's own POSTs, exactly as on the iron).
"""
import os

import pytest


def _build_client(storage_root, keystore_dir, monkeypatch, *, provision: bool):
    """Build a fresh node_api test client against a GIVEN storage root + keystore — a 'process start'.
    `provision=True` mints the node key (first start); `provision=False` is a RESTART: same durable key + same
    object registry on disk, but brand-new in-memory singletons (the compliance trail + gate start empty)."""
    monkeypatch.delenv("BREATHLINE_NODE_API_DEV", raising=False)
    monkeypatch.setenv("BREATHLINE_NODE_LOOPBACK_OWNER", "owner1")
    monkeypatch.setenv("SUBSTRATE_STORAGE_ROOT", str(storage_root))
    monkeypatch.setenv("NODE_KEYSTORE_DIR", str(keystore_dir))
    from sovereign_agent.node_api import deps
    from sovereign_agent.node_api.routes import substrate
    deps.reset_node()
    substrate.reset_substrate()          # drop in-memory _REG/_CROSSING/_GATE_META — the restart
    if provision:
        from sovereign_agent.keystore.node_keystore import generate_node_key
        os.makedirs(str(keystore_dir), exist_ok=True)
        generate_node_key(str(keystore_dir), "UniversalSovereignNode", at="2026-08-14T00:00:00Z")
    from sovereign_agent.node_api.server import create_app
    return create_app().test_client()


def _receipts(client):
    return client.get("/api/v1/inference/receipts").get_json()


def test_port_sanction_receipt_survives_restart(tmp_path, monkeypatch):
    storage_root = tmp_path / "substrate_storage"
    keystore_dir = tmp_path / "keystore"
    c = _build_client(storage_root, keystore_dir, monkeypatch, provision=True)

    # before any disposition: no durable receipts
    assert _receipts(c)["durable_count"] == 0

    # open a crossing → owner sanctions it (the owner's own POST; the surface never disposes)
    body = c.post("/api/v1/port/crossing",
                  json={"target": "external-relay", "instruction": {"send": "ref://drill1"}}).get_json()
    cid = body["crossing_id"]
    s = c.post(f"/api/v1/port/crossing/{cid}/sanction", json={"approval_ref": "send #1"}).get_json()
    assert s["crossed"] is True and s["durable"] is True
    root_before = s["crossing_root"]
    receipt_hash_before = s["receipt_version_hash"]
    # value-free fence still holds on the persisted path
    assert not any(k in s for k in ("value", "amount", "funds", "balance", "held"))

    # it is listable now (durable + in-memory both present)
    pre = _receipts(c)
    assert pre["durable_count"] == 1
    sanction = next(r for r in pre["receipts"] if r.get("disposition") == "sanctioned")
    assert sanction["compliance_block"]["crossing_root"] == root_before
    assert "value" not in sanction["compliance_block"]

    # ── RESTART ── new in-memory singletons, SAME on-disk registry + key
    c2 = _build_client(storage_root, keystore_dir, monkeypatch, provision=False)
    post = _receipts(c2)
    # the disposed act SURVIVES: still listable after the restart
    assert post["durable_count"] == 1
    assert post["session_count"] == 0        # the in-memory compliance trail is empty after a restart
    survived = next(r for r in post["receipts"] if r.get("disposition") == "sanctioned")
    # re-derivable: same crossing root + same hash-chained receipt hash across the restart
    assert survived["compliance_block"]["crossing_root"] == root_before
    assert survived["receipt_hash"] == receipt_hash_before
    assert survived["durable"] is True


def test_gate_deny_and_approve_receipts_survive_restart(tmp_path, monkeypatch):
    storage_root = tmp_path / "substrate_storage"
    keystore_dir = tmp_path / "keystore"
    c = _build_client(storage_root, keystore_dir, monkeypatch, provision=True)

    # deny one gate, approve another — both are REAL owner dispositions, both must persist
    r1 = c.post("/api/v1/onboard/run", json={"rationale": "act A"}).get_json()["req_id"]
    d = c.post(f"/api/v1/breath_gate/{r1}/deny", json={"reason": "not now"}).get_json()
    assert d["status"] == "denied" and d["durable"] is True

    r2 = c.post("/api/v1/onboard/run", json={"rationale": "act B"}).get_json()["req_id"]
    a = c.post(f"/api/v1/breath_gate/{r2}/approve").get_json()
    assert a["status"] == "approved" and a["durable"] is True

    pre = _receipts(c)
    assert pre["durable_count"] == 2
    dispositions = {r["disposition"] for r in pre["receipts"] if r.get("action_class") == "breath_gate"}
    assert dispositions == {"denied", "approved"}

    # ── RESTART ──
    c2 = _build_client(storage_root, keystore_dir, monkeypatch, provision=False)
    # the pending inbox is empty after restart (in-memory) …
    assert c2.get("/api/v1/breath_gate/pending").get_json()["count"] == 0
    # … but the DISPOSED acts are still on the record
    post = _receipts(c2)
    assert post["durable_count"] == 2 and post["session_count"] == 0
    gate_receipts = {r["disposition"]: r for r in post["receipts"] if r.get("action_class") == "breath_gate"}
    assert set(gate_receipts) == {"denied", "approved"}
    assert gate_receipts["denied"]["compliance_block"]["reason"] == "not now"
    # each carries a hash-chained receipt hash (re-derivable)
    assert all(g["receipt_hash"] for g in gate_receipts.values())


def test_durable_receipt_is_recomputable_from_the_registry_alone(tmp_path, monkeypatch):
    """The persisted receipt's version_hash re-derives byte-identical from the bare object list — an outsider
    can recompute it with no live process (the S5-05-E2-1 promise the registry already keeps)."""
    storage_root = tmp_path / "substrate_storage"
    keystore_dir = tmp_path / "keystore"
    c = _build_client(storage_root, keystore_dir, monkeypatch, provision=True)
    cid = c.post("/api/v1/port/crossing",
                 json={"target": "external-relay", "instruction": {"send": "ref://x"}}).get_json()["crossing_id"]
    s = c.post(f"/api/v1/port/crossing/{cid}/sanction", json={"approval_ref": "send"}).get_json()

    # recompute the receipt hash offline from objects.ndjson (no registry object, bare replay)
    from sovereign_agent.ndjson import read_ndjson
    from sovereign_agent.evidence.export_packet import _canon, _sha
    entries = read_ndjson(str(storage_root / "objects.ndjson")).entries
    rec = next(e for e in entries if e["object_id"] == f"receipt:port_sanction:{cid}")
    bare = {k: rec[k] for k in rec if k not in ("version_hash", "mandate")}
    assert _sha(_canon(bare)) == rec["version_hash"] == s["receipt_version_hash"]
