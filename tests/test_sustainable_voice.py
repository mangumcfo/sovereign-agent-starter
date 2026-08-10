# -*- coding: utf-8 -*-
"""Proof-first tests for discourse.sustainable_voice (S13 Vol 4:
Sustainable Voice & Long-Term Strategy).

Kill-targets pinned:
- composes the sealed Sovereign Discourse volumes ONLY (V1 verify_voice · V2 multi_platform_reach · V3
  reputation/govern_expression); re-implements none; rolls no crypto;
- assemble_voice_system verifies the author's whole body of owned voice (composes verify_voice) — self-
  sustaining iff every part verifies; an empty body is no system;
- responsible_growth extends reach only AFTER a human-gated growth decision (composes govern_expression + then
  multi_platform_reach) — refused without a named human;
- voice_as_asset makes the voice a compounding, inheritable asset (composes reputation_from_receipts) —
  weakest-party: a creator reads one honest indicator (endures) that their voice is theirs and will pass on;
- THE FENCE (broadened + compound): a feed_optimizer / growth_engine / vanity_ranker (carrier root + optimize
  root) is refused under any token; a reach-rental / audience-lease field is refused.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.economy.contribution import IncomeRefused
from sovereign_agent.discourse.sovereign_voice import publish_voice
from sovereign_agent.discourse.voice_governance import load_voice_constitution
from sovereign_agent.discourse.sustainable_voice import (
    assemble_voice_system, VoiceSystem, responsible_growth, voice_as_asset, VoiceAsset,
    SUSTAINABLE_BREACH_FIELDS, DiscourseRefused,
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


def test_assemble_voice_system_verifies_the_whole_body(tmp_path):
    reg = _reg(tmp_path)
    sysrec = assemble_voice_system(AUTHOR, _records(reg))
    assert isinstance(sysrec, VoiceSystem) and sysrec.self_sustaining is True and sysrec.verified == 3
    # a tampered content ref breaks self-sustaining
    recs = _records(reg); recs[0] = {**recs[0], "content_ref": "sha256:forged"}
    assert assemble_voice_system(AUTHOR, recs).self_sustaining is False
    assert assemble_voice_system(AUTHOR, []).self_sustaining is False       # empty body, no system


def test_responsible_growth_is_human_gated(tmp_path):
    reg = _reg(tmp_path)
    recs = _records(reg, 1)
    con = load_voice_constitution(AUTHOR, gated_classes=["grow_reach"])
    with pytest.raises(IncomeRefused):                                      # a gated growth decision needs a human
        responsible_growth(recs[0]["receipt"], ["alpha", "beta"], recs[0]["content_ref"], con, "grow_reach",
                           AUTHOR, "g1", gate=HumanApprovalGate(), at=AT, author_name=NAME, source_ref="s",
                           registry=reg)
    r = responsible_growth(recs[0]["receipt"], ["alpha", "beta"], recs[0]["content_ref"], con, "grow_reach",
                           AUTHOR, "g1", gate=HumanApprovalGate(), at=AT, author_name=NAME, source_ref="s",
                           registry=reg, approver="km-1176", approval_ref="b:1")
    assert r["mandate"] == AUTHOR                                           # growth is a human-gated act


def test_voice_as_asset_is_verified_inheritable_voice(tmp_path):
    reg = _reg(tmp_path)
    asset = voice_as_asset(AUTHOR, _records(reg))
    assert isinstance(asset, VoiceAsset) and asset.endures is True and asset.inheritable is True and asset.value == 3
    assert "mine to hand on" in asset.reason                               # weakest-party indicator
    # a tampered record means the asset does not fully endure
    recs = _records(reg); recs[0] = {**recs[0], "content_ref": "sha256:forged"}
    assert voice_as_asset(AUTHOR, recs).endures is False
    assert voice_as_asset(AUTHOR, []).value == 0                           # empty body, no asset


def test_the_compound_fence_refuses_the_feed_optimizer_family_and_reach_rental(tmp_path):
    reg = _reg(tmp_path)
    for bad in ("feed_optimizer", "feed_ranker", "growth_engine", "vanity_maximizer", "audience_ranker"):
        with pytest.raises(DiscourseRefused):
            assemble_voice_system(AUTHOR, [{"receipt": {}, "work_ref": "w", "content_ref": "c", bad: 1}])
    for bad in ("reach_rental", "audience_lease", "sustainability_authority"):
        with pytest.raises(DiscourseRefused):
            assemble_voice_system(AUTHOR, _records(reg), extra={bad: "acme"})
    assert {"growth_engine", "reach_rental", "audience_lease"} <= SUSTAINABLE_BREACH_FIELDS


def test_composes_the_sealed_v1_v3_only():
    import sovereign_agent.discourse.sustainable_voice as m
    src = pathlib.Path(m.__file__).read_text()
    for sealed in ("sovereign_voice", "advanced_reach", "voice_governance"):
        assert sealed in src                                               # composes sealed S13 V1-V3
