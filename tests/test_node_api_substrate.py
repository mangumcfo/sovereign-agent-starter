"""Substrate thin routes (KM Substrate Thin Routes GO, 2026-08-12) — gate-enqueue, storage, Port, e2e over HTTP.

Proves the Node Home e2e unblock: a gated act can be ENQUEUED over HTTP so GET /breath_gate/pending is non-empty
and the operator can approve/deny it; storage store→get→verify with integrity refusal; a Port crossing that lands
a pending sanction in the SAME inbox and completes with a value-free receipt. Pure translation over kernel verbs;
no simulate_* over HTTP; no key material in responses.
"""
import pytest


@pytest.fixture
def owner_client(tmp_path, monkeypatch):
    monkeypatch.delenv("BREATHLINE_NODE_API_DEV", raising=False)
    monkeypatch.setenv("BREATHLINE_NODE_LOOPBACK_OWNER", "owner1")
    monkeypatch.setenv("OBLIGATION_LEDGER_ROOT", str(tmp_path / "obligations"))
    monkeypatch.setenv("SUBSTRATE_STORAGE_ROOT", str(tmp_path / "substrate_storage"))
    monkeypatch.setenv("NODE_KEYSTORE_DIR", str(tmp_path / "keystore"))
    from sovereign_agent.node_api import deps
    from sovereign_agent.node_api.routes import substrate
    deps.reset_node()
    substrate.reset_substrate()
    # the API boots on a durable self-held key; provision one for the test node (explicit onboarding act)
    from sovereign_agent.keystore.node_keystore import generate_node_key
    import os
    os.makedirs(str(tmp_path / "keystore"), exist_ok=True)
    generate_node_key(str(tmp_path / "keystore"), "UniversalSovereignNode", at="2026-08-12T00:00:00Z")
    from sovereign_agent.node_api.server import create_app
    yield create_app().test_client()
    deps.reset_node()
    substrate.reset_substrate()


# ── Priority 1 · the gate inbox fills over HTTP, and the operator disposes it ──────────────────────────────
def test_onboard_run_enqueues_a_pending_gate_the_operator_can_approve(owner_client):
    # before: inbox empty
    assert owner_client.get("/api/v1/breath_gate/pending").get_json()["count"] == 0
    # propose the ceremony's first gated act over HTTP
    r = owner_client.post("/api/v1/onboard/run", json={"rationale": "first gated act"})
    assert r.status_code == 201
    body = r.get_json()
    assert body["status"] == "pending_gate" and body["req_id"].startswith("approval_")
    req_id = body["req_id"]
    # the SAME process breath-gate now shows it (Node Home can poll this)
    pend = owner_client.get("/api/v1/breath_gate/pending").get_json()
    assert pend["count"] == 1 and pend["pending"][0]["req_id"] == req_id
    # the operator approves from Node Home — a REAL disposition, not a simulation
    appr = owner_client.post(f"/api/v1/breath_gate/{req_id}/approve")
    assert appr.status_code == 200
    d = appr.get_json()
    assert d["status"] == "approved" and d.get("real") is True and d["approver"] == "owner1"
    # inbox is clear; status reports disposed
    assert owner_client.get("/api/v1/breath_gate/pending").get_json()["count"] == 0
    st = owner_client.get(f"/api/v1/onboard/status?req_id={req_id}").get_json()
    assert st["state"] == "disposed_or_unknown"


def test_onboard_run_gate_can_be_denied(owner_client):
    req_id = owner_client.post("/api/v1/onboard/run", json={}).get_json()["req_id"]
    dny = owner_client.post(f"/api/v1/breath_gate/{req_id}/deny", json={"reason": "not now"})
    assert dny.status_code == 200 and dny.get_json()["status"] == "denied"
    assert owner_client.get("/api/v1/breath_gate/pending").get_json()["count"] == 0


# ── Priority 2 / A5 · storage store → get → verify (integrity refusal unchanged, no custody, no key) ───────
def test_storage_store_get_verify_and_tamper_refusal(owner_client):
    r = owner_client.post("/api/v1/storage/datum",
                          json={"chunks": ["the owner's", " private", " bytes"], "visibility": "private"})
    assert r.status_code == 201
    d = r.get_json()
    assert d["object_id"].startswith("datum:") and d["root"] and d["visibility"] == "private"
    # no custody / no key material leaked in the store response
    blob = str(d).lower()
    assert "chunks" not in d and "private_key" not in blob and "secret" not in blob
    oid = d["object_id"]
    # GET returns metadata (never the bytes)
    g = owner_client.get(f"/api/v1/storage/datum/{oid}").get_json()
    assert g["object_id"] == oid and g["root"] == d["root"] and "chunks" not in g
    # verify with the correct content → integrity verified
    ok = owner_client.post(f"/api/v1/storage/datum/{oid}/verify",
                           json={"chunks": ["the owner's", " private", " bytes"]})
    assert ok.status_code == 200 and ok.get_json()["integrity"] == "verified"
    # tampered content → refused, integrity unchanged (deny)
    bad = owner_client.post(f"/api/v1/storage/datum/{oid}/verify",
                            json={"chunks": ["the owner's", " private", " ALTERED"]})
    assert bad.status_code == 403 and bad.get_json()["code"] == "RETRIEVAL_REFUSED"


