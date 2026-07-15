"""ATR-7 — Node API /series read-only Series Pipeline lens (Flask test client).

Covers: clean parse, the safe-prefix fallback when the peer's tail notes break strict YAML,
visibility defaulting (absent → public; explicit private preserved), and missing-file honesty.
"""
import json
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
            drill_down: "the operator pass"
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

# Same content + a peer_notes tail with a value the strict parser rejects (unbalanced quote/colon).
BROKEN_TAIL = CLEAN + textwrap.dedent(
    """
    peer_notes:
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
        # Hermetic by default: point the chapter index at a nonexistent file so tests don't pick up the
        # real repo extraction. The Path B test overrides CHAPTER_INDEX with its own fixture.
        monkeypatch.setenv("CHAPTER_INDEX", str(tmp_path / "no_chapter_index.json"))
        from sovereign_agent.node_api.server import create_app
        return create_app().test_client()

    return _make


def test_clean_parse_default_hides_private(make_client):
    # One-source-of-truth visibility gate (the operator 2026-06-09): the default public view shows only the
    # public ladder; private series are hidden but COUNTED honestly (never silently dropped).
    r = make_client(CLEAN).get("/api/v1/series")
    assert r.status_code == 200
    body = r.get_json()
    assert body["meta"]["ok"] is True
    assert body["meta"]["degraded"] is False
    assert body["meta"]["active_series_count"] == 2
    assert body["meta"]["include_private"] is False
    assert body["meta"]["private_hidden"] == 1
    assert "include_private" in body["meta"]["private_note"]
    by_slug = {s["slug"]: s for s in body["series"]}
    # private series withheld from the public view…
    assert "quadroof_private" not in by_slug
    # …public ladder renders, absent visibility defaults to public
    assert by_slug["agentic_playbooks"]["visibility"] == "public"
    t = by_slug["agentic_playbooks"]["titles"][0]
    assert t["title"] == "Scaling"
    assert t["next_gate"].startswith("Human handoff")


def test_include_private_surfaces_private(make_client):
    # the operator explicitly surfaces private series with ?include_private=1.
    r = make_client(CLEAN).get("/api/v1/series?include_private=1")
    assert r.status_code == 200
    body = r.get_json()
    assert body["meta"]["include_private"] is True
    assert body["meta"]["private_hidden"] == 0
    by_slug = {s["slug"]: s for s in body["series"]}
    assert by_slug["agentic_playbooks"]["visibility"] == "public"
    # explicit private is preserved + carries the null public number
    assert by_slug["quadroof_private"]["visibility"] == "private"
    assert by_slug["quadroof_private"]["number"] is None


def test_safe_prefix_fallback_on_broken_tail(make_client):
    r = make_client(BROKEN_TAIL).get("/api/v1/series?include_private=1")
    assert r.status_code == 200
    body = r.get_json()
    # the lens still renders the intact roadmap, but tells the truth that the tail was skipped
    assert body["meta"]["degraded"] is True
    assert body["meta"]["ok"] is True
    assert len(body["series"]) == 2
    assert "peer_notes" in body["meta"]["note"] or "tail" in body["meta"]["note"]


def test_path_b_chapters_merge_from_index(make_client, tmp_path, monkeypatch):
    # Path B (the operator 2026-06-09): a title with no chapters of its own gets the extracted TOC merged from
    # the index by book_id at render time — chapters trace to the manuscript; the roadmap stays lean.
    idx = tmp_path / "extracted_chapter_outlines_test.json"
    idx.write_text(json.dumps({"books": {
        "10_x": {"book_id": "10_x", "chapters": [
            {"n": 1, "title": "Scaling", "stage": "extracted"},
            {"n": 2, "title": "Drift", "stage": "extracted"}]}}}), encoding="utf-8")
    client = make_client(CLEAN)  # fixture sets CHAPTER_INDEX to a nonexistent file…
    monkeypatch.setenv("CHAPTER_INDEX", str(idx))  # …override it AFTER (lens reads env at request time)
    r = client.get("/api/v1/series?include_private=1")
    body = r.get_json()
    by_slug = {s["slug"]: s for s in body["series"]}
    t = by_slug["agentic_playbooks"]["titles"][0]
    # merged from the index, flagged honestly as extracted-sourced
    assert t["chapters_source"] == "extracted-index"
    assert [c["title"] for c in t["chapters"]] == ["Scaling", "Drift"]
    # a title NOT in the index stays chapterless (no fabrication)
    assert "chapters" not in by_slug["quadroof_private"]["titles"][0]


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
