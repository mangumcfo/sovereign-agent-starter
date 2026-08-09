# -*- coding: utf-8 -*-
"""economy.compliance — Sovereign Livelihood (Series 10, Vol 4: Operating Legally While Staying Sovereign).

A person can operate legally without handing a compliance intermediary the statutory position over their
economic life. This layer **records** tax events, **attributes** an income category to each, and hands the
principal a **portable reporting package** they carry to their accountant or authority — and it does one thing
more by refusing to do it: **it never files, pays, forms an entity, or represents the principal**. The
statutory act stays with the principal. It composes the sealed income record (S10 V1) and nothing else, so a
tax event is a governed object the principal OWNS, verifiable from a receipt they hold.

The **TAX-FENCE** (parallel in shape to the money-path fence): **permitted** — record a tax event, attribute
an income category, reference the income it derives from, assemble a portable reporting package the principal
holds; **breach → refused** — any in-node field that files a return, pays or remits tax, forms or incorporates
an entity, or represents the principal before an authority (`filing`, `pay_tax`, `remit`, `formation`,
`represent`, `power_of_attorney`, …). Kill-target: **the compliance intermediary that inserts itself as the
statutory authority — the filing engine you must trust and cannot leave — refused**; there is no in-node tax
authority, because the node records and attributes, and the filing/payment/formation is the principal's own
statutory act. Weakest-party: an operator with no second device and no tax expertise verifies their income is
categorized and reportable from a receipt they hold — and that nothing was filed on their behalf. NO TOKEN ·
no yield · rolls no cryptography. Depth homes OUT to Sovereign Tax and Compliance & Audit (S5 Vol 16) and
Analytics & Decision Intelligence (S5 Vol 19); inheritance to Generational Continuity (S5 Vol 29) /
Generational Transfer (S12).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .income import (attribute_income, verify_income,   # the sealed income record (S10 V1) — composed by identity
                     IncomeRefused, IncomeStatus)

__all__ = ["record_tax_event", "verify_tax_event", "reporting_package",
           "ReportingPackage", "TAX_CATEGORIES", "TAX_FENCE_BREACH_FIELDS",
           "IncomeRefused", "IncomeStatus"]

# Income categories for compliant, defensible treatment (Atlas Ch4). A small, honest set — the principal (or
# their accountant) maps these to the statutory categories of their jurisdiction; the node only records the
# category, it does not decide the law.
TAX_CATEGORIES = frozenset({"self_employment", "labor", "capital", "passive", "property", "in_kind", "other"})

# The TAX-FENCE: an in-node field that would FILE, PAY, FORM, or REPRESENT is a breach — refused. The node
# records and attributes; the statutory act stays with the principal.
TAX_FENCE_BREACH_FIELDS = frozenset({
    "filing", "filed", "file_return", "e_file", "efile", "submit_return", "submitted_return", "return_filed",
    "pay_tax", "tax_paid", "remit", "remittance", "withhold_and_remit", "settle_tax",
    "formation", "incorporate", "form_entity", "entity_formed", "register_entity",
    "represent", "representation", "power_of_attorney", "authorized_agent", "statutory_authority",
})


def _tax_extra(category: str, references_income: Optional[str],
               extra: Optional[Mapping[str, Any]]) -> dict:
    """The attribution fields that make an income record a tax event — records, not a statutory act."""
    cc = str(category).strip().lower()
    if cc not in TAX_CATEGORIES:
        raise IncomeRefused(
            f"unknown income category {category!r} — a tax event must state one of {sorted(TAX_CATEGORIES)}; "
            f"the node records the category, the principal (or their accountant) maps it to statutory law")
    out: Dict[str, Any] = {"tax_event": True, "tax_category": cc, "reportable": True}
    if references_income:
        out["references_income"] = str(references_income)
    if extra:
        for k, v in dict(extra).items():
            out[str(k)] = v
    for k in out:                                         # THE TAX-FENCE — refuse any in-node statutory act
        if str(k).lower() in TAX_FENCE_BREACH_FIELDS:
            raise IncomeRefused(
                f"tax event must carry no in-node statutory-act field ('{k}') — the node records and "
                f"attributes; filing, paying, forming an entity, and representing the principal are the "
                f"principal's own statutory acts, never the node's. There is no in-node tax authority.")
    return out


def record_tax_event(principal: str, work_ref: str, *, category: str, mandate: str, author: str,
                     source_ref: str, at: str, registry: Any, references_income: Optional[str] = None,
                     amount: Any = None, unit: str = "credits", port_ref: Optional[str] = None,
                     extra: Optional[Mapping[str, Any]] = None, approver: Optional[str] = None,
                     approval_ref: Optional[str] = None, gate: Any = None,
                     action_class: str = "record_tax_event",
                     role_spec: Optional[Mapping[str, Any]] = None, mode: str = "live") -> dict:
    """Record a tax event as a governed object the principal OWNS, attributing an income category and
    (optionally) the income it derives from. Composes `attribute_income` (S10 V1). It records and attributes —
    it does NOT file, pay, form, or represent (the TAX-FENCE refuses any such field). A gated tax event (e.g.
    a formation decision) passes a human. Returns the principal's receipt. Money-path OFF inherited."""
    ex = _tax_extra(category, references_income, extra)
    return attribute_income(principal, work_ref, mandate=mandate, author=author, source_ref=source_ref, at=at,
                            registry=registry, amount=amount, unit=unit, port_ref=port_ref, extra=ex,
                            approver=approver, approval_ref=approval_ref, gate=gate,
                            action_class=action_class, role_spec=role_spec, mode=mode)