def test_storage_store_refuses_empty_content(owner_client):
    r = owner_client.post("/api/v1/storage/datum", json={"visibility": "private"})
    assert r.status_code == 400 and r.get_json()["code"] == "STORAGE_MISSING_CONTENT"


# ── Priority 5 · Port open lands a pending sanction in the SAME inbox; sanction receipt has no value field ──
def test_port_crossing_surfaces_gate_then_sanctions_value_free(owner_client):
    r = owner_client.post("/api/v1/port/crossing",
                          json={"target": "email-relay", "instruction": {"send": "ref://m1"}})
    assert r.status_code == 201
    body = r.get_json()
    assert body["status"] == "pending_sanction" and body["crossing_id"].startswith("crossing:")
    cid, gate_id = body["crossing_id"], body["gate_req_id"]
    # the pending sanction is visible in the SAME breath-gate inbox
    pend = owner_client.get("/api/v1/breath_gate/pending").get_json()
    assert any(it["req_id"] == gate_id for it in pend["pending"])
    # the owner sanctions — a named-human act; receipt carries NO value field
    s = owner_client.post(f"/api/v1/port/crossing/{cid}/sanction", json={"approval_ref": "send #1"})
    assert s.status_code == 200
    receipt = s.get_json()
    assert receipt["crossed"] is True and receipt["approver"] == "owner1"
    for k in ("value", "amount", "funds", "balance", "held"):
        assert k not in receipt, f"the Port receipt must not custody value (found {k!r})"
    # the linked inbox item is cleared
    assert owner_client.get("/api/v1/breath_gate/pending").get_json()["count"] == 0


def test_port_crossing_refuses_empty_target_or_instruction(owner_client):
    assert owner_client.post("/api/v1/port/crossing",
                             json={"instruction": {"x": 1}}).status_code == 400
    assert owner_client.post("/api/v1/port/crossing",
                             json={"target": "relay", "instruction": {}}).status_code == 400


# ── AA fix 1 · a dotted hostname target must not trip R22-3 (→ 201, not KERNEL_EXCEPTION) ──────────────────
@pytest.mark.parametrize("host", ["example.com", "api.example.test"])
def test_port_crossing_accepts_dotted_hostname(owner_client, host):
    r = owner_client.post("/api/v1/port/crossing",
                          json={"target": host, "instruction": {"send": "ref://m1"}})
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["status"] == "pending_sanction"


# ── AA fix 2 · action_class validation + provenance stamp ─────────────────────────────────────────────────
def test_onboard_run_rejects_unknown_action_class(owner_client):
    r = owner_client.post("/api/v1/onboard/run", json={"action_class": "not_a_gated_act"})
    assert r.status_code == 400 and r.get_json()["code"] == "UNKNOWN_ACTION_CLASS"


def test_onboard_run_stamps_http_provenance(owner_client):
    owner_client.post("/api/v1/onboard/run", json={})
    pend = owner_client.get("/api/v1/breath_gate/pending").get_json()
    assert pend["pending"][0]["provenance"]["source"] == "http:onboard.run"


# ── AA fix 3 · a pending Port gate surfaces its boundary in /breath_gate/pending ──────────────────────────
def test_pending_port_gate_surfaces_boundary(owner_client):
    owner_client.post("/api/v1/port/crossing",
                      json={"target": "example.com", "instruction": {"send": "ref://m1"}})
    pend = owner_client.get("/api/v1/breath_gate/pending").get_json()
    port_items = [it for it in pend["pending"] if it["provenance"].get("source") == "http:port.crossing"]
    assert port_items and port_items[0]["provenance"]["boundary"] == "external:example.com"


# ── A1 · the 5-turn ceremony is drivable over HTTP: decline → 0 files, accept → receipt verifies ───────────
def test_onboard_ceremony_decline_leaves_zero_files(owner_client):
    r = owner_client.post("/api/v1/onboard/ceremony", json={"disposition": "decline"})
    assert r.status_code == 200
    b = r.get_json()
    assert b["status"] == "declined" and b["key_written"] is False and b["files_written"] == 0


