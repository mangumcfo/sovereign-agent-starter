"""Energy operations — a governed asset-intensive operation composing the sealed asset, supply, compliance, and posting surfaces.

Co-extrusion for s5_22 (Energy & Resources, KM Verticals wave 2026-08-05). Pure / structural, no crypto substrate
(F-1 pure-clone-clean). An energy, mining, or utilities operator does not re-implement asset registers, spare-parts
inventory, the human gate, or the general ledger: this vertical composes the sealed primitives into one governed
asset-intensive operation -- a maintenance or production work order on a REGISTERED governed asset, whose spare parts
are drawn fail-closed against governed on-hand (no phantom parts), whose execution on a regulated asset is authorized
only through a human gate, and whose cost posts as a balanced, value-conserving entry to the sealed general ledger.

Two governed acts:
  * `plan_operation` composes the sealed asset registry (the asset must be a real governed, registered asset), the
    sealed maintenance surface (the work order and its fail-closed lifecycle), and the sealed supply surface (every
    spare part is checked fail-closed against governed on-hand -- a part that would overdraw the location is refused, so
    an operation is never planned against parts that do not exist);
  * `authorize_operation` is DENY-BY-DEFAULT, fail-closed, in order: the operation must be a real planned operation, an
    asset operation must be a human-gated action class (composing the sealed `HumanApprovalGate`), and a NAMED human
    must approve (an approver and a non-empty approval reference naming the act); only then does the operation proceed,
    its cost posting to the sealed general ledger as a balanced {debits, credits} entry via financials.posting.from_entry.

Human primacy holds: the asset is registered, the parts are governed on-hand, and the operation is authorized by a
governed human act. This module holds the discipline and refuses what would break it -- an operation on an unregistered
asset, against parts that would overdraw, or without a named human's assent. Nothing here is a new asset register,
inventory engine, approval engine, or ledger; each is the sealed floor, composed."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Mapping, Sequence, Union

from ..assets.registry import validate_asset
from ..assets.maintenance import open_work_order
from ..supply.inventory import would_overdraw, on_hand_for
from ..compliance.human_approval_gate import HumanApprovalGate
from ..financials.posting import from_entry

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class EnergyError(ValueError):
    """Raised when an asset-intensive operation cannot proceed honestly: an unregistered asset, a spare part that would
    overdraw governed on-hand (a phantom part), a non-positive operation cost, or an operation authorized without a real
    planned operation, without the human-gated class, or without a named human's assent -- fail-closed, never a silent
    overrun of the asset, the parts, or human primacy."""


def plan_operation(asset: Mapping, kind: str, parts: Sequence[Mapping], movements,
                   *, location: str, memo: str = "") -> Dict[str, object]:
    """Plan a governed asset-intensive operation (a maintenance or production work order) on a REGISTERED asset,
    reserving its spare parts fail-closed against governed on-hand.

    The `asset` must be a real governed, registered asset -- composing the sealed asset registry (`validate_asset`); an
    asset with no id, no reporting currency, or an invalid cost/life/status is refused. The work order is opened on that
    asset through the sealed maintenance surface (`open_work_order`), starting `open` with its fail-closed lifecycle. Each
    required part -- a `{item, qty}` mapping -- is checked fail-closed against governed on-hand at `location` (composing
    `supply.inventory.would_overdraw`); a part whose issue would overdraw the location is refused, so an operation is
    never planned against parts that do not exist. Returns the planned operation carrying its asset, work order, reserved
    parts, and reporting currency."""
    validate_asset(asset)
    wo = open_work_order(asset["id"], kind, memo)
    reserved: List[Dict[str, object]] = []
    for p in parts:
        item, qty = p.get("item"), _dec(p.get("qty", 0))
        if not item:
            raise EnergyError("each part needs an item")
        if qty <= 0:
            raise EnergyError(f"part {item!r} qty must be > 0 (got {qty})")
        if would_overdraw(movements, item, location, qty):
            raise EnergyError(
                f"operation refused: part {item!r} would overdraw governed on-hand at {location!r} "
                f"(on hand {on_hand_for(movements, item, location)}, needs {qty}) -- no phantom parts"
            )
        reserved.append({"item": item, "qty": qty})
    return {"asset": asset["id"], "work_order": wo, "parts": reserved, "location": location,
            "currency": asset["currency"], "status": "planned"}


def authorize_operation(operation: Mapping, cost: Number, *, approver: str, approval_ref: str,
                        gate: HumanApprovalGate = None,
                        expense_account: str = "operations expense",
                        credit_account: str = "spare parts inventory") -> Dict[str, object]:
    """Authorize a planned asset-intensive operation -- DENY-BY-DEFAULT, fail-closed, on conditions in order:

      1. the `operation` must be a real PLANNED operation -- carrying an asset and a work order; an authorization of
         nothing, or of an operation not in `planned` state, is refused;
      2. an asset operation must be a HUMAN-GATED action class -- composing the sealed `HumanApprovalGate`
         (deny-by-default: an asset operation is high-materiality, so approval is required);
      3. a NAMED human must approve -- an `approver` and a non-empty `approval_ref` naming the act; an authorization with
         no named approver or no approval reference is refused.

    Only when the operation is real AND the class is gated AND a human has approved does the operation proceed, its
    `cost` posting to the sealed general ledger as a balanced {debits, credits} entry (operations expense debited, spare-
    parts inventory credited -- value-conserving, debits == credits by construction) via financials.posting.from_entry.
    The registry, the maintenance lifecycle, the gating policy, and the posting invariant are the sealed floors'; this
    adds only the fail-closed binding -- a real operation AND a human, or no authorization."""
    if not (operation and operation.get("asset") and operation.get("work_order")):
        raise EnergyError(
            "authorization refused: no real planned operation to authorize -- an operation carries a governed asset and work order"
        )
    if operation.get("status") != "planned":
        raise EnergyError(
            f"authorization refused: operation is {operation.get('status')!r}, not a planned operation"
        )
    gate = gate or HumanApprovalGate(policy={"high_materiality_classes": ["asset_operation"]})
    if not gate.requires_approval(
        "asset_operation",
        {"charter_v7_forbidden_classes": ["asset_operation"]},
        "corporate_regulated",
    ):
        raise EnergyError(
            "authorization refused: an asset operation must be a human-gated action class (deny-by-default)"
        )
    if not str(approver).strip():
        raise EnergyError("authorization refused: a named human approver is required (no silent asset operation)")
    if not str(approval_ref).strip():
        raise EnergyError("authorization refused: an approval reference naming the act is required")
    c = _dec(cost)
    if c <= 0:
        raise EnergyError(f"operation cost must be > 0 (got {c})")
    posting = from_entry(
        {"debits": [{"account": expense_account, "amount": c}],
         "credits": [{"account": credit_account, "amount": c}]},
        memo=f"asset operation {operation['work_order'].get('kind')} on {operation['asset']}",
    )
    return {"authorized": True, "asset": operation["asset"], "operation": operation,
            "posting": posting, "cost": c, "approver": approver, "approval_ref": approval_ref}
