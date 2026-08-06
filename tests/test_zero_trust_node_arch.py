"""Acceptance tests for Zero-Trust Node Architecture (s7_01, S7 Vol 1) — never trust, always verify; no standing trust.
A node presents its OWN governed evidence, and access is decided DENY-BY-DEFAULT, per request, by verifying that evidence
and a node-DECLARED rule for exactly this resource — never a central attestation, a standing grant, or a hub's vouching.
Composes the sealed object registry + Federation Node Governance authorize_crossing. Pure / structural (F-1 clean)."""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.objects.scope import SharingRule
from sovereign_agent.zero_trust.node_arch import present_evidence, verify_access, ZeroTrustError


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path))


def _evidence(reg, node="nodeB"):
    return present_evidence(reg, node, {"anchor": "trust_anchor:nodeB", "constitution": "adopted"},
                            mandate=node, author=node, source_ref=f"ev://{node}/1", at="2026-08-06")


def _resource(reg, obj_id="doc:X", owner="nodeA"):
    return reg.append(obj_id, {"content": "governed"}, author=owner, source_ref=f"res://{obj_id}",
                      at="2026-08-06", mandate=owner, kind="ratify")


# ── Ch2 · the node presents its own evidence (present_evidence) ────────────────────────────────────────
def test_present_evidence_registers_a_governed_object(tmp_path):
    reg = _reg(tmp_path)
    e = _evidence(reg)
    assert e["version_hash"]
    assert e["object_id"] == "evidence:nodeB"
    assert e["payload"]["anchor"] == "trust_anchor:nodeB"


def test_present_evidence_refuses_empty(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(ZeroTrustError):
        present_evidence(reg, "", {"a": 1}, mandate="nodeB", author="nodeB", source_ref="e://b/1", at="t")
    with pytest.raises(ZeroTrustError):
        present_evidence(reg, "nodeB", {}, mandate="nodeB", author="nodeB", source_ref="e://b/1", at="t")


# ── Ch3 · verify every access, deny-by-default, no standing trust (verify_access) ──────────────────────
def test_verify_access_grants_on_verified_evidence_and_declared_rule(tmp_path):
    reg = _reg(tmp_path)
    _resource(reg, "doc:X", "nodeA")
    e = _evidence(reg, "nodeB")
    rule = SharingRule("doc:X", "nodeB", "read")  # nodeA declares nodeB may read doc:X
    res = verify_access(reg, e, [rule], principal_mandate="nodeB", obj_id="doc:X", want="read")
    assert res["granted"] is True
    assert res["verified_against"] == e["version_hash"]
    assert res["resource"] == "doc:X"


def test_verify_access_denies_undeclared_request(tmp_path):
    reg = _reg(tmp_path)
    _resource(reg, "doc:X", "nodeA")
    e = _evidence(reg, "nodeB")
    with pytest.raises(ZeroTrustError):
        verify_access(reg, e, [], principal_mandate="nodeB", obj_id="doc:X", want="read")  # no rule -> deny


def test_verify_access_denies_nonexistent_or_tampered_evidence(tmp_path):
    reg = _reg(tmp_path)
    _resource(reg, "doc:X", "nodeA")
    rule = SharingRule("doc:X", "nodeB", "read")
    with pytest.raises(ZeroTrustError):
        verify_access(reg, {}, [rule], principal_mandate="nodeB", obj_id="doc:X", want="read")
    with pytest.raises(ZeroTrustError):  # evidence with no version_hash is not governed
        verify_access(reg, {"object_id": "evidence:nodeB"}, [rule], principal_mandate="nodeB", obj_id="doc:X", want="read")


def test_verify_access_no_standing_trust_across_resources(tmp_path):
    # a rule granting doc:A must NEVER grant doc:B -- trust is per-resource, re-verified each request
    reg = _reg(tmp_path)
    _resource(reg, "doc:A", "nodeA")
    _resource(reg, "doc:B", "nodeA")
    e = _evidence(reg, "nodeB")
    rule_a = SharingRule("doc:A", "nodeB", "read")
    assert verify_access(reg, e, [rule_a], principal_mandate="nodeB", obj_id="doc:A", want="read")["granted"] is True
    with pytest.raises(ZeroTrustError):  # same evidence, same rule set, DIFFERENT resource -> denied
        verify_access(reg, e, [rule_a], principal_mandate="nodeB", obj_id="doc:B", want="read")


def test_verify_access_denies_scope_escalation(tmp_path):
    # a read grant must never satisfy a write -- a grant is exactly its declared scope
    reg = _reg(tmp_path)
    _resource(reg, "doc:X", "nodeA")
    e = _evidence(reg, "nodeB")
    rule_read = SharingRule("doc:X", "nodeB", "read")
    with pytest.raises(ZeroTrustError):
        verify_access(reg, e, [rule_read], principal_mandate="nodeB", obj_id="doc:X", want="write")


def test_verify_access_denies_unknown_resource(tmp_path):
    reg = _reg(tmp_path)
    e = _evidence(reg, "nodeB")
    rule = SharingRule("ghost:1", "nodeB", "read")
    with pytest.raises(ZeroTrustError):  # resource not on the record -> deny-by-default, not an error
        verify_access(reg, e, [rule], principal_mandate="nodeB", obj_id="ghost:1", want="read")
