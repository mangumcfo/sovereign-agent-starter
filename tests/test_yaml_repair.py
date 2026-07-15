"""Shared resilient roadmap loader — audit 2026-06-13 (extracted from the series lens).

Locks the behavior the lens AND the roadmap derivers now share: clean YAML parses; an unquoted scalar
carrying an inner ': ' is auto-repaired (the peer's file untouched) and flagged degraded; an unparseable tail
falls back to the safe prefix — never a crash, never a silent empty.
"""
from sovereign_agent.node_api.yaml_repair import load_roadmap, repair_unquoted_colons


def test_clean_yaml_parses_not_degraded():
    data, degraded, detail = load_roadmap("series:\n  - series_number: 1\n    titles: []\n")
    assert data["series"][0]["series_number"] == 1
    assert degraded is False and detail == ""


def test_unquoted_inner_colon_is_auto_repaired():
    # the the peer gotcha: an unquoted value carrying ': ' breaks strict YAML
    bad = 'series:\n  - series_number: 1\n    note: Published; KDP evidence: Live $19.99\n'
    data, degraded, detail = load_roadmap(bad)
    assert degraded is True and "Auto-repaired" in detail
    assert data["series"][0]["note"].startswith("Published; KDP evidence")


def test_unparseable_tail_falls_back_to_safe_prefix():
    txt = ("series:\n  - series_number: 1\n    titles: []\n"
           "peer_notes:\n  - [unclosed, flow, sequence\n")
    data, degraded, detail = load_roadmap(txt)
    assert degraded is True and "safe prefix" in detail
    assert data["series"][0]["series_number"] == 1


def test_legacy_gb_notes_tail_still_falls_back():
    # Back-compat: an older roadmap whose notes tail uses the legacy key is still recognized + truncated.
    txt = ("series:\n  - series_number: 1\n    titles: []\n"
           "gb_notes:\n  - [unclosed, flow, sequence\n")
    data, degraded, detail = load_roadmap(txt)
    assert degraded is True and "safe prefix" in detail
    assert data["series"][0]["series_number"] == 1


def test_repair_counts_only_offending_lines():
    _, n = repair_unquoted_colons("a: 1\nb: plain value\nc: has: inner colon\n")
    assert n == 1      # only line c needed quoting
