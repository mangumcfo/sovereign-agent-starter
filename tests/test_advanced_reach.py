# -*- coding: utf-8 -*-
"""Proof-first tests for discourse.advanced_reach (S13 Vol 2:
Advanced Reach, Discovery & Platform Independence).

Kill-targets pinned:
- composes the sealed opener ONLY (S13 V1: syndicate, meaning_rank); NOT the sibling governance volume (V3);
- discover_across_sources merges the author's own sources and meaning-ranks the whole set (composes meaning_rank);
- multi_platform_reach syndicates to MANY platforms at once with ownership retained on every surface;
- bridge_adapter translates + carries the artifact but retains ownership (deep transport homes OUT to S6/S7);
- THE BROADENED S13 FENCE: no reach/second authority owns the audience; the attention-capture root fence refuses
  any amplification/engagement engine field under a novel name; an ownership-transfer field is refused.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.discourse.sovereign_voice import publish_voice
from sovereign_agent.discourse.advanced_reach import (
    discover_across_sources, multi_platform_reach, bridge_adapter, PlatformBridge, REACH_BREACH_FIELDS,
    DiscourseRefused,
)

AUTHOR, NAME, AT, CONTENT = "kenn-voice", "Kenneth Mangum", "2026-08-10T09:00:00Z", "sha256:essay-1"


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path / "node"))


def _receipt(reg):
    return publish_voice(AUTHOR, CONTENT, "essay-1", author_name=NAME, source_ref="s", at=AT, registry=reg)


def test_discover_across_sources_meaning_ranks_the_whole_federation():
    src_a = [{"id": "a", "meaning": 0.3}, {"id": "b", "meaning": 0.9}]
    src_b = [{"id": "c", "meaning": 0.6}]
    ranked = discover_across_sources([src_a, src_b], meaning_key="meaning")
    assert [it["id"] for it in ranked] == ["b", "c", "a"]            # merged + meaning-ranked (composes V1)
    with pytest.raises(DiscourseRefused):                            # broadened fence over items
        discover_across_sources([[{"id": "x", "meaning": 0.5, "engagement_ranker": 9}]], meaning_key="meaning")


def test_multi_platform_reach_syndicates_with_ownership_retained(tmp_path):
    reg = _reg(tmp_path)
    syns = multi_platform_reach(_receipt(reg), ["alpha", "beta", "alpha"], CONTENT)
    assert len(syns) == 2 and {s.platform for s in syns} == {"alpha", "beta"}   # dedup
    assert all(s.ownership_retained and s.author == AUTHOR for s in syns)
    with pytest.raises(DiscourseRefused):
        multi_platform_reach(_receipt(reg), [], CONTENT)             # needs a platform
    with pytest.raises(DiscourseRefused):
        multi_platform_reach(_receipt(reg), ["alpha"], CONTENT, extra={"ownership_transfer": 1})


def test_bridge_adapter_translates_and_retains_ownership(tmp_path):
    reg = _reg(tmp_path)
    br = bridge_adapter(_receipt(reg), "bigplatform", CONTENT, fmt="amp-html")
    assert isinstance(br, PlatformBridge) and br.ownership_retained is True and br.fmt == "amp-html"
    with pytest.raises(DiscourseRefused):
        bridge_adapter(_receipt(reg), "bigplatform", CONTENT, fmt="")   # needs a format
    with pytest.raises(DiscourseRefused):
        bridge_adapter(_receipt(reg), "bigplatform", CONTENT, extra={"platform_ownership": 1})


def test_the_reach_fence_refuses_the_reach_algorithm_that_owns_the_audience(tmp_path):
    reg = _reg(tmp_path)
    for bad in ("reach_authority", "audience_owner", "amplification_engine", "feed_authority",
                "distribution_authority"):
        with pytest.raises(DiscourseRefused):
            multi_platform_reach(_receipt(reg), ["alpha"], CONTENT, extra={bad: "acme-feed"})
    assert {"reach_authority", "audience_owner", "amplification_engine"} <= REACH_BREACH_FIELDS


def test_broadened_attention_capture_fence_refuses_novel_reach_engines(tmp_path):
    reg = _reg(tmp_path)
    for bad in ("virality_optimizer", "watch_time_ranker", "recommendation_feed", "rage_bait_amplifier"):
        with pytest.raises(DiscourseRefused):
            multi_platform_reach(_receipt(reg), ["alpha"], CONTENT, extra={bad: 1})


def test_composes_the_sealed_opener_only_not_the_sibling_volume():
    import sovereign_agent.discourse.advanced_reach as m
    src = pathlib.Path(m.__file__).read_text()
    assert "sovereign_voice" in src                                  # composes the sealed opener (S13 V1)
    assert "voice_governance" not in src                             # NOT the not-yet-sealed sibling (V3)
