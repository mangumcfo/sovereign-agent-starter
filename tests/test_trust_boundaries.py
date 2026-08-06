"""Acceptance tests for Inter-Node Trust Boundaries & Handoff (s6_05, S6 Vol 5) — a node's trust anchor is a governed
object handed off by a receipted, human-gated ceremony, composing the sealed object registry + generational-handoff
floor. No second recovery authority, no escrow. Pure / structural (F-1 clean)."""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.trust.boundaries import declare_trust_anchor, hand_off_trust, TrustError


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path))


def test_declare_trust_anchor_registers_a_governed_object(tmp_path):
    reg = _reg(tmp_path)
    a = declare_trust_anchor(reg, "nodeA", {"key": "ecdsa-pub-A"}, mandate="nodeA",
                             author="nodeA", source_ref="anchor://a/1", at="2026-08-06")
    assert a["version_hash"]
    assert a["object_id"] == "trust_anchor:nodeA"
    assert a["payload"]["key"] == "ecdsa-pub-A"


def test_declare_trust_anchor_refuses_empty(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(TrustError):
        declare_trust_anchor(reg, "", {"key": "x"}, mandate="nodeA", author="nodeA", source_ref="a://a/1", at="t")
    with pytest.raises(TrustError):
        declare_trust_anchor(reg, "nodeA", {}, mandate="nodeA", author="nodeA", source_ref="a://a/1", at="t")


def test_hand_off_trust_receipts_a_named_ceremony(tmp_path):
    reg = _reg(tmp_path)
    declare_trust_anchor(reg, "nodeA", {"key": "ecdsa-pub-A"}, mandate="nodeA",
                         author="nodeA", source_ref="anchor://a/1", at="t")
    res = hand_off_trust(reg, at="2026-08-06", approver="steward", approval_ref="succession deed #5")
    assert res["handed_off"] is True
    assert res["approver"] == "steward"
    assert res["package_root"]


def test_hand_off_trust_refuses_unnamed_approver_or_ref(tmp_path):
    reg = _reg(tmp_path)
    declare_trust_anchor(reg, "nodeA", {"key": "k"}, mandate="nodeA", author="nodeA", source_ref="a://a/1", at="t")
    with pytest.raises(TrustError):
        hand_off_trust(reg, at="t", approver="   ", approval_ref="deed")
    with pytest.raises(TrustError):
        hand_off_trust(reg, at="t", approver="steward", approval_ref="")
