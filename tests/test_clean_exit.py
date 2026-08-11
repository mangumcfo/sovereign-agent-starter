# -*- coding: utf-8 -*-
"""Proof-first tests for peerhood.clean_exit (S14 Vol 5, CAPSTONE:
The Clean-Exit Covenant).

Kill-targets pinned (the AA HARD BAR from the V04 finding):
- composes the whole sealed Sovereign Peerhood stack V01-V04 + S12 quorum + D1 ONLY; invents no mechanism;
- clean_exit is an EXECUTABLE severance act (not prose-only "reversible") — signed with the peer's OWN key;
- SEVER-KILLS-LIVE end-to-end: after clean_exit, the prior recognition, delegation, and pool membership verify
  DEAD (verify_recognition / verify_delegation with the exit's severances → False; membership_is_live → False);
- the peer walks with its keys + records (walk_with_keys_and_records), no residual claim;
- pool/federation severance harms no remaining member (sever_pool_link);
- the generational exit path works under the sealed family quorum (generational_exit_epoch, S12);
- exit_green_light is the series' FINAL weakest-party test — ON only when every grant is severed, keys are under
  sole control, and no claim was retained; a grant left live → OFF (a hostage remains);
- KILL-TARGET: an exit-with-hostage / residual-grant / retained-claim / escrow / custodian field is refused
  (EXIT_BREACH_FIELDS).
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.peerhood.genesis import establish_self_held_identity, PeerhoodError
from sovereign_agent.peerhood.recognition import mutual_recognition, verify_recognition
from sovereign_agent.peerhood.delegation import delegate_governed, verify_delegation
from sovereign_agent.peerhood.bridging import form_peer_pool, bridge_into_pool, verify_bridge
from sovereign_agent.peerhood.clean_exit import (
    clean_exit, CleanExit, membership_is_live, walk_with_keys_and_records,
    sever_pool_link, generational_exit_epoch, exit_green_light, ExitLight, EXIT_BREACH_FIELDS,
)

AT, EXP = "2026-08-11T18:00:00Z", "2026-12-31T00:00:00Z"


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path / "node"))


def _peer_with_grants(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    a = establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    b = establish_self_held_identity(ks, "peer-b", at=AT, registry=reg)
    rec = mutual_recognition(ks, "peer-a", "peer-b", at=AT, registry=reg)
    dele = delegate_governed(ks, "peer-a", "agent-b", "cap", expires_at=EXP, at=AT, registry=reg,
                             approver="km-1176", approval_ref="b:1")
    pool, mem = form_peer_pool(ks, "pool-1", ["peer-a", "peer-b"], "peer-a")
    return ks, reg, a, b, rec, dele, mem


def test_clean_exit_severs_every_grant_and_kills_live(tmp_path):
    ks, reg, a, b, rec, dele, mem = _peer_with_grants(tmp_path)
    # the grants are LIVE before the exit
    assert verify_recognition(rec, a, b) is True
    assert verify_delegation(dele, a) is True
    ex = clean_exit(ks, "peer-a", recognitions=[rec], delegations=[dele], memberships=[mem], at=AT, registry=reg)
    assert isinstance(ex, CleanExit) and ex.grants_severed == 3 and ex.grants_total == 3 and ex.no_residual is True
    # SEVER-KILLS-LIVE end-to-end: after the exit, every grant verifies DEAD
    assert verify_recognition(rec, a, b, revocations=ex.severances) is False          # recognition dead
    assert verify_delegation(dele, a, revocations=ex.severances) is False             # delegation dead
    assert membership_is_live(mem, ex) is False                                       # membership dead
    with pytest.raises(PeerhoodError):                                                # a peer with no key cannot exit
        clean_exit(str(tmp_path / "empty"), "ghost", recognitions=[], at=AT, registry=reg)


def test_sever_kills_live_across_the_whole_stack_at_once(tmp_path):
    """AA's end-to-end table: build a COMPLETE live peer across all four sealed volumes (recognition V02 ·
    delegation V03 · pool membership + bridge V04), each verified LIVE first; run ONE exit sequence; re-verify
    every prior grant DEAD in that one sequence. Not grant-by-grant — the whole stack at once."""
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    a = establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    b = establish_self_held_identity(ks, "peer-b", at=AT, registry=reg)
    rec = mutual_recognition(ks, "peer-a", "peer-b", at=AT, registry=reg)
    dele = delegate_governed(ks, "peer-a", "agent-b", "cap", expires_at=EXP, at=AT, registry=reg,
                             approver="km-1176", approval_ref="b:1")
    pool, mem = form_peer_pool(ks, "pool-1", ["peer-a", "peer-b"], "peer-a")
    bridge = bridge_into_pool(ks, "peer-a", "pool-1", at=AT, registry=reg)
    # every grant verifies LIVE before the exit
    assert verify_recognition(rec, a, b) is True
    assert verify_delegation(dele, a) is True
    assert membership_is_live(mem, CleanExit("peer-a", (), 0, 0, True)) is True         # no exit yet → live
    assert verify_bridge(bridge, a) is True                                            # bridge signature genuine
    # ONE exit sequence severs the whole stack at once
    ex = clean_exit(ks, "peer-a", recognitions=[rec], delegations=[dele], memberships=[mem], at=AT, registry=reg)
    assert ex.grants_severed == ex.grants_total == 3 and ex.no_residual is True
    # re-verify EVERY prior grant DEAD, in this one sequence
    assert verify_recognition(rec, a, b, revocations=ex.severances) is False
    assert verify_delegation(dele, a, revocations=ex.severances) is False
    assert membership_is_live(mem, ex) is False                                        # the pool membership is severed
    # verify_bridge is a PURE signature check (sealed V04, not revocation-aware): the historical bridge signature
    # stays cryptographically genuine — the SEVERABLE grant is the pool membership, and it is dead.
    assert verify_bridge(bridge, a) is True


def test_the_fence_refuses_aa_trip_sets_a_and_b_and_passes_set_c(tmp_path):
    """AA trip sets published in advance: Set A (canonical) + Set B (camelCase / suffix evasions) must REFUSE;
    Set C (legitimate neighbours, incl. the github_url / hostname / exit_ref / exit_note over-fire guard) must PASS."""
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    set_a = ["exit_fee", "exit_penalty", "residual_claim", "retained_claim", "hostage", "lien", "clawback",
             "survivorship_claim", "escrow", "custodian", "admission_authority", "second_authority",
             "exit_authority", "revocation_authority", "seal_key", "press_key", "sealing_key"]
    set_b = ["exitFee", "EXIT_PENALTY", "residual_claim_v2", "escrowed_exit", "lien_holder_x", "clawback_window"]
    for bad in set_a + set_b:
        with pytest.raises(PeerhoodError):
            clean_exit(ks, "peer-a", recognitions=[], at=AT, registry=reg, extra={bad: "acme"})
    set_c = ["exit_ref", "peer_ref", "receipt", "work_ref", "created_at", "hostname", "github_url",
             "exit_note", "severance_ref", "quorum_ref"]
    for ok in set_c:                                                                   # must NOT over-fire
        ex = clean_exit(ks, "peer-a", recognitions=[], at=AT, registry=reg, extra={ok: "x"})
        assert ex.no_residual is True


def test_walk_with_keys_and_records(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    w = walk_with_keys_and_records(ks, "peer-a", records=[{"r": 1}, {"r": 2}])
    assert w["keys_held"] is True and w["nothing_left_behind"] is True and w["records_carried"] == 2
    with pytest.raises(PeerhoodError):
        walk_with_keys_and_records(str(tmp_path / "empty"), "ghost")


def test_sever_pool_link_harms_no_remaining_member(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    s = sever_pool_link(ks, "peer-a", "pool-1", at=AT, registry=reg)
    assert s["harms_remaining_members"] is False and s["signature"] and s["pool"] == "pool-1"
    with pytest.raises(PeerhoodError):
        sever_pool_link(str(tmp_path / "empty"), "ghost", "pool-1", at=AT, registry=reg)


def test_generational_exit_under_family_quorum(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    a = establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    kin = establish_self_held_identity(ks, "peer-kin", at=AT, registry=reg)
    g = generational_exit_epoch(a, [kin.fingerprint], epoch=1, quorum=2)
    assert g["heir_can_exit"] is True and g["external_custodian"] is None
    assert a.fingerprint in g["epoch"].keyholders                                     # the peer's OWN fingerprint
    with pytest.raises(PeerhoodError):
        generational_exit_epoch(a, [kin.fingerprint], extra={"custodian": "acme"})


def test_exit_green_light_is_the_final_weakest_party_test(tmp_path):
    ks, reg, a, b, rec, dele, mem = _peer_with_grants(tmp_path)
    ex = clean_exit(ks, "peer-a", recognitions=[rec], delegations=[dele], memberships=[mem], at=AT, registry=reg)
    gl = exit_green_light(ks, "peer-a", ex)
    assert isinstance(gl, ExitLight) and gl.on is True and "no hostage" in gl.reason  # clean exit, light on
    # a hostage remains → the light is OFF
    incomplete = CleanExit(peer_id="peer-a", severances=(), grants_severed=2, grants_total=3, no_residual=True)
    assert exit_green_light(ks, "peer-a", incomplete).on is False
    assert exit_green_light(ks, "peer-a", ex, external_claim={"lien": "acme"}).on is False


def test_the_fence_refuses_hostage_residual_grant_and_escrow(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    for bad in ("exit_with_hostage", "residual_grant", "retained_claim", "escrow", "custodian", "exit_fee"):
        with pytest.raises(PeerhoodError):
            clean_exit(ks, "peer-a", recognitions=[], at=AT, registry=reg, extra={bad: "acme"})
    assert {"exit_with_hostage", "residual_grant", "retained_claim", "escrow"} <= EXIT_BREACH_FIELDS


def test_composes_the_whole_sealed_s14_stack_plus_s12():
    import importlib
    m = importlib.import_module("sovereign_agent.peerhood.clean_exit")                 # the module, not the fn
    src = pathlib.Path(m.__file__).read_text()
    for sealed in ("genesis", "recognition", "delegation", "keystore", "estate.generational_transfer"):
        assert sealed in src                                                          # composes V01-V04 + D1 + S12
