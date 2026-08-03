"""Report-pack invariants — co-extrusion for s5_14 (Option B+).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves named report packs
(management, statutory) as ordered projections with labels, assembled fail-closed -- an unknown statement key, an
unknown pack name, or a balance sheet that does not cross-foot is refused, never shipped incomplete."""
from decimal import Decimal

import pytest

from sovereign_agent.financials import (
    Line, post, build_pack, build_named_pack, PackError, MANAGEMENT_PACK, STATUTORY_PACK,
)

COA = {"1000-Cash": {"type": "asset"}, "3000-Equity": {"type": "equity"},
       "4000-Revenue": {"type": "revenue"}, "5000-COGS": {"type": "expense"}}


def _period():
    return [
        post([Line.dr("1000-Cash", "1000.00"), Line.cr("3000-Equity", "1000.00")]),
        post([Line.dr("1000-Cash", "400.00"), Line.cr("4000-Revenue", "400.00")]),
        post([Line.dr("5000-COGS", "250.00"), Line.cr("1000-Cash", "250.00")]),
    ]


CF = [{"activity": "operating", "amount": "150.00"}, {"activity": "financing", "amount": "1000.00"}]


def test_management_pack_orders_three_statements_with_labels():
    pack = build_named_pack("management", _period(), COA, CF)
    assert pack["name"] == "management" and pack["count"] == 3
    keys = [s["key"] for s in pack["statements"]]
    labels = [s["label"] for s in pack["statements"]]
    assert keys == ["income_statement", "balance_sheet", "cash_flow"]
    assert labels[0] == "Management P&L"


def test_statutory_pack_orders_balance_sheet_first():
    pack = build_named_pack("statutory", _period(), COA, CF)
    assert pack["statements"][0]["key"] == "balance_sheet"
    assert pack["statements"][0]["label"] == "Statement of Financial Position"


def test_unknown_pack_name_and_key_refused():
    with pytest.raises(PackError):
        build_named_pack("martian-gaap", _period(), COA, CF)
    with pytest.raises(PackError):
        build_pack([("ebitda", "EBITDA")], _period(), COA, CF)  # unknown statement key
    with pytest.raises(PackError):
        build_pack([], _period(), COA, CF)  # empty definition


def test_pack_fails_closed_when_balance_sheet_does_not_cross_foot():
    unbalanced = [{"lines": [
        {"account": "1000-Cash", "debit": "100.00", "credit": "0"},
        {"account": "4000-Revenue", "debit": "0", "credit": "80.00"},
    ]}]
    with pytest.raises(Exception):  # ReportingError propagates through the pack -> fail-closed
        build_named_pack("statutory", unbalanced, COA, CF)
