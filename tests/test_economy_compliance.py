# -*- coding: utf-8 -*-
"""Proof-first tests for economy.compliance (S10 Vol 4, Operating Legally While Staying Sovereign).

Kill-targets pinned: composes-income.py-only · a tax event is the principal's OWN categorized record · unknown
category refused · THE TAX-FENCE (an in-node filing / payment / formation / representation field is REFUSED —
the synthetic statutory-act path must trip it) · portable reporting package complete iff every event is the
principal's own + nothing filed · human-primacy (a gated tax event passes a human) · weakest-party.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.economy.compliance import (
    record_tax_event, verify_tax_event, reporting_package,
    ReportingPackage, TAX_CATEGORIES, TAX_FENCE_BREACH_FIELDS, IncomeRefused, IncomeStatus,
)

PRINCIPAL, MANDATE, AUTHOR, AT = "ridgeline-kenn", "ridgeline-kenn", "Kenneth Mangum", "2026-08-09T01:00:00Z"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def test_records_a_tax_event_as_the_principals_own_categorized_record(tmp_path):
    r = record_tax_event(PRINCIPAL, "aug-welding-income", category="self_employment", mandate=MANDATE,
                         author=AUTHOR, source_ref="tax:aug", at=AT, registry=_reg(tmp_path),
                         references_income="IncomeEvent:ridgeline-kenn:welding-qms", amount=1200.0)
    assert r["kind"] == "income" and r["mandate"] == PRINCIPAL
    assert r["payload"]["tax_event"] is True and r["payload"]["tax_category"] == "self_employment"
    assert r["payload"]["reportable"] is True
    st = verify_tax_event(r, PRINCIPAL, "aug-welding-income", category="self_employment",
                          references_income="IncomeEvent:ridgeline-kenn:welding-qms", amount=1200.0)
    assert st.provisioned is True


def test_unknown_income_category_is_refused(tmp_path):
    with pytest.raises(IncomeRefused):
        record_tax_event(PRINCIPAL, "x", category="guessed", mandate=MANDATE, author=AUTHOR,
                         source_ref="t", at=AT, registry=_reg(tmp_path))


def test_the_tax_fence_refuses_any_in_node_statutory_act(tmp_path):
    # AA's synthetic statutory-act path: filing / paying / forming / representing must all trip the fence
    for breach in ("filing", "pay_tax", "remit", "formation", "incorporate", "represent",
                   "power_of_attorney", "statutory_authority"):
        with pytest.raises(IncomeRefused):
            record_tax_event(PRINCIPAL, "job", category="self_employment", mandate=MANDATE, author=AUTHOR,
                             source_ref="t", at=AT, registry=_reg(tmp_path), extra={breach: True})
    assert {"filing", "pay_tax", "formation", "represent"}.issubset(TAX_FENCE_BREACH_FIELDS)


def test_a_tampered_category_flips_verify(tmp_path):
    r = record_tax_event(PRINCIPAL, "aug-income", category="self_employment", mandate=MANDATE, author=AUTHOR,
                         source_ref="t", at=AT, registry=_reg(tmp_path))
    assert verify_tax_event(r, PRINCIPAL, "aug-income", category="capital").provisioned is False


def test_portable_reporting_package_complete_only_from_the_principals_own(tmp_path):
    reg = _reg(tmp_path)
    items = []
    for work, cat, amt in [("welding", "self_employment", 1200.0), ("solar-credit", "in_kind", 42.0),
                           ("consult", "self_employment", 800.0)]:
        r = record_tax_event(PRINCIPAL, work, category=cat, mandate=MANDATE, author=AUTHOR, source_ref="t",
                             at=AT, registry=reg, amount=amt)
        items.append({"receipt": r, "work_ref": work, "category": cat, "amount": amt})
    pkg = reporting_package(PRINCIPAL, items)
    assert isinstance(pkg, ReportingPackage) and pkg.complete is True and pkg.event_count == 3
    assert pkg.by_category["self_employment"] == 2 and pkg.by_category["in_kind"] == 1
    assert "nothing filed" in pkg.reason
    # a tax event that is not the principal's own breaks the package
    other = record_tax_event("cedar-partner", "fence", category="self_employment", mandate="cedar-partner",
                             author=AUTHOR, source_ref="t", at=AT, registry=reg)
    items.append({"receipt": other, "work_ref": "fence", "category": "self_employment"})
    assert reporting_package(PRINCIPAL, items).complete is False


def test_empty_package_not_complete(tmp_path):
    pkg = reporting_package(PRINCIPAL, [])
    assert pkg.complete is False and pkg.event_count == 0


def test_human_primacy_gated_tax_event_refused_without_approval(tmp_path):
    gate = HumanApprovalGate()
    role_spec = {"charter_v7_forbidden_classes": ["record_tax_event"]}
    with pytest.raises(IncomeRefused):
        record_tax_event(PRINCIPAL, "entity-formation-decision", category="self_employment", mandate=MANDATE,
                         author=AUTHOR, source_ref="t", at=AT, registry=_reg(tmp_path),
                         gate=gate, role_spec=role_spec, mode="corporate_regulated")


def test_composes_income_only():
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "economy" / "compliance.py"
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography",
                    "objects.registry", "objects.identity", "provision_", "material.", ".pool", ".productivity"):
            assert tok not in ln, f"economy.compliance must compose the income record only, not {tok}"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from .")]
    assert sibling and all(".income" in ln for ln in sibling), "the only sibling import is the income record (S10 V1)"


def test_weakest_party_verdict_is_a_plain_bool(tmp_path):
    r = record_tax_event(PRINCIPAL, "aug-income", category="labor", mandate=MANDATE, author=AUTHOR,
                         source_ref="t", at=AT, registry=_reg(tmp_path), amount=500.0)
    st = verify_tax_event(r, PRINCIPAL, "aug-income", category="labor", amount=500.0)
    assert isinstance(st, IncomeStatus) and isinstance(st.provisioned, bool)
