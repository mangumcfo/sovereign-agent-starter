"""Sovereign ERP Operations Console (s5_32 / reading Vol 34) — the operator shell.

An operator running a sovereign ERP faces many governed surfaces: exceptions awaiting a human gate, approval
requests waiting at the breath-gate, migrations in cutover, audits to sign off. The legacy answer is a cockpit — a
big console application with its own store, its own notion of a work item, its own approve button, assembled from
feeds that lag the governed surfaces. That cockpit is a second system of record standing beside the real ones, and
on the items that matter it drifts out of step with them.

This module refuses that. It builds **one new act — an operator shell that BINDS the sealed surfaces**: a
**projection** (`operator_inbox`) that renders one unified, prioritized operator inbox over the sealed surfaces'
own state, and a **router** (`dispatch`) that sends one operator intent to the sealed gate or primitive that owns
it. It is deliberately thin:

  * `operator_inbox` holds **no store** — it is a pure projection over `HumanApprovalGate.get_pending()` (the sealed
    human-approval gate, Compliance & Audit) and the exception primitive's gate-pending queue (the sealed exception
    primitive, Exception & Governance Workflows). Every item decomposes to the surface it came from.
  * `dispatch` holds **no authority** — it approves nothing and resolves nothing itself. It routes an intent to the
    **sealed handler** (`record_disposition` on the gate; `resolve` on the exception primitive), which enforces its
    own gate. An intent with no sealed handler is refused — the console invents no action.

No second cockpit engine, no second approval system, no operations store — only the binding: one view and one
dispatch point over the sealed surfaces. Pure composition (no ledger, no merkle): runs green on a bare clone."""
from __future__ import annotations

from typing import Dict, List, Mapping, Sequence

# Operator priority: the highest-risk / most-material work rises to the top of the inbox. This is a presentation
# ordering over the surfaces' OWN risk/materiality fields — the console assigns no risk of its own, it only reads
# the field each sealed surface already carries and orders by it.
_PRIORITY = {"critical": 0, "high": 0, "material": 0, "medium": 1, "normal": 1, "low": 2}


def _rank(level) -> int:
    return _PRIORITY.get(str(level).lower(), 1)


class ConsoleError(ValueError):
    """Raised when the inbox is asked to project work that is not genuinely pending, or when an operator intent has
    no sealed handler to route to. Fail-closed: the console surfaces only real pending work and dispatches only to a
    sealed gate/primitive — it invents no work item and no action."""


def operator_inbox(
    pending_approvals: Mapping = None,
    pending_exceptions: Sequence[Mapping] = (),
) -> Dict[str, object]:
    """Project ONE unified, prioritized operator inbox over the sealed surfaces — a pure projection, no store.

    `pending_approvals` is `HumanApprovalGate.get_pending()` (the sealed human-approval gate, Compliance & Audit,
    Vol 16): a `{req_id: ApprovalRequest}` map. `pending_exceptions` is the gate-pending queue from the sealed
    exception primitive (`route_batch(...)["pending_gate"]`, Exception & Governance Workflows, Vol 31): a list of
    routed exceptions awaiting a human.

    Each inbox item carries `{source, ref, kind, priority, summary}` and **decomposes to the surface it came from**
    (`source` + `ref`), so the operator's view is the sealed surfaces' state, never a copy that can drift. Items are
    ordered by the surface's own risk/materiality (highest first). The inbox surfaces only genuinely-pending work: an
    exception that is not `pending_gate` is refused into it (fail-closed — the inbox is not a place to park
    non-pending items)."""
    items: List[Dict[str, object]] = []
    for req_id, req in dict(pending_approvals or {}).items():
        items.append({
            "source": "approval_gate",
            "ref": req_id,
            "kind": "approval",
            "priority": _rank(getattr(req, "risk_level", None)),
            "summary": (f"{getattr(req, 'action_class', '?')} by "
                        f"{getattr(req, 'principal_id', '?')} (risk {getattr(req, 'risk_level', '?')})"),
        })
    for exc in pending_exceptions:
        if str(exc.get("status")) != "pending_gate":
            raise ConsoleError(
                f"exception {exc.get('exception')!r} is {exc.get('status')!r}, not 'pending_gate' — the operator "
                "inbox projects only gate-pending work, it is not a store for disposed items"
            )
        items.append({
            "source": "exception",
            "ref": exc.get("exception"),
            "kind": "exception",
            "priority": _rank(exc.get("materiality")),
            "summary": f"{exc.get('action_class', '?')} exception (materiality {exc.get('materiality', '?')})",
        })
    items.sort(key=lambda it: (it["priority"], str(it["ref"])))
    return {"count": len(items), "items": items}


def dispatch(action: Mapping, *, gate=None) -> Dict[str, object]:
    """Route ONE operator intent to the SEALED handler that owns it — fail-closed. The console approves nothing and
    resolves nothing itself; it forwards the operator's action to the sealed gate/primitive, which enforces its own
    authority:

      * `kind == "approve_gate"` -> the sealed `HumanApprovalGate.record_disposition` records the REAL human
        disposition (the console records none of its own; the gate owns the approval).
      * `kind == "resolve_exception"` -> the sealed exception primitive's `resolve` runs, which itself checks the
        mandate guard and drives the GRC sign-off (the console grants no authority; a non-holder is still barred by
        the sealed handler).

    An intent whose `kind` has no sealed handler is refused — the console routes to a sealed surface, it invents no
    action. This is routing, not a second approval system: every dispatched decision is the sealed handler's."""
    kind = str(action.get("kind", ""))
    if kind == "approve_gate":
        if gate is None:
            raise ConsoleError("approve_gate dispatch requires the sealed human-approval gate")
        ref = action.get("ref")
        if not ref:
            raise ConsoleError("approve_gate dispatch requires the pending request ref")
        # The SEALED gate records the real human disposition — the console holds no approval authority of its own.
        return gate.record_disposition(
            ref, action.get("status", "approved"), action.get("approver", "node"), action.get("reason", "")
        )
    if kind == "resolve_exception":
        from ..governance import exception as _exc  # the sealed exception primitive (Vol 31)
        return _exc.resolve(action["routed"], action["approval"], action.get("checks_results", ()))
    raise ConsoleError(
        f"unknown operator intent {kind!r} — the console routes to a sealed handler (approve_gate | "
        "resolve_exception); it invents no action of its own"
    )
