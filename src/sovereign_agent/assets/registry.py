"""Asset registry — a governed registry of assets whose lifecycle is a receipted state machine.

Co-extrusion for s5_12 (Asset & Maintenance Management). Pure / structural, no crypto substrate (runs in a pure public
clone, no skip -- F-1 posture). An asset is registered with its cost, salvage value, useful life (in periods), and
reporting currency, and it moves through a governed lifecycle -- acquired → in_service → idle → retired → disposed --
only by allowed transitions, each of which is a receipted event. An illegal transition (disposing an asset still in
service, reviving a disposed one) is refused, so the register can never carry an asset in an impossible state."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Mapping, Set, Tuple, Union

Number = Union[int, float, str, Decimal]

LIFECYCLE = ("acquired", "in_service", "idle", "retired", "disposed")
_ALLOWED: Dict[str, Set[str]] = {
    "acquired": {"in_service"},
    "in_service": {"idle", "retired"},
    "idle": {"in_service", "retired"},
    "retired": {"disposed"},
    "disposed": set(),
}


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class AssetError(ValueError):
    """Raised for a malformed asset, or an illegal lifecycle transition."""


def validate_asset(asset: Mapping) -> None:
    """Fail-closed validation of an asset record. Requires an id, a reporting currency, cost > 0, salvage in
    [0, cost], and a useful life of at least one period; the status, if present, must be a known lifecycle state."""
    if not asset.get("id"):
        raise AssetError("asset has no id")
    if not asset.get("currency"):
        raise AssetError(f"asset {asset.get('id')!r} has no reporting currency")
    cost, salvage = _dec(asset.get("cost", 0)), _dec(asset.get("salvage", 0))
    if cost <= 0:
        raise AssetError(f"asset {asset['id']!r} cost must be > 0 (got {cost})")
    if not (Decimal("0") <= salvage <= cost):
        raise AssetError(f"asset {asset['id']!r} salvage {salvage} must be in [0, cost]")
    if int(asset.get("useful_life", 0)) < 1:
        raise AssetError(f"asset {asset['id']!r} useful_life must be >= 1 period")
    st = asset.get("status", "acquired")
    if st not in _ALLOWED:
        raise AssetError(f"asset {asset['id']!r} has unknown status {st!r}")


def can_transition(frm: str, to: str) -> bool:
    """Whether the lifecycle permits moving an asset from `frm` to `to`."""
    return to in _ALLOWED.get(frm, set())


def transition(asset: Mapping, to_status: str, period: str, memo: str = "") -> Tuple[Dict, Dict]:
    """Move an asset to `to_status`, returning (new_asset, event). The transition is refused fail-closed unless the
    lifecycle allows it. The event is a receipted record of the move (from, to, period) -- the append-only history of
    the asset's life; the returned asset is a new mapping, the input is not mutated."""
    validate_asset(asset)
    frm = asset.get("status", "acquired")
    if not can_transition(frm, to_status):
        raise AssetError(f"asset {asset['id']!r}: illegal lifecycle transition {frm!r} -> {to_status!r} "
                         f"(allowed from {frm!r}: {sorted(_ALLOWED.get(frm, set())) or 'none'})")
    new_asset = dict(asset)
    new_asset["status"] = to_status
    event = {"asset": asset["id"], "from": frm, "to": to_status, "period": period, "memo": memo}
    return new_asset, event
