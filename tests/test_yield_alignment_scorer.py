"""S4 Yield Engine 1.2 — four-component alignment scorer (spec artifacts/specs/yield_organism_v0.1.yaml).

Proves the book's model (S2-V5 Ch3 "What the Autonomy Ledgers Score"; S4-V3 Ch1) on the verified,
crypto-free substrate — the scorer READS the live GREEN/YELLOW/RED evidence off the obligation ledger and
never mutates it:

  (a) the four components combine per the book's model on a known evidence fixture;
  (b) thin / missing evidence degrades the posture CONSERVATIVELY (never up) — fail-safe;
  (c) determinism — same evidence set -> same posture;
  (d) bounded output — the posture weight stays in [0,1] on extreme inputs;
  (e) end-to-end — scorer posture -> projector weight -> value-flow (slices 1.2 and 1.1 compose).

These tests import alignment_scorer.py directly (the linkage the strengthened extrusion harness expects).
"""
from decimal import Decimal

import pytest

from sovereign_agent.obligations.ledger import ObligationLedger
from sovereign_agent.yield_organism.alignment_scorer import (
    AlignmentPosture,
    AlignmentScorer,
    ComponentScore,
    MISSING,
    SUFFICIENT,
    THIN,
    THIN_CEILING,
    WEIGHT_MAX,
    WEIGHT_MIN,
)
from sovereign_agent.yield_organism.value_flow import ValueFlowProjector, WeightBasis


def _real_gate(action, obligation):
    """A real human breath-gate disposition (real=True) — the operator acting through the owner-gated route."""
    return {"status": "approved", "real": True}


def _rubber_stamp_gate(action, obligation):
    """A NON-real gate: it dispositions 'approved' but real=False. AH-1 bars a self-approval of a MATERIAL
    obligation through such a gate (is_approved stays False) though the approval entry is recorded — the
    exact class-demotion the scorer's component 2 catches."""
    return {"status": "approved", "real": False}


def _gated_ledger(tmp_path):
    return ObligationLedger(root=str(tmp_path / "obl"), principal_id="owner", gate=_real_gate)


def _fully_aligned_cylinder(L, title, owner="holder-01", value="1000"):
    """A material reward that clears the real gate and closes with E2 (hash+path) evidence — the +4 shape:
    in-scope +1 (admitted) · class-respected +1 (material rode real gate) · evidence +1 (E2) · long-arc +1."""
    ob = L.open(title, owner=owner, material=True,
                lgp={"economic_value": value, "denomination": "SLATE"})
    L.approve(ob["id"], approved_by="owner")
    L.close(ob["id"], evidence="/proof/artifact.txt sha256 " + "a" * 40, closed_by="owner")
    return ob


# ── (a) four components combine per the book's model on a known evidence fixture ──────────────────
def test_four_components_on_known_fixture(tmp_path):
    """A fully-aligned material cylinder scores +1 on each of the four named components (total +4)."""
    L = _gated_ledger(tmp_path)
    ob = _fully_aligned_cylinder(L, "staking reward R-1")

    cs = AlignmentScorer(L).score_cylinder(ob["id"])

    assert isinstance(cs, ComponentScore)
    assert cs.in_scope == 1                    # admitted into authorized scope (approved)
    assert cs.class_respected == 1             # material rode the real GREEN/YELLOW/RED gate (AH-1)
    assert cs.evidence_producing == 1          # sealed E1/E2 audit-chainable evidence
    assert cs.long_arc_constitutional == 1     # approved + evidenced + no veto => strengthening
    assert cs.total == 4                       # the book's four components, each +1


def test_class_demotion_scores_minus_one(tmp_path):
    """A MATERIAL cylinder self-approved WITHOUT a real gate is a class-demotion attempt: component 2 = -1
    (reads the exact AH-1 bar). It also never clears scope-admission, so in-scope stays marginal (0)."""
    L = ObligationLedger(root=str(tmp_path / "obl"), principal_id="owner-x", gate=_rubber_stamp_gate)
    ob = L.open("unwitnessed material reward", owner="owner-x", material=True,
                lgp={"economic_value": "9000"})
    # self-approval by the owner through a NON-real gate — recorded 'approved' but barred by AH-1
    L.approve(ob["id"], approved_by="owner-x")

    cs = AlignmentScorer(L).score_cylinder(ob["id"])
    assert cs.class_respected == -1            # class demotion — book component 2 "-1 attempted to demote"
    assert cs.in_scope == 0                    # not admitted (is_approved False under AH-1)


