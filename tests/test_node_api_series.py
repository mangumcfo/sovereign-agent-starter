"""ATR-7 — Node API /series read-only Series Pipeline lens (Flask test client).

Covers: clean parse, the safe-prefix fallback when GB's tail notes break strict YAML,
visibility defaulting (absent → public; explicit private preserved), and missing-file honesty.
"""
import textwrap

import pytest

CLEAN = textwrap.dedent(
    """
    version: "test.v1"
    multi_series_roadmap:
      current_arc: "S1 → S2"
      active_series_count: 2
    series:
      - slug: agentic_playbooks
        name: "Series 1"
        series_number: 1
        status: "active"
        titles:
          - book_id: "10_x"
            title: "Scaling"
            subtitle: "ship"
            stage: "phase_2_iteration"
            lgp_alignment_score: "high"
            next_gate: "Human handoff | obligation: pending"
            drill_down: "KM pass"
      - slug: quadroof_private
        name: "QuadRoof"
        series_number: null
        visibility: "private"
        status: "private investor guide"
        titles:
          - book_id: "01_investor_guide"
            title: "Investor Guide"
            stage: "draft"
    """
)

# Same content + a gb_notes tail with a value the strict parser rejects (unbalanced quote/colon).
BROKEN_TAIL = CLEAN + textwrap.dedent(
    """
    gb_notes:
      - "this note: has an "inner" quote and : colons that break strict yaml
    """
)


@pytest.fixture
def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("BREATHLINE_NODE_API_DEV", "1")

    def _make(roadmap_text):
        rp = tmp_path / "series_roadmap.yaml"
        rp.write_text(roadmap_text, encoding="utf-8")
        monkeypatch.setenv("SERIES_ROADMAP", str(rp))
        from sovereign_agent.node_api.server import create_app
        return create_app().test_client()

    return _make


def test_clean_parse_and_visibility(make_client):
    r = make_client(CLEAN).get("/api/v1/series")
    assert r.status_code == 200
    body = r.get_json()
    assert body["meta"]["ok"] is True
    assert body["meta"]["degraded"] is False
    assert body["meta"]["active_series_count"] == 2
    by_slug = {s["slug"]: s for s in body["series"]}
    # absent visibility defaults to public (KDP ladder)
    assert by_slug["agentic_playbooks"]["visibility"] == "public"
    # explicit private is preserved (honest surfacing)
    assert by_slug["quadroof_private"]["visibility"] == "private"
    t = by_slug["agentic_playbooks"]["titles"][0]
    assert t["title"] == "Scaling"
    assert t["next_gate"].startswith("Human handoff")


def test_safe_prefix_fallback_on_broken_tail(make_client):
    r = make_client(BROKEN_TAIL).get("/api/v1/series")
    assert r.status_code == 200
    body = r.get_json()
    # the lens still renders the intact roadmap, but tells the truth that the tail was skipped
    assert body["meta"]["degraded"] is True
    assert body["meta"]["ok"] is True
    assert len(body["series"]) == 2
    assert "gb_notes" in body["meta"]["note"] or "tail" in body["meta"]["note"]


def test_missing_file_is_honest(make_client, tmp_path, monkeypatch):
    monkeypatch.setenv("BREATHLINE_NODE_API_DEV", "1")
    monkeypatch.setenv("SERIES_ROADMAP", str(tmp_path / "nope.yaml"))
    from sovereign_agent.node_api.server import create_app
    r = create_app().test_client().get("/api/v1/series")
    assert r.status_code == 200
    body = r.get_json()
    assert body["series"] == []
    assert body["meta"]["ok"] is False
    assert "not found" in body["meta"]["note"]
