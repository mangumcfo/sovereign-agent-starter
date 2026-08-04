"""Regulated traceability — a governed, verifiable chain of custody: value-conserving custody, merkle-anchored trace,
and a fail-closed release, composing the sealed floors rather than reimplementing them.

Co-extrusion for s5_24 (Regulated Industries, KM 2026-08-04). Pure / structural, no crypto substrate beyond the sealed
merkle accumulator it composes (which runs in a pure public clone -- its own tests are green here). In a regulated
sector the question an auditor asks is never "what do your systems say?" but "prove it": prove this batch is the batch
you received, prove nothing entered or left its custody without a governed event, prove it was quality-released before it
shipped, and -- when something goes wrong -- prove exactly which units are affected so you can recall precisely those and
no others. Most industry-specific ERPs answer these from a traceability table that is a copy of the truth, editable and
only as trustworthy as the last person who touched it. This primitive makes the chain of custody itself the record.

A lot (a batch, quantity many; or a serial, quantity one) is received into a holder's custody, transferred between
holders, and consumed -- each an ordered, governed custody event. Reconciliation proves custody is value-conserving: no
holder ever holds a negative quantity (you cannot transfer or consume what you do not hold -- a phantom custody the
detector refuses), and the received quantity equals what is currently held plus what was governed-consumed, so nothing
appears or disappears off the record. Provenance anchors the ORDERED custody events to a single merkle root (composing
the sealed merkle accumulator): the chain that was recorded is provably the chain presented at audit, and any altered or
reordered event -- custody order is history, so a reordered chain is a different history -- yields a different root.
Release is fail-closed on BOTH gates, the same discipline the sealed production order applies at completion: a lot cannot
be released until its chain of custody reconciles AND its quality gate has passed; a lot is never released on an unproven
chain or an uninspected unit. And because the chain is retained, a shipped lot is always recallable -- traceability's
whole purpose -- as a governed fork, so precise recall is available and never a one-way door.

The primitive does not re-implement the ledger, the inventory movement, the quality gate, or the merkle tree it anchors
against -- it composes them; its own new act is the proof that custody was conserved from source to end user."""
from __future__ import annotations

from decimal import Decimal
import json
from typing import Dict, List, Mapping, Sequence, Tuple, Union

from ..merkle_accumulator import MerkleAccumulator

Number = Union[int, float, str, Decimal]

# Lot lifecycle -- fail-closed, with quarantine available as a fork from any pre-disposal state (non-conformance is
# always containable) and recall available as a fork from shipped (a traced lot is never un-recallable). Recorded in
# docs/DOMAIN_VOCAB_CARD.md per spine item 8.
_LOT_ALLOWED: Dict[str, set] = {
    "received":    {"in_custody", "quarantined"},
    "in_custody":  {"released", "quarantined"},
    "released":    {"shipped", "quarantined"},
    "shipped":     {"recalled"},                      # a shipped lot is always recallable -- the point of traceability
    "quarantined": {"in_custody", "disposed"},        # disposition: re-inspect back into custody, or dispose
    "recalled":    set(),
    "disposed":    set(),
}


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class TraceabilityError(ValueError):
    """Raised for an illegal lot transition, a release attempted on an unreconciled chain or a failed quality gate, or a
    custody event that would drive a holder negative -- fail-closed, never a lot released on an unproven chain."""


def _canon(event: Mapping) -> bytes:
    """Canonical bytes for a custody event, so its merkle leaf is stable regardless of key order."""
    return json.dumps({k: str(v) for k, v in sorted(event.items())}, sort_keys=True, separators=(",", ":")).encode()


def receipt(lot_id: str, item: str, qty: Number, holder: str) -> Dict[str, object]:
    """A receipt custody event: `qty` of `item` (lot `lot_id`) enters `holder`'s custody. The origin of the chain."""
    return {"kind": "receipt", "lot": lot_id, "item": item, "qty": str(_dec(qty)), "holder": holder}


def transfer(lot_id: str, qty: Number, frm: str, to: str) -> Dict[str, object]:
    """A transfer custody event: `qty` moves from `frm` to `to`. Nets to zero across holders -- custody moves, it is not
    created. A transfer that would drive `frm` negative is a phantom custody `reconcile_custody` refuses."""
    return {"kind": "transfer", "lot": lot_id, "qty": str(_dec(qty)), "from": frm, "to": to}


def consume(lot_id: str, qty: Number, holder: str, reason: str) -> Dict[str, object]:
    """A consume custody event: `qty` leaves `holder`'s custody into a governed use (built into a product, scrapped under
    a reason). Reduces held, increases consumed -- it leaves the record accounted, not unaccounted."""
    return {"kind": "consume", "lot": lot_id, "qty": str(_dec(qty)), "holder": holder, "reason": reason}


