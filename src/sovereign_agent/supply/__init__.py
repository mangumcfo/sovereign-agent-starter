"""Sovereign supply-chain primitives over the immutable core + object model.

Co-extrusion for s5_09 (Supply Chain Execution, KM GO WAVE 2026-08-03). Pure arithmetic, no crypto substrate
(pure-clone-clean, F-1 posture). The governance, immutability and provenance of a procurement obligation or an
inventory movement come from the existing ObligationLedger / object model / witness; this module adds the
supply-chain views those governed records must satisfy — on-hand quantity as a replay of movements, and a
no-phantom-stock check. Demand planning, optimization, and carrier integration stay designed-toward."""
from .inventory import on_hand, on_hand_for, would_overdraw, NegativeStockError

__all__ = ["on_hand", "on_hand_for", "would_overdraw", "NegativeStockError"]
