"""sovereign_agent.yield_organism — the S4 Yield Engine (spec artifacts/specs/yield_organism_v0.1.yaml).

Slice 1.1 (IMPLEMENTED): the value-flow projector — a receipt projected to a weighted economic value,
built on the crypto-free verified substrate (obligations/ledger.py + obligations/projection.py). money_path
is OFF absolutely: it attributes value, it never moves it. The crypto engine ring is a SEALED-HOST seam
(the node lane), absent in this env and never faked.

Slice 1.2 (IMPLEMENTED): the four-component alignment scorer (autonomy-ledgers ring) — reads the live
GREEN/YELLOW/RED evidence off the same crypto-free ledger and computes a bounded, conservative alignment
posture. The posture plugs into 1.1's weight seam via WeightBasis.from_posture.

Slice 1.3 (IMPLEMENTED): the compounding ring — BoundedCompounder (Model 2, S2-V5 Ch4: yield compounds
with the rolling alignment posture as a HARD ceiling; excess accrues flat, never compounds) + DriftBrake
(reads the GAP_REGISTER-class drift signal, fail-closed; pauses the compound BEFORE the next period's
roll-up lands; resumes only via a dispositioned, AH-1 real-gated proposal). money_path OFF absolutely.

Slice 1.5 (IMPLEMENTED, the Phase-1 CLOSER): the economic/ verifiable-yield export — the
EconomicBundleExporter assembles the economic/ subdirectory of the constitutional verifiable-package
(value_flows.ndjson + posture.json + compounding_rollup.json + reserve_state.json + a content-hashed
manifest) and RE-DERIVES the yield computation from the bundle on verify (every value-flow references a
real cylinder; the roll-up re-runs the BoundedCompounder over the bundled inputs). Reproducibility is
computed here; the cryptographic signature is the SEALED-HOST seam (the node lane), reported SEPARATELY.

Slice 2.1 (IMPLEMENTED): Breath-26 engine wiring — the proven Breath-26 economic engines (engines/:
constant-product AMMPool, MintEngine payout, RecircAllocator 70/20/10) are extracted into the kernel
(each with a provenance header: origin path + source sha256 + self-test PASS lineage) and WIRED onto the
receipted substrate by economic_actions.py: a swap / distribution is recorded as a BALANCED set of dr/cr
obligations (attribution, not payment) with the declared-threshold gate (above an OPERATOR-DECLARED
threshold the action is material, waits for the human breath-gate, and FAILS CLOSED unapproved; below it
still seals as receipted obligations). What is INCLUDED: the constant-product swap math, the payout/recirc
allocations, balanced double-entry, fail-closed gating, money_path OFF. What is NOT (deliberately absent,
never invented): the fee model + pool-balance bands (Ch3 spec gap, register B3) — so NO cross-denomination
value-equality is claimed for a swap; and the token-typed schema (stake/reward/release) is AA's S4-G2
lane — this module exposes the seam (denomination parameters, normalized allocation form), it does not
build the typed substrate adapters.

Later slices (declared in the spec, NOT built here per the Authoritative Pattern Rule): the fuller
economic drift safeguard (auto-proposed compensating obligations, S4-V3 Ch7) and the guardrail/token-
Atrium surfaces.
"""
from .alignment_scorer import AlignmentPosture, AlignmentScorer, ComponentScore
from .compounding import (
    BoundedCompounder,
    BrakeSignal,
    CompoundingRecord,
    CompoundingRefused,
    DriftBrake,
    PeriodInput,
    ResumeRefused,
    RollUp,
)
from .economic_actions import (
    ActionLeg,
    DistributionRecord,
    EconomicActionRefused,
    SwapRecord,
    distribute_via_payout,
    ledger_leg_balance,
    payout_allocations,
    recirc_allocations,
    swap_via_pool,
)
from .economic_export import (
    BundleVerification,
    EconomicBundle,
    EconomicBundleExporter,
    EconomicExportRefused,
)
from .value_flow import ValueFlow, ValueFlowProjector, ValueFlowRefused, WeightBasis

__all__ = [
    "ValueFlowProjector", "ValueFlow", "WeightBasis", "ValueFlowRefused",
    "AlignmentScorer", "AlignmentPosture", "ComponentScore",
    "BoundedCompounder", "DriftBrake", "PeriodInput", "RollUp", "CompoundingRecord",
    "BrakeSignal", "CompoundingRefused", "ResumeRefused",
    "EconomicBundleExporter", "EconomicBundle", "BundleVerification", "EconomicExportRefused",
    "swap_via_pool", "distribute_via_payout", "SwapRecord", "DistributionRecord",
    "ActionLeg", "EconomicActionRefused", "ledger_leg_balance",
    "payout_allocations", "recirc_allocations",
]
