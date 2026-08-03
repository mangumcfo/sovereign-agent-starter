"""Close orchestration — the multi-step, ordered, soft/hard close workflow over the period-close gate and lock.

Co-extrusion for s5_40 (Sovereign Controlling & Financial Close, KM ratify Option B 2026-08-03). Pure arithmetic /
structural over Decimal, no crypto substrate (runs in a pure public clone, no skip — F-1 posture). The period-close
primitive supplies the gate (a period may close only if it balances and a human approves) and the lock; this module
sequences a real close around it: an ordered list of named steps that must complete in order, a soft close that locks
posting to a period while still allowing gated adjustments, and a hard close that is refused until every step is done
and the ledger balances. What stays external is connectivity to *other* systems' sub-ledgers (pulling an external AP
or payroll sub-ledger to reconcile), which is bank/rails/port connectivity, homed in S6-V07; the ordering, gating, and
soft/hard state of the close itself are here."""
from __future__ import annotations

from typing import Dict, List, Mapping, Sequence

from .period_close import period_is_balanced


class CloseWorkflowError(ValueError):
    """Raised on an out-of-order step, an unknown step, a missing approver, or a hard close attempted before the
    close is complete or on an unbalanced ledger."""


def new_close(period_id: str, steps: Sequence[str]) -> Dict[str, object]:
    """Open a close workflow for a period: an ordered list of named steps, none yet done, state 'open'.

    'open' allows posting; 'soft' locks posting but permits gated adjustments through the remaining steps; 'hard' is
    fully locked (the period-close lock). Steps are the ordered checklist a real close works through -- accruals,
    sub-ledger reconciliations, revaluation -- made governed rather than a spreadsheet tick-list."""
    if not steps:
        raise CloseWorkflowError("a close needs at least one step")
    return {"period": period_id, "steps": list(steps), "done": [], "state": "open"}


def soft_close(wf: Mapping) -> Dict[str, object]:
    """Enter soft close: posting is locked, but the ordered adjustment steps may still be worked. Idempotent from
    'open'; refused once hard-closed."""
    if wf.get("state") == "hard":
        raise CloseWorkflowError(f"period {wf.get('period')!r} is hard-closed")
    w = _copy(wf)
    w["state"] = "soft"
    return w


def complete_step(wf: Mapping, step: str, approver: str) -> Dict[str, object]:
    """Mark the next step done -- fail-closed on an out-of-order step, an unknown step, or a missing approver.

    Steps must complete in their declared order (a close is a sequence, not a set): the step offered must be the next
    not-yet-done step. Each completion carries a human approver, the same governed-act discipline as the close itself."""
    if not approver:
        raise CloseWorkflowError("each close step requires a human approver id")
    if wf.get("state") == "hard":
        raise CloseWorkflowError(f"period {wf.get('period')!r} is hard-closed")
    steps: List[str] = list(wf["steps"])
    done: List[str] = list(wf.get("done", []))
    if step not in steps:
        raise CloseWorkflowError(f"unknown close step {step!r}")
    expected = steps[len(done)] if len(done) < len(steps) else None
    if step != expected:
        raise CloseWorkflowError(f"out-of-order close step {step!r}; expected {expected!r}")
    w = _copy(wf)
    w["done"] = done + [step]
    return w


def hard_close(wf: Mapping, postings: List[Dict], approver: str) -> Dict[str, object]:
    """Hard-close the period: refused unless every step is done, the ledger balances, and a human approver is named.

    This is the orchestration's terminal gate, resting on the period-close balance check. Once hard, the period is
    locked -- guard_post_open (period_close) refuses further postings against the returned record."""
    if not approver:
        raise CloseWorkflowError("hard close requires a human approver id")
    steps: List[str] = list(wf["steps"])
    done: List[str] = list(wf.get("done", []))
    if done != steps:
        remaining = [s for s in steps if s not in done]
        raise CloseWorkflowError(f"cannot hard-close {wf.get('period')!r}: steps remaining {remaining}")
    if not period_is_balanced(postings):
        raise CloseWorkflowError(f"cannot hard-close {wf.get('period')!r}: ledger does not balance")
    w = _copy(wf)
    w["state"] = "hard"
    w["approver"] = approver
    w["locked"] = True
    return w


def _copy(wf: Mapping) -> Dict[str, object]:
    return {"period": wf.get("period"), "steps": list(wf.get("steps", [])),
            "done": list(wf.get("done", [])), "state": wf.get("state", "open")}
