"""S4 Yield Engine 1.1 — value-flow projector (spec artifacts/specs/yield_organism_v0.1.yaml).

Proves the book's model on the verified, crypto-free substrate:
  (a) a value-flow projects correctly from an approved receipt — numbers match the book's model;
  (b) projection REFUSES from an unapproved / gate-less MATERIAL obligation (rides AH-1 hardening);
  (c) money_path OFF — the projector exposes no fund-moving path, only computes (value-only, no side effect);
  (d) every value-flow record references a real source cylinder id.

These tests exercise value_flow.py directly (import linkage the strengthened extrusion harness expects).
"""
from decimal import Decimal

import pytest

from sovereign_agent.obligations.ledger import ObligationLedger
from sovereign_agent.yield_organism.value_flow import (
    ValueFlow,
    ValueFlowProjector,
    ValueFlowRefused,
    WeightBasis,
)


def _real_gate(action, obligation):
    """A real human breath-gate disposition (real=True) — the operator acting through the owner-gated route."""
    return {"status": "approved", "real": True}


def _gated_ledger(tmp_path):
    return ObligationLedger(root=str(tmp_path / "obl"), principal_id="owner", gate=_real_gate)


# ── (a) projects correctly from an approved receipt — numbers match the book ──────────────────────
def test_projects_weighted_value_from_approved_receipt(tmp_path):
    """Book model (Ch2/Ch6): a 12,000-unit reward, alignment-fidelity 0.92 -> weighted 11,040.00."""
    L = _gated_ledger(tmp_path)
    reward = L.open("staking reward R-140", owner="holder-01", material=True,
                    lgp={"economic_value": "12000", "denomination": "SLATE"})
    L.approve(reward["id"], approved_by="owner")   # real gate -> cleared, is_approved True

    vf = ValueFlowProjector(L).project(reward["id"], WeightBasis.supplied("0.92"))

    assert isinstance(vf, ValueFlow)
    assert vf.base_value == Decimal("12000")
    assert vf.weight == Decimal("0.92")
    assert vf.weighted_value == Decimal("11040.00")     # 12000 * 0.92, Decimal-exact
    assert vf.holder == "holder-01"
    assert vf.denomination == "SLATE"
    assert vf.material is True
    assert vf.basis == "alignment_fidelity"
    assert vf.summable is True and vf.directional is False


# ── (b) refuses from an unapproved / gate-less material obligation (AH-1 fail-closed) ──────────────
def test_refuses_unapproved_material_obligation(tmp_path):
    """A gate-less ledger cannot mint a material approval (AH-1); the projector then refuses the value-flow."""
    L = ObligationLedger(root=str(tmp_path / "obl"), principal_id="owner")  # NO gate injected
    reward = L.open("unwitnessed reward", owner="holder-02", material=True,
                    lgp={"economic_value": "5000"})

    # gate-less material approval is itself barred, fail-closed (records the denial, then raises)
    with pytest.raises(PermissionError):
        L.approve(reward["id"], approved_by="owner")

    # ...and no value-flow projects from the unsealed cylinder
    with pytest.raises(ValueFlowRefused):
        ValueFlowProjector(L).project(reward["id"], WeightBasis.supplied("0.9"))


# ── (c) money_path OFF — value-only, no fund-moving path, no side effect ───────────────────────────
def test_money_path_off_no_fund_moving_path(tmp_path):
    L = _gated_ledger(tmp_path)
    reward = L.open("reward", owner="holder-03", material=True, lgp={"economic_value": "1000"})
    L.approve(reward["id"], approved_by="owner")
    projector = ValueFlowProjector(L)

    vf = projector.project(reward["id"], WeightBasis.supplied("1"))
    assert vf.money_path == "OFF"

    # the projector exposes NO fund-moving path — only projection/compute
    for forbidden in ("transfer", "settle", "pay", "move_funds", "wire", "disburse", "send"):
        assert not hasattr(projector, forbidden), f"projector must not expose a {forbidden}() path"

    # projecting moves nothing and writes nothing to the chain (value-only, deterministic)
    before = list(L.iter_entries())
    vf_again = projector.project(reward["id"], WeightBasis.supplied("1"))
    after = list(L.iter_entries())
    assert before == after                       # nothing appended to the sealed chain
    assert vf.to_dict() == vf_again.to_dict()    # same inputs -> byte-identical value-flow record


# ── (d) every value-flow references a real source cylinder id ──────────────────────────────────────
def test_value_flow_references_real_source_cylinder(tmp_path):
    L = _gated_ledger(tmp_path)
    reward = L.open("reward", owner="holder-04", material=True, lgp={"economic_value": "800"})
    L.approve(reward["id"], approved_by="owner")
    L.close(reward["id"], evidence="/art/reward.json sha=deadbeefcafef00d", evidence_tier="E2")

    vf = ValueFlowProjector(L).project(reward["id"], WeightBasis.supplied("0.75"))

    # references the real sealed cylinder, and it resolves to an actual debit on the ledger
    assert vf.source_cylinder_id == reward["id"]
    debit_ids = {e["id"] for e in L.iter_entries() if e.get("type") == "debit"}
    assert vf.source_cylinder_id in debit_ids
    # closed cylinder -> the value-flow carries the minted receipt id (extra sealed provenance)
    assert vf.receipt_id is not None
    assert vf.weighted_value == Decimal("600.00")   # 800 * 0.75

    # an unknown cylinder is refused, never fabricated into a flow
    with pytest.raises(KeyError):
        ValueFlowProjector(L).project("obl_does_not_exist", WeightBasis.supplied("0.5"))
