# -*- coding: utf-8 -*-
"""Proof-first tests for peerhood.delegation (S14 Vol 3:
Delegation & Sponsorship Without Capture).

Kill-targets pinned:
- composes sealed floors + genesis ONLY (S14 V1 genesis · D1 keystore · S5 V16 gate + S5 V28 mandate · S6 V5
  declare_trust_anchor · S12 V1 open_key_epoch/family_quorum_recovery); invents no mechanism; rolls no crypto;
- delegate_governed is TIME-BOUND (no expiry refused), HUMAN-GATED (no approver refused), signed with the peer's
  own key; verify_delegation is public-only;
- join_mutual_protection has NO central insurer, signed with the key, portable;
- sponsor_without_claim keeps the S6 V5 boundary intact and the exit open — no lasting claim;
- mandate_and_quorum keeps control with the peer (owner's mandate + family quorum, S12 V1) — no external authority;
- revoke_delegation is a first-class SIGNED act that leaves NO residual claim;
- KILL-TARGET: a sponsor-authority / leverage / permanent-claim / central-insurer / scored-credit / escrow /
  custodian field is refused (DELEGATION_BREACH_FIELDS).
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.peerhood.genesis import establish_self_held_identity, PeerhoodError
from sovereign_agent.peerhood.delegation import (
    delegate_governed, verify_delegation, join_mutual_protection, sponsor_without_claim,
    mandate_and_quorum, revoke_delegation, DELEGATION_BREACH_FIELDS,
)

AT, EXP = "2026-08-11T16:00:00Z", "2026-12-31T00:00:00Z"


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path / "node"))


def test_delegate_governed_is_time_bound_human_gated_and_signed(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    ident = establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    with pytest.raises(PeerhoodError):                                            # human-gated — no approver refused
        delegate_governed(ks, "peer-a", "agent-b", "sign_x", expires_at=EXP, at=AT, registry=reg,
                          approver="", approval_ref="b:1")
    with pytest.raises(PeerhoodError):                                            # time-bound — no expiry refused
        delegate_governed(ks, "peer-a", "agent-b", "sign_x", expires_at="", at=AT, registry=reg,
                          approver="km-1176", approval_ref="b:1")
    d = delegate_governed(ks, "peer-a", "agent-b", "sign_x", expires_at=EXP, at=AT, registry=reg,
                          approver="km-1176", approval_ref="b:1")
    assert d["time_bound"] is True and d["revocable"] is True and d["signature"]
    assert verify_delegation(d, ident) is True                                    # public-only verify against own key


def test_join_mutual_protection_has_no_central_insurer(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    j = join_mutual_protection(ks, "peer-a", "pool-1", at=AT, registry=reg)
    assert j["central_insurer"] is None and j["portable"] is True and j["signature"]
    with pytest.raises(PeerhoodError):
        join_mutual_protection(ks, "peer-a", "pool-1", at=AT, registry=reg, extra={"insurer": "acme-ins"})


def test_sponsor_without_claim_keeps_the_boundary_and_exit(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    h = sponsor_without_claim(ks, "peer-a", "helper-x", "grant-1", at=AT, registry=reg)
    assert h["lasting_claim"] is None and h["exit_open"] is True and h["boundary"] and h["signature"]
    with pytest.raises(PeerhoodError):
        sponsor_without_claim(ks, "peer-a", "helper-x", "grant-1", at=AT, registry=reg,
                              extra={"permanent_claim": "yes"})


def test_mandate_and_quorum_keeps_control_with_the_peer(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    a = establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    kin = establish_self_held_identity(ks, "peer-kin", at=AT, registry=reg)
    mq = mandate_and_quorum(a, [kin.fingerprint], epoch=1, quorum=2)
    assert mq["under_peer_control"] is True and mq["external_authority"] is None
    assert a.fingerprint in mq["epoch"].keyholders                                # the peer's OWN fingerprint governs
    with pytest.raises(PeerhoodError):
        mandate_and_quorum(a, [kin.fingerprint], extra={"custodian": "acme"})


def test_revoke_delegation_is_first_class_no_residual_claim(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    r = revoke_delegation(ks, "peer-a", "delegation:peer-a:agent-b", at=AT, registry=reg)
    assert r["residual_claim"] is None and r["returned_to_peer"] is True and r["signature"]
    with pytest.raises(PeerhoodError):
        revoke_delegation(str(tmp_path / "empty"), "ghost", "d:1", at=AT, registry=reg)


def test_the_fence_refuses_leverage_insurer_and_scored_credit(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    for bad in ("leverage", "permanent_claim", "central_insurer", "scored_credit", "escrow", "custodian"):
        with pytest.raises(PeerhoodError):
            delegate_governed(ks, "peer-a", "agent-b", "x", expires_at=EXP, at=AT, registry=reg,
                              approver="km-1176", approval_ref="b:1", extra={bad: "acme"})
    assert {"leverage", "central_insurer", "scored_credit", "custodian"} <= DELEGATION_BREACH_FIELDS


def test_composes_sealed_floors_and_genesis():
    import sovereign_agent.peerhood.delegation as m
    src = pathlib.Path(m.__file__).read_text()
    for sealed in ("genesis", "keystore", "trust.boundaries", "estate.generational_transfer"):
        assert sealed in src                                                      # composes genesis + D1 + S6 V5 + S12 V1
    # ORTHOGONAL to the sibling V02 — delegation does NOT compose recognition (wave_dep width-2)
    assert "recognition" not in src
