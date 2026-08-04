"""Production order — a governed, value-conserving manufacturing order composing the sealed primitives.

Co-extrusion for s5_19 (Manufacturing Sovereign ERP, KM Option A 2026-08-04). Pure / structural, no crypto substrate
(F-1 pure-clone-clean). A vertical does not re-invent manufacturing modules: it composes the governed primitives the
core already presents. A production order here is a fail-closed lifecycle (planned -> released -> in_process ->
completed) over a bill of materials: the required materials are the sealed BOM explosion (supply.bom.explode_bom); the
materials issued to the order are value-conserving against that requirement -- issuing more than the BOM requires is
refused, and the order cannot COMPLETE until the issued materials conserve exactly to the requirement AND a quality gate
has passed. Completion is fail-closed: an order missing materials, or failing quality, does not complete -- the back
door of a finished good that was never fully built or never inspected stays closed by construction. The produced-good
cost is a value-conserving posting -- the issued-material cost debited to finished goods and credited out of
work-in-process, balanced -- emitted in the {debits, credits} shape that composes the sealed general ledger via
financials.posting.from_entry. Human primacy holds: the order is released and completed by governed acts; this module
holds the lifecycle and refuses what would break it."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Mapping, Tuple, Union

from ..supply.bom import explode_bom

Number = Union[int, float, str, Decimal]
_CENTS = Decimal("0.01")

# Production-order lifecycle -- fail-closed transitions (added to docs/DOMAIN_VOCAB_CARD.md per spine item 8).
_PO_ALLOWED: Dict[str, set] = {
    "planned": {"released", "cancelled"},
    "released": {"in_process", "cancelled"},
    "in_process": {"completed", "scrapped"},
    "completed": set(),
    "cancelled": set(),
    "scrapped": set(),
}


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class ProductionError(ValueError):
    """Raised for an illegal lifecycle transition, an over-issue beyond the BOM, or a completion that is not fully
    issued or has not passed quality -- fail-closed, never a silent build."""


def open_order(order_id: str, product: str, bom: Mapping[str, Number], build_qty: Number) -> Dict[str, object]:
    """Open a production order for `build_qty` of `product`, exploding the sealed bill of materials into the required
    material quantities (supply.bom.explode_bom). The order starts `planned` with nothing issued; the required map is
    the value it must conserve to before it can complete."""
    required = explode_bom(bom, build_qty)
    return {"id": order_id, "product": product, "build_qty": _dec(build_qty),
            "required": required, "issued": {}, "status": "planned"}


def transition(po: Mapping, to_status: str) -> Tuple[Dict, Dict]:
    """Move a production order to `to_status`, fail-closed: the lifecycle must permit the move (you cannot put a
    `planned` order in process without releasing it, or complete a `cancelled` one). Returns (new_order, event); the
    input is not mutated."""
    frm = po.get("status", "planned")
    if to_status not in _PO_ALLOWED.get(frm, set()):
        raise ProductionError(f"order {po.get('id')!r}: illegal transition {frm!r} -> {to_status!r} "
                              f"(allowed from {frm!r}: {sorted(_PO_ALLOWED.get(frm, set())) or 'none'})")
    npo = dict(po)
    npo["status"] = to_status
    return npo, {"order": po.get("id"), "from": frm, "to": to_status}


def issue_materials(po: Mapping, issues: Mapping[str, Number]) -> Dict[str, object]:
    """Issue materials to an in-process order, value-conserving: every issued component must be on the bill of
    materials, and the cumulative issued quantity may not exceed the BOM requirement (an over-issue is refused -- a
    production order consumes what it was planned to, not more). Returns the updated order; the input is not mutated."""
    if po.get("status") != "in_process":
        raise ProductionError(f"order {po.get('id')!r}: cannot issue materials to a {po.get('status')!r} order "
                              "-- release it to in_process first")
    required = po["required"]
    issued = dict(po.get("issued", {}))
    for c, q in issues.items():
        if c not in required:
            raise ProductionError(f"order {po.get('id')!r}: component {c!r} is not on the bill of materials")
        nq = issued.get(c, Decimal("0")) + _dec(q)
        if nq > required[c]:
            raise ProductionError(f"order {po.get('id')!r}: issuing {c!r} to {nq} would exceed the BOM requirement "
                                  f"{required[c]} -- over-issue refused")
        issued[c] = nq
    npo = dict(po)
    npo["issued"] = issued
    return npo


def is_fully_issued(po: Mapping) -> bool:
    """True when the issued materials conserve EXACTLY to the BOM requirement -- issued == required for every
    component. This is the value-conservation the completion gate enforces."""
    required = po["required"]
    issued = po.get("issued", {})
    return all(issued.get(c, Decimal("0")) == q for c, q in required.items())


def complete(po: Mapping, quality_passed: bool) -> Dict[str, object]:
    """Complete a production order, fail-closed on BOTH gates: the issued materials must conserve exactly to the BOM
    requirement (nothing built short), and the quality gate must have passed. A shortfall or a failed quality event
    refuses completion -- a finished good that was never fully built or never inspected does not exist. Returns the
    completed order."""
    if po.get("status") != "in_process":
        raise ProductionError(f"order {po.get('id')!r}: cannot complete a {po.get('status')!r} order "
                              "-- only an in-process order completes")
    short = {c: q - po.get("issued", {}).get(c, Decimal("0"))
             for c, q in po["required"].items() if po.get("issued", {}).get(c, Decimal("0")) != q}
    if short:
        raise ProductionError(f"order {po.get('id')!r}: cannot complete -- materials not fully issued "
                              f"(issued != BOM required): short {short}")
    if not quality_passed:
        raise ProductionError(f"order {po.get('id')!r}: cannot complete -- quality gate did not pass")
    npo = dict(po)
    npo["status"] = "completed"
    return npo


def cost_posting(po: Mapping, unit_costs: Mapping[str, Number],
                 finished_account: str = "finished goods", wip_account: str = "work in process") -> Dict[str, object]:
    """The produced-good cost as a value-conserving, balanced posting in the {debits, credits} shape. The cost is the
    sum of the issued-material quantities at their unit costs; it is debited to finished goods and credited out of
    work-in-process, so debits equal credits by construction -- nothing created or lost, only moved from materials into
    the finished good. Posts to the sealed general ledger via financials.posting.from_entry."""
    total = Decimal("0")
    for c, q in po.get("issued", {}).items():
        if c not in unit_costs:
            raise ProductionError(f"order {po.get('id')!r}: no unit cost for issued component {c!r}")
        total += _dec(q) * _dec(unit_costs[c])
    total = total.quantize(_CENTS)
    return {"order_id": po.get("id"), "debits": [{"account": finished_account, "amount": total}],
            "credits": [{"account": wip_account, "amount": total}], "balanced": True, "amount": total}
