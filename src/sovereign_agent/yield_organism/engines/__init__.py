"""sovereign_agent.yield_organism.engines — the Breath-26 economic engines, EXTRACTED (B4 Tiger half).

Three proven Breath-26 engines, brought into the kernel extract-don't-rewrite (each module's provenance
header records the origin path + source sha256 + self-test PASS lineage). The engines COMPUTE economic
quantities and move NOTHING — the money_path-OFF, receipted wiring onto the ObligationLedger lives in
the sibling economic_actions.py adapter, which exposes clean seams for AA's deeper token-typed substrate
(S4-G2 schema) without building her half.

  · amm_pool.AMMPool        — constant-product x*y=k swap (Decimal, NO fee; fee model = spec gap B3).
  · payout_engine.MintEngine — senior weekly payout with a $25 floor + eligibility.
  · recirc_allocator.RecircAllocator — Sri Yantra 70/20/10 value-conserving distribution.

Each module exposes a module-level self_test() (payout_engine wraps MintEngine.self_test()); all three
retain their Breath-26 PASS lineage.
"""
from .amm_pool import AMMPool
from .amm_pool import self_test as amm_pool_self_test
from .payout_engine import MintEngine, Recipient
from .payout_engine import self_test as payout_engine_self_test
from .recirc_allocator import AllocationBand, RecircAllocator
from .recirc_allocator import self_test as recirc_allocator_self_test

__all__ = [
    "AMMPool", "amm_pool_self_test",
    "MintEngine", "Recipient", "payout_engine_self_test",
    "RecircAllocator", "AllocationBand", "recirc_allocator_self_test",
]
