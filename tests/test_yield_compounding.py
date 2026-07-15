"""S4 Yield Engine 1.3 — bounded compounding (Model 2) + drift brake (spec
artifacts/specs/yield_organism_v0.1.yaml).

Proves the sealed books' model on the verified, crypto-free substrate — the compounding ring in
src/sovereign_agent/yield_organism/compounding.py:

  (a) Model 2 compounds correctly under a known posture ceiling (S2-V5 Ch4 ROI sidebar's own numbers);
  (b) the ceiling BINDS — a posture drop mid-series lowers the compound; the rate never exceeds the
      rolling ceiling; excess fidelity accrues flat, never compounds;
  (c) drift above tolerance fires the brake BEFORE the period's roll-up lands (no roll-up written),
      and a structural cockpit-alert-shaped signal is emitted (receipted);
  (d) the brake is fail-closed — an unreadable/absent signal source BRAKES, never passes;
  (e) resume requires a REAL dispositioned proposal (AH-1 idiom) — a gate-less resume is refused;
  (f) end-to-end: scorer posture -> projector flows -> bounded compound (slices 1.1+1.2+1.3 compose);
  (g) read-only invariant — compounding + brake checks + resume never mutate the obligation ledger.

These tests import compounding.py directly (the linkage the strengthened extrusion harness expects).
"""
from decimal import Decimal

import pytest

from sovereign_agent.obligations.ledger import ObligationLedger
from sovereign_agent.yield_organism.alignment_scorer import AlignmentPosture, AlignmentScorer
from sovereign_agent.yield_organism.compounding import (
    MODEL_2_BOUNDED,
    SIGNAL_DRIFT,
    SIGNAL_UNREADABLE,
    BoundedCompounder,
    BrakeSignal,
    CompoundingRefused,
    DriftBrake,
    PeriodInput,
    ResumeRefused,
)
from sovereign_agent.yield_organism.value_flow import ValueFlowProjector, WeightBasis


# ── fixtures ──────────────────────────────────────────────────────────────────────────────────────
def _posture(weight: str) -> AlignmentPosture:
    """A posture fixture with a known weight — the compounder duck-types on .weight (bound [0,1])."""
    return AlignmentPosture(weight=Decimal(weight), posture_raw=Decimal(weight), components={},
                            n_cylinders=3, sufficiency="SUFFICIENT", degraded=False)


class _Flow:
    """ValueFlow-shaped record (duck-typed: .weighted_value + .directional) for unit fixtures."""
    def __init__(self, weighted_value: str, directional: bool = False):
        self.weighted_value = Decimal(weighted_value)
        self.directional = directional


def _real_gate(action, obligation):
    return {"status": "approved", "real": True}


def _rubber_stamp_gate(action, obligation):
    """Dispositions 'approved' but real=False — AH-1 bars a material self-approval through it."""
    return {"status": "approved", "real": False}


def _gated_ledger(tmp_path, name="obl"):
    return ObligationLedger(root=str(tmp_path / name), principal_id="owner", gate=_real_gate)


def _clean_register():
    """A GAP_REGISTER-class snapshot with no standing material drift (documented schema)."""
    return [{"id": "G-F1", "scope": "GREEN", "status": "DEFERRED"},
            {"id": "G-B2", "scope": "YELLOW", "status": "CLOSED"}]


def _drifting_register():
    """Standing material gaps above any zero tolerance — the drift the brake reads."""
    return _clean_register() + [{"id": "G-V1", "scope": "YELLOW", "status": "OPEN"},
                                {"id": "G-X9", "scope": "RED", "status": "BLOCKED-the operator"}]


