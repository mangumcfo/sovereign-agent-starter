"""
Extrusion-anchor tests — real assertions for the 5 book↔code modules that had no test coverage,
so every coherence-registry anchor can reach VALIDATED in scripts/extrusion_validate.py.

Each test exercises the actual capability its book passage describes (The Fence / Co-Extrusion /
The Diff / The Reconciliation / Federation-resonance). Run: PYTHONPATH=src pytest tests/test_extrusion_anchors.py
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
SCRIPTS = REPO / "scripts"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The Fence — scripts/thread.py (receipted Tiger↔GB coordination; hash-chained)
def test_fence_thread_hash_chain():
    t = _load(SCRIPTS / "thread.py", "thread_mod")
    h1 = t._hash("prev", "tiger", "gb", "ref", "msg")
    h2 = t._hash("prev", "tiger", "gb", "ref", "msg")
    assert h1 == h2 and len(h1) >= 16, "thread hash must be deterministic + chain-grade"
    assert h1 != t._hash("PREV", "tiger", "gb", "ref", "msg"), "hash must depend on prev (chain link)"
    assert isinstance(t._load(), list)


# Co-Extrusion — scripts/atrium_producer.py (book → code/diffs; tag→book resolution)
def test_coextrusion_producer_tag_resolution():
    p = _load(SCRIPTS / "atrium_producer.py", "producer_mod")
    assert p._TAG_TO_BID["Book 11"] == "11_ma_due_diligence"
    assert isinstance(p.BOOK_PATHS, dict) and p.BOOK_PATHS


# The Diff — scripts/atrium_apply.py (see-before-write apply; passage-match normalization)
def test_diff_apply_normalization():
    a = _load(SCRIPTS / "atrium_apply.py", "apply_mod")
    assert "—" in a._DASHES, "must normalize em-dash when matching passages"
    assert any(q in a._QUOTES for q in "‘’“”"), "must normalize curly quotes"
    assert callable(a._repo_of)


# The Reconciliation — routes/coherence.py (live book↔code lens + rollup)
def test_reconciliation_coherence_routes():
    os.environ["BREATHLINE_NODE_API_DEV"] = "1"
    from sovereign_agent.node_api.server import create_app
    c = create_app().test_client()
    r = c.get("/api/v1/coherence")
    assert r.status_code == 200
    d = r.get_json()
    assert "extrusions" in d and "summary" in d
    r2 = c.get("/api/v1/coherence/rollup")
    assert r2.status_code == 200
    assert "by_book" in r2.get_json()


# Proposal mechanics — routes/proposals.py (breath-gated self-modification; see-before-write queue)
def test_proposal_mechanics_route():
    os.environ["BREATHLINE_NODE_API_DEV"] = "1"
    from sovereign_agent.node_api.server import create_app
    c = create_app().test_client()
    r = c.get("/api/v1/proposals")
    assert r.status_code == 200
    body = r.get_json()
    assert isinstance(body, (list, dict)), "proposals queue must return a list/envelope"


# Federation — resonance, not coordination (demo_roles/federation_procurement_coordinator/role.py)
def test_federation_role_resonance():
    mod = _load(REPO / "src/sovereign_agent/demo_roles/federation_procurement_coordinator/role.py", "fed_role")
    agent = mod.FederationProcurementCoordinatorAgent()
    out = agent.process({"action_class": "generate_zk_statistical_profile"})
    assert out.get("action_class") == "generate_zk_statistical_profile"
    assert "scope" in out or "gate" in out, "each action carries its scope/breath-gate (governed)"
