"""Maintenance — governed work orders and deterministic condition triggers.

Co-extrusion for s5_12 (Asset & Maintenance Management). Pure / structural, no crypto substrate (F-1 pure-clone-clean).
A maintenance work order is a governed obligation that moves through a fail-closed lifecycle -- open → approved →
executed → closed -- and cannot skip a step (you cannot execute an unapproved order, or close an unexecuted one). And
a preventive work order is raised by a DETERMINISTIC condition trigger: a meter reading that reaches a governed
threshold raises exactly one work order, re-runnably -- not a scheduler's discretion. The approval step is a governed
act on the sealed access surface; the trigger is arithmetic anyone can reproduce from the reading and the threshold."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, List, Mapping, Set, Union

Number = Union[int, float, str, Decimal]

WO_STATES = ("open", "approved", "executed", "closed")
_WO_ALLOWED: Dict[str, Set[str]] = {
    "open": {"approved"},
    "approved": {"executed"},
    "executed": {"closed"},
    "closed": set(),
}


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class MaintenanceError(ValueError):
    """Raised for an out-of-order work-order transition, or a malformed trigger."""


def open_work_order(asset_id: str, kind: str, memo: str = "") -> Dict:
    """Open a work order against an asset. `kind` is 'preventive' or 'corrective' (free-form, recorded, not gated)."""
    if not asset_id:
        raise MaintenanceError("work order needs an asset id")
    return {"asset": asset_id, "kind": kind, "status": "open", "memo": memo}


def advance(wo: Mapping, to_status: str) -> Dict:
    """Advance a work order to `to_status`, fail-closed: the lifecycle must permit open→approved→executed→closed with
    no step skipped. Returns a new work order; the input is not mutated. (Approval is where a human governs the act on
    the sealed access surface; this function enforces that the step cannot be bypassed.)"""
    frm = wo.get("status", "open")
    if to_status not in _WO_ALLOWED.get(frm, set()):
        raise MaintenanceError(f"work order on {wo.get('asset')!r}: illegal transition {frm!r} -> {to_status!r} "
                               f"(allowed from {frm!r}: {sorted(_WO_ALLOWED.get(frm, set())) or 'none'})")
    nw = dict(wo)
    nw["status"] = to_status
    return nw


def meter_triggered(reading: Number, threshold: Number) -> bool:
    """Whether a meter reading has reached its governed maintenance threshold — a deterministic, reproducible test."""
    return _dec(reading) >= _dec(threshold)


def due_work_orders(readings: Iterable[Mapping], kind: str = "preventive") -> List[Dict]:
    """Raise a preventive work order for every asset whose meter reading has reached its threshold. Each input maps
    `asset`, `reading`, and `threshold`; the result is deterministic in the inputs -- re-run it and get the same set of
    orders, so preventive maintenance is a governed consequence of the readings, not a planner's discretion."""
    due: List[Dict] = []
    for r in readings:
        if "threshold" not in r or "reading" not in r or not r.get("asset"):
            raise MaintenanceError(f"meter reading missing asset/reading/threshold: {dict(r)!r}")
        if meter_triggered(r["reading"], r["threshold"]):
            due.append(open_work_order(r["asset"], kind,
                                       memo=f"meter {_dec(r['reading'])} >= threshold {_dec(r['threshold'])}"))
    return due
