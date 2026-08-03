"""Investment position-view invariants — co-extrusion for s5_41 Treasury Investment & Financing (Option B).

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the treasury position
view over governed acts -- net holdings per (issuer, instrument, currency) and per (issuer, currency), currencies never
blended. Governance of each move (gate/mandate/witness/receipt) comes from the sealed primitives, not tested here."""
from decimal import Decimal

import pytest

from sovereign_agent.financials import holdings, total_by_issuer, InvestmentError


def test_holdings_net_opens_against_closes_per_key():
    h = holdings([
        {"issuer": "UST", "instrument": "bond", "currency": "USD", "amount": "1000000"},
        {"issuer": "UST", "instrument": "bond", "currency": "USD", "amount": "-250000"},
        {"issuer": "ACME", "instrument": "equity", "currency": "USD", "amount": "500000"},
    ])
    assert h[("UST", "bond", "USD")] == Decimal("750000")
    assert h[("ACME", "equity", "USD")] == Decimal("500000")


def test_currencies_never_blended():
    h = holdings([
        {"issuer": "BUND", "instrument": "bond", "currency": "EUR", "amount": "1000"},
        {"issuer": "BUND", "instrument": "bond", "currency": "USD", "amount": "1000"},
    ])
    assert h[("BUND", "bond", "EUR")] == Decimal("1000")
    assert h[("BUND", "bond", "USD")] == Decimal("1000")


def test_total_by_issuer_sums_instruments_per_currency():
    t = total_by_issuer([
        {"issuer": "ACME", "instrument": "equity", "currency": "USD", "amount": "500000"},
        {"issuer": "ACME", "instrument": "note", "currency": "USD", "amount": "200000"},
    ])
    assert t[("ACME", "USD")] == Decimal("700000")


def test_malformed_position_is_refused():
    with pytest.raises(InvestmentError):
        holdings([{"instrument": "bond", "currency": "USD", "amount": "1"}])  # no issuer