# ── (a) Model 2 compounds correctly under a known posture ceiling — the book's own numbers ────────
def test_model2_reproduces_book_roi_sidebar_series():
    """S2-V5 Ch4 ROI sidebar: Y(n) = $2.0M · 1.06^(n-1); Y(25) ≈ $8.1M; 25-yr cumulative ≈ $109.7M.
    Constant posture 0.06 => rolling ceiling 0.06 => effective rate 0.06 — the book's 6% net series."""
    periods = [PeriodInput.of([_Flow("2.0")], _posture("0.06"))] + \
              [PeriodInput.of([], _posture("0.06")) for _ in range(24)]
    rec = BoundedCompounder().compound(periods)

    assert rec.model == MODEL_2_BOUNDED
    assert rec.completed is True and rec.paused_at_period is None
    assert len(rec.roll_ups) == 25
    q = Decimal("0.1")
    series = {r.period: r.yield_after for r in rec.roll_ups}
    assert series[1] == Decimal("2.0")                                        # Year 1: $2.0M
    assert series[5].quantize(q) == Decimal("2.5")                            # Year 5: $2.5M
    assert series[10].quantize(q) == Decimal("3.4")                           # Year 10: $3.4M
    assert series[25].quantize(q) == Decimal("8.1")                           # Year 25: $8.1M
    assert rec.cumulative.quantize(q) == Decimal("109.7")                     # cumulative ≈ $109.7M
    # exact closed form: sum = 2.0 * (1.06^25 - 1) / 0.06 (Decimal-exact recurrence matches)
    closed = Decimal("2.0") * (Decimal("1.06") ** 25 - 1) / Decimal("0.06")
    assert abs(rec.cumulative - closed) < Decimal("1e-15")
    assert rec.flat_total == 0                                                # no fidelity above ceiling
    assert all(r.money_path == "OFF" for r in rec.roll_ups) and rec.money_path == "OFF"


def test_model2_is_deterministic():
    """Same inputs -> byte-identical records (no timestamp/random in any roll-up)."""
    periods = [PeriodInput.of([_Flow("100")], _posture("0.05")),
               PeriodInput.of([_Flow("10")], _posture("0.04")),
               PeriodInput.of([], _posture("0.06"))]
    r1 = BoundedCompounder().compound(periods)
    r2 = BoundedCompounder().compound(periods)
    assert r1.to_dict() == r2.to_dict()


def test_directional_flow_is_never_summed():
    """A DIRECTIONAL/illustrative figure in a compounding sum is refused loudly, never summed."""
    periods = [PeriodInput.of([_Flow("100"), _Flow("999", directional=True)], _posture("0.05"))]
    with pytest.raises(CompoundingRefused, match="DIRECTIONAL"):
        BoundedCompounder().compound(periods)


# ── (b) the ceiling BINDS ─────────────────────────────────────────────────────────────────────────
def test_posture_drop_lowers_the_compound_and_ceiling_never_exceeded():
    """Fidelity dropping mid-series lowers the compounding rate with it (never exceeds the rolling
    ceiling), so the dropped series lands strictly below the constant-posture series."""
    n = 12
    constant = [PeriodInput.of([_Flow("100")], _posture("0.08"))] + \
               [PeriodInput.of([], _posture("0.08")) for _ in range(n - 1)]
    dropped = [PeriodInput.of([_Flow("100")], _posture("0.08"))] + \
              [PeriodInput.of([], _posture("0.08")) for _ in range(5)] + \
              [PeriodInput.of([], _posture("0.02")) for _ in range(n - 6)]
    rc = BoundedCompounder().compound(constant)
    rd = BoundedCompounder().compound(dropped)

    assert rd.roll_ups[-1].yield_after < rc.roll_ups[-1].yield_after   # posture drop lowered the compound
    assert rd.cumulative < rc.cumulative
    for r in rd.roll_ups:
        assert r.effective_rate <= r.ceiling                           # HARD bound — never exceeded
        assert r.effective_rate <= r.fidelity                          # and never above running fidelity


def test_fidelity_above_rolling_ceiling_accrues_flat_never_compounds():
    """When running fidelity spikes above the rolling posture ceiling, the excess accrues as flat
    yield and does NOT enter the compounding base (Model 2: 'the excess does not compound')."""
    periods = [PeriodInput.of([_Flow("1000")], _posture("0.04")),
               PeriodInput.of([], _posture("0.04")),
               PeriodInput.of([], _posture("0.10"))]     # spike above the rolling mean
    rec = BoundedCompounder().compound(periods)
    spike = rec.roll_ups[2]
    assert spike.fidelity > spike.ceiling
    assert spike.effective_rate == spike.ceiling                       # capped at the ceiling
    assert spike.flat_accrual == spike.yield_before * (spike.fidelity - spike.ceiling)
    assert spike.flat_accrual > 0
    # the flat excess is NOT in the compounding base:
    assert spike.yield_after == spike.yield_before * (1 + spike.ceiling)
    assert rec.flat_total == spike.flat_accrual


