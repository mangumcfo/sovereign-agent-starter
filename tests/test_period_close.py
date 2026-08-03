"""Period-close invariants — co-extrusion for s5_40 Sovereign Controlling & Financial Close.

Pure arithmetic: NO sealed crypto substrate, so this runs green in a pure public clone (no skip). It proves the
close floor over governed postings — a close is refused unless the period balances and a human approver is named,
closing locks the period, and a posting into a closed period is refused fail-closed. The full close orchestration
workflow is designed-toward (not tested here)."""
from decimal import Decimal

import pytest

from sovereign_agent.financials import (
    Line, post, period_is_balanced, close_period, guard_post_open,
    PeriodNotBalancedError, PeriodClosedError,
)


def _balanced_period():
    return [
        post([Line.dr("5100-COGS", "300.00"), Line.cr("1000-Cash", "300.00")], memo="materials"),
        post([Line.dr("5200-Opex", "150.00"), Line.cr("1000-Cash", "150.00")], memo="services"),
    ]


def test_period_is_balanced_true_for_balanced_postings():
    assert period_is_balanced(_balanced_period()) is True


def test_period_is_balanced_false_for_an_unbalanced_ledger():
    # a raw (un-post()ed) journal whose debits != credits — the gate must catch it
    unbalanced = [{"lines": [
        {"account": "5100-COGS", "debit": "300.00", "credit": "0"},
        {"account": "1000-Cash", "debit": "0", "credit": "250.00"},
    ]}]
    assert period_is_balanced(unbalanced) is False


def test_close_period_returns_a_locked_record():
    rec = close_period("2026-07", _balanced_period(), approver="KM-1176")
    assert rec["closed"] is True and rec["locked"] is True
    assert rec["approver"] == "KM-1176"
    assert rec["postings"] == 2


def test_close_refused_without_approver():
    with pytest.raises(ValueError):
        close_period("2026-07", _balanced_period(), approver="")


def test_close_refused_on_unbalanced_period():
    unbalanced = [{"lines": [
        {"account": "5100-COGS", "debit": "300.00", "credit": "0"},
        {"account": "1000-Cash", "debit": "0", "credit": "250.00"},
    ]}]
    with pytest.raises(PeriodNotBalancedError):
        close_period("2026-07", unbalanced, approver="KM-1176")


def test_guard_refuses_posting_into_a_closed_period():
    rec = close_period("2026-07", _balanced_period(), approver="KM-1176")
    with pytest.raises(PeriodClosedError):
        guard_post_open(rec)


def test_guard_allows_posting_into_an_open_period():
    guard_post_open({"period": "2026-08", "locked": False})  # no raise
