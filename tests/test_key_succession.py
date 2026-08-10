# -*- coding: utf-8 -*-
"""Proof-first tests for estate.key_succession (S12 Vol 2:
Advanced Key Management, Recovery & Secure Succession).

Kill-targets pinned:
- composes the sealed key primitives of the OPENER ONLY (S12 V1: open_key_epoch / KeyEpoch /
  family_quorum_recovery / breath_gated_key_transfer); re-implements none; rolls no crypto; stores no key
  material; composes NOT the sibling venture volume (V3, not-yet-sealed);
- rotate_key_epoch opens the family's NEXT epoch (versioned rotation) over the family's own keyholders;
- define_quorum refuses a threshold below two (a single approver is a custodian) and one above the keyholder
  count (unrecoverable); recover_with_quorum recovers iff M-of-N and refuses a foreign family's policy;
- secure_key_handoff is receipted + human-gated and refuses a handoff from a non-keyholder;
- simulate_succession is a dry-run that moves NO key and reports whether the remaining quorum still recovers;
- SEAL-KEY-CLOSED (the sharpest test): a press/seal key field is refused; a custodial-recovery / key-escrow /
  recovery-engine / stored-key-material field is refused in code (the synthetic custodial-recovery trip).
"""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.economy.contribution import IncomeRefused
from sovereign_agent.estate.generational_transfer import open_key_epoch, family_quorum_recovery, EstateRefused
from sovereign_agent.estate.key_succession import (
    rotate_key_epoch, QuorumPolicy, define_quorum, recover_with_quorum, secure_key_handoff, SuccessionDrill,
    simulate_succession, KEY_SUCCESSION_BREACH_FIELDS,
)

FAM, AUTHOR, AT = "ridgeline", "Kenneth Mangum", "2026-08-10T09:00:00Z"
HOLDERS = ("kenn", "mara", "iris", "dev")


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path / "node"))


def _epoch():
    return open_key_epoch(FAM, 1, HOLDERS)


def test_rotate_key_epoch_opens_the_next_family_epoch():
    e1 = _epoch()
    e2 = rotate_key_epoch(e1, ("kenn", "mara", "iris", "dev", "sol"))
    assert e2.family_id == FAM and e2.epoch == 2               # versioned rotation, same family
    assert "sol" in e2.keyholders and set(e1.keyholders) <= set(e2.keyholders)


def test_define_quorum_refuses_a_single_custodian_and_an_unreachable_threshold():
    e = _epoch()
    pol = define_quorum(e, threshold=3)
    assert isinstance(pol, QuorumPolicy) and pol.threshold == 3 and pol.family_id == FAM
    with pytest.raises(EstateRefused):
        define_quorum(e, threshold=1)                          # a single approver is a custodian
    with pytest.raises(EstateRefused):
        define_quorum(e, threshold=len(HOLDERS) + 1)           # can never be met


def test_recover_with_quorum_recovers_only_at_the_family_threshold():
    e = _epoch()
    pol = define_quorum(e, threshold=3)
    assert recover_with_quorum(e, ("kenn", "mara", "iris"), pol) is True      # M-of-N met
    assert recover_with_quorum(e, ("kenn", "mara"), pol) is False             # short of quorum
    assert recover_with_quorum(e, ("kenn", "stranger", "ghost"), pol) is False  # non-keyholders don't count
    # it composes the sealed family_quorum_recovery (same verdict at the threshold)
    assert family_quorum_recovery(e, ("kenn", "mara", "iris"), quorum=3) is True


def test_recover_refuses_a_foreign_familys_policy():
    e = _epoch()
    other = QuorumPolicy(family_id="not-ridgeline", threshold=2)
    with pytest.raises(EstateRefused):
        recover_with_quorum(e, ("kenn", "mara"), other)


def test_secure_key_handoff_is_receipted_gated_and_from_a_keyholder(tmp_path):
    reg = _reg(tmp_path)
    gate = HumanApprovalGate()
    e = _epoch()
    # a secure handoff is refused without a named human's approval (breath-gated)
    with pytest.raises(IncomeRefused):
        secure_key_handoff("kenn", "heir", e, "handoff-2026", gate=gate, at=AT, author=AUTHOR, source_ref="s",
                           registry=reg)
    rcpt = secure_key_handoff("kenn", "heir", e, "handoff-2026", gate=gate, at=AT, author=AUTHOR,
                              source_ref="s", registry=reg, approver="Kenneth Mangum", approval_ref="KM-1")
    assert rcpt["mandate"] == "heir"                            # the heir owns the handoff receipt
    with pytest.raises(EstateRefused):                          # a stranger cannot hand off the family's key
        secure_key_handoff("stranger", "heir", e, "h2", gate=gate, at=AT, author=AUTHOR, source_ref="s",
                           registry=reg, approver="Kenneth Mangum", approval_ref="KM-2")


def test_simulate_succession_is_a_dry_run_that_moves_no_key():
    e = _epoch()
    pol = define_quorum(e, threshold=3)
    ok = simulate_succession(e, pol, lost=("dev",))            # 3 remain, need 3
    assert isinstance(ok, SuccessionDrill) and ok.recoverable is True and ok.remaining == 3 and ok.needed == 3
    bad = simulate_succession(e, pol, lost=("dev", "iris"))    # only 2 remain, need 3
    assert bad.recoverable is False and bad.remaining == 2
    with pytest.raises(EstateRefused):
        simulate_succession(e, QuorumPolicy(family_id="other", threshold=2), lost=())


def test_seal_key_closed_a_press_or_seal_key_field_is_refused():
    e = _epoch()
    for bad in ("seal_key", "press_key", "sealing_key"):
        with pytest.raises(EstateRefused):
            rotate_key_epoch(e, HOLDERS, extra={bad: "x"})
    assert {"seal_key", "press_key", "sealing_key"} <= KEY_SUCCESSION_BREACH_FIELDS


def test_a_custodial_recovery_or_key_escrow_path_is_refused_in_code():
    # THE synthetic trip AA verifies: a custodial recovery authority / key-escrow / recovery engine is refused.
    e = _epoch()
    for bad in ("custodial_recovery", "key_escrow", "recovery_engine", "backup_custodian", "key_material"):
        with pytest.raises(EstateRefused):
            define_quorum(e, threshold=2, extra={bad: "acme-recovery-co"})
    assert {"custodial_recovery", "key_escrow", "recovery_engine"} <= KEY_SUCCESSION_BREACH_FIELDS


def test_composes_the_sealed_opener_only_not_the_sibling_volume():
    import sovereign_agent.estate.key_succession as m
    src = __import__("pathlib").Path(m.__file__).read_text()
    assert "generational_transfer" in src                       # composes the sealed opener (S12 V1)
    assert "venture_continuity" not in src                      # NOT the not-yet-sealed sibling (V3)
