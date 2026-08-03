"""FX conversion invariants (bounded) — co-extrusion for s5_40 Sovereign Controlling & Financial Close.

Pure arithmetic: NO sealed crypto substrate, so this runs green in a pure public clone (no skip). It proves the
bounded FX floor sealed treasury pointed here — conversion as an explicit act at a supplied rate, refused at a
non-positive rate, same-currency only at rate 1, and converted amounts summed only within one currency (never
blended). The FX rate engine (sourcing, curves, revaluation) is designed-toward (not tested here)."""
from decimal import Decimal

import pytest

from sovereign_agent.financials import convert, combine_converted, FXError


def test_convert_applies_the_supplied_rate_and_records_the_act():
    rec = convert("100.00", "USD", "EUR", "0.90")
    assert rec["to"]["amount"] == Decimal("90.00")
    assert rec["to"]["currency"] == "EUR"
    assert rec["from"] == {"amount": Decimal("100.00"), "currency": "USD"}
    assert rec["rate"] == Decimal("0.90")


def test_convert_refuses_non_positive_rate():
    with pytest.raises(FXError):
        convert("100", "USD", "EUR", "0")
    with pytest.raises(FXError):
        convert("100", "USD", "EUR", "-1.5")


def test_same_currency_conversion_must_use_rate_one():
    ok = convert("100", "USD", "USD", "1")
    assert ok["to"]["amount"] == Decimal("100.00")
    with pytest.raises(FXError):
        convert("100", "USD", "USD", "1.2")


def test_combine_converted_never_blends_currencies():
    recs = [
        convert("100.00", "USD", "EUR", "0.90"),   # -> 90.00 EUR
        convert("50.00", "GBP", "EUR", "1.15"),    # -> 57.50 EUR
        convert("200.00", "EUR", "USD", "1.10"),   # -> 220.00 USD
    ]
    totals = combine_converted(recs)
    assert totals["EUR"] == Decimal("147.50")   # 90.00 + 57.50, same currency only
    assert totals["USD"] == Decimal("220.00")   # distinct — not merged with the EUR total
