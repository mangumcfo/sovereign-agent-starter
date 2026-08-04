"""QuickBooks-escape invariants — co-extrusion for s5_34 (Escaping QuickBooks, escape arc 1/4).

Pure/structural: composes the sealed floors — the migration primitive (manifest_root provenance + lifecycle), the sealed
Chart of Accounts validator (financials.controlling.validate_coa), and the sealed balanced posting
(financials.posting.from_entry). Proves the receipted cutover is value-conserving (every QuickBooks account mapped, the
mapped total equal to the source total), that the opening balances post as one balanced double-entry, and that it is
fail-closed at every seam (an unmapped account, a target absent from the chart, an invalid chart, or an unbalanced trial
balance refuses the cutover), with the source and mapped sets anchored to order-independent merkle provenance roots."""
from decimal import Decimal
import pytest
from sovereign_agent.migration.quickbooks import (
    map_to_coa, opening_entry, receipted_cutover, QuickBooksError,
)
from sovereign_agent.financials.controlling import CoAError
from sovereign_agent.financials.posting import UnbalancedPostingError

COA = {"ASSETS": {"parent": None}, "CASH": {"parent": "ASSETS"}, "AR": {"parent": "ASSETS"},
       "LIAB": {"parent": None}, "AP": {"parent": "LIAB"},
       "EQUITY": {"parent": None}, "RETAINED": {"parent": "EQUITY"}}
# A balanced QuickBooks trial balance (signed: debit-normal +, credit-normal -), sums to zero.
QB_TB = {"Checking": "1000", "Accounts Receivable": "500", "Accounts Payable": "-300", "Opening Bal Equity": "-1200"}
MAP = {"Checking": "CASH", "Accounts Receivable": "AR", "Accounts Payable": "AP", "Opening Bal Equity": "RETAINED"}


def test_clean_cutover_conserves_and_posts_balanced():
    rec = receipted_cutover("MIG-QB-1", QB_TB, MAP, COA)
    assert rec["status"] == "cutover"
    assert rec["mapped_balances"] == {"CASH": "1000", "AR": "500", "AP": "-300", "RETAINED": "-1200"}
    p = rec["opening_posting"]                                    # balanced double-entry (sealed posting accepted it)
    assert p["balanced"] is True and p["amount"] == "1500"        # total debits == total credits == 1500
    assert rec["source_root"] and rec["mapped_root"]


def test_unmapped_account_refused():
    tb = dict(QB_TB); tb["Undeposited Funds"] = "50"             # no mapping -> refused (and would break balance)
    with pytest.raises(QuickBooksError):
        receipted_cutover("MIG-QB-2", tb, MAP, COA)


def test_target_not_in_chart_refused():
    bad = dict(MAP); bad["Checking"] = "NOPE"                    # maps to an account absent from the chart
    with pytest.raises(QuickBooksError):
        map_to_coa(QB_TB, bad, COA)


def test_invalid_chart_refused():
    broken = {"CASH": {"parent": "MISSING"}}                     # a chart whose parent does not exist
    with pytest.raises(CoAError):
        map_to_coa(QB_TB, MAP, broken)                          # composes the sealed CoA validator, which refuses


def test_value_conserved_and_merged():
    # two QuickBooks accounts map to the same sovereign account -> they sum, value conserved
    tb = {"Checking": "1000", "Savings": "400", "Owner Equity": "-1400"}
    mp = {"Checking": "CASH", "Savings": "CASH", "Owner Equity": "RETAINED"}
    mapped = map_to_coa(tb, mp, COA)
    assert mapped["CASH"] == Decimal("1400")                     # merged
    assert sum(mapped.values(), Decimal("0")) == Decimal("0")    # total conserved (== source total)


def test_unbalanced_trial_balance_refused():
    off = {"Checking": "1000", "Accounts Payable": "-300"}       # signed total 700 != 0 -> opening entry unbalanced
    mp = {"Checking": "CASH", "Accounts Payable": "AP"}
    with pytest.raises(UnbalancedPostingError):
        receipted_cutover("MIG-QB-3", off, mp, COA)             # sealed posting refuses the unbalanced opening entry


def test_source_root_order_independent():
    r1 = receipted_cutover("MIG-QB-4", QB_TB, MAP, COA)["source_root"]
    reordered = {k: QB_TB[k] for k in reversed(list(QB_TB))}     # same set, different order
    r2 = receipted_cutover("MIG-QB-5", reordered, MAP, COA)["source_root"]
    assert r1 == r2 and r1                                       # provenance depends on the SET, not the order
