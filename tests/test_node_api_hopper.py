"""ATR-8 — Node API /hopper lane (Flask test client).

Covers: honest mock fallback when no source is set, real parse from a B51 session.yaml,
and the Send-to-Packet write opening a real obligation (the one human gate, reversible).
"""
import textwrap

import pytest

SESSION_YAML = textwrap.dedent(
    """
    export:
      version: '1.0'
      session_id: cyl_testfeed01
      source: Tiger
    entries:
      - id: cap_aaa
        timestamp: '2026-06-01T15:19:34Z'
        source: Voice Note
        content_type: voice
        content: First captured thought about the continuous book to code loop.
      - id: cap_bbb
        timestamp: '2026-06-01T15:22:00Z'
        source: Voice Note
        content_type: voice
        content: Second thought — write a chapter and see the code gated.
    """
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BREATHLINE_NODE_API_DEV", "1")
    monkeypatch.setenv("OBLIGATION_LEDGER_ROOT", str(tmp_path / "obligations"))
    monkeypatch.delenv("HOPPER_SOURCE", raising=False)
    from sovereign_agent.node_api import deps
    deps.reset_node()
    from sovereign_agent.node_api.server import create_app
    yield create_app().test_client()
    deps.reset_node()


def test_mock_fallback_is_honest(client):
    r = client.get("/api/v1/hopper")
    assert r.status_code == 200
    body = r.get_json()
    assert body["meta"]["live"] is False
    assert "MOCK" in body["meta"]["note"]
    assert len(body["cards"]) >= 1
    # every card still carries a preview + text so the lane is usable
    assert all(c.get("preview") and c.get("text") for c in body["cards"])


def test_real_session_parse(tmp_path, monkeypatch):
    sp = tmp_path / "session.yaml"
    sp.write_text(SESSION_YAML, encoding="utf-8")
    monkeypatch.setenv("BREATHLINE_NODE_API_DEV", "1")
    monkeypatch.setenv("HOPPER_SOURCE", str(sp))
    from sovereign_agent.node_api.server import create_app
    r = create_app().test_client().get("/api/v1/hopper")
    body = r.get_json()
    assert body["meta"]["live"] is True
    assert body["meta"]["session_id"] == "cyl_testfeed01"
    # newest-first ordering
    assert body["cards"][0]["id"] == "cap_bbb"
    assert body["cards"][1]["id"] == "cap_aaa"


def test_send_to_packet_opens_real_obligation(client):
    r = client.post("/api/v1/hopper/packet",
                    json={"card_id": "cap_xyz", "text": "Turn this delta into a governed packet."})
    assert r.status_code == 201
    ob = r.get_json()["obligation"]
    assert ob["draft"] is True            # DRAFT debit — the gate is downstream
    assert ob["ref"] == "b51:cap_xyz"
    assert "Turn this delta" in ob["intent"]
    # it actually landed on the ledger
    lst = client.get("/api/v1/obligations").get_json()
    assert any(o["id"] == ob["id"] for o in lst["open"])


def test_packet_requires_text(client):
    assert client.post("/api/v1/hopper/packet", json={"card_id": "x"}).status_code == 400
