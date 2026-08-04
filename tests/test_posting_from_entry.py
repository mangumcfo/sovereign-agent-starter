"""posting.from_entry consumer adapter — the ledger-bound-emitter -> sealed-posting composition (AA meta lane, KM 2026-08-04).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the three-way-match AP
posting (procurement.ap_entry) composes the sealed double-entry posting invariants via financials.from_entry WITHOUT
changing ap_entry's return shape, and that a tampered (unbalanced) entry is refused fail-closed."""
from decimal import Decimal
import pytest
from sovereign_agent.financials import from_entry, post, trial_balance, UnbalancedPostingError
from sovereign_agent.procurement import three_way_match, ap_entry

PO = {"po_id": "PO-9", "lines": [{"item": "plate", "quantity": "20", "unit_price": "15.00"}]}
GR = {"lines": [{"item": "plate", "quantity": "20"}]}
INV = {"invoice_id": "INV-9", "lines": [{"item": "plate", "quantity": "20", "unit_price": "15.00"}]}


def test_ap_entry_composes_sealed_posting_unchanged():
    entry = ap_entry(three_way_match(PO, GR, INV))          # sealed procurement emitter, shape unchanged
    assert entry["balanced"] is True and entry["amount"] == Decimal("300.00")
    posting = from_entry(entry)                             # adapter reads the shape -> sealed posting
    assert posting["balanced"] is True
    assert posting["amount"] == "300.00"                   # 20 * 15.00
    # every emitter debit/credit line survived into the ledger-ready posting
    accts = {l["account"] for l in posting["lines"]}
    assert "GR/IR clearing" in accts and "accounts payable" in accts
    assert "ap_entry INV-9" in posting["memo"]


def test_from_entry_is_a_pure_adapter_not_a_rewrite():
    # ap_entry's return shape is the sealed contract; from_entry must not mutate it.
    entry = ap_entry(three_way_match(PO, GR, INV))
    before = dict(entry)
    from_entry(entry)
    assert entry == before                                 # emitter record untouched by the adapter


def test_bridged_entry_nets_zero_in_trial_balance():
    posting = from_entry(ap_entry(three_way_match(PO, GR, INV)))
    tb = trial_balance([posting])                          # the bridged posting is ledger-ready
    assert sum(tb.values(), Decimal("0")) == Decimal("0")  # a balanced posting nets to zero


def test_unbalanced_entry_refused_fail_closed():
    tampered = {"invoice_id": "X", "debits": [{"account": "a", "amount": "100"}],
                "credits": [{"account": "b", "amount": "90"}]}   # debits != credits
    with pytest.raises(UnbalancedPostingError):
        from_entry(tampered)


def test_empty_entry_refused_fail_closed():
    with pytest.raises(UnbalancedPostingError):
        from_entry({"debits": [], "credits": []})          # empty posting — refused, not a no-op


def test_from_entry_matches_hand_built_posting():
    entry = {"debits": [{"account": "expense", "amount": "42.00"}],
             "credits": [{"account": "payable", "amount": "42.00"}]}
    from sovereign_agent.financials import Line
    assert from_entry(entry) == post([Line.dr("expense", "42.00"), Line.cr("payable", "42.00")])