# ── (c) drift above tolerance fires the brake BEFORE the period lands ─────────────────────────────
def test_brake_fires_pre_period_no_rollup_written():
    """The register fills above tolerance between periods: the brake blocks the NEXT period's
    roll-up (nothing lands for it) and emits the structural cockpit-alert-shaped signal."""
    register = _clean_register()
    brake = DriftBrake(signal_source=lambda: register, tolerance=0)

    periods = [PeriodInput.of([_Flow("500")], _posture("0.05")),
               PeriodInput.of([_Flow("500")], _posture("0.05")),
               PeriodInput.of([_Flow("500")], _posture("0.05"))]

    # run period-by-period the way the engine does: fill the register after the first roll-up.
    rec1 = BoundedCompounder().compound(periods[:1], brake=brake)
    assert rec1.completed and len(rec1.roll_ups) == 1                  # clean signal — period 1 landed
    register.extend([{"id": "G-V1", "scope": "YELLOW", "status": "OPEN"}])

    rec2 = BoundedCompounder().compound(periods, brake=brake)
    assert rec2.completed is False
    assert rec2.paused_at_period == 1                                  # blocked BEFORE the roll-up lands
    assert rec2.roll_ups == ()                                         # NO roll-up written
    sig = rec2.brake_signal
    assert isinstance(sig, BrakeSignal)
    assert sig.status == SIGNAL_DRIFT and sig.kind == "cockpit_alert" and sig.severity == "STRUCTURAL"
    assert sig.synod_review_item is True                               # cockpit alert + Synod review item
    assert "G-V1" in sig.standing_material_gaps
    assert sig.proposal_hook["mechanism"] == "proposal"                # the proposal-mechanism hook
    assert sig.signal_id and sig.signal_id == sig.to_dict()["signal_id"]   # receipted, deterministic
    assert brake.engaged and sig in brake.fires                        # evidence trail retained


def test_engaged_brake_blocks_every_subsequent_period():
    brake = DriftBrake(signal_source=_drifting_register, tolerance=0)
    periods = [PeriodInput.of([_Flow("100")], _posture("0.05"))]
    rec = BoundedCompounder().compound(periods, brake=brake)
    assert rec.paused_at_period == 1 and rec.roll_ups == ()
    # still engaged: a fresh run stays blocked even if the register is now clean — resume is the gate.
    brake.signal_source = _clean_register
    rec2 = BoundedCompounder().compound(periods, brake=brake)
    assert rec2.paused_at_period == 1 and rec2.completed is False


# ── (d) fail-closed: a brake that cannot read its signal must brake ───────────────────────────────
def test_brake_fail_closed_when_signal_source_unreadable():
    for bad_brake in (
        DriftBrake(signal_source=None, tolerance=0),                        # no source configured
        DriftBrake(signal_source=lambda: (_ for _ in ()).throw(OSError("shard absent")), tolerance=0),
        DriftBrake(signal_source=lambda: [{"id": "?", "scope": "PURPLE", "status": "OPEN"}], tolerance=0),
        DriftBrake(signal_source=lambda: ["not-a-mapping"], tolerance=0),   # off-schema entry
    ):
        rec = BoundedCompounder().compound(
            [PeriodInput.of([_Flow("100")], _posture("0.05"))], brake=bad_brake)
        assert rec.completed is False and rec.paused_at_period == 1
        assert rec.roll_ups == ()
        assert rec.brake_signal.status == SIGNAL_UNREADABLE
        assert "fail-closed" in rec.brake_signal.reason
        assert bad_brake.engaged


# ── (e) resume requires a REAL dispositioned proposal (AH-1 idiom) ────────────────────────────────
def test_resume_refused_without_real_gate_and_granted_with_it(tmp_path):
    """Gate-less resumes are refused (unknown / non-material / unapproved / rubber-stamped self-
    approval); a material proposal dispositioned through a real human gate releases the brake."""
    brake = DriftBrake(signal_source=_drifting_register, tolerance=0)
    assert brake.check(period=1) is not None and brake.engaged

    L = _gated_ledger(tmp_path)
    # (1) invented proposal — refused
    with pytest.raises(ResumeRefused, match="does not exist"):
        brake.resume(L, "prop-invented")
    # (2) non-material proposal — refused (resume is a material act)
    soft = L.open("note the drift", owner="holder-01", material=False)
    with pytest.raises(ResumeRefused, match="not material"):
        brake.resume(L, soft["id"])
    # (3) material but undispositioned — refused (no breath-gate clearance)
    prop = L.open("resume compounding after G-V1 addressed", owner="holder-01", material=True)
    with pytest.raises(ResumeRefused, match="breath-gate"):
        brake.resume(L, prop["id"])
    assert brake.engaged                                                # every refusal left it engaged

    # (4) material self-approval WITHOUT a real gate (AH-1 bar) — refused
    L2 = ObligationLedger(root=str(tmp_path / "obl2"), principal_id="owner-x", gate=_rubber_stamp_gate)
    sham = L2.open("rubber-stamped resume", owner="owner-x", material=True)
    L2.approve(sham["id"], approved_by="owner-x")
    with pytest.raises(ResumeRefused, match="breath-gate"):
        brake.resume(L2, sham["id"])

    # (5) the real thing: material proposal approved through the REAL gate — brake releases, receipted.
    L.approve(prop["id"], approved_by="owner")
    receipt = brake.resume(L, prop["id"])
    assert brake.engaged is False
    assert receipt["proposal_id"] == prop["id"] and receipt["resumed_via"] == "proposal_mechanism"
    assert receipt["resume_receipt_id"] and receipt in brake.resumes    # resume evidence trail
    # and compounding proceeds again once the register is clean
    brake.signal_source = _clean_register
    rec = BoundedCompounder().compound([PeriodInput.of([_Flow("100")], _posture("0.05"))], brake=brake)
    assert rec.completed is True and len(rec.roll_ups) == 1


