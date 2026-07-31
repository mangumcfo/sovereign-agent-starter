"""S5-06-E2-3 — Helix distribution rendering (KM/G ruling 2026-07-31).

Proves the /coherence/distribution join is VISIBLE FROM THE THREE READ-ONLY SOURCES the ruling pinned —
book↔code coherence records + book_code_tree + CHANNEL_TRACKER distribution overlay — composed onto one
authoritative book row. This is the acceptance test for the HOLD→PRESENT flip.
"""
import hashlib
import json
import textwrap

import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BREATHLINE_NODE_API_DEV", "1")

    # SOURCE 1 — book↔code coherence records (make it coherent: passage present + hash matches)
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("the authoritative join passage")
    passage_hash = hashlib.sha256(b"the authoritative join passage").hexdigest()[:12]
    reg = tmp_path / "coherence_registry.json"
    reg.write_text(json.dumps({"extrusions": [{
        "capability": "Distribution join", "book": "Distribution Matrix Governance", "book_id": "s5_06",
        "code_file": "src/sovereign_agent/node_api/routes/coherence.py",
        "tests_file": "tests/test_helix_distribution.py",
        "book_file": str(manuscript), "passage": "the authoritative join passage",
        "passage_hash": passage_hash, "chapter": "Ch 2"}], "reconciliation": {}}))
    from sovereign_agent.node_api.routes import coherence as coh
    monkeypatch.setattr(coh, "_registry_path", lambda: reg)

    # SOURCE 2 — book_code_tree (book↔code edges)
    tree = tmp_path / "book_code_tree.json"
    tree.write_text(json.dumps({"edges": [{
        "book": "s5_06", "code": "routes/coherence.py", "class": "derived",
        "rule": "R2", "anchor": "the join", "pin": "pending"}],
        "book_tree": [], "findings": {}, "meta": {}}))
    monkeypatch.setenv("BOOK_CODE_TREE", str(tree))

    # SOURCE 3 — CHANNEL_TRACKER distribution overlay
    ct = tmp_path / "CHANNEL_TRACKER.yaml"
    ct.write_text(textwrap.dedent("""
        books:
          s5_06:
            kdp: {state: staged}
    """))
    monkeypatch.setenv("CHANNEL_TRACKER", str(ct))

    from sovereign_agent.node_api import deps
    deps.reset_node()
    from sovereign_agent.node_api.server import create_app
    yield create_app().test_client()
    deps.reset_node()


def test_helix_distribution_join_visible_from_three_sources(client):
    r = client.get("/api/v1/coherence/distribution")
    assert r.status_code == 200
    b = r.get_json()

    # all three read-only sources were read and contributed
    assert b["sources"] == {"coherence_records": True, "book_code_tree": True, "channel_overlay": True}
    assert b["summary"]["coherent"] + b["summary"]["drift"] >= 1  # source 1 (coherence records)
    assert b["summary"]["tree_edges_total"] == 1                  # source 2 (book_code_tree)
    assert b["summary"]["channels_total"] == 1                    # source 3 (CHANNEL_TRACKER)

    # the join composes all three onto ONE authoritative book row
    row = next(x for x in b["join_record"] if x["key"] == "s506")
    assert row["coherence"] == {"coherent": 1, "drift": 0}        # from the coherence records
    assert row["tree_edges"] == 1                                 # from the book_code_tree
    assert row["channels"] == {"kdp": {"state": "staged"}}        # from the CHANNEL_TRACKER overlay
    assert b["note"].startswith("Helix distribution rendering")
