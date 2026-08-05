"""Migration — a governed, verifiable migration primitive: value-conserving reconciliation (source == migrated),
merkle provenance, and a fail-closed cutover lifecycle with rollback-as-fork, composing the sealed floors (s5_33).
The escape arc composes this primitive into receipted cutovers off incumbent systems -- QuickBooks onto the sovereign
ledger (s5_34), Salesforce onto governed mandates (s5_35), and enterprise giants as a portfolio carve-in (s5_36)."""
from .reconcile import (
    reconcile, assert_reconciled, manifest_root, open_migration, transition, cutover, MigrationError,
)
from .quickbooks import (
    map_to_coa, opening_entry, receipted_cutover, QuickBooksError,
)
from .salesforce import (
    opportunity_to_mandate, map_opportunities, bill_mandate, SalesforceError,
)
from .carve_in import (
    open_carve_in, reconcile_carve_in, carve_in_cutover, portfolio_root, portfolio_cutover, CarveInError,
)

__all__ = [
    "reconcile", "assert_reconciled", "manifest_root", "open_migration", "transition", "cutover", "MigrationError",
    "map_to_coa", "opening_entry", "receipted_cutover", "QuickBooksError",
    "opportunity_to_mandate", "map_opportunities", "bill_mandate", "SalesforceError",
    "open_carve_in", "reconcile_carve_in", "carve_in_cutover", "portfolio_root", "portfolio_cutover", "CarveInError",
]
