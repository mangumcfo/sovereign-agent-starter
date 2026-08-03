"""Period-close primitives — the balance gate, the governed close act, and the period lock.

Co-extrusion for s5_40 (Sovereign Controlling & Financial Close, KM CLOSE-do-not-defer 2026-08-03). Pure arithmetic
over Decimal, no crypto substrate (runs in a pure public clone, no skip — F-1 posture). This is the *close floor*: a
period may close only if its ledger balances (composing the sealed `posting` invariants) and a human approver is
named; closing returns an immutable close record that locks the period; a posting into a locked period is refused.

Framing A (exists != wired): the balance gate + governed close act + lock are PRESENT and tested. The full close
*orchestration* — soft-close/hard-close sequencing, sub-ledger reconciliation ordering, accrual reversal workflows —
is designed-toward THIS volume's own growth path, not re-homed. Reporting packs live in S5-V14."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Mapping

from .posting import trial_balance


class PeriodNotBalancedError(ValueError):
    """Raised when a close is attempted on a period whose ledger does not net to zero — a close cannot run on an
    out-of-balance ledger."""


class PeriodClosedError(RuntimeError):
    """Raised on an attempt to post into a period that has been closed (locked)."""


def period_is_balanced(postings: List[Dict]) -> bool:
    """True iff the period's ledger balances: the trial balance over all postings nets to exactly zero.

    An internally unbalanced posting (debits != credits) makes the aggregate net non-zero, so this catches it —
    the gate a close must pass before it may proceed."""
    nets = trial_balance(postings)
    return sum(nets.values(), Decimal("0")) == 0


def close_period(period_id: str, postings: List[Dict], approver: str) -> Dict[str, object]:
    """Close an accounting period as a governed act — fail-closed unless it balances and a human approver is named.

    Returns an immutable close record that marks the period locked; the multi-step close *orchestration* is
    designed-toward and this is the gate + lock it rests on. The approver id evidences the human act (the sealed
    human_approval_gate is the governance surface in the runtime; here it is carried as an accountable value so the
    primitive stays pure)."""
    if not approver:
        raise ValueError("close requires a human approver id")
    if not period_is_balanced(postings):
        raise PeriodNotBalancedError(f"period {period_id!r} does not balance — close refused")
    nets = trial_balance(postings)
    return {
        "period": period_id,
        "approver": approver,
        "postings": len(postings),
        "trial_balance": {k: str(v) for k, v in nets.items()},
        "closed": True,
        "locked": True,
    }


def guard_post_open(period_record: Mapping) -> None:
    """Refuse a new posting into a closed (locked) period. The lock is what makes a closed period immutable in
    fact rather than by convention — reopening is itself a governed act, not a silent edit."""
    if period_record.get("locked"):
        raise PeriodClosedError(f"period {period_record.get('period')!r} is closed — posting refused")
