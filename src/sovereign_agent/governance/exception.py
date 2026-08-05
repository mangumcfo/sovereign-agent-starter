"""Exception & governance workflows at scale (s5_29 / reading Vol 31).

A governed **exception** is a deviation that must not resolve itself: an out-of-policy event, a limit breach, a
manual override, a stuck obligation. At volume, the failure mode is a second, home-grown approval system standing
beside the real one -- its own roles, its own sign-off, drifting out of step with the governed gates, so that an
exception is "approved" by something the ledger never authorized.

This module refuses that. It builds **one new act -- routing an exception to the right human gate, then resolving it
fail-closed** -- and it builds it by *composing the sealed gates*, not by re-implementing approval:

  * the **human-approval gate** (`compliance.human_approval_gate.HumanApprovalGate.requires_approval`, Compliance &
    Audit) decides whether an exception's action-class *needs* a human -- this module never re-decides that;
  * the **GRC case lifecycle** (`compliance.grc_workflow.new_case/advance/hard_close`, Compliance & Audit) is the
    ordered, gap-gated workflow an exception travels -- this module never re-implements a case;
  * the **mandate authorization** (`obligations.mandate_guard.approval_holds_mandate`, Structural SoD & Access
    Governance) is who is *allowed* to resolve it -- this module never re-checks scope its own way.

What is genuinely new is the **binding**: the default-deny routing decision (a material exception that no gate would
catch is *refused*, not waved through) and the fail-closed resolution (authorized under the exception's mandate AND
signed off through the governed case, or it does not resolve). No second approval engine is added -- only the routing
and the lifecycle over the sealed gates.

Pure composition (no ledger, no merkle): runs green on a bare public clone."""
from __future__ import annotations

from typing import Dict, List, Mapping, Sequence

from ..compliance.human_approval_gate import HumanApprovalGate
from ..compliance import grc_workflow
from ..obligations.mandate_guard import approval_holds_mandate

# The ordered lifecycle an exception case travels. `detect` is stamped at routing (the exception was found and
# classified); `review` and `resolve` are the governed steps the human gate drives at resolution. The hard close is
# the sign-off itself, not a step -- mirroring the sealed GRC workflow's own shape.
EXCEPTION_STEPS = ("detect", "review", "resolve")


class ExceptionError(ValueError):
    """Raised when an exception is routed to no human gate but is material (default-deny), when a resolution is
    attempted out of lifecycle, by a party that does not hold the exception's mandate, or against an open compliance
    gap. Fail-closed: an exception that cannot be governed does not resolve."""


def open_exception(
    exception_id: str,
    action_class: str,
    mandate: str,
    description: str,
    materiality: str = "high",
) -> Dict[str, object]:
    """Open a governed exception: an id, its action-class (what kind of deviation -- the key the human gate classifies
    on), the mandate that governs its resolution, a description, and a materiality. Status starts `open` -- unrouted,
    and therefore unresolvable. A material exception (the default) cannot later auto-resolve; it must pass a gate."""
    if not exception_id:
        raise ExceptionError("an exception needs an id")
    if not action_class:
        raise ExceptionError("an exception needs an action_class -- the human gate classifies on it")
    if not mandate:
        raise ExceptionError("an exception needs a governing mandate -- resolution is authorized against it")
    if materiality not in ("high", "low"):
        raise ExceptionError(f"unknown materiality {materiality!r}; expected 'high' or 'low'")
    return {
        "exception": exception_id,
        "action_class": action_class,
        "mandate": mandate,
        "description": description,
        "materiality": materiality,
        "status": "open",
    }


