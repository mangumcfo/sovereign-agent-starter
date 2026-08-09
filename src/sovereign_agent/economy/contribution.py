# -*- coding: utf-8 -*-
"""economy.contribution — Sovereign Livelihood (Series 10, Vol 1: Building Income & Productivity on Rails
You Own). The concrete-sources layer over the Income Primitive.

A **contribution** is an income the earner OWNS, tagged with a **proof grade** — its *contribution class* —
and a concrete **source**. It turns what a person already has (surplus energy, idle compute/storage,
verification work, skills, local production) into a receipted, owned income. It **composes
`attribute_income`/`verify_income` (income.py) and nothing else** — so every contribution inherits the
Income Primitive's guarantees: owned by the earner (its mandate), money-path OFF (an amount is an
attribution, value rides the sealed Port S6 Vol 7, the record holds no value), human primacy (a gated
contribution passes a HumanApprovalGate S5 Vol 16), and weakest-party verifiability (the earner confirms
ownership from a receipt they hold). It records nothing of its own and rolls no cryptography.

Contribution classes = the four proof grades (Atlas Ch2): **computed** (the node derives it from its own
data) · **metered** (a meter reading — kWh, compute-seconds, stored GB) · **attested** (a human or peer
attests — a skill, a service) · **hybrid** (two or more proof sources). Concrete sources (Atlas Ch3–5) are
thin, honest wrappers that fix a source and a sensible default class. A personal contribution ledger (Atlas
Ch6) summarises an earner's own contribution receipts by class — a productivity view, holding no value.

Kill-targets: **composes income.py only** (no registry of its own, no crypto, no held value) · **proof grade
is honest** (an unknown class is refused; a tampered class/source flips the light) · **money-path OFF**
(inherited) · **weakest-party** (verify a contribution from the receipt alone). OUT — money reconcile homes
to Treasury/Controlling/Revenue (S5); tax/compliance to Tax + Compliance & Audit (S5 Vol 16, full home in
V04); people/payroll to Human Capital & Sovereign Payroll (S5) where a contribution class is labor;
exit/succession & inheritance to Generational Continuity (S5 Vol 29) / Generational Transfer (S12), full home
in V05.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence

from .income import attribute_income, verify_income, IncomeRefused, IncomeStatus  # S10 V1 primitive — composed by identity

__all__ = ["record_contribution", "verify_contribution", "contribution_ledger",
           "contribute_surplus_energy", "contribute_idle_compute", "contribute_storage",
           "contribute_verification_work", "contribute_skill_service", "contribute_local_production",
           "CONTRIBUTION_CLASSES", "SOURCE_DEFAULT_CLASS",
           "IncomeRefused", "IncomeStatus", "LedgerStatus"]

# The four proof grades (Atlas Ch2 — computed / metered / attested / hybrid).
CONTRIBUTION_CLASSES = frozenset({"computed", "metered", "attested", "hybrid"})

# Concrete sources (Atlas Ch3–5) → their honest default proof grade.
SOURCE_DEFAULT_CLASS = {
    "surplus_energy": "metered",        # a meter reads the dispatched kWh
    "idle_compute": "metered",          # compute-seconds are metered
    "storage": "metered",               # stored GB·time is metered
    "verification_work": "computed",    # the node computes the verification performed
    "skill_service": "attested",        # a counterparty attests the service
    "local_production": "attested",     # a receiver attests the goods
}


def _contribution_extra(contribution_class: str, source: str,
                        extra: Optional[Mapping[str, Any]]) -> dict:
    """The attribution fields that make an income a proof-graded contribution — records, not value."""
    cc = str(contribution_class).strip().lower()
    if cc not in CONTRIBUTION_CLASSES:
        raise IncomeRefused(
            f"unknown contribution class {contribution_class!r} — the proof grade must be one of "
            f"{sorted(CONTRIBUTION_CLASSES)} (computed/metered/attested/hybrid)")
    if not str(source).strip():
        raise IncomeRefused("a contribution requires a concrete source — what the earner already has")
    out = {"contribution_class": cc, "source": str(source)}
    if extra:
        for k, v in dict(extra).items():
            out[str(k)] = v
    return out


def record_contribution(earner: str, source: str, work_ref: str, *, contribution_class: str, mandate: str,
                        author: str, source_ref: str, at: str, registry: Any, amount: Any = None,
                        unit: str = "credits", port_ref: Optional[str] = None,
                        extra: Optional[Mapping[str, Any]] = None, approver: Optional[str] = None,
                        approval_ref: Optional[str] = None, gate: Any = None,
                        action_class: str = "record_contribution",
                        role_spec: Optional[Mapping[str, Any]] = None, mode: str = "live") -> dict:
    """Record a concrete contribution as an income the earner OWNS, proof-graded by its contribution class.
    Composes `attribute_income` (S10 V1): the contribution's class + source ride the record as attribution
    fields; the amount (if any) is an attribution, value rides the sealed Port. A gated contribution passes a
    human (HumanApprovalGate). Returns the earner's receipt. Records no value; rolls no cryptography."""
    ex = _contribution_extra(contribution_class, source, extra)
    return attribute_income(earner, work_ref, mandate=mandate, author=author, source_ref=source_ref, at=at,
                            registry=registry, amount=amount, unit=unit, port_ref=port_ref, extra=ex,
                            approver=approver, approval_ref=approval_ref, gate=gate,
                            action_class=action_class, role_spec=role_spec, mode=mode)


