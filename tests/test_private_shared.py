"""Acceptance tests for Private vs Shared Storage Governance (s7_05, S7 Vol 5) — data classified
private/shared/hybrid as a governed object, integrity-proven (sealed P5 Merkle), shared only by a
declared, revocable, deny-by-default scope grant. A private datum is never shareable; no standing trust
across data; no central store, no second classification authority. Lands S5-06-E3-2 (the distribution
matrix / resonant-shard partition as a built classification)."""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.objects.scope import SharingRule
from sovereign_agent.governance.private_shared import classify_datum, govern_shared_access, GovernanceError


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path))


def _classify(reg, owner="nodeA", chunks=(b"records",), visibility="shared"):
    return classify_datum(reg, owner, list(chunks), visibility=visibility, mandate=owner,
                          author=owner, source_ref=f"cls://{owner}", at="2026-08-06")


def test_classify_datum_records_governed_object_with_partition(tmp_path):
    reg = _reg(tmp_path)
    d = _classify(reg, visibility="hybrid")
    assert d["version_hash"] and d["object_id"].startswith("datum:nodeA:")
    assert d["payload"]["visibility"] == "hybrid" and d["payload"]["root"]


def test_classify_datum_refuses_empty_or_bad_visibility(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(GovernanceError):
        classify_datum(reg, "", [b"x"], visibility="shared", mandate="nodeA", author="a", source_ref="c://1", at="t")
    with pytest.raises(GovernanceError):
        classify_datum(reg, "nodeA", [], visibility="shared", mandate="nodeA", author="a", source_ref="c://1", at="t")
    with pytest.raises(GovernanceError):  # 'public' is not a class
        classify_datum(reg, "nodeA", [b"x"], visibility="public", mandate="nodeA", author="a", source_ref="c://1", at="t")


def test_own_mandate_access_is_whole(tmp_path):
    reg = _reg(tmp_path)
    d = _classify(reg, "nodeA", visibility="private")
    res = govern_shared_access(reg, d, [], principal_mandate="nodeA")
    assert res["granted"] is True and res["basis"] == "own-mandate"


def test_private_datum_is_never_shareable(tmp_path):
    reg = _reg(tmp_path)
    d = _classify(reg, "nodeA", visibility="private")
    # even WITH a declared rule, a private datum refuses a cross-mandate share
    rule = SharingRule(d["object_id"], "nodeB", "read")
    with pytest.raises(GovernanceError):
        govern_shared_access(reg, d, [rule], principal_mandate="nodeB")


def test_shared_datum_needs_declared_scope(tmp_path):
    reg = _reg(tmp_path)
    d = _classify(reg, "nodeA", visibility="shared")
    with pytest.raises(GovernanceError):  # no rule -> no standing trust
        govern_shared_access(reg, d, [], principal_mandate="nodeB")
    rule = SharingRule(d["object_id"], "nodeB", "read")
    res = govern_shared_access(reg, d, [rule], principal_mandate="nodeB")
    assert res["granted"] is True and res["basis"] == "declared-scope"


def test_hybrid_datum_shareable_by_declared_scope(tmp_path):
    reg = _reg(tmp_path)
    d = _classify(reg, "nodeA", visibility="hybrid")
    rule = SharingRule(d["object_id"], "nodeB", "read")
    assert govern_shared_access(reg, d, [rule], principal_mandate="nodeB")["granted"] is True


def test_access_refuses_no_real_datum(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(GovernanceError):
        govern_shared_access(reg, {}, [], principal_mandate="nodeA")
