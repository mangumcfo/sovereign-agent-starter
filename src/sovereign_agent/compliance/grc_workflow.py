"""GRC workflow — the governance-risk-compliance workflow floor: an ordered compliance case
(open → evidence → checks → package → sign-off) with soft steps and a hard close, where an out-of-order step is refused
and an open compliance gap blocks the hard close.

Co-extrusion for s5_14 (Compliance & Audit + Reporting, KM Option B+ 2026-08-03). Pure / structural, no crypto substrate
(runs in a pure public clone, no skip — F-1 posture). A compliance exercise -- preparing for an audit, closing a control
review -- is a sequence: open the case, gather evidence, run the checks, build the audit package, and sign off. This
module makes that sequence a governed workflow over the audit-checks and audit-package primitives: steps complete in
order, each carrying a human, and the hard close (sign-off) is refused unless every step is done, the checks show no
open gap, and an approver is named. The advanced case-management depth (assignment, escalation, SLAs) deepens within
this volume; the ordered, gap-gated workflow floor runs today."""
from __future__ import annotations

from typing import Dict, List, Mapping, Sequence

from .audit_checks import audit_readiness

# canonical ordered compliance workflow steps (the hard close is the sign-off itself, not a step)
STEPS = ("open", "evidence", "checks", "package")


class GRCError(ValueError):
    """Raised on an out-of-order or unknown step, a missing approver, or a hard close attempted with an open gap or an
    incomplete workflow."""


def new_case(case_id: str, steps: Sequence[str] = STEPS) -> Dict[str, object]:
    """Open a GRC case: an id, the ordered steps, none yet done, state 'open'. Steps default to the canonical
    open→evidence→checks→package→sign-off; a caller may supply their own ordered list (non-empty)."""
    if not case_id:
        raise GRCError("a case needs an id")
    if not steps:
        raise GRCError("a case needs at least one step")
    return {"case": case_id, "steps": list(steps), "done": [], "state": "open"}


def advance(case: Mapping, step: str, approver: str) -> Dict[str, object]:
    """Complete the next step of the case -- fail-closed on an unknown step, an out-of-order step, or a missing
    approver. Steps must complete in their declared order (a compliance case is a sequence, not a set)."""
    if not approver:
        raise GRCError("each step requires a human approver id")
    if case.get("state") == "closed":
        raise GRCError(f"case {case.get('case')!r} is closed")
    steps: List[str] = list(case["steps"])
    done: List[str] = list(case.get("done", []))
    if step not in steps:
        raise GRCError(f"unknown step {step!r}")
    expected = steps[len(done)] if len(done) < len(steps) else None
    if step != expected:
        raise GRCError(f"out-of-order step {step!r}; expected {expected!r}")
    w = _copy(case)
    w["done"] = done + [step]
    w["state"] = "in_progress"
    return w


def hard_close(case: Mapping, checks_results: List[Mapping], approver: str) -> Dict[str, object]:
    """Sign off (hard close) the case -- refused unless every step is done, the checks show NO open gap, and a human
    approver is named. An open compliance gap blocks the hard close: a case cannot be signed off out of compliance.

    `checks_results` is the output of `audit_checks.run_checks`; readiness is computed from it, and a not-ready case is
    refused with its gaps named."""
    if not approver:
        raise GRCError("sign-off requires a human approver id")
    steps: List[str] = list(case["steps"])
    done: List[str] = list(case.get("done", []))
    if done != steps:
        remaining = [s for s in steps if s not in done]
        raise GRCError(f"cannot sign off {case.get('case')!r}: steps remaining {remaining}")
    readiness = audit_readiness(checks_results)
    if not readiness["ready"]:
        raise GRCError(f"cannot sign off {case.get('case')!r}: open compliance gaps {readiness['gaps']}")
    w = _copy(case)
    w["state"] = "closed"
    w["approver"] = approver
    w["signed_off"] = True
    return w


def _copy(case: Mapping) -> Dict[str, object]:
    return {"case": case.get("case"), "steps": list(case.get("steps", [])),
            "done": list(case.get("done", [])), "state": case.get("state", "open")}