def verify_contribution(receipt: Mapping[str, Any], earner: str, work_ref: str, *, contribution_class: str,
                        source: str, amount: Any = None, unit: str = "credits",
                        port_ref: Optional[str] = None,
                        extra: Optional[Mapping[str, Any]] = None) -> IncomeStatus:
    """Weakest-party check: the earner confirms they OWN this contribution — and that its proof grade + source
    are as recorded — from the receipt alone. Composes `verify_income` (S10 V1) over the contribution's
    attribution fields; a tampered class, source, or amount flips the light. No platform, no second device."""
    ex = _contribution_extra(contribution_class, source, extra)
    return verify_income(receipt, earner, work_ref, amount=amount, unit=unit, port_ref=port_ref, extra=ex)


# ── Concrete-source helpers (Atlas Ch3–5): honest wrappers over record_contribution ──────────────────────
def _by_source(source: str, earner: str, work_ref: str, *, contribution_class: Optional[str] = None,
               **kw) -> dict:
    return record_contribution(earner, source, work_ref,
                               contribution_class=(contribution_class or SOURCE_DEFAULT_CLASS[source]), **kw)


def contribute_surplus_energy(earner: str, work_ref: str, **kw) -> dict:
    """Atlas Ch3 — income from surplus energy generation & flexibility (dispatch, grid services). Metered."""
    return _by_source("surplus_energy", earner, work_ref, **kw)


def contribute_idle_compute(earner: str, work_ref: str, **kw) -> dict:
    """Atlas Ch4 — income from spare compute capacity. Metered."""
    return _by_source("idle_compute", earner, work_ref, **kw)


def contribute_storage(earner: str, work_ref: str, **kw) -> dict:
    """Atlas Ch4 — income from spare storage capacity. Metered."""
    return _by_source("storage", earner, work_ref, **kw)


def contribute_verification_work(earner: str, work_ref: str, **kw) -> dict:
    """Atlas Ch4 — income from verification work the node performs. Computed."""
    return _by_source("verification_work", earner, work_ref, **kw)


def contribute_skill_service(earner: str, work_ref: str, **kw) -> dict:
    """Atlas Ch5 — income from personal skills & services. Attested by the counterparty."""
    return _by_source("skill_service", earner, work_ref, **kw)


def contribute_local_production(earner: str, work_ref: str, **kw) -> dict:
    """Atlas Ch5 — income from small-scale local production. Attested by the receiver."""
    return _by_source("local_production", earner, work_ref, **kw)


# ── The personal contribution ledger (Atlas Ch6): a productivity view, holding no value ───────────────────
@dataclass(frozen=True)
class LedgerStatus:
    """A personal-ledger verdict: whether every contribution verifies as the earner's own, with a by-class
    productivity tally. Holds no value — it summarises receipts the earner already holds."""
    provisioned: bool
    reason: str
    earner: str
    verified_count: int
    by_class: Dict[str, int] = field(default_factory=dict)


def contribution_ledger(earner: str, contributions: Sequence[Mapping[str, Any]]) -> LedgerStatus:
    """Summarise an earner's OWN contribution receipts (Atlas Ch6 — the personal sovereign ledger &
    productivity system). Composes `verify_contribution` over each item `{receipt, work_ref,
    contribution_class, source, amount?, unit?, port_ref?, extra?}`. Returns a by-class tally and a verdict
    that holds iff every contribution verifies as the earner's own. Records nothing, holds no value."""
    by_class = {c: 0 for c in sorted(CONTRIBUTION_CLASSES)}
    verified = 0
    reason = []
    for i, item in enumerate(contributions):
        st = verify_contribution(item["receipt"], earner, item["work_ref"],
                                 contribution_class=item["contribution_class"], source=item["source"],
                                 amount=item.get("amount"), unit=item.get("unit", "credits"),
                                 port_ref=item.get("port_ref"), extra=item.get("extra"))
        if not st.provisioned:
            reason.append(f"contribution {i} ({item.get('source')}) is not the earner's own: {st.reason}")
            continue
        verified += 1
        by_class[str(item["contribution_class"]).strip().lower()] += 1
    ok = bool(contributions) and not reason
    return LedgerStatus(provisioned=ok, reason="; ".join(reason) or "all contributions verified",
                        earner=earner, verified_count=verified, by_class=by_class)
