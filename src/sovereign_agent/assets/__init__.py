"""Assets — governed asset registry + lifecycle, value-conserving depreciation, and governed maintenance (s5_12)."""
from .registry import (
    validate_asset, can_transition, transition, LIFECYCLE, AssetError,
)
from .depreciation import (
    straight_line, units_of_production, schedule,
    STRAIGHT_LINE, UNITS_OF_PRODUCTION, DepreciationError,
)
from .maintenance import (
    open_work_order, advance, meter_triggered, due_work_orders, WO_STATES, MaintenanceError,
)

__all__ = [
    "validate_asset", "can_transition", "transition", "LIFECYCLE", "AssetError",
    "straight_line", "units_of_production", "schedule", "STRAIGHT_LINE", "UNITS_OF_PRODUCTION", "DepreciationError",
    "open_work_order", "advance", "meter_triggered", "due_work_orders", "WO_STATES", "MaintenanceError",
]
