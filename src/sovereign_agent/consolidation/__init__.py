"""Consolidation — multi-entity structure, intercompany, and the group view as a projection (S5-V18)."""
from .entities import (
    validate_structure, group_members, effective_ownership, EntityError, CONTROL_THRESHOLD,
)
from .intercompany import record_intercompany, intercompany_accounts, IntercompanyError
from .consolidation import consolidate, ConsolidationError, CTA_ACCOUNT

__all__ = [
    "validate_structure", "group_members", "effective_ownership", "EntityError", "CONTROL_THRESHOLD",
    "record_intercompany", "intercompany_accounts", "IntercompanyError",
    "consolidate", "ConsolidationError", "CTA_ACCOUNT",
]
