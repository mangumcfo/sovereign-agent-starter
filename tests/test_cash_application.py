# -*- coding: utf-8 -*-
"""Cash application floor — the extrusion owed by V15 Ch5 / V08 Ch2 (extrude-debt case).

High bar per KM-NO1 GO 14:21Z item 2 / AA order 14:52Z:
  * pure shapers, value-conserving, over-application and over-allocation REFUSED;
  * allocations operator-explicit only — no FIFO, no auto-allocation;
  * paid/partial DERIVED BY REPLAY, never mutated;
  * the dormant billing hook (`if inv.get("paid"): continue`) engages via aging_rows;
  * identities: per-invoice billed = applied + remaining_open · per-receipt
    received = applied + unapplied · aggregates tie;
  * persistence via the EXISTING gated writer only — a human-approved write or no write;
    a refusal is BYTE-SILENT on the store;
  * reversal is a counter-record, never an erasure;
  * fail-loud replay: an inconsistent store is refused, never plugged.
"""
from __future__ import annotations

import copy
import os
from decimal import Decimal

import pytest

from sovereign_agent.revenue import cash_application as ca
from sovereign_agent.revenue.billing import ar_aging, invoice as billing_invoice
from sovereign_agent.revenue.cash_application import CashApplicationError


def _inv(inv_id, amount, day=0):
    return {"invoice_id": inv_id, "amount": amount, "issued_day": day}


INVOICES = [_inv("INV-1", 1000, 10), _inv("INV-2", 500, 40), _inv("INV-3", 600, 70)]


# ==================================================================================================
# receipt() — pure shaper
# ==================================================================================================

def test_receipt_shapes_and_quantizes():
    r = ca.receipt("RCT-1", "Acme", 750.005, 80, memo="check 1042")
    assert r["kind"] == ca.RECEIPT_KIND and r["receipt_ref"] == "RCT-1"
    assert r["amount"] == Decimal("750.00") or r["amount"] == Decimal("750.01")  # bankers vs half-even
    assert r["customer"] == "Acme" and r["day"] == 80


@pytest.mark.parametrize("kw", [
    {"receipt_ref": "", "customer": "Acme", "amount": 10, "day": 1},
    {"receipt_ref": "R", "customer": "", "amount": 10, "day": 1},
    {"receipt_ref": "R", "customer": "Acme", "amount": 0, "day": 1},
    {"receipt_ref": "R", "customer": "Acme", "amount": -5, "day": 1},
    {"receipt_ref": "R", "customer": "Acme", "amount": 10, "day": -1},
])
def test_receipt_refuses_invalid(kw):
    with pytest.raises(CashApplicationError):
        ca.receipt(**kw)


# ==================================================================================================
# apply() — operator-explicit, value-conserving, fail-closed
# ==================================================================================================

def test_apply_happy_path_full_and_partial():
    r = ca.receipt("RCT-1", "Acme", 1200, 80)
    a = ca.apply(r, [{"invoice_id": "INV-1", "amount": 1000},
                     {"invoice_id": "INV-2", "amount": 200}], INVOICES)
    assert a["kind"] == ca.APPLICATION_KIND and a["amount"] == Decimal("1200.00")
    assert a["allocations"][0] == {"invoice_id": "INV-1", "amount": Decimal("1000.00")}


def test_apply_refuses_empty_allocations():
    r = ca.receipt("RCT-1", "Acme", 100, 1)
    with pytest.raises(CashApplicationError, match="operator-explicit"):
        ca.apply(r, [], INVOICES)


def test_apply_refuses_unknown_invoice():
    r = ca.receipt("RCT-1", "Acme", 100, 1)
    with pytest.raises(CashApplicationError, match="unknown invoice"):
        ca.apply(r, [{"invoice_id": "INV-99", "amount": 50}], INVOICES)


def test_apply_refuses_nonpositive_line():
    r = ca.receipt("RCT-1", "Acme", 100, 1)
    with pytest.raises(CashApplicationError, match="> 0"):
        ca.apply(r, [{"invoice_id": "INV-1", "amount": 0}], INVOICES)


def test_apply_refuses_over_application_fresh():
    r = ca.receipt("RCT-1", "Acme", 5000, 1)
    with pytest.raises(CashApplicationError, match="over-application"):
        ca.apply(r, [{"invoice_id": "INV-2", "amount": 501}], INVOICES)


def test_apply_refuses_over_application_net_of_prior_records():
    r1 = ca.receipt("RCT-1", "Acme", 400, 1)
    a1 = ca.apply(r1, [{"invoice_id": "INV-2", "amount": 400}], INVOICES)
    r2 = ca.receipt("RCT-2", "Acme", 400, 2)
    with pytest.raises(CashApplicationError, match="over-application"):
        ca.apply(r2, [{"invoice_id": "INV-2", "amount": 101}], INVOICES,
                 prior_records=[r1, a1])
    ok = ca.apply(r2, [{"invoice_id": "INV-2", "amount": 100}], INVOICES,
                  prior_records=[r1, a1])
    assert ok["amount"] == Decimal("100.00")


