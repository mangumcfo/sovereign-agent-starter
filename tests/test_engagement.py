"""Engagement invariants — co-extrusion for s5_21 (Professional Services, third vertical).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the governed engagement
is value-conserving (billable = recorded hours at the rate-card rate; the invoice conserves to the recorded time),
fail-closed (a resource not on the rate card, a non-positive hour, an over-budget bill, and an illegal lifecycle jump
are each refused), and that the bill posts to the sealed general ledger in the canonical posting shape via
financials.posting.from_entry (spine step S3 time->invoice -> S5 one ledger)."""
from decimal import Decimal
import pytest
from sovereign_agent.services import (
    open_engagement, transition, record_time, billable_amount, budget_position, bill, bill_posting, EngagementError,
)
from sovereign_agent.financials import from_entry, trial_balance

RATE = {"senior": "300", "junior": "150"}


def _active(budget="20000"):
    e = open_engagement("ENG-1", "Ridgeline", RATE, budget=budget)
    e = record_time(e, [{"resource": "senior", "task": "design", "hours": "10"},
                        {"resource": "junior", "task": "build", "hours": "20"}])   # 3000 + 3000 = 6000
    return e


def test_billable_conserves_to_recorded_time():
    e = _active()
    assert billable_amount(e) == Decimal("6000.00")             # 10*300 + 20*150
    inv = bill(e, tax="360")
    assert sum((l["amount"] for l in inv["lines"]), Decimal("0")) == inv["subtotal"]   # lines conserve
    assert inv["subtotal"] == Decimal("6000.00")
    assert inv["total"] == inv["subtotal"] + inv["tax"]


def test_resource_not_on_rate_card_refused():
    e = open_engagement("ENG-2", "Ridgeline", RATE, budget="20000")
    with pytest.raises(EngagementError):
        record_time(e, [{"resource": "contractor", "task": "x", "hours": "5"}])   # not on rate card


def test_non_positive_hours_refused():
    e = open_engagement("ENG-3", "Ridgeline", RATE, budget="20000")
    with pytest.raises(EngagementError):
        record_time(e, [{"resource": "senior", "task": "x", "hours": "0"}])


def test_billing_fail_closed_on_budget():
    e = open_engagement("ENG-4", "Ridgeline", RATE, budget="5000")   # budget below billable 6000
    e = record_time(e, [{"resource": "senior", "task": "design", "hours": "10"},
                        {"resource": "junior", "task": "build", "hours": "20"}])
    assert budget_position(e)["over_budget"] is True
    with pytest.raises(EngagementError):
        bill(e)                                                     # over budget -> refused


def test_illegal_lifecycle_jump_refused():
    e = open_engagement("ENG-5", "Ridgeline", RATE, budget="20000")
    with pytest.raises(EngagementError):
        transition(e, "billed")                                    # open -> billed is not an allowed edge


def test_bill_posts_balanced_to_sealed_ledger():
    entry = bill_posting(_active(), tax="360")
    assert entry["balanced"] is True                                # AR debit == services revenue + tax credits
    assert entry["amount"] == Decimal("6360.00")                    # 6000 + 360
    posting = from_entry(entry)                                      # posting-shape composes the sealed ledger (spine S5)
    assert posting["balanced"] is True
    assert sum(trial_balance([posting]).values(), Decimal("0")) == Decimal("0")   # nets to zero
