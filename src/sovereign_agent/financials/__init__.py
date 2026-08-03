"""Sovereign financials — thin, in-scope double-entry + allocation primitives over the immutable core.

Co-extrusion for s5_07 (Sovereign Financials, KM GO WAVE 2026-08-03). These are PURE (no crypto substrate):
double-entry balance enforcement, trial balance, and cost allocation are arithmetic that must hold regardless
of attestation, so they run in a pure public clone with no skip. The *immutability + governed posting + replay*
of a posting is provided by the existing ObligationLedger / projection (already tested); this module adds only
the financial-accounting invariants those records must satisfy. A full posting/statement/consolidation engine
stays designed-toward its own volumes (Framing A: exists != wired)."""
from .treasury import cash_position, total_by_currency, liquidity_coverage
from .project import budget_status, portfolio_roll_up
from .controlling import (
    validate_coa,
    roll_up_accounts,
    allocate_cost_pool,
    roll_up_center_costs,
    CoAError,
)
from .period_close import (
    period_is_balanced,
    close_period,
    guard_post_open,
    PeriodNotBalancedError,
    PeriodClosedError,
)
from .fx import convert, combine_converted, rate_for, revalue, FXError
from .dimensions import validate_dimension, roll_up_members, slice_amounts, DimensionError
from .drivers import (
    weights_from_driver, allocate_by_driver, DriverError,
    PROPORTIONAL, EQUAL, FIXED, DRIVERS,
)
from .close_workflow import (
    new_close, soft_close, complete_step, hard_close, CloseWorkflowError,
)
from .posting import (
    Line,
    UnbalancedPostingError,
    validate_balanced,
    post,
    trial_balance,
    allocate,
    AllocationError,
)

__all__ = [
    "Line", "UnbalancedPostingError", "validate_balanced", "post",
    "trial_balance", "allocate", "AllocationError",
    "cash_position", "total_by_currency", "liquidity_coverage",
    "budget_status", "portfolio_roll_up",
    "validate_coa", "roll_up_accounts", "allocate_cost_pool", "roll_up_center_costs", "CoAError",
    "period_is_balanced", "close_period", "guard_post_open",
    "PeriodNotBalancedError", "PeriodClosedError",
    "convert", "combine_converted", "rate_for", "revalue", "FXError",
    "validate_dimension", "roll_up_members", "slice_amounts", "DimensionError",
    "weights_from_driver", "allocate_by_driver", "DriverError",
    "PROPORTIONAL", "EQUAL", "FIXED", "DRIVERS",
    "new_close", "soft_close", "complete_step", "hard_close", "CloseWorkflowError",
]