def route(
    exception: Mapping,
    policy: Mapping,
    role_spec: Mapping,
    mode: str = "corporate_regulated",
    detected_by: str = "exception-detection",
) -> Dict[str, object]:
    """Route an opened exception to the right disposition by **asking the sealed human-approval gate** whether its
    action-class requires a human (`HumanApprovalGate(policy).requires_approval`) -- this module does not re-decide
    that. Two honest outcomes, plus one refusal:

      * **requires a human** -> open a governed GRC case (`grc_workflow.new_case`) and stamp its `detect` step; status
        becomes `pending_gate`. The exception now waits for a fail-closed resolution.
      * **does not require a human AND immaterial** -> status `auto_resolved`; recorded, no gate needed.
      * **does not require a human BUT material** -> **refused** (`ExceptionError`). Default-deny: a material exception
        that the policy would let pass ungated is a governance gap, not a fast path. It must be gated or the policy
        fixed -- it is never silently auto-resolved.

    `policy` and `role_spec` are the sealed gate's own inputs (`high_materiality_classes`,
    `charter_v7_forbidden_classes`) -- passed straight through, not reinterpreted here."""
    if exception.get("status") != "open":
        raise ExceptionError(
            f"exception {exception.get('exception')!r} is {exception.get('status')!r}, not 'open' -- route once, at open"
        )
    gate = HumanApprovalGate(dict(policy))
    needs_human = gate.requires_approval(str(exception["action_class"]), dict(role_spec), mode)
    if needs_human:
        case = grc_workflow.new_case(str(exception["exception"]), EXCEPTION_STEPS)
        case = grc_workflow.advance(case, "detect", detected_by)
        routed = dict(exception)
        routed["status"] = "pending_gate"
        routed["case"] = case
        return routed
    # No human required by the sealed gate. Default-deny for anything material.
    if str(exception.get("materiality")) == "high":
        raise ExceptionError(
            f"material exception {exception.get('exception')!r} (action_class "
            f"{exception.get('action_class')!r}) routes to no human gate -- refused. A material exception must pass a "
            "gate; gate the class or fix the policy. It is not auto-resolved."
        )
    routed = dict(exception)
    routed["status"] = "auto_resolved"
    return routed


def resolve(
    routed: Mapping,
    approval: Mapping,
    checks_results: Sequence[Mapping] = (),
) -> Dict[str, object]:
    """Resolve a routed, gate-pending exception -- **fail-closed on every governed gate, in order**:

      1. the exception must be `pending_gate` (an `auto_resolved` or already-`resolved` exception has no gate to pass);
      2. the approver must **hold the exception's mandate** (`mandate_guard.approval_holds_mandate` over the
         exception's mandate) -- a party that does not is *barred*, no matter what disposition they carry;
      3. the approval must name a human approver;
      4. the governed case is driven to completion and **signed off** through the sealed GRC workflow
         (`advance` `review` -> `advance` `resolve` -> `hard_close`), which itself refuses an open compliance gap.

    Only when all four pass does the exception become `resolved`, carrying the closed case. The authorization is the
    sealed mandate guard's; the sign-off is the sealed GRC workflow's; the resolution adds no approval of its own."""
    if routed.get("status") != "pending_gate":
        raise ExceptionError(
            f"exception {routed.get('exception')!r} is {routed.get('status')!r}, not 'pending_gate' -- only a "
            "gate-pending exception resolves through the human gate"
        )
    # Authorization: the sealed mandate guard decides, over the exception's own mandate. A non-holder is barred.
    debit = {"mandate": routed["mandate"]}
    if not approval_holds_mandate(debit, dict(approval)):
        raise ExceptionError(
            f"resolution of {routed.get('exception')!r} barred: approver does not hold the exception's mandate "
            f"{routed.get('mandate')!r}"
        )
    approver = str(approval.get("approver", "")).strip()
    if not approver:
        raise ExceptionError("resolution requires a named human approver")
    # Sign-off: drive the sealed GRC case to close. hard_close refuses an open compliance gap on its own.
    case = grc_workflow.advance(routed["case"], "review", approver)
    case = grc_workflow.advance(case, "resolve", approver)
    case = grc_workflow.hard_close(case, list(checks_results), approver)
    resolved = dict(routed)
    resolved["status"] = "resolved"
    resolved["case"] = case
    resolved["resolved_by"] = approver
    return resolved


def route_batch(
    exceptions: Sequence[Mapping],
    policy: Mapping,
    role_spec: Mapping,
    mode: str = "corporate_regulated",
    detected_by: str = "exception-detection",
) -> Dict[str, object]:
    """Route a high-volume batch of exceptions through the **same** `route` primitive -- the scale answer is the same
    governed decision applied per exception, not a bulk shortcut that skips the gate. Returns the routed exceptions
    split by disposition (`pending_gate` awaiting a human, `auto_resolved` recorded) and the refusals (material
    exceptions no gate would catch), each named -- so a queue of thousands surfaces exactly which need a human, which
    were recorded, and which expose a policy gap, with nothing silently waved through."""
    pending: List[Dict[str, object]] = []
    auto: List[Dict[str, object]] = []
    refused: List[Dict[str, object]] = []
    for exc in exceptions:
        try:
            routed = route(exc, policy, role_spec, mode, detected_by)
        except ExceptionError as e:
            refused.append({"exception": exc.get("exception"), "reason": str(e)})
            continue
        (pending if routed["status"] == "pending_gate" else auto).append(routed)
    return {
        "total": len(exceptions),
        "pending_gate": pending,
        "auto_resolved": auto,
        "refused": refused,
    }