def test_apply_refuses_over_allocation_of_the_receipt():
    r = ca.receipt("RCT-1", "Acme", 300, 1)
    with pytest.raises(CashApplicationError, match="over-allocation"):
        ca.apply(r, [{"invoice_id": "INV-1", "amount": 200},
                     {"invoice_id": "INV-2", "amount": 101}], INVOICES)


def test_apply_refuses_over_allocation_net_of_prior_applications_of_same_receipt():
    r = ca.receipt("RCT-1", "Acme", 300, 1)
    a1 = ca.apply(r, [{"invoice_id": "INV-1", "amount": 250}], INVOICES)
    with pytest.raises(CashApplicationError, match="over-allocation"):
        ca.apply(r, [{"invoice_id": "INV-2", "amount": 51}], INVOICES, prior_records=[r, a1])


def test_apply_mutates_nothing():
    r = ca.receipt("RCT-1", "Acme", 300, 1)
    invs = copy.deepcopy(INVOICES)
    allocs = [{"invoice_id": "INV-1", "amount": 100}]
    allocs_copy = copy.deepcopy(allocs)
    r_copy = copy.deepcopy(r)
    ca.apply(r, allocs, invs)
    assert invs == INVOICES and allocs == allocs_copy and r == r_copy


def test_no_auto_allocation_verb_exists_on_the_module():
    for name in dir(ca):
        low = name.lower()
        assert not any(v in low for v in ("fifo", "auto_alloc", "auto_apply", "allocate_oldest",
                                          "fill_", "policy")), \
            f"auto-allocation-shaped name on the sealed floor: {name}"


# ==================================================================================================
# replay_state() — the only source of paid / partial / remaining / unapplied
# ==================================================================================================

def _happy_records():
    r1 = ca.receipt("RCT-1", "Acme", 1200, 80)
    a1 = ca.apply(r1, [{"invoice_id": "INV-1", "amount": 1000},
                       {"invoice_id": "INV-2", "amount": 200}], INVOICES)
    return [r1, a1]


def test_replay_derives_paid_partial_and_identities():
    st = ca.replay_state(INVOICES, _happy_records())
    i1, i2, i3 = st["invoices"]["INV-1"], st["invoices"]["INV-2"], st["invoices"]["INV-3"]
    assert i1["paid"] is True and i1["remaining_open"] == Decimal("0.00")
    assert i2["partial"] is True and i2["remaining_open"] == Decimal("300.00")
    assert i3["paid"] is False and i3["applied"] == Decimal("0.00")
    r = st["receipts"]["RCT-1"]
    assert r["received"] == Decimal("1200.00") and r["unapplied"] == Decimal("0.00")
    # identities — per entity and aggregate
    for s in st["invoices"].values():
        assert s["billed"] == s["applied"] + s["remaining_open"]
    for s in st["receipts"].values():
        assert s["received"] == s["applied"] + s["unapplied"]
    t = st["totals"]
    assert t["billed"] == t["applied_to_invoices"] + t["remaining_open"]
    assert t["received"] == t["applied_to_invoices"] + t["unapplied"]
    assert st["identities_hold"] is True


def test_replay_never_mutates_inputs_and_stores_no_paid():
    invs = copy.deepcopy(INVOICES)
    recs = _happy_records()
    recs_copy = copy.deepcopy(recs)
    ca.replay_state(invs, recs)
    assert invs == INVOICES, "replay added keys (e.g. paid) onto the invoice inputs — mutation"
    assert recs == recs_copy
    assert all("paid" not in inv for inv in invs), "'paid' may exist ONLY in replay output"


def test_replay_fail_louds_on_an_inconsistent_store():
    # a hand-forged over-application (bypassing apply's gate, e.g. a tampered store)
    r1 = ca.receipt("RCT-1", "Acme", 5000, 1)
    forged = {"kind": ca.APPLICATION_KIND, "receipt_ref": "RCT-1",
              "allocations": [{"invoice_id": "INV-2", "amount": 9999}], "amount": 9999}
    with pytest.raises(CashApplicationError, match="identity violated"):
        ca.replay_state(INVOICES, [r1, forged])


def test_replay_refuses_application_with_no_receipt_record():
    orphan = {"kind": ca.APPLICATION_KIND, "receipt_ref": "GHOST",
              "allocations": [{"invoice_id": "INV-1", "amount": 10}], "amount": 10}
    with pytest.raises(CashApplicationError, match="no receipt record"):
        ca.replay_state(INVOICES, [orphan])


# ==================================================================================================
# reverse() — counter-record, never erasure
# ==================================================================================================