def test_denied_action_is_out_of_scope(tmp_path):
    """A denied disposition => the gate ruled the action out of authorized scope: component 1 = -1."""
    L = _gated_ledger(tmp_path)
    ob = L.open("out-of-scope request", owner="holder-09", material=True,
                lgp={"economic_value": "100"})
    # a denial disposition on the chain — the gate ruled the action out of authorized scope
    L._append({"type": "approval", "approves": ob["id"], "approved_by": "owner",
               "disposition": "denied", "timestamp": "t"})

    cs = AlignmentScorer(L).score_cylinder(ob["id"])
    assert cs.in_scope == -1                   # book component 1 "-1 if out-of-scope"


def test_incomplete_evidence_scores_minus_one(tmp_path):
    """A cylinder closed with EMPTY evidence => component 3 = -1 (incomplete)."""
    L = _gated_ledger(tmp_path)
    ob = L.open("thin-evidence action", owner="holder-03", material=True,
                lgp={"economic_value": "500"})
    L.approve(ob["id"], approved_by="owner")
    # force a close credit with empty evidence directly on the chain (the ledger's close() requires E1;
    # here we exercise the scorer's incomplete-evidence branch on a malformed-but-present credit)
    L._append({"type": "credit", "closes": ob["id"], "evidence": "",
               "evidence_tier": "E0", "closed_by": "owner", "timestamp": "t"})

    cs = AlignmentScorer(L).score_cylinder(ob["id"])
    assert cs.evidence_producing == -1


# ── (b) thin / missing evidence degrades conservatively (never up) ────────────────────────────────
def test_missing_evidence_floors_to_zero(tmp_path):
    """No cylinders in scope => MISSING, weight 0 — the conservative floor. Never fabricates alignment."""
    L = _gated_ledger(tmp_path)
    posture = AlignmentScorer(L).score(owner="nobody")
    assert isinstance(posture, AlignmentPosture)
    assert posture.sufficiency == MISSING
    assert posture.weight == WEIGHT_MIN == Decimal("0")
    assert posture.n_cylinders == 0
    assert posture.degraded is True


def test_thin_evidence_is_capped_down(tmp_path):
    """One perfectly-aligned cylinder (raw posture 1.0) with THIN evidence is capped DOWN to THIN_CEILING —
    the same-shaped SUFFICIENT evidence would score higher, so thin never scores higher than rich."""
    L = _gated_ledger(tmp_path)
    _fully_aligned_cylinder(L, "lone reward")
    thin = AlignmentScorer(L).score()
    assert thin.n_cylinders == 1
    assert thin.sufficiency == THIN
    assert thin.posture_raw == Decimal("1")           # raw alignment is perfect...
    assert thin.weight == THIN_CEILING                # ...but the weight is capped down (conservative)
    assert thin.weight < thin.posture_raw

    # add two more identical cylinders => SUFFICIENT => the cap lifts, weight rises above the thin cap.
    _fully_aligned_cylinder(L, "reward 2")
    _fully_aligned_cylinder(L, "reward 3")
    rich = AlignmentScorer(L).score()
    assert rich.sufficiency == SUFFICIENT
    assert rich.weight == WEIGHT_MAX == Decimal("1")
    assert rich.weight > thin.weight                  # more evidence => never lower than thin (degrade only down)


def test_negative_alignment_floors_to_zero(tmp_path):
    """A drifting evidence set (net-negative alignment) floors the weight to 0 — yield never compounds on
    drift — even though there is plenty of evidence."""
    L = ObligationLedger(root=str(tmp_path / "obl"), principal_id="owner-x", gate=_rubber_stamp_gate)
    for i in range(4):
        ob = L.open(f"self-approved material {i}", owner="owner-x", material=True,
                    lgp={"economic_value": "100"})
        L.approve(ob["id"], approved_by="owner-x")    # barred self-approval => class demotion -1s
    posture = AlignmentScorer(L).score()
    assert posture.n_cylinders == 4
    assert posture.posture_raw < 0
    assert posture.weight == Decimal("0")
    assert posture.degraded is True


