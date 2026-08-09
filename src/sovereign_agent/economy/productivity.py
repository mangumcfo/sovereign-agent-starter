# -*- coding: utf-8 -*-
"""economy.productivity — Sovereign Livelihood (Series 10, Vol 3: Programmable Productivity on Rails You Govern).

A personal productivity system you **govern**, not one that governs you. It turns commitments into
**receipted actions** (intent → receipt), runs **programmable rituals** (governed routines aligned to your
chosen contribution classes), and **measures output by proof grade to inform, never to punish** — all on
rails the person owns. It **composes `contribution.py` (S10 V1) and nothing else**: an intent fulfilled is a
contribution the person owns; a ritual is a set of contributions; a measure is a proof-graded tally that
holds no value. Human primacy is inherited — a gated productivity act passes a named human.

Kill-targets: **composes contribution.py only** · **intent → receipted action** (a commitment becomes an
owned, proof-graded record, not a private metric) · **measurement informs, never punishes** (a tally by
proof grade, holding no value — no normalized performance score that a platform could weaponise) ·
**you govern it** (a gated productivity act passes a human; deny-by-default on the material) · **weakest-party**
(the person verifies their own intent-receipt). OUT — the unified command dashboard/cockpit homes to the
sealed Lens / Atrium (Interface Sovereignty, S8) at six-sov.com/seeit; a livelihood's money reconciles to
Treasury / Controlling / Revenue (S5); inheritance/forking of a productivity system to Generational
Continuity (S5 Vol 29) / Generational Transfer (S12).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .contribution import (record_contribution, verify_contribution, CONTRIBUTION_CLASSES,   # S10 V1
                           IncomeRefused, IncomeStatus)

__all__ = ["record_intent", "verify_intent", "run_ritual", "measure_output",
           "OutputMeasure", "IncomeRefused", "IncomeStatus"]


def record_intent(earner: str, intent: str, work_ref: str, *, contribution_class: str, mandate: str,
                  author: str, source_ref: str, at: str, registry: Any, amount: Any = None,
                  unit: str = "credits", port_ref: Optional[str] = None,
                  extra: Optional[Mapping[str, Any]] = None, approver: Optional[str] = None,
                  approval_ref: Optional[str] = None, gate: Any = None,
                  action_class: str = "record_intent",
                  role_spec: Optional[Mapping[str, Any]] = None, mode: str = "live") -> dict:
    """Turn a commitment (an `intent`) into a **receipted action the person owns** — composes
    `record_contribution` (S10 V1) with the intent as an attribution field and the source `intent`. The
    fulfilled intent is a proof-graded contribution; the person owns the receipt. A gated intent passes a
    human. Money-path OFF inherited."""
    if not str(intent).strip():
        raise IncomeRefused("an intent-to-receipt needs a stated intent — the commitment being made")
    ex = dict(extra or {})
    ex["intent"] = str(intent)
    return record_contribution(earner, "intent", work_ref, contribution_class=contribution_class,
                               mandate=mandate, author=author, source_ref=source_ref, at=at,
                               registry=registry, amount=amount, unit=unit, port_ref=port_ref, extra=ex,
                               approver=approver, approval_ref=approval_ref, gate=gate,
                               action_class=action_class, role_spec=role_spec, mode=mode)


def verify_intent(receipt: Mapping[str, Any], earner: str, intent: str, work_ref: str, *,
                  contribution_class: str, amount: Any = None, unit: str = "credits",
                  port_ref: Optional[str] = None,
                  extra: Optional[Mapping[str, Any]] = None) -> IncomeStatus:
    """Weakest-party check: the person confirms an intent-to-receipt from the receipt they hold. Composes
    `verify_contribution` (S10 V1) with the intent tag; a tampered intent, class, or amount flips the light."""
    ex = dict(extra or {})
    ex["intent"] = str(intent)
    return verify_contribution(receipt, earner, work_ref, contribution_class=contribution_class,
                               source="intent", amount=amount, unit=unit, port_ref=port_ref, extra=ex)


def run_ritual(earner: str, ritual_id: str, steps: Sequence[Mapping[str, Any]], *, mandate: str, author: str,
               source_ref: str, at: str, registry: Any, gate: Any = None,
               role_spec: Optional[Mapping[str, Any]] = None, mode: str = "live") -> List[dict]:
    """Run a **programmable ritual** — a governed routine that records each of its `steps` as a contribution
    of the earner's chosen class (composes `record_contribution`, S10 V1), tagged with the ritual. Each step
    is `{source, work_ref, contribution_class, amount?, unit?, port_ref?, approver?, approval_ref?, extra?}`.
    A gated step passes a human. Returns the list of the earner's receipts. Deny-by-default: a ritual needs an
    id and at least one step; a step with an unknown class is refused by the composed layer."""
    if not str(ritual_id).strip():
        raise IncomeRefused("a ritual needs an id — the routine being run")
    if not steps:
        raise IncomeRefused("a ritual needs at least one step")
    receipts: List[dict] = []
    for i, st in enumerate(steps):
        ex = dict(st.get("extra") or {})
        ex["ritual"] = str(ritual_id)
        ex["ritual_step"] = i
        receipts.append(record_contribution(
            earner, st["source"], st["work_ref"], contribution_class=st["contribution_class"],
            mandate=mandate, author=author, source_ref=source_ref, at=at, registry=registry,
            amount=st.get("amount"), unit=st.get("unit", "credits"), port_ref=st.get("port_ref"), extra=ex,
            approver=st.get("approver"), approval_ref=st.get("approval_ref"), gate=gate,
            action_class="run_ritual", role_spec=role_spec, mode=mode))
    return receipts


@dataclass(frozen=True)
class OutputMeasure:
    """A productivity measure: a proof-graded tally that **informs, never punishes** — it holds no value and
    computes no normalized performance score. It is the person's own picture of their output, by proof grade."""
    earner: str
    verified_count: int
    by_class: Dict[str, int] = field(default_factory=dict)
    reason: str = "measures to inform, not to punish"


def measure_output(earner: str, actions: Sequence[Mapping[str, Any]]) -> OutputMeasure:
    """Measure an earner's OWN productivity by proof grade (Atlas Ch6 — measurement without self-exploitation).
    Composes `verify_contribution` (S10 V1) over each action `{receipt, work_ref, contribution_class, source,
    amount?, unit?, port_ref?, extra?}`; tallies the ones that verify as the earner's own, by class. It holds
    no value and produces NO single performance score — a tally to inform decisions, never a stick."""
    by_class = {c: 0 for c in sorted(CONTRIBUTION_CLASSES)}
    verified = 0
    for a in actions:
        st = verify_contribution(a["receipt"], earner, a["work_ref"],
                                 contribution_class=a["contribution_class"], source=a["source"],
                                 amount=a.get("amount"), unit=a.get("unit", "credits"),
                                 port_ref=a.get("port_ref"), extra=a.get("extra"))
        if st.provisioned:
            verified += 1
            by_class[str(a["contribution_class"]).strip().lower()] += 1
    return OutputMeasure(earner=earner, verified_count=verified, by_class=by_class)
