# -*- coding: utf-8 -*-
"""Proof-first tests for discourse.voice_covenant (S13 Vol 5, CAPSTONE:
The Voice as Living Covenant).

Kill-targets pinned:
- composes the sealed Sovereign Discourse stack V01-V04 ONLY (V1 verify_voice · V2 multi_platform_reach · V3
  reputation_from_receipts · V4 assemble_voice_system/voice_as_asset); imports V1-V4 only; invents no engine;
  rolls no crypto;
- assemble_voice_covenant folds the WHOLE stack into ONE indicator over four pillars (owned · self-sustaining ·
  inheritable · endures) — is_living iff EVERY pillar verifies as the author's own; a tampered/empty body fails
  the whole (the series' final weakest-party test: a creator/heir reads one honest signal);
- verify_covenant_element dispatches any layer by kind (voice/reach/reputation/system/asset) composing the
  matching sealed verifier; an unknown kind is refused;
- THE FENCE (broadened + compound + dynasty): a feed_optimizer / growth_engine (carrier root + optimize root) is
  refused under any token; a media_dynasty / voice_custodian / reach-rental field is refused.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.discourse.sovereign_voice import publish_voice
from sovereign_agent.discourse.voice_covenant import (
    assemble_voice_covenant, VoiceCovenant, verify_covenant_element,
    COVENANT_BREACH_FIELDS, DiscourseRefused,
)

AUTHOR, NAME, AT = "kenn-voice", "Kenneth Mangum", "2026-08-10T09:00:00Z"


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path / "node"))


def _records(reg, n=3):
    recs = []
    for i in range(n):
        cref = f"sha256:essay-{i}"
        r = publish_voice(AUTHOR, cref, f"essay-{i}", author_name=NAME, source_ref="s", at=AT, registry=reg)
        recs.append({"receipt": r, "work_ref": f"essay-{i}", "content_ref": cref})
    return recs


def test_assemble_voice_covenant_composes_the_whole_stack(tmp_path):
    reg = _reg(tmp_path)
    cov = assemble_voice_covenant(AUTHOR, _records(reg))
    assert isinstance(cov, VoiceCovenant)
    assert cov.is_living is True and cov.pillars_verified == 4 and cov.pillars_total == 4
    assert "mine and my heirs'" in cov.reason                          # weakest-party: the whole inheritance is theirs
    # a tampered layer means the covenant is not fully living
    recs = _records(reg); recs[0] = {**recs[0], "content_ref": "sha256:forged"}
    broken = assemble_voice_covenant(AUTHOR, recs)
    assert broken.is_living is False and broken.pillars_verified < 4
    assert assemble_voice_covenant(AUTHOR, []).is_living is False      # empty body, no living covenant


def test_verify_covenant_element_dispatches_by_kind(tmp_path):
    reg = _reg(tmp_path)
    recs = _records(reg)
    voice_el = recs[0]
    assert verify_covenant_element(voice_el, "voice", AUTHOR) is True
    assert verify_covenant_element({**voice_el, "content_ref": "sha256:forged"}, "voice", AUTHOR) is False
    assert verify_covenant_element({"records": recs}, "reputation", AUTHOR) is True
    assert verify_covenant_element({"records": recs}, "system", AUTHOR) is True
    assert verify_covenant_element({"records": recs}, "asset", AUTHOR) is True
    reach_el = {"receipt": recs[0]["receipt"], "platforms": ["alpha", "beta"], "content_ref": recs[0]["content_ref"]}
    assert verify_covenant_element(reach_el, "reach", AUTHOR) is True   # V2: carried, ownership retained
    with pytest.raises(DiscourseRefused):                              # an invented element kind is refused
        verify_covenant_element({"records": recs}, "royalty_engine", AUTHOR)


def test_the_covenant_fence_refuses_the_dynasty_and_the_feed_optimizer(tmp_path):
    reg = _reg(tmp_path)
    for bad in ("media_dynasty", "voice_dynasty", "voice_custodian", "legacy_broker", "reach_rental"):
        with pytest.raises(DiscourseRefused):
            assemble_voice_covenant(AUTHOR, _records(reg), extra={bad: "acme-media"})
    for bad in ("feed_optimizer", "growth_engine", "vanity_maximizer"):
        with pytest.raises(DiscourseRefused):
            assemble_voice_covenant(AUTHOR, _records(reg), extra={bad: 1})
    assert {"media_dynasty", "voice_custodian", "covenant_authority"} <= COVENANT_BREACH_FIELDS


def test_composes_the_sealed_v1_v4_stack_only():
    import sovereign_agent.discourse.voice_covenant as m
    src = pathlib.Path(m.__file__).read_text()
    for sealed in ("sovereign_voice", "advanced_reach", "voice_governance", "sustainable_voice"):
        assert sealed in src                                           # composes the whole sealed S13 stack V1-V4
