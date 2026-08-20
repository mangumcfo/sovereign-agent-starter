"""Customer cash application (V15 Ch5 "Collections and Credit"; cash-side semantics V08 Ch2).

The extrusion owed by the books (V15_CASH_APP_HOME_AUDIT.md, KM-NO1 GO 2026-08-20 14:21Z item 2):
the sealed aging rule has skipped `paid` invoices since it was written (`billing.py` — `if
inv.get("paid"): continue`) and nothing in the kernel could set `paid`. This module is that
missing middle, extruded to the same law as every sealed floor:

  * **Pure shapers.** `receipt` and `apply` validate and shape governed records; they persist
    nothing and mutate nothing. Persistence rides the EXISTING gated writer (the economy
    attribution path) — a human-approved write or no write at all; a refusal writes nothing.
  * **Allocations are operator-explicit lines.** A human names which receipt money applies to
    which invoice. There is no FIFO, no auto-allocation, no policy engine — the machine may
    compute the arithmetic, the human must choose the application.
  * **`paid` / `partial` are DERIVED BY REPLAY** (`replay_state`) from the application records —
    never stored, never mutated onto an invoice. A second stored copy of "paid" would be a second
    ledger wearing a different coat.
  * **Reversal is a counter-record** (`reverse`), never an erasure: the chain keeps both acts and
    replay nets them.
  * **Value conservation is refused into existence:** over-application (per-invoice applied >
    billed) and over-allocation (lines > receipt) are refused at shaping time, and `replay_state`
    fail-louds on a store that violates the identities rather than presenting a wrong number.
  * **The node RECORDS application; Port/bank moves money.** Nothing here touches value — a
    receipt record says money arrived (by the operator's own hand, outside this system); an
    application record says which invoice it belongs to. No custody, no settlement, no statutory
    act.

Identities (the BAR's equality proofs):
  per invoice:  billed  = applied + remaining_open
  per receipt:  received = applied + unapplied
  aggregates:   Σbilled = Σapplied + Σremaining · Σreceived = Σapplied + Σunapplied
"""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Mapping, Sequence, Union

Number = Union[int, float, str, Decimal]
_CENTS = Decimal("0.01")

#: The doc kinds an application-side governed record carries in its payload. The gated writer
#: stores these as ordinary attribution records; replay recognises them by kind.
RECEIPT_KIND = "cash_receipt"
APPLICATION_KIND = "cash_application"
REVERSAL_KIND = "cash_application_reversal"


class CashApplicationError(ValueError):
    """Raised when a receipt or application would break value conservation, name an unknown
    record, or auto-decide what only a human may choose. Fail-closed: it is refused, not fixed."""


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


# --------------------------------------------------------------------------------------------------
# Pure shapers
# --------------------------------------------------------------------------------------------------

def receipt(receipt_ref: str, customer: str, amount: Number, day: int,
            currency: str = "USD", memo: str = "") -> Dict[str, object]:
    """Shape a customer receipt record: money the operator RECEIVED (outside this system, by
    their own act) that is now to be recorded and later applied. Pure; refuses a non-positive
    amount, an empty reference, or an empty customer. The reference is operator-explicit, like
    an invoice id — this module mints nothing."""
    ref = str(receipt_ref or "").strip()
    cust = str(customer or "").strip()
    if not ref:
        raise CashApplicationError("a receipt needs an operator-explicit reference (e.g. 'RCT-001')")
    if not cust:
        raise CashApplicationError("a receipt needs the customer who paid")
    amt = _dec(amount)
    if amt <= 0:
        raise CashApplicationError(f"receipt amount must be > 0 (got {amt})")
    if int(day) < 0:
        raise CashApplicationError(f"receipt day must be >= 0 (got {day})")
    return {"kind": RECEIPT_KIND, "receipt_ref": ref, "customer": cust,
            "amount": amt.quantize(_CENTS), "day": int(day),
            "currency": str(currency), "memo": str(memo or "")}


