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
      source: the node
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


MIXED_SESSION = textwrap.dedent(
    """
    export:
      session_id: cyl_mixed
    entries:
      - id: t1
        source: the node
        content_type: text
        content: A the node status message, not a hopper delta.
      - id: v1
        source: Voice Note
        content_type: voice
        content: A real spoken thought worth turning into a packet.
      - id: g1
        source: external-reviewer
        content_type: text
        content: A G review note, not a hopper delta.
    """
)


def test_voice_preference_filters_mixed_session(tmp_path, monkeypatch):
    sp = tmp_path / "session.yaml"
    sp.write_text(MIXED_SESSION, encoding="utf-8")
    monkeypatch.setenv("BREATHLINE_NODE_API_DEV", "1")
    monkeypatch.setenv("HOPPER_SOURCE", str(sp))
    from sovereign_agent.node_api.server import create_app
    body = create_app().test_client().get("/api/v1/hopper").get_json()
    ids = [c["id"] for c in body["cards"]]
    assert ids == ["v1"]          # only the voice capture surfaces; the node/G text dropped
    assert body["meta"]["live"] is True


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
    r = client.post("/api/v1/hopper/packet", json={"card_id": "x"})
    assert r.status_code == 400
    # canonical error shape (audit 2026-06-13d #9): code mirrors slug + why + next_step + cylinder_ref
    b = r.get_json()
    assert b["error"] == "missing_text" and b["code"] == "missing_text"
    assert b["why"] and b["next_step"] and "cylinder_ref" in b


FEED = (
    '{"_genesis": "schema line — skipped"}\n'
    '{"ts":"2026-06-04T14:15:00","source_cyl":"cyl_x","source_entry_hash":"h1","lane":"book:11",'
    '"series_ref":"S1 Agentic AI Playbooks / B11","one_line_intent":"Tighten the DataBridge example.",'
    '"lgp_hint":"human-ease","priority":"normal","ref":"hmc:h1"}\n'
    '{"ts":"2026-06-04T14:20:00","source_cyl":"cyl_x","source_entry_hash":"h2","lane":"tooling",'
    '"series_ref":"tooling/Atrium","one_line_intent":"Add a dark mode toggle.","priority":"high","ref":"hmc:h2"}\n'
)


def test_iron_clad_feed_consumed(tmp_path, monkeypatch):
    fp = tmp_path / "hopper_feed.ndjson"
    fp.write_text(FEED, encoding="utf-8")
    monkeypatch.setenv("BREATHLINE_NODE_API_DEV", "1")
    monkeypatch.setenv("HOPPER_FEED", str(fp))
    from sovereign_agent.node_api.server import create_app
    body = create_app().test_client().get("/api/v1/hopper").get_json()
    assert body["meta"]["iron_clad"] is True
    assert len(body["cards"]) == 2
    # high priority first, _genesis skipped
    assert body["cards"][0]["lane"] == "tooling"
    assert body["cards"][0]["priority"] == "high"
    assert all(c.get("series_ref") for c in body["cards"])


def test_feed_packet_lane_routing(tmp_path, monkeypatch):
    monkeypatch.setenv("BREATHLINE_NODE_API_DEV", "1")
    monkeypatch.setenv("OBLIGATION_LEDGER_ROOT", str(tmp_path / "obl"))
    from sovereign_agent.node_api import deps
    deps.reset_node()
    from sovereign_agent.node_api.server import create_app
    c = create_app().test_client()
    # tooling card → Tooling/Build title + tooling: ref (skips the book producer)
    t = c.post("/api/v1/hopper/packet", json={"card_id": "h2", "text": "Add a dark mode toggle.",
               "lane": "tooling", "series_ref": "tooling/Atrium", "ref": "hmc:h2"}).get_json()["obligation"]
    assert t["title"].startswith("Tooling/Build ·") and t["ref"].startswith("tooling:")
    # book card → processable Hopper packet + Page: Book 11 grounded in intent
    bk = c.post("/api/v1/hopper/packet", json={"card_id": "h1", "text": "Tighten the DataBridge example.",
                "lane": "book:11", "series_ref": "S1 Agentic AI Playbooks / B11", "ref": "hmc:h1"}).get_json()["obligation"]
    assert bk["title"].startswith("Hopper packet —") and "Page: Book 11" in bk["intent"]
    deps.reset_node()
