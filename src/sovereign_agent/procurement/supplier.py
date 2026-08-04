"""Supplier — a governed supplier registry with transparent, composed scoring and fail-closed award.

Co-extrusion for s5_16 (Procurement-to-Pay, KM Option B 2026-08-04). Pure / structural, no crypto substrate (F-1
pure-clone-clean). A supplier is a governed record with a lifecycle -- prospective, qualified, active, suspended,
rejected, retired -- and the lifecycle is fail-closed: you cannot activate a supplier that was never qualified, or
re-award a rejected one. Sourcing and performance scoring is not a black box: it composes the sealed decision-support
surface (Analytics & Decision Intelligence), so every supplier's score carries its full per-criterion breakdown and the
weights used, and is re-runnable and auditable. Award is fail-closed on qualification: only a qualified or active
supplier is eligible, so an unqualified supplier -- however high its raw scorecard -- is refused at award rather than
silently selected. Human primacy holds: the module ranks and recommends among the eligible; the governed award that
acts on it is a separate human-gated act."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Mapping, Sequence, Set, Tuple, Union

from ..analytics.decision_support import rank, recommend, DecisionError

Number = Union[int, float, str, Decimal]

# Supplier lifecycle -- fail-closed transitions. A supplier is prospective until qualified; only a qualified/active
# supplier may be awarded; a rejected or retired supplier is terminal.
_SUP_ALLOWED: Dict[str, Set[str]] = {
    "prospective": {"qualified", "rejected"},
    "qualified": {"active", "suspended", "rejected"},
    "active": {"suspended", "retired"},
    "suspended": {"active", "retired"},
    "rejected": set(),
    "retired": set(),
}
# Statuses eligible to receive an award.
_ELIGIBLE: Set[str] = {"qualified", "active"}


class SupplierError(ValueError):
    """Raised for an illegal lifecycle transition, or an award with no eligible (qualified/active) supplier."""


def register(supplier_id: str, name: str, **meta) -> Dict[str, object]:
    """Register a new supplier as `prospective` -- a governed record that must be qualified before it can be awarded.
    Extra metadata (e.g. a `scorecard`) is carried through unchanged."""
    if not supplier_id:
        raise SupplierError("supplier_id required")
    return {"id": supplier_id, "name": name, "status": "prospective", **meta}


def transition(supplier: Mapping, to_status: str) -> Tuple[Dict, Dict]:
    """Move a supplier to `to_status`, fail-closed: the lifecycle must permit the move (you cannot activate a supplier
    that was never qualified, or re-award a rejected one). Returns (new_supplier, event); the input is not mutated and
    the event is a receipted record of the move."""
    frm = supplier.get("status", "prospective")
    if to_status not in _SUP_ALLOWED.get(frm, set()):
        raise SupplierError(f"supplier {supplier.get('id')!r}: illegal transition {frm!r} -> {to_status!r} "
                            f"(allowed from {frm!r}: {sorted(_SUP_ALLOWED.get(frm, set())) or 'none'})")
    ns = dict(supplier)
    ns["status"] = to_status
    event = {"supplier": supplier.get("id"), "from": frm, "to": to_status}
    return ns, event


def _options(suppliers: Sequence[Mapping]) -> List[Dict[str, object]]:
    opts = []
    for s in suppliers:
        sc = s.get("scorecard")
        if not sc:
            raise SupplierError(f"supplier {s.get('id')!r}: no scorecard to score")
        opts.append({"id": s.get("id"), "criteria": sc})
    return opts


def score_suppliers(suppliers: Sequence[Mapping], weights: Mapping[str, Number]) -> List[Dict[str, object]]:
    """Rank suppliers by a transparent weighted score over their scorecards, highest first. Composes the sealed
    decision-support surface: every supplier's score carries its per-criterion breakdown and the weights, so the ranking
    is re-runnable and every position is explainable -- never a silent number."""
    if not suppliers:
        raise SupplierError("no suppliers to score")
    return rank(_options(suppliers), weights)


def award(suppliers: Sequence[Mapping], weights: Mapping[str, Number]) -> Dict[str, object]:
    """Recommend an award among the ELIGIBLE suppliers (status qualified or active), fail-closed on qualification. An
    unqualified supplier -- however high its raw scorecard -- is excluded from consideration, so it can never be awarded
    by a hidden default; if no supplier is eligible, the award is refused. Returns the decision-support recommendation
    (top eligible supplier with its breakdown, runner-up, and margin) plus the eligible id set -- advice with its
    reasoning attached, for a human-gated award."""
    eligible = [s for s in suppliers if s.get("status") in _ELIGIBLE]
    if not eligible:
        raise SupplierError("no eligible (qualified or active) supplier to award -- unqualified suppliers are refused")
    rec = recommend(_options(eligible), weights)
    rec["eligible_ids"] = [s.get("id") for s in eligible]
    return rec
