"""Acceptance tests for Resilience & Recovery Shields (s7_06, S7 Vol 6, capstone) — a node recovers
authority by COMPOSITION: a recovery constitution (Constitutions S5 Vol 30), a governed integrity-proven
snapshot (Object Model + sealed P5 Merkle), and a human-gated M-of-N recovery ceremony (HumanApprovalGate
S5 Vol 16, succession per Continuity S5 Vol 29). No second recovery authority, no standing escrow, no
central trust service; dry-run never touches the live root."""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.shields.resilience import (
    declare_recovery_plan, snapshot_resource, recover_authority, ResilienceError,
)


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path))


def _plan(reg, resource="root:nodeA", guardians=("alice", "bob", "carol"), threshold=2):
    return declare_recovery_plan(reg, resource, list(guardians), threshold=threshold, mandate="nodeA",
                                 author="nodeA", source_ref="plan://nodeA", at="2026-08-06")


# ---- declare_recovery_plan (the recovery constitution — no keys, no escrow) ----------------------

def test_declare_recovery_plan_is_a_governed_constitution(tmp_path):
    reg = _reg(tmp_path)
    p = _plan(reg)
    assert p["version_hash"] and p["object_id"].startswith("constitution:recovery:")
    assert p["payload"]["threshold"] == 2 and p["payload"]["guardians"] == ["alice", "bob", "carol"]
    assert p["payload"]["holds_keys"] is False and p["payload"]["escrow"] is False  # no escrow


def test_declare_recovery_plan_refuses_empty_or_bad_threshold(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(ResilienceError):
        declare_recovery_plan(reg, "", ["a"], threshold=1, mandate="n", author="n", source_ref="s", at="t")
    with pytest.raises(ResilienceError):  # no guardians
        declare_recovery_plan(reg, "root", [], threshold=1, mandate="n", author="n", source_ref="s", at="t")
    with pytest.raises(ResilienceError):  # threshold > guardian count
        declare_recovery_plan(reg, "root", ["a", "b"], threshold=3, mandate="n", author="n", source_ref="s", at="t")
    with pytest.raises(ResilienceError):  # threshold < 1
        declare_recovery_plan(reg, "root", ["a"], threshold=0, mandate="n", author="n", source_ref="s", at="t")


# ---- snapshot_resource (governed, integrity-proven) ---------------------------------------------

def test_snapshot_resource_carries_merkle_root(tmp_path):
    reg = _reg(tmp_path)
    s = snapshot_resource(reg, "root:nodeA", [b"state", b"bytes"], mandate="nodeA", author="nodeA",
                          source_ref="snap://nodeA", at="2026-08-06")
    assert s["version_hash"] and s["object_id"].startswith("snapshot:root:nodeA:")
    assert s["payload"]["root"] and s["payload"]["kind"] == "snapshot"


def test_snapshot_resource_refuses_empty(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(ResilienceError):
        snapshot_resource(reg, "", [b"x"], mandate="n", author="n", source_ref="s", at="t")
    with pytest.raises(ResilienceError):
        snapshot_resource(reg, "root", [], mandate="n", author="n", source_ref="s", at="t")


# ---- recover_authority (human-gated M-of-N ceremony) --------------------------------------------

def _ap(*names):
    return [{"approver": n, "approval_ref": f"breath://approve/{n}"} for n in names]


def test_recover_authority_m_of_n_met_ratifies(tmp_path):
    reg = _reg(tmp_path)
    p = _plan(reg, threshold=2)
    res = recover_authority(reg, p, _ap("alice", "bob"), mandate="nodeA", author="nodeA",
                            source_ref="rec://nodeA", at="2026-08-06")
    assert res["recovered"] is True and res["ratified"] is True
    assert sorted(res["assented"]) == ["alice", "bob"] and res["succession"]


def test_recover_authority_below_threshold_refused(tmp_path):
    reg = _reg(tmp_path)
    p = _plan(reg, threshold=2)
    with pytest.raises(ResilienceError):  # only 1 of 2
        recover_authority(reg, p, _ap("alice"), mandate="nodeA", author="nodeA", source_ref="r", at="t")


def test_recover_authority_unnamed_guardian_does_not_count(tmp_path):
    reg = _reg(tmp_path)
    p = _plan(reg, guardians=("alice", "bob", "carol"), threshold=2)
    # alice (named) + mallory (NOT a guardian) => only 1 valid => refused
    with pytest.raises(ResilienceError):
        recover_authority(reg, p, _ap("alice", "mallory"), mandate="nodeA", author="nodeA", source_ref="r", at="t")


def test_recover_authority_assent_without_reference_does_not_count(tmp_path):
    reg = _reg(tmp_path)
    p = _plan(reg, threshold=2)
    approvals = [{"approver": "alice", "approval_ref": "breath://a"}, {"approver": "bob", "approval_ref": ""}]
    with pytest.raises(ResilienceError):  # bob's assent has no reference => only 1 valid
        recover_authority(reg, p, approvals, mandate="nodeA", author="nodeA", source_ref="r", at="t")


def test_recover_authority_dry_run_never_touches_live_root(tmp_path):
    reg = _reg(tmp_path)
    p = _plan(reg, threshold=2)
    before = len(reg.entries())
    res = recover_authority(reg, p, _ap("alice", "bob"), mandate="nodeA", author="nodeA",
                            source_ref="r", at="t", dry_run=True)
    assert res["would_recover"] is True and res["ratified"] is False
    assert len(reg.entries()) == before  # dry-run ratified nothing — the live root is untouched


def test_recover_authority_no_real_plan_refused(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(ResilienceError):
        recover_authority(reg, {}, _ap("alice", "bob"), mandate="nodeA", author="nodeA", source_ref="r", at="t")
