"""Acceptance tests for Sovereign Collaboration (s6_02, S6 Vol 2) — nodes co-govern shared work with no central server,
composing the sealed object registry + cross-mandate access check. Pure / structural (F-1 clean)."""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.objects.scope import SharingRule
from sovereign_agent.collaboration.shared_work import (
    contribute, authorize_participation, CollaborationError,
)


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path))


def test_contribute_records_a_governed_provenance_carrying_version(tmp_path):
    reg = _reg(tmp_path)
    v = contribute(reg, "plan", {"section": "budget", "text": "draft"}, mandate="nodeA",
                   author="nodeA", source_ref="collab://nodeA/1", at="2026-08-05")
    assert v["version_hash"]
    assert v["author"] == "nodeA"
    assert v["source_ref"] == "collab://nodeA/1"
    assert v["object_id"] == "collab:plan"


def test_contribute_refuses_empty_id_or_body(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(CollaborationError):
        contribute(reg, "", {"x": 1}, mandate="nodeA", author="nodeA", source_ref="c://a/1", at="t")
    with pytest.raises(CollaborationError):
        contribute(reg, "plan", {}, mandate="nodeA", author="nodeA", source_ref="c://a/1", at="t")


def test_authorize_participation_own_mandate_is_whole(tmp_path):
    reg = _reg(tmp_path)
    contribute(reg, "plan", {"x": 1}, mandate="nodeA", author="nodeA", source_ref="c://a/1", at="t")
    assert authorize_participation(reg, [], "plan", peer_mandate="nodeA", want="write") is True


def test_authorize_participation_grants_a_declared_crossing(tmp_path):
    reg = _reg(tmp_path)
    contribute(reg, "plan", {"x": 1}, mandate="nodeA", author="nodeA", source_ref="c://a/1", at="t")
    rules = [SharingRule("collab:plan", "nodeB", "read")]
    assert authorize_participation(reg, rules, "plan", peer_mandate="nodeB", want="read") is True


def test_authorize_participation_refuses_undeclared_peer(tmp_path):
    reg = _reg(tmp_path)
    contribute(reg, "plan", {"x": 1}, mandate="nodeA", author="nodeA", source_ref="c://a/1", at="t")
    with pytest.raises(CollaborationError):
        authorize_participation(reg, [], "plan", peer_mandate="nodeB", want="read")


def test_authorize_participation_refuses_scope_escalation(tmp_path):
    reg = _reg(tmp_path)
    contribute(reg, "plan", {"x": 1}, mandate="nodeA", author="nodeA", source_ref="c://a/1", at="t")
    rules = [SharingRule("collab:plan", "nodeB", "read")]  # read-only grant
    with pytest.raises(CollaborationError):
        authorize_participation(reg, rules, "plan", peer_mandate="nodeB", want="write")