def test_onboard_ceremony_accept_receipt_verifies_no_key_leak(owner_client):
    r = owner_client.post("/api/v1/onboard/ceremony",
                          json={"disposition": "accept", "name": "sandbox-node", "first_gate": "approve"})
    assert r.status_code == 201
    b = r.get_json()
    assert b["status"] == "onboarded" and b["verified"] is True and b["fingerprint"]
    assert b["first_gate"]["status"] == "approved"
    blob = str(b).lower()
    assert "private_key" not in blob and "secret" not in blob  # only public verification material


# ── A4 · peers MINIMAL PRESENT: this node refuses with no residual; clean_exit of its own grants ───────────
def test_peers_refuse_leaves_no_residual(owner_client):
    r = owner_client.post("/api/v1/peers/refuse", json={"other": "peer-x", "reason": "stepping back"})
    assert r.status_code == 201
    b = r.get_json()
    assert b["refused"] == "peer-x" and b["residual_claim"] is None
    assert b["hostage_free"] is True and b["signature"]


def test_peers_refuse_requires_other(owner_client):
    assert owner_client.post("/api/v1/peers/refuse", json={}).status_code == 400


def test_peers_clean_exit_this_node_walks_clean(owner_client):
    r = owner_client.post("/api/v1/peers/clean_exit", json={})
    assert r.status_code == 201
    b = r.get_json()
    assert b["no_residual"] is True and b["grants_severed"] == b["grants_total"]


# ── /node exposes the REAL self-held identity (16-hex fingerprint + 128-hex public_hex), no private material ─
def test_node_get_exposes_real_fingerprint_and_public_hex(owner_client):
    b = owner_client.get("/api/v1/node").get_json()
    assert b["fingerprint"] and len(b["fingerprint"]) == 16
    assert b["public_hex"] and len(b["public_hex"]) == 128
    assert "private_key" not in str(b).lower() and "private" not in str(b).lower()


# ── peer verbs over HTTP: PRESENT single-node-honest (recognize half · sign · verify), no private key ──────
def test_peers_recognize_returns_my_half_no_private_key(owner_client):
    r = owner_client.post("/api/v1/peers/recognize",
                          json={"peer_public_hex": "ab" * 64, "peer_name": "beard"})
    assert r.status_code == 201
    b = r.get_json()
    assert b["obj_hash"] and b["my_half_sig"] and len(b["my_public_hex"]) == 128
    assert "this node's half only" in b["note"].lower()
    blob = str(b).lower()
    assert "private_key" not in blob and "private" not in blob  # only public material + signature


def test_peers_message_sign_then_verify_roundtrip_and_tamper(owner_client):
    s = owner_client.post("/api/v1/peers/message", json={"text": "hello, peer"})
    assert s.status_code == 201
    m = s.get_json()
    assert m["hash"] and m["sig"] and len(m["my_public_hex"]) == 128 and "private" not in str(m).lower()
    ok = owner_client.post("/api/v1/peers/verify/message",
                           json={"hash": m["hash"], "sig": m["sig"], "sender_public_hex": m["my_public_hex"]})
    assert ok.get_json()["verified"] is True
    bad = owner_client.post("/api/v1/peers/verify/message",
                            json={"hash": m["hash"][:-2] + "00", "sig": m["sig"], "sender_public_hex": m["my_public_hex"]})
    assert bad.get_json()["verified"] is False


def test_peers_verify_recognition_bilateral(owner_client, tmp_path):
    import datetime
    from sovereign_agent.keystore.node_keystore import generate_node_key, load_node_keypair, sign_node_act
    # A = the node's durable key (via /peers/recognize) ; B = a second provisioned key on this iron (test only)
    half = owner_client.post("/api/v1/peers/recognize",
                             json={"peer_public_hex": "cd" * 64, "peer_name": "peerB"}).get_json()
    ks = str(tmp_path / "keystore")
    generate_node_key(ks, "peerB", at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    b_kp = load_node_keypair(ks, "peerB")
    sig_b = sign_node_act(ks, "peerB", half["obj_hash"].encode())
    rec = {"recognition": half["recognition_object"], "sig_a": half["my_half_sig"], "sig_b": sig_b}
    v = owner_client.post("/api/v1/peers/verify/recognition",
                          json={"recognition": rec, "a_public_hex": half["my_public_hex"],
                                "b_public_hex": b_kp.public_hex})
    assert v.get_json()["verified"] is True
    # a wrong b_public_hex must NOT verify
    bad = owner_client.post("/api/v1/peers/verify/recognition",
                            json={"recognition": rec, "a_public_hex": half["my_public_hex"],
                                  "b_public_hex": "ff" * 64})
    assert bad.get_json()["verified"] is False


def test_peers_recognize_missing_peer_is_400(owner_client):
    assert owner_client.post("/api/v1/peers/recognize", json={}).status_code == 400
