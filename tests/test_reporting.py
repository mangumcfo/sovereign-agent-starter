"""Report-as-projection invariants — co-extrusion for s5_14 (discharges the reporting->S5-V14 debt).

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves P&L, balance sheet,
and cash flow projected from the governed postings + CoA classification: the balance sheet cross-foots fail-closed, and
every figure ties to the trial balance. Statements are recomputed, never stored."""
from decimal import Decimal

import pytest

from sovereign_agent.financials import (
    Line, post, income_statement, balance_sheet, cash_flow_statement, ReportingError,
)

COA = {
    "1000-Cash": {"type": "asset"},
    "1200-AR": {"type": "asset"},
    "3000-Equity": {"type": "equity"},
    "4000-Revenue": {"type": "revenue"},
    "5000-COGS": {"type": "expense"},
}


def _period():
    # equity funding 1000; a sale of 400 on credit costing 250 cash
    return [
        post([Line.dr("1000-Cash", "1000.00"), Line.cr("3000-Equity", "1000.00")]),
        post([Line.dr("1200-AR", "400.00"), Line.cr("4000-Revenue", "400.00")]),
        post([Line.dr("5000-COGS", "250.00"), Line.cr("1000-Cash", "250.00")]),
    ]


def test_income_statement_projects_revenue_minus_expense():
    inc = income_statement(_period(), COA)
    assert inc["revenue"] == Decimal("400.00")
    assert inc["expense"] == Decimal("250.00")
    assert inc["net_income"] == Decimal("150.00")


def test_balance_sheet_cross_foots():
    bs = balance_sheet(_period(), COA)
    # assets: cash 750 + AR 400 = 1150; equity 1000; net income 150 -> 1000+150 = 1150
    assert bs["assets"] == Decimal("1150.00")
    assert bs["equity"] == Decimal("1000.00")
    assert bs["net_income"] == Decimal("150.00")
    assert bs["assets"] == bs["total_liabilities_and_equity"]


def test_balance_sheet_refuses_unbalanced_postings():
    # a raw un-post()ed journal whose debits != credits would break the sheet -> refused
    bad = [{"lines": [
        {"account": "1000-Cash", "debit": "100.00", "credit": "0"},
        {"account": "4000-Revenue", "debit": "0", "credit": "80.00"},
    ]}]
    with pytest.raises(ReportingError):
        balance_sheet(bad, COA)


def test_untyped_account_is_refused():
    p = [post([Line.dr("9999-Mystery", "10.00"), Line.cr("1000-Cash", "10.00")])]
    with pytest.raises(ReportingError):
        income_statement(p, COA)   # 9999-Mystery not in the chart


def test_cash_flow_classifies_and_ties():
    cf = cash_flow_statement([
        {"activity": "operating", "amount": "500.00"},
        {"activity": "operating", "amount": "-200.00"},
        {"activity": "investing", "amount": "-300.00"},
        {"activity": "financing", "amount": "1000.00"},
    ])
    assert cf["operating"] == Decimal("300.00")
    assert cf["investing"] == Decimal("-300.00")
    assert cf["financing"] == Decimal("1000.00")
    assert cf["net_change"] == Decimal("1000.00")


def test_cash_flow_refuses_unknown_activity():
    with pytest.raises(ReportingError):
        cash_flow_statement([{"activity": "speculation", "amount": "1"}])
