"""Migration — a governed, verifiable migration primitive: value-conserving reconciliation (source == migrated),
merkle provenance, and a fail-closed cutover lifecycle with rollback-as-fork, composing the sealed floors (s5_33).
The QuickBooks escape (s5_34) and the Salesforce escape (s5_35) compose this primitive into receipted cutovers off
those systems -- QuickBooks onto the sovereign ledger, Salesforce onto governed mandates."""
from .reconcile import (
    reconcile, assert_reconciled, manifest_root, open_migration, transition, cutover, MigrationError,
)
from .quickbooks import (
    map_to_coa, opening_entry, receipted_cutover, QuickBooksError,
)
from .salesforce import (
    opportunity_to_mandate, map_opportunities, bill_mandate, SalesforceError,
)

__all__ = [
    "reconcile", "assert_reconciled", "manifest_root", "open_migration", "transition", "cutover", "MigrationError",
    "map_to_coa", "opening_entry", "receipted_cutover", "QuickBooksError",
    "opportunity_to_mandate", "map_opportunities", "bill_mandate", "SalesforceError",
]
