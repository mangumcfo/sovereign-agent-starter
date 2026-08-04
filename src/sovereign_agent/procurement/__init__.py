"""Procurement — governed three-way match (PO/GR/invoice, fail-closed, value-conserving) + governed supplier registry
with transparent composed scoring and fail-closed award (s5_16, Procurement-to-Pay)."""
from .matching import three_way_match, ap_entry, MatchError
from .supplier import register, transition, score_suppliers, award, SupplierError

__all__ = [
    "three_way_match", "ap_entry", "MatchError",
    "register", "transition", "score_suppliers", "award", "SupplierError",
]
