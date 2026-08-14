"""CH3 — the node status document has ONE source: sovereign_agent.agent.local_mind.facts().
GET /api/v1/status returns exactly that; the CLI (node_agent status) renders the same function. No divergence."""
from __future__ import annotations

import importlib.util
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parent.parent
from sovereign_agent.agent import local_mind  # noqa: E402


def test_facts_canonical_keys():
    f = local_mind.facts()
    for k in ("node_fp", "gpu", "peers", "grants", "units_offered", "puller_running", "model_up", "source"):
        assert k in f, f"canonical status missing {k}"
    assert f["source"] == "sovereign_agent.agent.local_mind.facts"
    assert f["gpu"].get("state") in ("ok", "no-check", "error")   # three-state
    assert isinstance(f["peers"]["count"], int)


def test_api_status_returns_facts(monkeypatch, tmp_path):
    # the /api/v1/status route body IS local_mind.facts() — one source, not a re-derivation
    from sovereign_agent.node_api import server
    monkeypatch.setenv("BREATHLINE_NODE_LOOPBACK_OWNER", "owner")
    app = server.create_app()
    client = app.test_client()
    r = client.get("/api/v1/status", environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
                   headers={"Sec-Fetch-Site": "same-origin"})
    assert r.status_code == 200, r.data
    body = r.get_json()
    assert body.get("source") == "sovereign_agent.agent.local_mind.facts"
    assert set(("node_fp", "gpu", "peers", "grants", "puller_running", "model_up")).issubset(body.keys())


def test_cli_status_renders_same_source():
    # the CLI status command imports and renders the same local_mind.facts() (verified structurally)
    src = (_ROOT / "scripts" / "node_agent.py").read_text()
    assert "local_mind.facts()" in src and "from sovereign_agent.agent import local_mind" in src
