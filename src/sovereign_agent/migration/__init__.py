"""Migration — a governed, verifiable migration primitive: value-conserving reconciliation (source == migrated),
merkle provenance, and a fail-closed cutover lifecycle with rollback-as-fork, composing the sealed floors (s5_33).
The QuickBooks escape (s5_34) composes this primitive + the sealed chart of accounts + the sealed posting into a
receipted cutover off QuickBooks."""
from .reconcile import (
    reconcile, assert_reconciled, manifest_root, open_migration, transition, cutover, MigrationError,
)
from .quickbooks import (
    map_to_coa, opening_entry, receipted_cutover, QuickBooksError,
)

__all__ = [
    "reconcile", "assert_reconciled", "manifest_root", "open_migration", "transition", "cutover", "MigrationError",
    "map_to_coa", "opening_entry", "receipted_cutover", "QuickBooksError",
]
