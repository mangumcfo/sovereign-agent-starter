"""Migration — a governed, verifiable migration primitive: value-conserving reconciliation (source == migrated),
merkle provenance, and a fail-closed cutover lifecycle with rollback-as-fork, composing the sealed floors (s5_33)."""
from .reconcile import (
    reconcile, assert_reconciled, manifest_root, open_migration, transition, cutover, MigrationError,
)

__all__ = [
    "reconcile", "assert_reconciled", "manifest_root", "open_migration", "transition", "cutover", "MigrationError",
]
