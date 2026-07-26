"""S4 Yield Engine 2.1 — Breath-26 engine wiring (spec artifacts/specs/yield_organism_v0.1.yaml).

Proves the B4 Tiger half on the verified, crypto-free substrate — the extracted engines
(src/sovereign_agent/yield_organism/engines/) and the adapter
(src/sovereign_agent/yield_organism/economic_actions.py):

  (a) engine math is PRESERVED through extraction — the constant-product invariant holds and a
      known-value swap matches the Breath-26 numbers;
  (b) the three extracted engines' self_test()s still PASS (Breath-26 lineage intact);
  (c) a below-threshold swap seals as a BALANCED dr/cr pair (receipted, debits == credits);
  (d) an above-threshold swap is MATERIAL: it waits (proposed, unsealed) and FAILS CLOSED unapproved,
      then PROCEEDS when a named human approves through the ledger's real gate;
  (e) a payout/recirc distribution records balanced legs (legs sum to the total drawn), and a material
      distribution is human-gated (fail-closed unapproved);
  (f) negative control — a forced-bad / forced-unbalanced input is refused LOUDLY, never booked.

These tests import economic_actions.py + engines/ directly (the linkage the extrusion harness expects).
"""
from decimal import Decimal

import pytest

from sovereign_agent.obligations.ledger import ObligationLedger
from sovereign_agent.yield_organism.economic_actions import (
    DistributionRecord,
    EconomicActionRefused,
    SwapRecord,
    distribute_via_payout,
    ledger_leg_balance,
    payout_allocations,
    recirc_allocations,
    swap_via_pool,
)
from sovereign_agent.yield_organism.engines import amm_pool as amm_mod
from sovereign_agent.yield_organism.engines import payout_engine as payout_mod
from sovereign_agent.yield_organism.engines import recirc_allocator as recirc_mod
from sovereign_agent.yield_organism.engines.amm_pool import AMMPool
from sovereign_agent.yield_organism.engines.payout_engine import MintEngine
from sovereign_agent.yield_organism.engines.recirc_allocator import RecircAllocator


# ── fixtures ──────────────────────────────────────────────────────────────────────────────────────
def _real_gate(action, obligation):
    """A real human breath-gate disposition (real=True) — the operator acting through the owner-gated route."""
    return {"status": "approved", "real": True}


def _rubber_stamp_gate(action, obligation):
    """Dispositions 'approved' but real=False — AH-1 bars a material self-approval through it."""
    return {"status": "approved", "real": False}


def _gated_ledger(tmp_path, name="obl"):
    return ObligationLedger(root=str(tmp_path / name), principal_id="owner", gate=_real_gate)


# ── (a) engine math is preserved through extraction ───────────────────────────────────────────────
def test_constant_product_invariant_and_known_value_swap():
    """x*y=k holds across a swap, and the Breath-26 known value reproduces: 10 into a 1000/1000 pool
    yields 9.9009900990099… (k preserved exactly, Decimal)."""
    pool = AMMPool(Decimal("1000"), Decimal("1000"))
    k_before = pool.reserve_x * pool.reserve_y
    out = pool.swap(Decimal("10"))
    assert abs(out - Decimal("9.9009900990099")) < Decimal("0.0001")   # known Breath-26 value
    # constant-product invariant: reserves still multiply to k (Decimal-exact)
    assert pool.reserve_x * pool.reserve_y == k_before == pool.k
    assert pool.reserve_x == Decimal("1010")


def test_output_is_pure_calculate_does_not_mutate():
    """calculate_output_amount computes without touching reserves — the adapter relies on this to stay
    fail-closed (no pool mutation until the sealed proceed path)."""
    pool = AMMPool(Decimal("500"), Decimal("2000"))
    rx, ry = pool.reserve_x, pool.reserve_y
    out = pool.calculate_output_amount(Decimal("50"))
    assert abs(out - Decimal("181.818181818")) < Decimal("0.0001")
    assert (pool.reserve_x, pool.reserve_y) == (rx, ry)                # unchanged


