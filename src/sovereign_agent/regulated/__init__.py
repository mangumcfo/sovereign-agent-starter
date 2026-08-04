"""Regulated Industries — governed traceability, quality-gated release, and audit readiness composing the sealed
primitives (merkle provenance, the fail-closed quality gate, scoped compliance) for the Regulated Industries vertical
(s5_24). The one new act is an end-to-end chain of custody: a batch- or serial-level, value-conserving, merkle-anchored
custody record whose release is fail-closed on both an intact chain and a passed quality gate."""
from .traceability import (
    open_lot, receipt, transfer, consume, custody_position, reconcile_custody, assert_custody,
    trace_root, lot_transition, release, TraceabilityError,
)

__all__ = [
    "open_lot", "receipt", "transfer", "consume", "custody_position", "reconcile_custody", "assert_custody",
    "trace_root", "lot_transition", "release", "TraceabilityError",
]
