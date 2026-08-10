# -*- coding: utf-8 -*-
"""Proof-first tests for discourse.voice_governance (S13 Vol 3:
Governance, Risk Management & Human Primacy in Public Voice).

Kill-targets pinned:
- composes the sealed layers ONLY — the governance skin (S11 V4) + the sealed voice verify (S13 V1); NOT the
  sibling reach volume (V2);
- load_voice_constitution is the author's own content constitution (composes S11 V4); needs an author + a class;
- govern_expression routes a high-impact statement through the sealed human gate — refused without a human;
- reputation_from_receipts assembles the author's standing from VERIFIED voice receipts (composes verify_voice),
  never a platform score; an empty history has no standing;
- THE FENCE: no moderation authority owns the rules of the voice; the broadened attention-capture root fence
  holds; a moderation-authority / shadow-ban field is refused.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.economy.contribution import IncomeRefused
from sovereign_agent.risk.governance import GovernanceSkin
from sovereign_agent.discourse.sovereign_voice import publish_voice
from sovereign_agent.discourse.voice_governance import (
    load_voice_constitution, fork_voice_constitution, govern_expression, ReputationStanding,
    reputation_from_receipts, VOICE_GOV_BREACH_FIELDS, DiscourseRefused,
)

AUTHOR, NAME, AT, CONTENT = "kenn-voice", "Kenneth Mangum", "2026-08-10T09:00:00Z", "sha256:essay-1"
GATED = ["high_impact_claim", "retract_statement", "endorse_third_party"]


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path / "node"))


def _con():
    return load_voice_constitution(AUTHOR, gated_classes=GATED)


def test_load_voice_constitution_composes_the_sealed_skin():
    con = _con()
    assert isinstance(con, GovernanceSkin) and con.skin_id == "voice:kenn-voice"
    assert "high_impact_claim" in con.gated_classes
    with pytest.raises(DiscourseRefused):
        load_voice_constitution("", gated_classes=GATED)             # needs an author
    with pytest.raises(Exception):
        load_voice_constitution(AUTHOR, gated_classes=[])            # gates nothing governs nothing


def test_fork_voice_constitution_revises_the_rules():
    con = _con()
    forked = fork_voice_constitution(con, "v2", add_gated=["livestream"], remove_gated=["endorse_third_party"])
    assert forked.skin_id == "voice:kenn-voice:v2"
    assert "livestream" in forked.gated_classes and "endorse_third_party" not in forked.gated_classes
    assert "high_impact_claim" in forked.gated_classes               # preserved


def test_govern_expression_gates_a_high_impact_statement_through_a_human(tmp_path):
    reg = _reg(tmp_path); con = _con()
    with pytest.raises(IncomeRefused):                               # a gated statement refused without a human
        govern_expression(con, "high_impact_claim", AUTHOR, "stmt-1", gate=HumanApprovalGate(), at=AT,
                          author_name=NAME, source_ref="s", registry=reg)
    r = govern_expression(con, "high_impact_claim", AUTHOR, "stmt-1", gate=HumanApprovalGate(), at=AT,
                          author_name=NAME, source_ref="s", registry=reg, approver="km-1176", approval_ref="b:1")
    assert r["mandate"] == AUTHOR


def test_reputation_from_receipts_is_verified_voice_not_a_platform_score(tmp_path):
    reg = _reg(tmp_path)
    r1 = publish_voice(AUTHOR, CONTENT, "essay-1", author_name=NAME, source_ref="s", at=AT, registry=reg)
    r2 = publish_voice(AUTHOR, "sha256:essay-2", "essay-2", author_name=NAME, source_ref="s", at=AT, registry=reg)
    recs = [{"receipt": r1, "work_ref": "essay-1", "content_ref": CONTENT},
            {"receipt": r2, "work_ref": "essay-2", "content_ref": "sha256:essay-2"}]
    rep = reputation_from_receipts(AUTHOR, recs)
    assert isinstance(rep, ReputationStanding) and rep.standing == 2 and rep.total == 2 and rep.intact is True
    # a tampered content ref does not count toward standing
    bad = [{"receipt": r1, "work_ref": "essay-1", "content_ref": "sha256:forged"}]
    assert reputation_from_receipts(AUTHOR, bad).intact is False
    assert reputation_from_receipts(AUTHOR, []).standing == 0        # empty history, no standing


def test_the_fence_refuses_the_moderation_authority_that_owns_the_rules(tmp_path):
    reg = _reg(tmp_path); con = _con()
    for bad in ("moderation_authority", "content_authority", "censor_authority", "shadow_ban", "second_authority"):
        with pytest.raises(DiscourseRefused):
            govern_expression(con, "high_impact_claim", AUTHOR, "s", gate=HumanApprovalGate(), at=AT,
                              author_name=NAME, source_ref="s", registry=reg, approver="km-1176",
                              extra={bad: "acme-mod-co"})
    assert {"moderation_authority", "content_authority", "censor_authority"} <= VOICE_GOV_BREACH_FIELDS


def test_broadened_attention_capture_fence_holds_in_governance():
    con = _con()
    for bad in ("engagement_engine", "virality_score", "recommendation_feed"):
        with pytest.raises(DiscourseRefused):
            fork_voice_constitution(con, "v2", extra={bad: 1})


def test_composes_the_sealed_layers_only_not_the_sibling_volume():
    import sovereign_agent.discourse.voice_governance as m
    src = pathlib.Path(m.__file__).read_text()
    assert "sovereign_voice" in src and "risk.governance" in src     # S13 V1 + S11 V4
    assert "advanced_reach" not in src                               # NOT the not-yet-sealed sibling (V2)