def verify_tax_event(receipt: Mapping[str, Any], principal: str, work_ref: str, *, category: str,
                     references_income: Optional[str] = None, amount: Any = None, unit: str = "credits",
                     port_ref: Optional[str] = None,
                     extra: Optional[Mapping[str, Any]] = None) -> IncomeStatus:
    """Weakest-party check: the principal confirms their income is categorized and reportable — and that
    nothing was filed on their behalf — from the receipt alone. Composes `verify_income` (S10 V1) over the
    tax-event record; a tampered category, reference, or amount flips the light. Because the record carries no
    statutory-act field (the TAX-FENCE), a green light is also proof the node filed nothing."""
    ex = _tax_extra(category, references_income, extra)
    return verify_income(receipt, principal, work_ref, amount=amount, unit=unit, port_ref=port_ref, extra=ex)


@dataclass(frozen=True)
class ReportingPackage:
    """A portable reporting package: the principal's own bundle of verified tax events, carried to their
    accountant or authority. It holds NO statutory authority, files NOTHING, and is complete iff every tax
    event verifies as the principal's own. A by-category tally makes it audit-ready."""
    principal: str
    complete: bool
    reason: str
    event_count: int
    by_category: Dict[str, int] = field(default_factory=dict)


def reporting_package(principal: str, tax_events: Sequence[Mapping[str, Any]]) -> ReportingPackage:
    """Assemble a PORTABLE reporting package (Atlas Ch6 — audit readiness) from the principal's OWN tax events.
    Composes `verify_tax_event` over each item `{receipt, work_ref, category, references_income?, amount?,
    unit?, port_ref?, extra?}`; the package is complete iff every one verifies as the principal's own, and it
    tallies by income category. It holds no statutory authority and files nothing — it is a bundle the
    principal hands over, not a filing the node makes."""
    by_category = {c: 0 for c in sorted(TAX_CATEGORIES)}
    verified = 0
    reason: List[str] = []
    for i, item in enumerate(tax_events):
        st = verify_tax_event(item["receipt"], principal, item["work_ref"], category=item["category"],
                              references_income=item.get("references_income"), amount=item.get("amount"),
                              unit=item.get("unit", "credits"), port_ref=item.get("port_ref"),
                              extra=item.get("extra"))
        if not st.provisioned:
            reason.append(f"tax event {i} ({item.get('category')}) is not the principal's own: {st.reason}")
            continue
        verified += 1
        by_category[str(item["category"]).strip().lower()] += 1
    ok = bool(tax_events) and not reason
    return ReportingPackage(principal=principal, complete=ok,
                            reason="; ".join(reason) or "portable package complete — nothing filed on your behalf",
                            event_count=verified, by_category=by_category)
