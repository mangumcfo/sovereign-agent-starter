"""Treasury cash-position + liquidity invariants — co-extrusion for s5_08 Treasury & Cash.

Pure arithmetic: NO sealed crypto substrate, so this runs green in a pure public clone (no skip). It proves the
treasury *views* over governed cash movements — net position per account/currency (currencies never mixed) and
honest liquidity coverage — independently of the immutability/governance the ObligationLedger + witness/quorum
supply. Forecasting and FX conversion are deliberately NOT here (designed-toward)."""
from decimal import Decimal

import pytest

from sovereign_agent.financials import cash_position, total_by_currency, liquidity_coverage


def test_cash_position_nets_per_account_and_currency():
    pos = cash_position([
        {"account": "1000-Cash-Op", "currency": "USD", "amount": "100.00"},
        {"account": "1000-Cash-Op", "currency": "USD", "amount": "-30.00"},
        {"account": "1010-Cash-Res", "currency": "USD", "amount": "500.00"},
    ])
    assert pos[("1000-Cash-Op", "USD")] == Decimal("70.00")
    assert pos[("1010-Cash-Res", "USD")] == Decimal("500.00")


def test_currencies_are_never_summed_together():
    pos = cash_position([
        {"account": "1000-Cash", "currency": "USD", "amount": "100"},
        {"account": "1000-Cash", "currency": "EUR", "amount": "100"},
    ])
    # same account, two currencies -> two distinct positions, never one cross-currency total
    assert pos[("1000-Cash", "USD")] == Decimal("100")
    assert pos[("1000-Cash", "EUR")] == Decimal("100")
    totals = total_by_currency(pos)
    assert totals == {"USD": Decimal("100"), "EUR": Decimal("100")}


def test_liquidity_coverage_reports_shortfall_honestly():
    covered = liquidity_coverage("1000", "800")
    assert covered["covered"] is True and covered["shortfall"] == Decimal("0")
    short = liquidity_coverage("800", "1000")
    assert short["covered"] is False and short["shortfall"] == Decimal("200")


def test_liquidity_rejects_negative_inputs():
    with pytest.raises(ValueError):
        liquidity_coverage("-1", "100")
    with pytest.raises(ValueError):
        liquidity_coverage("100", "-1")