# ── (b) the extracted engines' self_test()s still pass (Breath-26 lineage) ────────────────────────
def test_extracted_engine_self_tests_pass():
    assert amm_mod.self_test() is True
    assert recirc_mod.self_test() is True
    assert payout_mod.self_test() is True                              # module-level wrapper over MintEngine
    assert MintEngine(treasury_wallet="rTESTwallet0000000000000000000000000000").self_test() is True


# ── (c) below-threshold swap seals as a balanced dr/cr pair (receipted) ───────────────────────────
def test_below_threshold_swap_seals_balanced_pair(tmp_path):
    L = _gated_ledger(tmp_path)
    pool = AMMPool(Decimal("1000"), Decimal("1000"))

    rec = swap_via_pool(L, pool, Decimal("10"), threshold=Decimal("100"), principal="owner")

    assert isinstance(rec, SwapRecord)
    assert rec.material is False and rec.sealed is True and rec.balanced is True
    assert rec.money_path == "OFF"
    assert abs(rec.amount_out - Decimal("9.9009900990099")) < Decimal("0.0001")
    # two legs (out=debit + in=credit), each carrying a close receipt
    assert len(rec.legs) == 2 and all(leg.receipt_id for leg in rec.legs)
    # ledger-level balance proof: debits == credits (every open was closed)
    debits, credits = ledger_leg_balance(L, rec.obligation_ids)
    assert debits == credits == 2
    # the pool actually swapped (engine reserve model advanced on the sealed proceed path)
    assert pool.reserve_x == Decimal("1010")
    # no fund-moving path is exposed on the module surface
    import sovereign_agent.yield_organism.economic_actions as ea
    for forbidden in ("transfer", "settle", "pay", "move_funds", "wire", "disburse", "send"):
        assert not hasattr(ea, forbidden), f"adapter must not expose a {forbidden}() path"


# ── (d) above-threshold swap: waits + fails closed unapproved; proceeds when approved ─────────────
def test_above_threshold_swap_fails_closed_then_proceeds_on_approval(tmp_path):
    L = _gated_ledger(tmp_path)
    pool = AMMPool(Decimal("1000"), Decimal("1000"))
    rx_before = pool.reserve_x

    # unapproved (no named approver) — MATERIAL, fails closed; proposed obligations remain OPEN, pool untouched
    with pytest.raises(EconomicActionRefused, match="MATERIAL"):
        swap_via_pool(L, pool, Decimal("200"), threshold=Decimal("100"), principal="owner")
    assert pool.reserve_x == rx_before                                 # pool NOT mutated on refusal
    open_material = [e for e in L.iter_entries()
                    if e.get("type") == "debit" and e.get("material")]
    assert open_material, "the material swap left proposed obligations open on the chain"
    # none of those proposed obligations were closed (no credit) — waiting at the gate
    closed_ids = {e.get("closes") for e in L.iter_entries() if e.get("type") == "credit"}
    assert all(ob["id"] not in closed_ids for ob in open_material)

    # rubber-stamp gate (real=False) still fails closed (AH-1 bars material self-approval)
    L_rs = ObligationLedger(root=str(tmp_path / "rs"), principal_id="owner", gate=_rubber_stamp_gate)
    with pytest.raises(EconomicActionRefused):
        swap_via_pool(L_rs, AMMPool(Decimal("1000"), Decimal("1000")), Decimal("200"),
                      threshold=Decimal("100"), principal="owner", approver="owner")

    # named human approves through the REAL gate — the swap proceeds and seals balanced
    rec = swap_via_pool(L, pool, Decimal("200"), threshold=Decimal("100"), principal="owner",
                        approver="owner")
    assert rec.material is True and rec.sealed is True and rec.balanced is True
    debits, credits = ledger_leg_balance(L, rec.obligation_ids)
    assert debits == credits == 2
    assert pool.reserve_x == rx_before + Decimal("200")               # NOW the engine advanced


