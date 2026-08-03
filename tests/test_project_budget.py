"""Project budget/cost + portfolio roll-up invariants — co-extrusion for s5_11 Project & Portfolio Management.

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the budget views a
governed project must satisfy — consumed/remaining/over-budget from committed + actual, and a portfolio roll-up that
surfaces over-budget counts — independently of the governance/immutability the ObligationLedger + financials/posting
supply."""
from decimal import Decimal

import pytest

from sovereign_agent.financials import budget_status, portfolio_roll_up


def test_budget_status_within_budget():
    st = budget_status("100000", committed="30000", actual="50000")
    assert st["consumed"] == Decimal("80000")
    assert st["remaining"] == Decimal("20000")
    assert st["over_budget"] is False and st["overrun"] == Decimal("0")


def test_budget_status_over_budget_reports_overrun_honestly():
    st = budget_status("100000", committed="60000", actual="50000")
    assert st["over_budget"] is True
    assert st["overrun"] == Decimal("10000")   # 110k consumed vs 100k budget
    assert st["remaining"] == Decimal("-10000")


def test_budget_rejects_negative_inputs():
    with pytest.raises(ValueError):
        budget_status("-1", "0", "0")
    with pytest.raises(ValueError):
        budget_status("100", "-1", "0")


def test_portfolio_roll_up_surfaces_over_budget_count():
    roll = portfolio_roll_up([
        {"budget": "100", "committed": "50", "actual": "40"},   # ok
        {"budget": "100", "committed": "80", "actual": "40"},   # over by 20
        {"budget": "100", "committed": "0", "actual": "0"},     # ok
    ])
    assert roll["projects"] == 3
    assert roll["budget"] == Decimal("300")
    assert roll["over_budget_projects"] == 1