def test_reverse_is_a_counter_record_replay_nets_it():
    r1 = ca.receipt("RCT-1", "Acme", 1000, 1)
    a1 = ca.apply(r1, [{"invoice_id": "INV-1", "amount": 1000}], INVOICES)
    v1 = ca.reverse(a1, reason="applied to the wrong invoice")
    st = ca.replay_state(INVOICES, [r1, a1, v1])
    i1 = st["invoices"]["INV-1"]
    assert i1["paid"] is False and i1["applied"] == Decimal("0.00")
    assert st["receipts"]["RCT-1"]["unapplied"] == Decimal("1000.00")
    assert st["identities_hold"] is True
    # and the record set still CONTAINS both acts — nothing erased
    assert len([x for x in [r1, a1, v1] if x["kind"] == ca.APPLICATION_KIND]) == 1
    assert len([x for x in [r1, a1, v1] if x["kind"] == ca.REVERSAL_KIND]) == 1


def test_reverse_requires_a_reason():
    r1 = ca.receipt("RCT-1", "Acme", 100, 1)
    a1 = ca.apply(r1, [{"invoice_id": "INV-1", "amount": 100}], INVOICES)
    with pytest.raises(CashApplicationError, match="reason"):
        ca.reverse(a1, reason="  ")


# ==================================================================================================
# The dormant billing hook engages — sealed aging narrows honestly
# ==================================================================================================

def test_aging_rows_engage_the_sealed_paid_hook():
    rows = ca.aging_rows(INVOICES, _happy_records())
    aged = ar_aging(rows, as_of_day=75)
    # INV-1 fully applied → paid → the sealed rule's own line skips it
    # INV-2 partial → ages at REMAINING 300 (issued 40 → age 35 → 31_60)
    # INV-3 untouched → ages at 600 (issued 70 → age 5 → current)
    assert aged["total_receivable"] == Decimal("900.00")
    assert aged["buckets"]["31_60"] == Decimal("300.00")
    assert aged["buckets"]["current"] == Decimal("600.00")
    assert aged["balances"] is True


def test_aging_rows_with_no_applications_is_all_open_unchanged():
    rows = ca.aging_rows(INVOICES, [])
    aged = ar_aging(rows, as_of_day=75)
    assert aged["total_receivable"] == Decimal("2100.00")   # v0.9's by-construction world, reproduced


# ==================================================================================================
# Persistence — the EXISTING gated writer only; a refusal is BYTE-SILENT
# ==================================================================================================

def _record_payload(shaped):
    """The extra-dict a governed record carries: the shaped record, doc-kinded for replay."""
    p = {k: (str(v) if isinstance(v, Decimal) else v) for k, v in shaped.items()}
    p["doc_kind"] = p.pop("kind")
    return p


def test_gated_writer_refusal_writes_nothing_and_approval_lands(tmp_path):
    from sovereign_agent.compliance.human_approval_gate import ApprovalRequest, HumanApprovalGate
    from sovereign_agent.economy.income import IncomeRefused, attribute_income
    from sovereign_agent.objects.registry import ObjectRegistry

    reg_root = str(tmp_path / "registry")
    os.makedirs(reg_root)
    registry = ObjectRegistry(reg_root)
    gate = HumanApprovalGate({"high_materiality_classes": ["record_cash_receipt"]})
    r1 = ca.receipt("RCT-1", "Acme", 500, 10)
    log = os.path.join(reg_root, "objects.ndjson")

    before = open(log, "rb").read() if os.path.exists(log) else b""
    with pytest.raises(IncomeRefused):
        attribute_income("kenn", "receipt:RCT-1", mandate="demo", author="kenn",
                         source_ref="test", at="2026-08-20T00:00:00+00:00", registry=registry,
                         amount=500, unit="USD", extra=_record_payload(r1),
                         gate=gate, mode="corporate_regulated",
                         action_class="record_cash_receipt")
    after = open(log, "rb").read() if os.path.exists(log) else b""
    assert after == before, "a refused gated write left bytes on the store — must be byte-silent"

    # a REAL human disposition, then the write lands
    req_id = gate.request_approval(ApprovalRequest(
        action_class="record_cash_receipt", role_id="test", principal_id="kenn",
        risk_level="material", rationale="record receipt RCT-1", required_approvers=["kenn"]))
    gate.record_disposition(req_id, status="approved", approver="kenn", reason="ok")
    rec = attribute_income("kenn", "receipt:RCT-1", mandate="demo", author="kenn",
                           source_ref="test", at="2026-08-20T00:00:00+00:00", registry=registry,
                           amount=500, unit="USD", extra=_record_payload(r1),
                           gate=gate, mode="corporate_regulated",
                           action_class="record_cash_receipt",
                           approver="kenn", approval_ref=req_id)
    assert rec["payload"]["doc_kind"] == ca.RECEIPT_KIND

    # replay from the DISK payloads reproduces the state — no second store anywhere
    stored = [e["payload"] for e in ObjectRegistry(reg_root).entries()
              if (e.get("payload") or {}).get("doc_kind") in
                 (ca.RECEIPT_KIND, ca.APPLICATION_KIND, ca.REVERSAL_KIND)]
    st = ca.replay_state([_inv("INV-1", 1000, 10)], stored)
    assert st["receipts"]["RCT-1"]["received"] == Decimal("500.00")
    assert st["receipts"]["RCT-1"]["unapplied"] == Decimal("500.00")
    assert st["identities_hold"] is True