# ── (e) distribution: balanced legs; material distribution human-gated ────────────────────────────
def test_recirc_distribution_legs_balanced(tmp_path):
    """RecircAllocator 70/20/10 -> distribution legs sum EXACTLY to the total drawn (value-conserving)."""
    L = _gated_ledger(tmp_path)
    allocator = RecircAllocator(total_allocation=1000.0)
    allocator.allocate()
    allocs = recirc_allocations(allocator)                            # [(family,700),(posterity,200),(community,100)]

    rec = distribute_via_payout(L, allocs, principal="owner", approval_threshold=Decimal("100000"),
                                denomination="LGP")
    assert isinstance(rec, DistributionRecord)
    assert rec.sealed is True and rec.balanced is True and rec.money_path == "OFF"
    assert rec.legs_sum == rec.total == Decimal("1000")               # legs conserve the total drawn
    assert {leg.value for leg in rec.legs} == {Decimal("700"), Decimal("200"), Decimal("100")}
    debits, credits = ledger_leg_balance(L, rec.obligation_ids)
    assert debits == credits == 3


def test_payout_distribution_material_is_gated(tmp_path):
    """MintEngine payouts above the declared approval_threshold are material — fail-closed unapproved,
    then proceed on a real human approval."""
    L = _gated_ledger(tmp_path)
    engine = MintEngine(treasury_wallet="rTESTwallet0000000000000000000000000000", payout_amount=25.0)
    engine.add_recipient("001", "rWalletA000000000000000000000000000000")
    engine.add_recipient("002", "rWalletB000000000000000000000000000000")
    allocs = payout_allocations(engine)                              # [(001,25),(002,25)] -> total 50

    # threshold 40 -> total 50 is material -> fails closed with no approver
    with pytest.raises(EconomicActionRefused, match="MATERIAL"):
        distribute_via_payout(L, allocs, principal="owner", approval_threshold=Decimal("40"),
                              denomination="USD")
    # with a named approver through the real gate -> proceeds, balanced
    rec = distribute_via_payout(L, allocs, principal="owner", approval_threshold=Decimal("40"),
                                denomination="USD", approver="owner")
    assert rec.material is True and rec.sealed is True and rec.balanced is True
    assert rec.total == Decimal("50")
    debits, credits = ledger_leg_balance(L, rec.obligation_ids)
    assert debits == credits == 2


# ── (f) negative control: forced-bad / forced-unbalanced input refused loudly ─────────────────────
def test_negative_controls_refused_loudly(tmp_path):
    L = _gated_ledger(tmp_path)
    pool = AMMPool(Decimal("1000"), Decimal("1000"))

    # bad engine input (non-positive amount_in) — refused by the constant-product engine, loudly
    with pytest.raises(EconomicActionRefused):
        swap_via_pool(L, pool, Decimal("0"), threshold=Decimal("100"), principal="owner")

    # forced-UNBALANCED distribution: a declared total that disagrees with the summed legs is refused
    with pytest.raises(EconomicActionRefused, match="UNBALANCED"):
        distribute_via_payout(L, [("a", Decimal("70")), ("b", Decimal("30"))], principal="owner",
                              approval_threshold=Decimal("1000"), total=Decimal("999"))

    # below-floor allocation (senior $25 floor discipline) — refused loudly, never silently booked
    with pytest.raises(EconomicActionRefused, match="floor"):
        distribute_via_payout(L, [("senior-1", Decimal("10"))], principal="owner",
                              approval_threshold=Decimal("1000"), floor=Decimal("25"))

    # over-cap allocation — refused loudly, never silently clamped
    with pytest.raises(EconomicActionRefused, match="cap"):
        distribute_via_payout(L, [("whale-1", Decimal("500"))], principal="owner",
                              approval_threshold=Decimal("1000"), cap=Decimal("100"))

    # empty distribution — refused, never a silent zero
    with pytest.raises(EconomicActionRefused):
        distribute_via_payout(L, [], principal="owner", approval_threshold=Decimal("1000"))
