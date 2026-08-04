"""Manufacturing — a governed, value-conserving production order composing the sealed primitives (BOM explosion,
fail-closed lifecycle, quality-gated completion, posting-shape cost) for the Manufacturing Sovereign ERP vertical (s5_19)."""
from .production_order import (
    open_order, transition, issue_materials, is_fully_issued, complete, cost_posting, ProductionError,
)

__all__ = [
    "open_order", "transition", "issue_materials", "is_fully_issued", "complete", "cost_posting", "ProductionError",
]
