"""Sovereign ERP Operations Console (s5_32 / reading Vol 34) — proof that the console PROJECTS the sealed surfaces
into one operator inbox and ROUTES one operator intent to the sealed handler, holding no store and no authority of
its own (no second cockpit engine, no second approval system).

Pure composition (no ledger, no merkle) — runs green on a bare public clone; no substrate guard needed."""
import pytest

from sovereign_agent.console import operations as con
from sovereign_agent.console.operations import ConsoleError
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate, ApprovalRequest
from sovereign_agent.governance import exception as ex

POLICY = {"high_materiality_classes": ["credit_limit_override"]}
ROLE_SPEC = {"charter_v7_forbidden_classes": []}


def _gate_with_pending():
    gate = HumanApprovalGate(POLICY)
    gate.request_approval(ApprovalRequest(
        action_class="wire_transfer", role_id="treasury", principal_id="ops-1",
        risk_level="high", rationale="urgent vendor", required_approvers=["cfo"]))
    gate.request_approval(ApprovalRequest(
        action_class="format_note", role_id="clerk", principal_id="ops-2",
        risk_level="low", rationale="cosmetic", required_approvers=["lead"]))
    return gate


def _pending_exception(exc_id="EXC-1", materiality="high"):
    exc = ex.open_exception(exc_id, "credit_limit_override", "M-CREDIT", "limit breached", materiality)
    return ex.route(exc, POLICY, ROLE_SPEC)  # -> pending_gate


# --- projection: operator_inbox is a pure projection over the sealed surfaces ------------------------------------

def test_inbox_projects_approvals_and_exceptions_into_one_prioritized_list():
    gate = _gate_with_pending()
    inbox = con.operator_inbox(gate.get_pending(), [_pending_exception("EXC-9", "high")])
    assert inbox["count"] == 3
    # highest risk/materiality first (high==0), low last
    assert inbox["items"][0]["priority"] == 0
    assert inbox["items"][-1]["priority"] == 2
    kinds = {it["kind"] for it in inbox["items"]}
    assert kinds == {"approval", "exception"}


def test_every_inbox_item_decomposes_to_its_source_surface():
    gate = _gate_with_pending()
    exc = _pending_exception("EXC-7", "high")
    inbox = con.operator_inbox(gate.get_pending(), [exc])
    for it in inbox["items"]:
        assert it["source"] in ("approval_gate", "exception")
        assert it["ref"]  # ties back to the surface's own id
    # the exception item's ref is the sealed exception's own id, not a console-minted one
    exc_items = [it for it in inbox["items"] if it["kind"] == "exception"]
    assert exc_items[0]["ref"] == "EXC-7"


def test_inbox_refuses_a_non_pending_exception_fail_closed():
    gate = HumanApprovalGate(POLICY)
    # an auto_resolved exception is not gate-pending work
    auto = ex.route(ex.open_exception("EXC-L", "minor_note", "M-X", "trivial", "low"), POLICY, ROLE_SPEC)
    assert auto["status"] == "auto_resolved"
    with pytest.raises(ConsoleError, match="not 'pending_gate'"):
        con.operator_inbox(gate.get_pending(), [auto])


def test_empty_surfaces_give_an_empty_inbox():
    assert con.operator_inbox({}, []) == {"count": 0, "items": []}
    assert con.operator_inbox(None) == {"count": 0, "items": []}


# --- routing: dispatch forwards to the SEALED handler; the console holds no authority ----------------------------

def test_dispatch_approve_gate_records_a_real_disposition_via_the_sealed_gate():
    gate = _gate_with_pending()
    req_id = next(iter(gate.get_pending()))
    out = con.dispatch({"kind": "approve_gate", "ref": req_id, "status": "approved", "approver": "cfo-jane"}, gate=gate)
    assert out["status"] == "approved" and out["real"] is True and out["approver"] == "cfo-jane"
    # the sealed gate owns the queue — the request left it because the SEALED gate disposed it
    assert req_id not in gate.get_pending()


def test_dispatch_resolve_exception_runs_the_sealed_primitive_for_a_mandate_holder():
    routed = _pending_exception("EXC-2", "high")
    approval = {"held_mandates": ["M-CREDIT"], "approver": "controller-jane"}
    out = con.dispatch({"kind": "resolve_exception", "routed": routed, "approval": approval, "checks_results": []})
    assert out["status"] == "resolved" and out["resolved_by"] == "controller-jane"


def test_dispatch_resolve_by_a_non_holder_is_barred_by_the_sealed_handler_not_the_console():
    # THE no-second-approval-system proof: the console grants no authority — a non-holder is barred by the SEALED
    # exception primitive's mandate guard, exactly as if resolve were called directly.
    routed = _pending_exception("EXC-3", "high")
    approval = {"held_mandates": ["M-TREASURY"], "approver": "someone-else"}
    with pytest.raises(ex.ExceptionError, match="does not hold the exception's mandate"):
        con.dispatch({"kind": "resolve_exception", "routed": routed, "approval": approval})


def test_dispatch_of_an_unknown_intent_is_refused():
    with pytest.raises(ConsoleError, match="unknown operator intent"):
        con.dispatch({"kind": "delete_everything"})


def test_dispatch_approve_gate_without_the_gate_is_refused():
    with pytest.raises(ConsoleError, match="requires the sealed human-approval gate"):
        con.dispatch({"kind": "approve_gate", "ref": "approval_1"})