def custody_position(events: Sequence[Mapping]) -> Dict[str, object]:
    """Replay the ordered custody events into a position: quantity per current holder, total received, total consumed,
    and any holder driven negative by an event (a custody break). Pure replay -- the position is derived from the events,
    never stored beside them."""
    held: Dict[str, Decimal] = {}
    received = Decimal("0")
    consumed = Decimal("0")
    breaks: List[Dict[str, object]] = []

    def _apply(holder: str, delta: Decimal, idx: int, kind: str) -> None:
        nxt = held.get(holder, Decimal("0")) + delta
        if nxt < 0:                                   # cannot hold/move/consume what you do not have -- phantom custody
            breaks.append({"event": idx, "kind": kind, "holder": holder,
                           "held": str(held.get(holder, Decimal("0"))), "delta": str(delta)})
        held[holder] = nxt

    for idx, e in enumerate(events):
        kind = e.get("kind")
        if kind == "receipt":
            q = _dec(e["qty"]); received += q; _apply(e["holder"], q, idx, kind)
        elif kind == "transfer":
            q = _dec(e["qty"]); _apply(e["from"], -q, idx, kind); _apply(e["to"], q, idx, kind)
        elif kind == "consume":
            q = _dec(e["qty"]); consumed += q; _apply(e["holder"], -q, idx, kind)
        else:
            breaks.append({"event": idx, "kind": kind, "holder": None, "held": None, "delta": None})
    return {"held": {h: q for h, q in held.items() if q != 0}, "received": received,
            "consumed": consumed, "breaks": breaks}


def reconcile_custody(events: Sequence[Mapping]) -> Dict[str, object]:
    """Reconcile a chain of custody, value-conserving. Returns a report: whether custody is intact (no holder ever went
    negative -- nothing entered or left off the record) and value-conserving (received == currently held + consumed).
    Carries the breaks, the totals, and the trace root. This is the detector -- it does not raise; `assert_custody` is
    the fail-closed gate `release` runs through."""
    pos = custody_position(events)
    held_total = sum(pos["held"].values(), Decimal("0"))
    conserves = pos["received"] == held_total + pos["consumed"]
    reconciled = not pos["breaks"] and conserves
    return {"reconciled": reconciled, "conserves": conserves, "breaks": pos["breaks"],
            "received_total": pos["received"], "held_total": held_total, "consumed_total": pos["consumed"],
            "held": pos["held"], "trace_root": trace_root(events)}


def assert_custody(events: Sequence[Mapping]) -> Dict[str, object]:
    """Fail-closed reconciliation: raise TraceabilityError unless the chain of custody is intact and value-conserving.
    Returns the report on success. `release` runs through this gate."""
    rep = reconcile_custody(events)
    if not rep["reconciled"]:
        raise TraceabilityError(
            f"chain of custody does not reconcile -- release refused: breaks={rep['breaks']} "
            f"received={rep['received_total']} held={rep['held_total']} consumed={rep['consumed_total']}")
    return rep


def trace_root(events: Sequence[Mapping]) -> str:
    """The provenance root of a chain of custody: the merkle root over the ORDERED canonical custody events (composing
    the sealed merkle accumulator). The order is retained -- custody order is history, so the same events in a different
    order are a different chain and produce a different root, and any added, dropped, or altered event produces a
    different one. The lot that reconciles carries this root, so the lot presented at audit can be proven to be the same
    lot with the same history. Returns a hex root, or '' for an empty chain."""
    leaves = [_canon(e) for e in events]
    root = MerkleAccumulator.from_leaves(leaves).get_root() if leaves else None
    return root.hex() if root else ""


def open_lot(lot_id: str, item: str, qty: Number, holder: str) -> Dict[str, object]:
    """Open a lot (batch qty-many or serial qty-one) at receipt. Starts `received`, carrying its opening custody event
    and its trace root."""
    ev = [receipt(lot_id, item, qty, holder)]
    return {"id": lot_id, "item": item, "events": ev, "status": "received", "trace_root": trace_root(ev)}


def lot_transition(lot: Mapping, to_status: str) -> Tuple[Dict, Dict]:
    """Move a lot to `to_status`, fail-closed: the lifecycle must permit the move (you cannot ship a lot that was never
    released; you cannot release here -- `release` is the gated path). Quarantine is available as a fork from any
    pre-disposal state; recall as a fork from shipped. Returns (new_lot, event); input not mutated."""
    frm = lot.get("status", "received")
    if to_status not in _LOT_ALLOWED.get(frm, set()):
        raise TraceabilityError(f"lot {lot.get('id')!r}: illegal transition {frm!r} -> {to_status!r} "
                                f"(allowed from {frm!r}: {sorted(_LOT_ALLOWED.get(frm, set())) or 'none'})")
    nl = dict(lot)
    nl["status"] = to_status
    return nl, {"lot": lot.get("id"), "from": frm, "to": to_status}


def release(lot: Mapping, events: Sequence[Mapping], quality_passed: bool) -> Dict[str, object]:
    """Release a lot to the next stage, fail-closed on BOTH gates -- the same discipline the sealed production order
    applies at completion. The lot must be `in_custody`; its chain of custody must reconcile (intact and value-conserving,
    via `assert_custody`); and the quality gate must have passed. A broken chain or a failed quality event refuses the
    release -- a lot released on an unproven chain, or never inspected, does not exist. On success the lot moves to
    `released` carrying the reconciled trace root -- the proof custody was conserved. Recall remains available as a fork
    once shipped."""
    if lot.get("status") != "in_custody":
        raise TraceabilityError(f"lot {lot.get('id')!r}: release requires the in_custody state "
                                f"(is {lot.get('status')!r}) -- take custody before release")
    rep = assert_custody(events)
    if not quality_passed:
        raise TraceabilityError(f"lot {lot.get('id')!r}: release refused -- quality gate did not pass "
                                "(quarantine the lot; it is never released uninspected)")
    nl = dict(lot)
    nl["events"] = list(events)
    nl["status"] = "released"
    nl["trace_root"] = rep["trace_root"]
    nl["reconciliation"] = rep
    return nl
