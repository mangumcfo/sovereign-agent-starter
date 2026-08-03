"""Close-orchestration invariants — co-extrusion for s5_40 (Option B expansion).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the ordered soft/hard
close workflow over the period-close gate -- steps complete in order with a human approver, soft close locks posting,
and hard close is refused until every step is done and the ledger balances. External sub-ledger connectivity stays in
S6-V07."""
import pytest

from sovereign_agent.financials import (
    Line, post, new_close, soft_close, complete_step, hard_close, CloseWorkflowError,
)

STEPS = ["accruals", "reconcile-ar", "revalue-fx"]


def _balanced():
    return [post([Line.dr("5100-COGS", "300.00"), Line.cr("1000-Cash", "300.00")])]


def test_new_close_opens_with_steps_and_open_state():
    wf = new_close("2026-07", STEPS)
    assert wf["state"] == "open" and wf["done"] == [] and wf["steps"] == STEPS


def test_soft_close_locks_posting_state():
    wf = soft_close(new_close("2026-07", STEPS))
    assert wf["state"] == "soft"


def test_steps_must_complete_in_order_with_an_approver():
    wf = new_close("2026-07", STEPS)
    wf = complete_step(wf, "accruals", approver="KM-1176")
    assert wf["done"] == ["accruals"]
    # out of order -> refused
    with pytest.raises(CloseWorkflowError):
        complete_step(wf, "revalue-fx", approver="KM-1176")
    # missing approver -> refused
    with pytest.raises(CloseWorkflowError):
        complete_step(wf, "reconcile-ar", approver="")


def test_hard_close_refused_until_all_steps_done():
    wf = new_close("2026-07", STEPS)
    wf = complete_step(wf, "accruals", "KM-1176")
    with pytest.raises(CloseWorkflowError):
        hard_close(wf, _balanced(), approver="KM-1176")


def test_hard_close_refused_on_unbalanced_ledger():
    wf = new_close("2026-07", STEPS)
    for s in STEPS:
        wf = complete_step(wf, s, "KM-1176")
    unbalanced = [{"lines": [
        {"account": "5100-COGS", "debit": "300.00", "credit": "0"},
        {"account": "1000-Cash", "debit": "0", "credit": "250.00"},
    ]}]
    with pytest.raises(CloseWorkflowError):
        hard_close(wf, unbalanced, approver="KM-1176")


def test_hard_close_succeeds_when_complete_and_balanced():
    wf = new_close("2026-07", STEPS)
    for s in STEPS:
        wf = complete_step(wf, s, "KM-1176")
    closed = hard_close(wf, _balanced(), approver="KM-1176")
    assert closed["state"] == "hard" and closed["locked"] is True and closed["approver"] == "KM-1176"
