# -*- coding: utf-8 -*-
"""Proof-first tests for risk.governance (S11 Vol 4, Governance, Compliance & Integrated Risk Systems).

Kill-targets pinned:
- composes the sealed S11 V1–V3 + S10 floors ONLY — invents no new engine, rolls no cryptography;
- a governance skin is POLICY-AS-CODE = ENFORCEMENT, not optimization: an underwriting / pricing / optimization
  rule is REFUSED (the sharpened GOVERNANCE_BREACH_FIELDS); a skin that gates nothing is refused;
- policy-as-code is enforced by the SEALED gate — a gated governed decision is refused without a named human;
- escalate_if_over_limit flags an amount over the skin's limit (ROE-style), a threshold not a price;
- audit_ready_package is complete only from the principal's own verified records (claims/premiums/group/chain),
  a foreign or tampered record breaks it, an unknown kind is refused, an empty package is not complete;
- the governance skin is versioned + forkable; weakest-party plain bool.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.risk.mutual_protection import form_protection_pool, record_premium, record_claim
from sovereign_agent.risk.advanced_pooling import build_attestation_chain
from sovereign_agent.risk.governance import (
    load_governance_skin, skin_role_spec, fork_governance_skin, enforce_decision, escalate_if_over_limit,
    audit_ready_package, GovernanceSkin, AuditPackage, AUDIT_KINDS, GOVERNANCE_BREACH_FIELDS, IncomeRefused,
)

A, B, C, AUTHOR, AT = "ridgeline-kenn", "cedar-partner", "granite-neighbor", "Kenneth Mangum", "2026-08-10T07:00:00Z"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def test_a_governance_skin_is_policy_as_code_enforcement_not_pricing(tmp_path):
    skin = load_governance_skin("ridgeline-gov", gated_classes=["approve_large_claim", "change_pool_terms"],
                                limits={"approve_large_claim": 500.0}, version="v1")
    assert isinstance(skin, GovernanceSkin) and "approve_large_claim" in skin.gated_classes
    assert skin_role_spec(skin) == {"charter_v7_forbidden_classes": ["approve_large_claim", "change_pool_terms"]}
    # a skin that gates nothing governs nothing
    with pytest.raises(IncomeRefused):
        load_governance_skin("empty", gated_classes=[])
    # policy-as-code = ENFORCEMENT, not optimization: a pricing/underwriting/optimization rule is refused
    for breach in ("premium_pricing", "underwrite", "optimize", "price_risk", "optimizer"):
        with pytest.raises(IncomeRefused):
            load_governance_skin("bad", gated_classes=["x"], limits={breach: 1.0})
        with pytest.raises(IncomeRefused):
            load_governance_skin("bad", gated_classes=[breach])
    assert {"underwrite", "premium_pricing", "optimize"}.issubset(GOVERNANCE_BREACH_FIELDS)


def test_a_gated_governed_decision_is_refused_without_a_human(tmp_path):
    skin = load_governance_skin("ridgeline-gov", gated_classes=["approve_large_claim"])
    gate = HumanApprovalGate()
    # a gated class routed through the sealed gate is refused without a named human's approval
    with pytest.raises(IncomeRefused):
        enforce_decision(skin, "approve_large_claim", A, "big-claim-decision", gate=gate, at=AT, author=AUTHOR,
                         source_ref="s", registry=_reg(tmp_path))
    # a non-gated decision passes (records as the principal's own governed decision)
    r = enforce_decision(skin, "note_meeting", A, "routine", gate=gate, at=AT, author=AUTHOR, source_ref="s",
                         registry=_reg(tmp_path))
    assert r["mandate"] == A


def test_a_governed_decision_refuses_an_underwriting_field(tmp_path):
    skin = load_governance_skin("ridgeline-gov", gated_classes=["x"])
    with pytest.raises(IncomeRefused):
        enforce_decision(skin, "note", A, "w", gate=HumanApprovalGate(), at=AT, author=AUTHOR, source_ref="s",
                         registry=_reg(tmp_path), extra={"price_risk": 1.0})


def test_escalate_if_over_limit_flags_material_decisions(tmp_path):
    skin = load_governance_skin("ridgeline-gov", gated_classes=["approve_large_claim"],
                                limits={"approve_large_claim": 500.0})
    assert escalate_if_over_limit(skin, "approve_large_claim", 800.0).escalate is True
    assert escalate_if_over_limit(skin, "approve_large_claim", 300.0).escalate is False
    assert escalate_if_over_limit(skin, "ungated", 999.0).escalate is False   # no limit -> no escalation


def test_governance_skin_is_versioned_and_forkable(tmp_path):
    skin = load_governance_skin("ridgeline-gov", gated_classes=["a", "b"], version="v1")
    forked = fork_governance_skin(skin, "ridgeline-gov-2", add_gated=["c"], remove_gated=["a"], version="v2")
    assert forked.version == "v2" and set(forked.gated_classes) == {"b", "c"}
    assert set(skin.gated_classes) == {"a", "b"}          # original preserved (history kept)


def _audit_records(tmp_path):
    reg = _reg(tmp_path)
    pool = form_protection_pool("ridgeline-aid", (A, B))
    prem = record_premium(pool, A, "aug-prem", contribution_class="attested", author=AUTHOR, source_ref="s",
                          at=AT, registry=reg, amount=25.0)
    clm = record_claim(A, pool, "storm", claim_class="attested", author=AUTHOR, source_ref="s", at=AT,
                       registry=reg, amount=300.0)
    chain = build_attestation_chain(A, pool, "big-storm", claim_class="attested",
                                    attestors=[{"party": B, "work_ref": "b-att"}], registry=reg, at=AT,
                                    author=AUTHOR, source_ref="s", amount=400.0)
    recs = [
        {"kind": "premium", "receipt": prem, "pool": pool, "work_ref": "aug-prem",
         "contribution_class": "attested", "amount": 25.0},
        {"kind": "claim", "receipt": clm, "pool": pool, "work_ref": "storm", "claim_class": "attested",
         "amount": 300.0},
        {"kind": "attestation_chain", "chain": chain, "pool": pool, "work_ref": "big-storm",
         "claim_class": "attested", "attestors": [{"party": B, "work_ref": "b-att"}], "amount": 400.0},
    ]
    return pool, reg, recs


def test_audit_ready_package_complete_only_from_verified_records(tmp_path):
    pool, reg, recs = _audit_records(tmp_path)
    pkg = audit_ready_package(A, recs)
    assert isinstance(pkg, AuditPackage) and pkg.complete is True and pkg.verified_count == 3
    assert pkg.by_kind["premium"] == 1 and pkg.by_kind["claim"] == 1 and pkg.by_kind["attestation_chain"] == 1
    # a tampered record breaks the package
    tampered = dict(recs[1]); tampered["claim_class"] = "computed"
    assert audit_ready_package(A, [recs[0], tampered, recs[2]]).complete is False
    # a foreign principal does not verify
    assert audit_ready_package("stranger", recs).complete is False


def test_empty_audit_package_not_complete_and_unknown_kind_refused(tmp_path):
    assert audit_ready_package(A, []).complete is False
    with pytest.raises(IncomeRefused):
        audit_ready_package(A, [{"kind": "invented", "receipt": {}}])
    assert set(AUDIT_KINDS) == {"claim", "premium", "group_premium", "attestation_chain"}


def test_composes_the_sealed_s11_and_s10_floors_only():
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "risk" / "governance.py"
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography", "zk_proofs",
                    "objects.registry", "objects.identity", "material.", "provision_"):
            assert tok not in ln, f"governance composes the sealed S11 V1-V3 + S10 floors only, not {tok}"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from .")]
    assert sibling
    allowed = (".mutual_protection", ".advanced_pooling", ".group_applications", ".economy")
    for ln in sibling:
        assert any(m in ln for m in allowed), f"only the sealed S11 V1-V3 + S10 floors may be composed: {ln}"
