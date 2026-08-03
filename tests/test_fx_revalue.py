"""FX rate-table + revaluation invariants — co-extrusion for s5_40 (Option B expansion).

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the governed rate
table (rates entered, not sourced) and period-end revaluation of open foreign balances into an unrealized gain/loss,
each a recorded conversion act, currencies never blended. Live market-rate sourcing / forward curves stay external
(S6-V07)."""
from decimal import Decimal

import pytest

from sovereign_agent.financials import rate_for, revalue, FXError

TABLE = {
    ("EUR", "USD", "2026-07-31"): "1.10",
    ("GBP", "USD", "2026-07-31"): "1.28",
}


def test_rate_for_returns_a_governed_rate():
    assert rate_for(TABLE, "EUR", "USD", "2026-07-31") == Decimal("1.10")


def test_rate_for_refuses_a_missing_rate():
    with pytest.raises(FXError):
        rate_for(TABLE, "JPY", "USD", "2026-07-31")   # not in the governed table
    with pytest.raises(FXError):
        rate_for(TABLE, "EUR", "USD", "2026-08-31")   # wrong date


def test_revalue_reports_unrealized_gain_and_loss():
    # 1000 EUR booked at 1050 USD; closing rate 1.10 -> 1100 USD -> +50 unrealized gain
    # 500 GBP booked at 650 USD; closing rate 1.28 -> 640 USD -> -10 unrealized loss
    open_bals = [
        {"amount": "1000.00", "currency": "EUR", "book_value": "1050.00"},
        {"amount": "500.00", "currency": "GBP", "book_value": "650.00"},
    ]
    res = revalue(open_bals, TABLE, base_ccy="USD", as_of="2026-07-31")
    by_ccy = {r["currency"]: r for r in res}
    assert by_ccy["EUR"]["closing_value"] == Decimal("1100.00")
    assert by_ccy["EUR"]["unrealized_gl"] == Decimal("50.00")
    assert by_ccy["GBP"]["closing_value"] == Decimal("640.00")
    assert by_ccy["GBP"]["unrealized_gl"] == Decimal("-10.00")


def test_revalue_skips_base_currency_and_refuses_missing_rate():
    # a USD balance is not revalued (nothing to convert)
    res = revalue([{"amount": "100", "currency": "USD", "book_value": "100"}], TABLE, "USD", "2026-07-31")
    assert res == []
    # a foreign balance with no governed rate is refused, not guessed
    with pytest.raises(FXError):
        revalue([{"amount": "100", "currency": "JPY", "book_value": "1"}], TABLE, "USD", "2026-07-31")
