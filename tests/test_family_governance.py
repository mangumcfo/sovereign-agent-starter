# -*- coding: utf-8 -*-
"""Proof-first tests for estate.family_governance (S12 Vol 4:
Family Governance, Disputes & Dignity Preservation).

Kill-targets pinned:
- composes the sealed layers ONLY — the governance skin load/fork/enforce (Sovereign Risk & Mutual Protection
  Vol 4) + the sealed human gate (S5 Vol 16); re-implements none; rolls no crypto;
- load_family_constitution / fork_family_constitution are the family's own policy-as-code (compose S11 V4);
- govern_decision routes a gated family decision through the sealed human gate — refused without a named human;
- resolve_dispute is human-mediated on receipted evidence — refused without evidence, without a mediator, or
  if the constitution does not gate 'resolve_dispute' (no automated or delegated dispute resolution);
- dignified_exit records a fair share with NO penalty — a penalty/forfeiture/clawback field is refused;
- weakest_party_protected (LOUD): the least-powerful member is protected iff EVERY class that could override
  them is gated; any ungated class is surfaced by name;
- THE SUCCESSION-FENCE (sharpened): escrow / custodian / second-authority / arbitration-authority / dispute-
  custodian is refused; dignity fence refuses penalty/forfeiture/clawback; seal-key-closed refuses press/seal key.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.economy.contribution import IncomeRefused
from sovereign_agent.risk.governance import GovernanceSkin
from sovereign_agent.estate.generational_transfer import EstateRefused
from sovereign_agent.estate.family_governance import (
    load_family_constitution, fork_family_constitution, govern_decision, resolve_dispute, dignified_exit,
    WeakestPartyCheck, weakest_party_protected, FAMILY_GOVERNANCE_BREACH_FIELDS,
)

FAM, MEMBER, AUTHOR, AT = "ridgeline", "ridgeline-heir", "Kenneth Mangum", "2026-08-10T09:00:00Z"
GATED = ["amend_constitution", "remove_member", "distribute_estate", "resolve_dispute", "dignified_exit"]


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path / "node"))


def _con():
    return load_family_constitution(FAM, gated_decisions=GATED)


def test_load_family_constitution_composes_the_sealed_skin():
    con = _con()
    assert isinstance(con, GovernanceSkin) and con.skin_id == "family:ridgeline"
    assert "resolve_dispute" in con.gated_classes and "remove_member" in con.gated_classes
    with pytest.raises(EstateRefused):
        load_family_constitution("", gated_decisions=GATED)          # needs a family id
    with pytest.raises(Exception):
        load_family_constitution(FAM, gated_decisions=[])            # gates nothing governs nothing


def test_fork_family_constitution_forks_for_the_next_generation():
    con = _con()
    forked = fork_family_constitution(con, "g2", add_gated=["appoint_steward"], remove_gated=["distribute_estate"])
    assert forked.skin_id == "family:ridgeline:g2"
    assert "appoint_steward" in forked.gated_classes
    assert "distribute_estate" not in forked.gated_classes
    assert "remove_member" in forked.gated_classes                   # preserved


def test_govern_decision_gates_a_family_decision_through_a_human(tmp_path):
    reg = _reg(tmp_path); con = _con()
    with pytest.raises(IncomeRefused):                               # a gated decision is refused without a human
        govern_decision(con, "remove_member", MEMBER, "d1", gate=HumanApprovalGate(), at=AT, author=AUTHOR,
                        source_ref="s", registry=reg)
    r = govern_decision(con, "remove_member", MEMBER, "d1", gate=HumanApprovalGate(), at=AT, author=AUTHOR,
                        source_ref="s", registry=reg, approver="km-1176", approval_ref="breath:1")
    assert r["mandate"] == MEMBER


def test_resolve_dispute_is_human_mediated_on_receipted_evidence(tmp_path):
    reg = _reg(tmp_path); con = _con()
    r = resolve_dispute(con, "dispute-7", MEMBER, "r1", evidence=["receipt:aa", "receipt:bb"],
                        gate=HumanApprovalGate(), at=AT, author=AUTHOR, source_ref="s", registry=reg,
                        mediator="km-1176", approval_ref="breath:1")
    assert r["mandate"] == MEMBER
    with pytest.raises(EstateRefused):                               # no evidence -> refused
        resolve_dispute(con, "d", MEMBER, "r2", evidence=[], gate=HumanApprovalGate(), at=AT, author=AUTHOR,
                        source_ref="s", registry=reg, mediator="km-1176", approval_ref="b")
    with pytest.raises(IncomeRefused):                               # no mediator -> refused (human-gated)
        resolve_dispute(con, "d", MEMBER, "r3", evidence=["receipt:aa"], gate=HumanApprovalGate(), at=AT,
                        author=AUTHOR, source_ref="s", registry=reg)
    # a constitution that does not gate resolve_dispute has no dispute resolution
    ungated = load_family_constitution(FAM, gated_decisions=["amend_constitution"])
    with pytest.raises(EstateRefused):
        resolve_dispute(ungated, "d", MEMBER, "r4", evidence=["receipt:aa"], gate=HumanApprovalGate(), at=AT,
                        author=AUTHOR, source_ref="s", registry=reg, mediator="km-1176")


def test_dignified_exit_keeps_a_fair_share_and_refuses_a_penalty(tmp_path):
    reg = _reg(tmp_path); con = _con()
    r = dignified_exit(con, MEMBER, "share:one-fourth", "x1", gate=HumanApprovalGate(), at=AT, author=AUTHOR,
                       source_ref="s", registry=reg, approver="km-1176", approval_ref="breath:1")
    assert r["mandate"] == MEMBER
    with pytest.raises(EstateRefused):                               # no share named -> refused
        dignified_exit(con, MEMBER, "", "x2", gate=HumanApprovalGate(), at=AT, author=AUTHOR, source_ref="s",
                       registry=reg, approver="km-1176")
    for bad in ("penalty", "forfeiture", "clawback", "exit_penalty"):
        with pytest.raises(EstateRefused):                          # dignity: no penalty for leaving
            dignified_exit(con, MEMBER, "share:one-fourth", "x3", gate=HumanApprovalGate(), at=AT, author=AUTHOR,
                           source_ref="s", registry=reg, approver="km-1176", extra={bad: "10pct"})


def test_weakest_party_protected_is_true_only_when_every_overriding_class_is_gated():
    con = _con()
    ok = weakest_party_protected(con, ["remove_member", "distribute_estate"])
    assert isinstance(ok, WeakestPartyCheck) and ok.protected is True and ok.ungated == ()
    bad = weakest_party_protected(con, ["remove_member", "seize_share", "override_vote"])
    assert bad.protected is False and set(bad.ungated) == {"seize_share", "override_vote"}
    assert "exposed" in bad.reason                                  # the gap is surfaced by name, not hidden


def test_the_succession_fence_refuses_second_authority_and_arbitration(tmp_path):
    reg = _reg(tmp_path); con = _con()
    for bad in ("escrow", "custodian", "second_authority", "succession_authority", "arbitration_authority",
                "dispute_custodian", "recovery_engine"):
        with pytest.raises(EstateRefused):
            govern_decision(con, "remove_member", MEMBER, "d", gate=HumanApprovalGate(), at=AT, author=AUTHOR,
                            source_ref="s", registry=reg, approver="km-1176", extra={bad: "acme-family-office"})
    assert {"arbitration_authority", "dispute_custodian", "second_authority"} <= FAMILY_GOVERNANCE_BREACH_FIELDS


def test_seal_key_closed_a_press_or_seal_key_field_is_refused(tmp_path):
    con = _con()
    for bad in ("seal_key", "press_key", "sealing_key"):
        with pytest.raises(EstateRefused):
            fork_family_constitution(con, "g2", extra={bad: "x"})
    assert {"seal_key", "press_key", "sealing_key"} <= FAMILY_GOVERNANCE_BREACH_FIELDS


def test_composes_the_sealed_layers_only():
    import sovereign_agent.estate.family_governance as m
    src = pathlib.Path(m.__file__).read_text()
    assert "risk.governance" in src and "generational_transfer" in src   # S11 V4 + S12 V1
    assert "key_succession" not in src and "venture_continuity" not in src  # not the sibling modules' engines