def apply(receipt_rec: Mapping, allocations: Sequence[Mapping], invoices: Sequence[Mapping],
          prior_records: Sequence[Mapping] = ()) -> Dict[str, object]:
    """Shape an application: OPERATOR-EXPLICIT allocation lines from one receipt to named
    invoices. Pure — validates against the replayed current state and refuses:

      * an empty allocation list, or any line without a positive amount and an invoice id;
      * an allocation to an invoice not in `invoices` (unknown paper);
      * over-application — a line (net of prior applications) exceeding an invoice's remaining;
      * over-allocation — lines exceeding the receipt's unapplied amount (net of prior
        applications of the same receipt).

    There is no automatic ordering and no fill-by-policy: every line is a human's explicit choice.
    """
    if receipt_rec.get("kind") != RECEIPT_KIND:
        raise CashApplicationError("apply() takes a receipt record shaped by receipt()")
    lines = [dict(a) for a in allocations]
    if not lines:
        raise CashApplicationError("an application needs at least one operator-explicit allocation line")

    state = replay_state(invoices, prior_records)
    ref = str(receipt_rec["receipt_ref"])
    unapplied = state["receipts"].get(ref, {}).get("unapplied")
    if unapplied is None:
        # the receipt has no prior applications on record — its full amount is available
        unapplied = _dec(receipt_rec["amount"])

    remaining = {inv_id: r["remaining_open"] for inv_id, r in state["invoices"].items()}
    total = Decimal("0")
    shaped: List[Dict[str, object]] = []
    for ln in lines:
        inv_id = str(ln.get("invoice_id") or "").strip()
        if not inv_id:
            raise CashApplicationError("every allocation line names its invoice_id — the human chooses")
        if inv_id not in remaining:
            raise CashApplicationError(f"allocation names unknown invoice {inv_id!r} — refused")
        amt = _dec(ln.get("amount", 0))
        if amt <= 0:
            raise CashApplicationError(f"allocation to {inv_id!r} must be > 0 (got {amt})")
        if amt > remaining[inv_id]:
            raise CashApplicationError(
                f"over-application refused: {amt} to invoice {inv_id!r} exceeds its remaining open "
                f"{remaining[inv_id]} (billed = applied + remaining is an identity, not a suggestion)")
        remaining[inv_id] -= amt
        total += amt
        shaped.append({"invoice_id": inv_id, "amount": amt.quantize(_CENTS)})
    if total > unapplied:
        raise CashApplicationError(
            f"over-allocation refused: lines total {total} but receipt {ref!r} has {unapplied} "
            f"unapplied (received = applied + unapplied is an identity, not a suggestion)")

    return {"kind": APPLICATION_KIND, "receipt_ref": ref,
            "customer": receipt_rec.get("customer"),
            "allocations": shaped, "amount": total.quantize(_CENTS),
            "day": receipt_rec.get("day")}


def reverse(application_rec: Mapping, reason: str) -> Dict[str, object]:
    """Shape a reversal COUNTER-RECORD for a prior application. Nothing is erased: the chain
    keeps the application and its reversal, and replay nets the two. A reversal needs a reason —
    it is recorded loudly, like a veto."""
    if application_rec.get("kind") != APPLICATION_KIND:
        raise CashApplicationError("reverse() takes an application record shaped by apply()")
    if not str(reason or "").strip():
        raise CashApplicationError("a reversal requires a reason — it is a loud counter-record, not an undo")
    return {"kind": REVERSAL_KIND, "receipt_ref": application_rec["receipt_ref"],
            "reverses_allocations": [dict(a) for a in application_rec["allocations"]],
            "amount": _dec(application_rec["amount"]).quantize(_CENTS),
            "reason": str(reason).strip()}


# --------------------------------------------------------------------------------------------------
# Replay — the ONLY source of paid / partial / remaining / unapplied
# --------------------------------------------------------------------------------------------------

