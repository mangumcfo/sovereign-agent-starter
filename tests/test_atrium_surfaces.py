"""S5 re-cycle (KM/G ruling 2026-07-31) — Atrium READ-ONLY view surfaces.

Per the no-overclaim rule: a claim flips to PRESENT only if a genuine read-only surface satisfies it.
These prove the two view-type claims already satisfied by existing read-only routes:
  · S5-06-E1-2 — the distribution view shows integration fragmentation (coherent vs drift) across systems.
  · S5-04-E5-4 — the ledger view renders current state AND provenance per book↔code extrusion.
Operator-ACTION surfaces (watch+gate, resolve, cockpit) are NOT proven here — they stay HOLD.
"""
import hashlib
import json

import pytest


def _client(tmp_path, monkeypatch, extrusions):
    monkeypatch.setenv("BREATHLINE_NODE_API_DEV", "1")
    reg = tmp_path / "coherence_registry.json"
    reg.write_text(json.dumps({"extrusions": extrusions, "reconciliation": {}}))
    from sovereign_agent.node_api.routes import coherence as coh
    monkeypatch.setattr(coh, "_registry_path", lambda: reg)
    monkeypatch.delenv("BOOK_CODE_TREE", raising=False)
    monkeypatch.delenv("CHANNEL_TRACKER", raising=False)
    from sovereign_agent.node_api import deps
    deps.reset_node()
    from sovereign_agent.node_api.server import create_app
    return create_app().test_client()


def _ext(book_id, book, coherent, tmp_path):
    """One extrusion; coherent=True makes passage present + hash match, else drift."""
    m = tmp_path / f"{book_id}.md"
    m.write_text("passage " + book_id)
    ph = hashlib.sha256(("passage " + book_id).encode()).hexdigest()[:12]
    return {"capability": f"{book} cap", "book": book, "book_id": book_id,
            "code_file": "src/sovereign_agent/node_api/routes/coherence.py",
            "tests_file": "tests/test_atrium_surfaces.py",
            "book_file": str(m), "passage": "passage " + book_id,
            "passage_hash": ph if coherent else "deadbeef", "chapter": "Ch"}


def test_e1_2_distribution_view_shows_fragmentation(tmp_path, monkeypatch):
    # two systems: one coherent, one drifted → the surface must show the fragmentation
    client = _client(tmp_path, monkeypatch,
                     [_ext("bookA", "System A", True, tmp_path),
                      _ext("bookB", "System B", False, tmp_path)])
    r = client.get("/api/v1/coherence/distribution")
    assert r.status_code == 200
    b = r.get_json()
    assert b["summary"]["drift"] >= 1 and b["summary"]["coherent"] >= 1   # fragmentation visible
    keys = {row["key"] for row in b["join_record"]}
    assert "booka" in keys and "bookb" in keys                            # across every connected system


def test_e5_4_ledger_view_renders_state_and_provenance(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, [_ext("ledgerbook", "ERP Ledger", True, tmp_path)])
    r = client.get("/api/v1/coherence")
    assert r.status_code == 200
    b = r.get_json()
    row = b["extrusions"][0]
    assert row["status"] in ("coherent", "DRIFT")        # current state rendered
    assert row.get("book_file") and row.get("code_file") # provenance rendered (book↔code)
    assert row.get("passage")                            # the cited provenance passage