def test_resume_on_disengaged_brake_is_refused():
    brake = DriftBrake(signal_source=_clean_register, tolerance=0)
    with pytest.raises(ResumeRefused, match="no engaged brake"):
        brake.resume(None, "prop-x")


# ── (f) end-to-end: scorer posture -> projector flows -> bounded compound (three slices compose) ──
def _fully_aligned_cylinder(L, title, owner="holder-01", value="1000"):
    ob = L.open(title, owner=owner, material=True,
                lgp={"economic_value": value, "denomination": "SLATE"})
    L.approve(ob["id"], approved_by="owner")
    L.close(ob["id"], evidence="/proof/artifact.txt sha256 " + "a" * 40, closed_by="owner")
    return ob


def test_end_to_end_scorer_projector_compounder_compose(tmp_path):
    """1.2's posture weights 1.1's flows; 1.3 compounds them under the posture as the HARD ceiling."""
    L = _gated_ledger(tmp_path)
    rewards = [_fully_aligned_cylinder(L, f"reward r{i}", value="500") for i in range(3)]

    posture = AlignmentScorer(L).score(owner="holder-01")               # SUFFICIENT, weight 1.0
    assert posture.weight == Decimal("1")
    flows = [ValueFlowProjector(L).project(ob["id"], WeightBasis.from_posture(posture))
             for ob in rewards]
    assert all(f.summable and f.money_path == "OFF" for f in flows)

    periods = [PeriodInput.of(flows, posture),                          # 1500 lands in period 1
               PeriodInput.of([], posture)]                            # then compounds at min(1.0, 1.0)
    brake = DriftBrake(signal_source=_clean_register, tolerance=0)
    rec = BoundedCompounder().compound(periods, brake=brake)

    assert rec.completed is True
    assert rec.roll_ups[0].inflow == Decimal("1500")                    # projector flows summed exactly
    assert rec.roll_ups[1].effective_rate == posture.weight             # the scorer posture IS the rate/ceiling
    assert rec.roll_ups[1].yield_after == Decimal("1500") * (1 + posture.weight)
    assert rec.money_path == "OFF"                                      # nothing moved anywhere


# ── (g) read-only invariant: compounding + brake never mutate the ledger ──────────────────────────
def test_compounding_and_brake_never_mutate_ledger(tmp_path):
    L = _gated_ledger(tmp_path)
    reward = _fully_aligned_cylinder(L, "r1")
    prop = L.open("resume proposal", owner="holder-01", material=True)
    L.approve(prop["id"], approved_by="owner")
    before = [dict(e) for e in L.iter_entries()]

    posture = AlignmentScorer(L).score(owner="holder-01")
    flow = ValueFlowProjector(L).project(reward["id"], WeightBasis.from_posture(posture))
    brake = DriftBrake(signal_source=_drifting_register, tolerance=0)
    rec = BoundedCompounder().compound([PeriodInput.of([flow], posture)], brake=brake)  # brake fires
    assert rec.paused_at_period == 1
    with pytest.raises(ResumeRefused):
        brake.resume(L, "prop-invented")                                # refused resume reads only
    brake.resume(L, prop["id"])                                         # granted resume reads only
    BoundedCompounder().compound([PeriodInput.of([flow], posture)],
                                 brake=DriftBrake(signal_source=_clean_register, tolerance=0))

    after = [dict(e) for e in L.iter_entries()]
    assert before == after                                              # byte-identical chain
