"""Exposure (risk-from-ledger) invariants — co-extrusion for s5_41 (Option B).

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves exposure as observed
ledger state -- exposure by issuer (per currency, no blend), concentration as each issuer's share of the total, and
issuers breaching a supplied limit. Deliberately NO valuation (live price -> S6-V07) and NO prediction (VaR/scenario ->
S5-V17): it reports what is provably held and how concentrated it is."""
from decimal import Decimal

from sovereign_agent.financials import exposure_by_issuer, concentration, breaches

POS = [
    {"issuer": "UST", "instrument": "tbill", "currency": "USD", "amount": "600000"},
    {"issuer": "ACME", "instrument": "note", "currency": "USD", "amount": "300000"},
    {"issuer": "ACME", "instrument": "equity", "currency": "USD", "amount": "100000"},
    {"issuer": "BUND", "instrument": "bond", "currency": "EUR", "amount": "500000"},
]


def test_exposure_by_issuer_per_currency_no_blend():
    e = exposure_by_issuer(POS)
    assert e[("UST", "USD")] == Decimal("600000")
    assert e[("ACME", "USD")] == Decimal("400000")     # 300k note + 100k equity
    assert e[("BUND", "EUR")] == Decimal("500000")     # distinct currency, never merged into USD


def test_concentration_shares_sum_and_largest():
    c = concentration(POS, "USD")
    assert c["total"] == Decimal("1000000")            # 600k + 400k (EUR excluded)
    assert c["shares"]["UST"] == Decimal("0.6")
    assert c["shares"]["ACME"] == Decimal("0.4")
    assert c["largest"] == Decimal("0.6") and c["largest_issuer"] == "UST"


def test_breaches_reports_issuers_over_limit():
    b = breaches(POS, {"ACME": "250000", "UST": "1000000"}, "USD")
    # ACME 400k > 250k limit -> breach; UST 600k < 1M -> ok
    assert len(b) == 1
    assert b[0]["issuer"] == "ACME" and b[0]["over"] == Decimal("150000")


def test_no_positions_no_concentration():
    c = concentration([], "USD")
    assert c["total"] == Decimal("0") and c["largest"] == Decimal("0")