def replay_state(invoices: Sequence[Mapping], records: Sequence[Mapping]) -> Dict[str, object]:
    """Derive the application state by replaying the governed records. `paid` and `partial` exist
    ONLY here — never stored, never mutated onto an invoice. Fail-loud: a store whose records
    over-apply an invoice or over-allocate a receipt breaks an identity, and this function
    REFUSES to present it rather than clamping or plugging the number."""
    inv_state: Dict[str, Dict[str, object]] = {}
    for inv in invoices:
        inv_id = str(inv.get("invoice_id") or "").strip()
        if not inv_id:
            raise CashApplicationError("an invoice without an invoice_id cannot participate in application")
        inv_state[inv_id] = {"billed": _dec(inv.get("amount", 0)).quantize(_CENTS),
                             "applied": Decimal("0")}

    rcpt_state: Dict[str, Dict[str, object]] = {}
    for rec in records:
        kind = rec.get("kind") or rec.get("doc_kind")
        if kind == RECEIPT_KIND:
            ref = str(rec["receipt_ref"])
            rcpt_state[ref] = {"received": _dec(rec.get("amount", 0)).quantize(_CENTS),
                               "applied": Decimal("0"), "customer": rec.get("customer")}
    for rec in records:
        kind = rec.get("kind") or rec.get("doc_kind")
        if kind not in (APPLICATION_KIND, REVERSAL_KIND):
            continue
        sign = Decimal("1") if kind == APPLICATION_KIND else Decimal("-1")
        ref = str(rec.get("receipt_ref"))
        if ref not in rcpt_state:
            raise CashApplicationError(
                f"application references receipt {ref!r} with no receipt record on the store — "
                f"the chain is incomplete; investigate before trusting any figure")
        allocs = rec.get("allocations") if kind == APPLICATION_KIND else rec.get("reverses_allocations")
        for ln in (allocs or []):
            inv_id = str(ln.get("invoice_id"))
            amt = _dec(ln.get("amount", 0)) * sign
            if inv_id not in inv_state:
                raise CashApplicationError(
                    f"application line names invoice {inv_id!r} not on the store — refused")
            inv_state[inv_id]["applied"] += amt
            rcpt_state[ref]["applied"] += amt

    invoices_out: Dict[str, Dict[str, object]] = {}
    for inv_id, s in inv_state.items():
        applied = s["applied"].quantize(_CENTS)
        billed = s["billed"]
        remaining = (billed - applied).quantize(_CENTS)
        if applied < 0 or remaining < 0:
            raise CashApplicationError(
                f"identity violated on invoice {inv_id!r}: billed {billed}, applied {applied} — "
                f"the store is inconsistent; refusing to present a plugged number")
        invoices_out[inv_id] = {"billed": billed, "applied": applied,
                                "remaining_open": remaining,
                                "paid": (billed > 0 and remaining == 0),
                                "partial": (Decimal("0") < applied < billed)}

    receipts_out: Dict[str, Dict[str, object]] = {}
    for ref, s in rcpt_state.items():
        applied = s["applied"].quantize(_CENTS)
        received = s["received"]
        unapplied = (received - applied).quantize(_CENTS)
        if applied < 0 or unapplied < 0:
            raise CashApplicationError(
                f"identity violated on receipt {ref!r}: received {received}, applied {applied} — "
                f"the store is inconsistent; refusing to present a plugged number")
        receipts_out[ref] = {"received": received, "applied": applied,
                             "unapplied": unapplied, "customer": s["customer"]}

    totals = {
        "billed": sum((r["billed"] for r in invoices_out.values()), Decimal("0")),
        "applied_to_invoices": sum((r["applied"] for r in invoices_out.values()), Decimal("0")),
        "remaining_open": sum((r["remaining_open"] for r in invoices_out.values()), Decimal("0")),
        "received": sum((r["received"] for r in receipts_out.values()), Decimal("0")),
        "unapplied": sum((r["unapplied"] for r in receipts_out.values()), Decimal("0")),
    }
    return {"invoices": invoices_out, "receipts": receipts_out, "totals": totals,
            "identities_hold": (
                totals["billed"] == totals["applied_to_invoices"] + totals["remaining_open"]
                and totals["received"] == totals["applied_to_invoices"] + totals["unapplied"])}


def aging_rows(invoices: Sequence[Mapping], records: Sequence[Mapping]) -> List[Dict[str, object]]:
    """Rows for the SEALED `billing.ar_aging` — this is where the dormant hook engages. A fully
    applied invoice carries `paid: True` and the sealed rule skips it (its own line, unchanged);
    a partially applied invoice ages at its REMAINING amount, because that is the open figure."""
    state = replay_state(invoices, records)
    rows: List[Dict[str, object]] = []
    for inv in invoices:
        inv_id = str(inv.get("invoice_id"))
        s = state["invoices"][inv_id]
        rows.append({"amount": s["remaining_open"], "issued_day": int(inv.get("issued_day", 0)),
                     "paid": bool(s["paid"])})
    return rows


__all__ = ["receipt", "apply", "reverse", "replay_state", "aging_rows",
           "CashApplicationError", "RECEIPT_KIND", "APPLICATION_KIND", "REVERSAL_KIND"]
