# -*- coding: utf-8 -*-
"""sovereign_ux.gate_interaction — Breath-Gated Interfaces (S8 Vol 2).

The operator layer's WRITE discipline: a surface never applies a proposed action. It **proposes** it
as a DRAFT obligation, surfaces it for human **review**, and **disposes** of it only by an
attributable human assent scoped to the actor's mandate — landing in the LEDGER-BACKED constitutional
gate with a minted receipt. The surface transports the word; the write is the core's.

    propose(ledger, title)  → open a DRAFT obligation (the action is NOT applied)
    review(ledger)          → the open, undisposed obligations (ledger-backed, honest)
    dispose(ledger, id, …)  → human breath-gate + mandate_guard (deny-by-default), then close with evidence

**Honesty boundary — the volume's spine (two surfaces, never conflated):**
  * The SESSION-SCOPED breath-gate view (`session_view`) is a convenience read that is honestly EMPTY
    until something is opened in THIS session; it persists nothing. *Empty is honest, not a stub* — it
    never implies the persistence it lacks.
  * The LEDGER-BACKED obligation gate (`obligations/ledger.py`) is the constitutional truth:
    append-only, hash-chained; the material record of who proposed, who assented at the breath-gate,
    and the evidence on close.
Material dispositions ALWAYS travel through the ledger. This module composes the sealed
`ObligationLedger` (the AH-1 invariant: a gate-less ledger CANNOT approve a material obligation —
deny-by-default, fail-closed) and `mandate_guard` (the scoping principal, S5 Vol 28 — a principal not
holding the obligation's mandate is barred). It **rolls no cryptography**.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from ..obligations.ledger import ObligationLedger  # the ledger-backed constitutional gate (composed)
from ..obligations import mandate_guard            # the S5 Vol 28 scoping principal (composed)

__all__ = [
    "propose", "review", "dispose", "session_view",
    "GateDenied", "SESSION_VIEW_NOTE",
]


class GateDenied(RuntimeError):
    """A disposition refused at the breath-gate or by mandate scope — fail-closed, and recorded."""


SESSION_VIEW_NOTE = (
    "Session-scoped breath-gate view. Empty is honest, not a stub — this surface persists nothing "
    "and never implies otherwise. The constitutional gate for a material disposition is the "
    "ledger-backed obligation gate (obligations/ledger.py); use review()/dispose() for that."
)


def propose(ledger: ObligationLedger, title: str, *, owner: Optional[str] = None,
            material: bool = False, mandate: Optional[str] = None,
            intent: Optional[str] = None, ref: Optional[str] = None) -> str:
    """Propose an action — open it as a DRAFT obligation. The action is **not applied**; only a
    draft debit is recorded. Returns the obligation id. A material proposal will require a human
    breath-gate to dispose (never an auto-approve).
    """
    debit = ledger.open(title, owner=owner, material=material, mandate=mandate,
                        intent=intent, ref=ref)
    oid = debit.get("id") or debit.get("obligation_id")
    if not oid:
        raise ValueError("ledger.open did not return an obligation id")
    return oid


def review(ledger: ObligationLedger) -> list:
    """The open, undisposed obligations from the LEDGER — the constitutional pending list.

    This reads the ledger-backed truth, not a session store. An obligation appears here from the
    moment it is proposed until it is disposed (approved+closed, or rejected).
    """
    out = []
    for e in ledger.iter_entries():
        if e.get("type") == "debit":
            oid = e.get("id")
            if oid and not ledger._is_closed(oid):  # the ledger's own canonical closed-check
                out.append(e)
    return out


def dispose(ledger: ObligationLedger, obligation_id: str, *, approver: str,
            held_mandates: Optional[Sequence[str]] = None,
            cross_mandate_auth: Optional[Mapping[str, Any]] = None,
            evidence: Optional[str] = None, rationale: str = "",
            reject: bool = False) -> dict:
    """Dispose of a proposed action, human-gated and mandate-scoped.

    * ``reject=True`` — a human REFUSAL. A 'no' needs no breath-gate; the obligation is closed as
      rejected. (``evidence`` may record why.)
    * otherwise — APPROVE: the ledger's breath-gate must assent (a gate-less ledger denies a material
      obligation, fail-closed — AH-1), and if the obligation is scoped to a mandate, ``held_mandates``
      must contain it (or an explicit ``cross_mandate_auth``), else it is barred (deny-by-default,
      S5 Vol 28). On assent, the obligation is closed with ``evidence`` and a receipt is minted.

    Raises :class:`GateDenied` when the breath-gate or the mandate scope refuses.
    """
    if reject:
        return ledger.close(obligation_id, evidence or "human refusal — action declined",
                            closed_by=approver, rejected=True, require_e1=False)
    try:
        approval = ledger.approve(obligation_id, approved_by=approver, rationale=rationale,
                                  held_mandates=list(held_mandates) if held_mandates else None,
                                  cross_mandate_auth=dict(cross_mandate_auth) if cross_mandate_auth else None)
    except Exception as exc:  # the ledger raises + records on a denied breath-gate / mandate bar
        raise GateDenied(str(exc)) from exc
    if str(approval.get("disposition") or approval.get("status") or "approved") == "denied":
        raise GateDenied(f"breath-gate denied the disposition of {obligation_id!r}")
    if evidence is None:
        return approval
    return ledger.close(obligation_id, evidence, closed_by=approver)


def session_view(items: Optional[Sequence[dict]] = None) -> dict:
    """The session-scoped breath-gate convenience view. Honestly EMPTY when nothing was opened in
    this session — it persists nothing and never implies otherwise (the honesty boundary).
    """
    return {
        "scope": "session",
        "persists": False,
        "pending": list(items) if items else [],
        "constitutional_gate": "obligations/ledger.py (ledger-backed)",
        "note": SESSION_VIEW_NOTE,
    }
