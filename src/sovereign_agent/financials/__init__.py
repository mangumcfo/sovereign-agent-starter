"""Sovereign financials — thin, in-scope double-entry + allocation primitives over the immutable core.

Co-extrusion for s5_07 (Sovereign Financials, KM GO WAVE 2026-08-03). These are PURE (no crypto substrate):
double-entry balance enforcement, trial balance, and cost allocation are arithmetic that must hold regardless
of attestation, so they run in a pure public clone with no skip. The *immutability + governed posting + replay*
of a posting is provided by the existing ObligationLedger / projection (already tested); this module adds only
the financial-accounting invariants those records must satisfy. A full posting/statement/consolidation engine
stays designed-toward its own volumes (Framing A: exists != wired)."""
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
]