# ── (c) determinism ───────────────────────────────────────────────────────────────────────────────
def test_deterministic_same_evidence_same_posture(tmp_path):
    """Same evidence set -> byte-identical posture (no timestamp/random read into the posture)."""
    L = _gated_ledger(tmp_path)
    _fully_aligned_cylinder(L, "r1")
    _fully_aligned_cylinder(L, "r2")
    _fully_aligned_cylinder(L, "r3")
    s = AlignmentScorer(L)
    p1 = s.score()
    p2 = s.score()
    assert p1.to_dict() == p2.to_dict()
    assert p1.weight == p2.weight


# ── (d) bounded output on extreme inputs ─────────────────────────────────────────────────────────
def test_bounded_output_on_extreme_inputs(tmp_path):
    """Huge economic values and many cylinders — the posture weight stays within [0,1]. The scorer does
    not read economic magnitude into the posture (alignment is a fidelity score, not a size score)."""
    L = _gated_ledger(tmp_path)
    for i in range(25):
        _fully_aligned_cylinder(L, f"whale reward {i}", value="99999999999999999999")
    posture = AlignmentScorer(L).score()
    assert WEIGHT_MIN <= posture.weight <= WEIGHT_MAX
    assert Decimal("-1") <= posture.posture_raw <= Decimal("1")
    # bounded weight feeds a valid WeightBasis (its own [0,1] guard would raise otherwise)
    wb = WeightBasis.from_posture(posture)
    assert Decimal("0") <= wb.weight <= Decimal("1")


# ── (e) end-to-end: scorer posture -> projector weight -> value-flow (1.2 composes with 1.1) ──────
def test_end_to_end_scorer_posture_drives_value_flow(tmp_path):
    """The composition proof: an AlignmentScorer posture becomes the ValueFlowProjector's weight via
    WeightBasis.from_posture, and the projected value-flow uses exactly that weight — provenance
    'alignment_scorer', not 'supplied'."""
    L = _gated_ledger(tmp_path)
    # three fully-aligned cylinders => SUFFICIENT, raw posture 1.0, weight 1.0
    _fully_aligned_cylinder(L, "r1", owner="holder-01", value="1000")
    _fully_aligned_cylinder(L, "r2", owner="holder-01", value="1000")
    reward = _fully_aligned_cylinder(L, "r3", owner="holder-01", value="12000")

    posture = AlignmentScorer(L).score(owner="holder-01")
    weight_basis = WeightBasis.from_posture(posture)
    assert weight_basis.source == "alignment_scorer"     # honest provenance seam (not "supplied")

    vf = ValueFlowProjector(L).project(reward["id"], weight_basis)
    assert vf.weight == posture.weight                   # the scorer's weight rode into the value-flow
    assert vf.weighted_value == Decimal("12000") * posture.weight
    assert vf.weight_source == "alignment_scorer"
    assert vf.money_path == "OFF"                         # scoring never moved money; projection moves none


def test_partial_posture_scales_value_flow_down(tmp_path):
    """A partial alignment posture scales the value-flow DOWN (fidelity never amplifies): mix aligned +
    drifting cylinders => posture in (0,1) => weighted_value < base_value."""
    L = _gated_ledger(tmp_path)
    reward = _fully_aligned_cylinder(L, "aligned", owner="holder-07", value="1000")
    _fully_aligned_cylinder(L, "aligned-2", owner="holder-07", value="1000")
    _fully_aligned_cylinder(L, "aligned-3", owner="holder-07", value="1000")
    # a neutral, in-flight cylinder (approved, not yet closed) drags long-arc/evidence toward 0
    drift = L.open("in-flight", owner="holder-07", material=True, lgp={"economic_value": "1000"})
    L.approve(drift["id"], approved_by="owner")

    posture = AlignmentScorer(L).score(owner="holder-07")
    assert Decimal("0") < posture.weight < Decimal("1")
    vf = ValueFlowProjector(L).project(reward["id"], WeightBasis.from_posture(posture))
    assert vf.weighted_value < vf.base_value             # bounded — scaled down by imperfect fidelity


# ── read-only invariant: scoring never mutates the ledger ────────────────────────────────────────
def test_scoring_never_mutates_ledger(tmp_path):
    """The scorer reads evidence and never writes — the chain is byte-identical before and after scoring."""
    L = _gated_ledger(tmp_path)
    _fully_aligned_cylinder(L, "r1")
    before = [dict(e) for e in L.iter_entries()]
    AlignmentScorer(L).score()
    after = [dict(e) for e in L.iter_entries()]
    assert before == after
