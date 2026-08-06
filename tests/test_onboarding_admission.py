"""Acceptance tests for Node Onboarding (s6_06, S6 Vol 6) — a new node joins by adopting the federation's constitution
and passing a human-gated admission, composing the sealed constitution templates + compliance human-gate. No central
trust service. Pure / structural (F-1 clean)."""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.onboarding.admission import propose_onboarding, admit_node, OnboardingError


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path))


def _propose(reg, node="nodeB"):
    return propose_onboarding(reg, node, {"article1": "human primacy", "article2": "no central owner"},
                              mandate=node, author=node, source_ref=f"con://{node}/1", at="t")


def test_propose_onboarding_opens_a_governed_constitution_adoption(tmp_path):
    reg = _reg(tmp_path)
    p = _propose(reg)
    assert p["version_hash"]
    assert p["object_id"] == "constitution:onboarding:nodeB"


def test_propose_onboarding_refuses_empty(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(OnboardingError):
        propose_onboarding(reg, "", {"a": 1}, mandate="nodeB", author="nodeB", source_ref="c://b/1", at="t")
    with pytest.raises(OnboardingError):
        propose_onboarding(reg, "nodeB", {}, mandate="nodeB", author="nodeB", source_ref="c://b/1", at="t")


def test_admit_node_with_named_human(tmp_path):
    reg = _reg(tmp_path)
    p = _propose(reg)
    res = admit_node(p, approver="federation-steward", approval_ref="admission minute #12")
    assert res["admitted"] is True
    assert res["constitution_root"] == p["version_hash"]
    assert res["approver"] == "federation-steward"


def test_admit_node_refuses_nonexistent_proposal(tmp_path):
    with pytest.raises(OnboardingError):
        admit_node({}, approver="steward", approval_ref="minute #1")


def test_admit_node_refuses_unnamed_approver_or_ref(tmp_path):
    reg = _reg(tmp_path)
    p = _propose(reg)
    with pytest.raises(OnboardingError):
        admit_node(p, approver="  ", approval_ref="minute")
    with pytest.raises(OnboardingError):
        admit_node(p, approver="steward", approval_ref="")
