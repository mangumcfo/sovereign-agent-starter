# -*- coding: utf-8 -*-
"""Proof-first tests for discourse.sovereign_voice (S13 Vol 1, the OPENER:
Owning Your Voice, Audience & Attention).

Kill-targets pinned:
- composes the sealed governed-record surface ONLY (S10 V1 / Object Model S5 V5); re-implements none; rolls no
  crypto;
- publish_voice records an idea as a signed, content-addressed governed object the author owns; verify_voice is
  the weakest-party check (an author with no platform verifies their idea is theirs from the receipt);
- syndicate distributes to a platform WITHOUT transferring ownership (the platform carries the artifact, not the
  ownership; an ownership-transfer field is refused);
- record_subscription is a direct receipted audience relationship; sever_subscription is by the subscriber's
  consent ONLY (a platform cannot sever it — that is what makes the audience uncapturable);
- meaning_rank ranks by the author's OWN declared meaning, never an engagement engine — an item/extra carrying
  an engagement/recommendation/virality field is refused (the attention-capture engine is the breach → the
  kill-target);
- THE S13 FENCE: no second discourse authority · no attention-capture engine · no ownership transfer to a
  platform · money-path OFF · seal-key-closed.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.discourse.sovereign_voice import (
    publish_voice, verify_voice, Syndication, syndicate, record_subscription, sever_subscription, meaning_rank,
    DISCOURSE_BREACH_FIELDS, DiscourseRefused,
)

AUTHOR, NAME, AT = "kenn-voice", "Kenneth Mangum", "2026-08-10T09:00:00Z"
CONTENT = "sha256:essay-on-sovereignty"


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path / "node"))


def test_publish_voice_records_a_signed_content_addressed_object(tmp_path):
    reg = _reg(tmp_path)
    rcpt = publish_voice(AUTHOR, CONTENT, "essay-1", author_name=NAME, source_ref="s", at=AT, registry=reg)
    assert rcpt["mandate"] == AUTHOR
    # weakest-party: the author verifies the idea is theirs from the receipt, no platform
    assert verify_voice(rcpt, AUTHOR, "essay-1", content_ref=CONTENT) is True
    with pytest.raises(DiscourseRefused):
        publish_voice(AUTHOR, "", "e", author_name=NAME, source_ref="s", at=AT, registry=reg)   # needs content addr


def test_verify_voice_fails_on_a_tampered_content_address(tmp_path):
    reg = _reg(tmp_path)
    rcpt = publish_voice(AUTHOR, CONTENT, "essay-1", author_name=NAME, source_ref="s", at=AT, registry=reg)
    assert verify_voice(rcpt, AUTHOR, "essay-1", content_ref="sha256:forged") is False
    assert verify_voice(rcpt, "stranger", "essay-1", content_ref=CONTENT) is False


def test_syndicate_carries_the_artifact_not_the_ownership(tmp_path):
    reg = _reg(tmp_path)
    rcpt = publish_voice(AUTHOR, CONTENT, "essay-1", author_name=NAME, source_ref="s", at=AT, registry=reg)
    syn = syndicate(rcpt, "bigplatform", CONTENT)
    assert isinstance(syn, Syndication) and syn.platform == "bigplatform"
    assert syn.ownership_retained is True and syn.author == AUTHOR    # author keeps ownership + proof
    for bad in ("ownership_transfer", "platform_ownership", "rent_audience"):
        with pytest.raises(DiscourseRefused):
            syndicate(rcpt, "bigplatform", CONTENT, extra={bad: "yes"})


def test_record_subscription_is_a_direct_receipted_relationship(tmp_path):
    reg = _reg(tmp_path)
    rcpt = record_subscription(AUTHOR, "reader-mara", "sub-1", author_name=NAME, source_ref="s", at=AT,
                               registry=reg)
    assert rcpt["mandate"] == AUTHOR
    with pytest.raises(DiscourseRefused):
        record_subscription(AUTHOR, "", "sub-2", author_name=NAME, source_ref="s", at=AT, registry=reg)


def test_sever_subscription_is_by_the_subscribers_consent_only():
    assert sever_subscription("reader-mara", "reader-mara") is True         # the subscriber ends it
    assert sever_subscription("reader-mara", "kenn-voice", consent=True) is True  # explicit consent
    with pytest.raises(DiscourseRefused):                                   # a platform cannot sever it
        sever_subscription("reader-mara", "bigplatform")


def test_meaning_rank_ranks_by_the_authors_own_meaning_not_engagement():
    items = [{"id": "a", "meaning": 0.3}, {"id": "b", "meaning": 0.9}, {"id": "c", "meaning": 0.6}]
    ranked = meaning_rank(items, meaning_key="meaning")
    assert [it["id"] for it in ranked] == ["b", "c", "a"]                   # author's declared meaning, desc
    with pytest.raises(DiscourseRefused):                                   # an item missing the meaning value
        meaning_rank([{"id": "x"}], meaning_key="meaning")


def test_no_attention_capture_engine_is_refused_in_code():
    # THE kill-target: content is NEVER ranked by an engagement/recommendation/virality engine.
    for bad in ("engagement_engine", "recommendation_engine", "ranking_engine", "engagement_score",
                "virality_engine", "outrage_optimizer", "addiction_loop"):
        with pytest.raises(DiscourseRefused):
            meaning_rank([{"id": "a", "meaning": 0.5, bad: 99}], meaning_key="meaning")
        with pytest.raises(DiscourseRefused):
            meaning_rank([{"id": "a", "meaning": 0.5}], meaning_key="meaning", extra={bad: 99})
    assert {"engagement_engine", "recommendation_engine", "virality_engine"} <= DISCOURSE_BREACH_FIELDS


def test_the_fence_refuses_second_authority_ownership_transfer_and_seal_key(tmp_path):
    reg = _reg(tmp_path)
    for bad in ("second_authority", "discourse_authority", "ownership_transfer", "held_value", "custody"):
        with pytest.raises(DiscourseRefused):
            publish_voice(AUTHOR, CONTENT, "e", author_name=NAME, source_ref="s", at=AT, registry=reg,
                          extra={bad: "acme-platform"})
    for bad in ("seal_key", "press_key", "sealing_key"):
        with pytest.raises(DiscourseRefused):
            publish_voice(AUTHOR, CONTENT, "e", author_name=NAME, source_ref="s", at=AT, registry=reg,
                          extra={bad: "x"})
    assert {"second_authority", "ownership_transfer", "held_value"} <= DISCOURSE_BREACH_FIELDS


def test_broadened_attention_capture_fence_refuses_novel_variant_names():
    # S13 Wave A fence-breadth: a synthetic in-node engine cannot evade the fence by renaming its field.
    from sovereign_agent.discourse.sovereign_voice import ATTENTION_CAPTURE_ROOTS
    for bad in ("engagement_ranker", "virality_score", "recommendation_feed", "attention_farming",
                "doomscroll_loop", "rage_bait_score", "watch_time_optimizer", "algo_feed_ranker"):
        with pytest.raises(DiscourseRefused):
            meaning_rank([{"id": "a", "meaning": 0.5, bad: 1}], meaning_key="meaning")
    assert {"engagement", "virality", "recommendation", "doomscroll"} <= ATTENTION_CAPTURE_ROOTS


def test_compound_root_fence_refuses_the_feed_optimizer_family():
    # S13 V04 compound-root patch: a carrier root (feed/growth/vanity/follower) + an optimize root, under any token.
    for bad in ("feed_optimizer", "feed_ranker", "feed_boost", "growth_engine", "vanity_ranker",
                "follower_farm", "audience_maximizer", "feed_algorithm"):
        with pytest.raises(DiscourseRefused):
            meaning_rank([{"id": "a", "meaning": 0.5, bad: 1}], meaning_key="meaning")
    # legitimate carrier-only fields (no optimize root) are NOT compound-caught
    ok = meaning_rank([{"id": "a", "meaning": 0.7}, {"id": "b", "meaning": 0.9, "audience_note": "x"}],
                      meaning_key="meaning")
    assert [it["id"] for it in ok] == ["b", "a"]


def test_composes_the_sealed_governed_record_surface_only():
    import sovereign_agent.discourse.sovereign_voice as m
    src = pathlib.Path(m.__file__).read_text()
    assert "economy.contribution" in src                                   # composes S10 V1 / Object Model S5 V5
    assert "record_contribution" in src and "verify_contribution" in src
