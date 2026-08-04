"""Production-order invariants — co-extrusion for s5_19 (Manufacturing Sovereign ERP, first vertical).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the governed production
order is value-conserving (issued materials conserve to the BOM requirement; produced-good cost conserves), fail-closed
(over-issue, incomplete build, and failed quality each refuse completion; illegal lifecycle jumps refuse), and that its
cost posts to the sealed general ledger in the canonical posting shape via financials.posting.from_entry (spine step
S4 materials -> S5 one ledger)."""
from decimal import Decimal
import pytest
from sovereign_agent.manufacturing import (
    open_order, transition, issue_materials, is_fully_issued, complete, cost_posting, ProductionError,
)
from sovereign_agent.financials import from_entry, trial_balance

BOM = {"steel": "2", "flux": "0.5"}          # per finished unit
BUILD = "10"                                  # -> required steel 20, flux 5


def _released():
    po = open_order("MO-1", "bracket", BOM, BUILD)
    po, _ = transition(po, "released")
    po, _ = transition(po, "in_process")
    return po


def test_bom_explodes_and_full_issue_conserves():
    po = open_order("MO-1", "bracket", BOM, BUILD)
    assert po["required"] == {"steel": Decimal("20"), "flux": Decimal("5.0")}
    po, _ = transition(po, "released")
    po, _ = transition(po, "in_process")
    po = issue_materials(po, {"steel": "20", "flux": "5.0"})
    assert is_fully_issued(po) is True                       # issued conserves EXACTLY to the BOM requirement
    po = complete(po, quality_passed=True)
    assert po["status"] == "completed"


def test_over_issue_refused():
    po = _released()
    with pytest.raises(ProductionError):
        issue_materials(po, {"steel": "21"})                 # 21 > required 20 -- over-issue refused


def test_completion_fail_closed_on_short_issue():
    po = _released()
    po = issue_materials(po, {"steel": "20"})                # flux never issued
    with pytest.raises(ProductionError):
        complete(po, quality_passed=True)                    # not fully issued -> refused


def test_completion_fail_closed_on_quality():
    po = _released()
    po = issue_materials(po, {"steel": "20", "flux": "5.0"})
    with pytest.raises(ProductionError):
        complete(po, quality_passed=False)                   # quality gate not passed -> refused


def test_illegal_lifecycle_jump_refused():
    po = open_order("MO-1", "bracket", BOM, BUILD)
    with pytest.raises(ProductionError):
        transition(po, "completed")                          # planned -> completed is not an allowed edge


def test_cost_posting_composes_sealed_ledger_value_conserving():
    po = _released()
    po = issue_materials(po, {"steel": "20", "flux": "5.0"})
    entry = cost_posting(po, {"steel": "4.50", "flux": "12.00"})
    assert entry["amount"] == Decimal("150.00")              # 20*4.50 + 5*12.00 = 90 + 60
    assert entry["balanced"] is True                          # debits == credits (value-conserving)
    posting = from_entry(entry)                               # posting-shape composes the sealed ledger (spine S5)
    assert posting["balanced"] is True
    assert sum(trial_balance([posting]).values(), Decimal("0")) == Decimal("0")   # nets to zero
