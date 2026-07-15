"""BoundedCompounder + DriftBrake — the S4 Yield Engine's compounding ring (spec
yield_organism_v0.1.yaml, slice 1.3, yield-organism ring).

The sealed books name the model exactly:

  · **Model 2 — Bounded Compounding Yield** (S2-V5 Ch4): "Yield compounds across periods, with a
    constitutional-fidelity ceiling on the compounding rate. The Charter defines the ceiling (e.g.,
    'compounding is bounded at the federation's average alignment posture over the rolling 12-period
    window'); when the running fidelity exceeds the ceiling, the excess does not compound (it accrues
    as flat yield); when the running fidelity drops below the ceiling, the compounding rate drops with
    it. The ceiling is the structural barrier against the compounding outrunning the constitution."
  · **The drift brake** (S2-V5 Ch4): the brake reads the GAP_REGISTER-class drift signal and "pauses
    the compound *before* the next period's roll-up lands"; when it fires "the operator gets a
    structural signal (cockpit alert + Synod review item) explaining why the compounding paused";
    "compounding resumes only after the drift is addressed through the proposal mechanism".
    "*Compounding is architected as a privilege the constitutional surface grants*".
  · **Ring 3** (S4-V3 Ch1): the yield organism ring is "the compounding that is bounded by that
    fidelity rather than by time".

Named assumptions (stated, never silent):
  · An AlignmentPosture weight (the [0,1] fidelity the scorer computes, slice 1.2) is read DIRECTLY as
    the per-period compounding-rate fraction (weight 0.06 ⇒ 6%/period). The Charter's posture→rate
    mapping is a configuration seam the book leaves to the Charter; identity is the minimum honest
    default and reproduces the book's own worked series (Ch4 ROI sidebar: Y(n) = base·(1+r)^(n-1)).
  · The ceiling is the rolling mean of the posture weights over the trailing ROLLING_WINDOW periods
    (book default 12), including the current period. The effective rate is min(current fidelity,
    ceiling) — the ceiling is a HARD bound, never exceeded.
  · The GAP_REGISTER-class drift signal follows the documented federation schema
    (breathline-federation/governance/GAP_REGISTER.md): gap entries carrying a scope in
    {GREEN, YELLOW, RED} and a status in {OPEN, CLOSING, BLOCKED-the operator, DEFERRED, CLOSED}. A standing
    material gap (YELLOW/RED, OPEN or BLOCKED-the operator) is unaddressed drift. DESIGNED-TOWARD (the 1.2
    precedent, honestly marked): the live wire to the federation governance shard is a sealed-host /
    federation input NOT present in this env — the reader here is built and tested against the
    documented schema; wiring it to the live shard is the deployment step, never faked here.

Invariants (constitutional, non-negotiable):
  · money_path OFF — this computes a compounding posture / roll-up record; it moves NOTHING. There is
    deliberately no settle/pay/transfer/disburse method anywhere in this module.
  · read-only on the ledger — the brake READS approval evidence via pure projection; it never writes.
  · deterministic — same inputs -> byte-identical records (no timestamp/random in any record).
  · Decimal-exact — every surfaced number is an exact Decimal (evidence law: no float drift).
  · DIRECTIONAL never summed — a directional/illustrative ValueFlow in a compounding sum is REFUSED
    loudly (CompoundingRefused), never silently skipped or summed.
  · fail-closed brake — a brake that cannot read its drift signal MUST brake, not pass. An engaged
    brake blocks every subsequent period until an explicit, dispositioned, AH-1-real-gated resume.
  · brake-fires are receipted — every fire emits a structural BrakeSignal with a deterministic
    signal_id (content hash) and is retained on the brake's fire trail (evidence, replayable).
  · crypto-free — no breathline_primitives dependency; any crypto site routes through the
    _sealed_host_seam adapter (none is needed to compound; the ring stands alone).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Callable, Iterable, Optional, Sequence

from ..obligations import projection as _proj

MODEL_2_BOUNDED = "MODEL_2_BOUNDED_COMPOUNDING"   # S2-V5 Ch4 — the model this slice implements
ROLLING_WINDOW_DEFAULT = 12                        # the book's rolling 12-period posture window

# ── GAP_REGISTER-class drift-signal schema (documented federation form, GAP_REGISTER.md) ──
GAP_SCOPES = frozenset({"GREEN", "YELLOW", "RED"})
MATERIAL_GAP_SCOPES = frozenset({"YELLOW", "RED"})           # the gated classes — drift that matters
STANDING_GAP_STATUSES = frozenset({"OPEN", "BLOCKED-the operator"})    # unaddressed; CLOSING/DEFERRED/CLOSED are dispositioned
_ALL_GAP_STATUSES = frozenset({"OPEN", "CLOSING", "BLOCKED-the operator", "DEFERRED", "CLOSED"})

# Signal-read outcomes — explicit, never a silent default.
SIGNAL_CLEAN = "CLEAN"
SIGNAL_DRIFT = "DRIFT_ABOVE_TOLERANCE"
SIGNAL_UNREADABLE = "UNREADABLE"   # fail-closed: an unreadable signal BRAKES


class CompoundingRefused(ValueError):
    """Loud refusal to compound — bad inputs never become a silent zero (evidence law).

    Raised for a DIRECTIONAL flow in a compounding sum (never summed), an out-of-bounds posture
    weight, or a malformed period sequence. Mirrors the projector's refuse-don't-fabricate idiom.
    """


class ResumeRefused(PermissionError):
    """Fail-closed refusal to release the drift brake — mirrors the ledger's PermissionError idiom.

    Raised when a resume is attempted without a real, dispositioned proposal: unknown cylinder,
    non-material cylinder, or a cylinder that has not cleared the AH-1 breath-gate (incl. material
    self-approval without a real gate). A gate-less resume never releases the brake.
    """


def _dec(value) -> Decimal:
    """Coerce to an exact Decimal (evidence law — no float drift in any surfaced number)."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise CompoundingRefused(f"not a decimal: {value!r}") from exc


def _sig_hash(payload: dict) -> str:
    """Deterministic content hash for a receipt/signal record (sha256[:12] over canonical JSON)."""
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]


# ═══════════════════════════════ the drift brake ═══════════════════════════════

@dataclass(frozen=True)
class BrakeSignal:
    """The structural signal a brake-fire emits — cockpit-alert shaped, receipted, deterministic.

    The book's designed semantics, exactly: "when the brake fires the operator gets a structural
    signal (cockpit alert + Synod review item) explaining why the compounding paused" (S2-V5 Ch4).
    `proposal_hook` is the proposal-mechanism hook: it names what a resume requires (a material
    obligation dispositioned through a real human gate — the AH-1 idiom). `signal_id` is a
    deterministic content hash — the evidence-trail receipt of the fire (no timestamp, replayable).
    """
    period_blocked: int
    status: str                       # SIGNAL_DRIFT or SIGNAL_UNREADABLE (fail-closed fire)
    reason: str
    standing_material_gaps: tuple     # gap ids read from the register (empty when UNREADABLE)
    observed: Optional[int]           # standing material gap count (None when UNREADABLE)
    tolerance: int
    kind: str = "cockpit_alert"       # cockpit-alert shaped (Drift / Stillpoint Synod surface)
    synod_review_item: bool = True    # the paired structural signal the book names
    severity: str = "STRUCTURAL"      # structural, not advisory (S2-V5 Ch4)
    proposal_hook: dict = field(default_factory=lambda: {
        "mechanism": "proposal",
        "resume_requires": "a MATERIAL obligation on the ledger, dispositioned 'approved' through a "
                           "real human breath-gate (AH-1: opener != approver, or gate.real) — "
                           "DriftBrake.resume(ledger, proposal_id)",
    })
    money_path: str = "OFF"

    @property
    def signal_id(self) -> str:
        """Deterministic receipt id over the signal's content — the fire's evidence trail."""
        return _sig_hash({
            "period_blocked": self.period_blocked, "status": self.status, "reason": self.reason,
            "standing_material_gaps": list(self.standing_material_gaps),
            "observed": self.observed, "tolerance": self.tolerance,
        })

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id, "kind": self.kind, "severity": self.severity,
            "synod_review_item": self.synod_review_item,
            "period_blocked": self.period_blocked, "status": self.status, "reason": self.reason,
            "standing_material_gaps": list(self.standing_material_gaps),
            "observed": self.observed, "tolerance": self.tolerance,
            "proposal_hook": dict(self.proposal_hook), "money_path": self.money_path,
        }


class DriftBrake:
    """Reads the GAP_REGISTER-class drift signal; above tolerance it BLOCKS the next compound period.

    Fail-closed, absolutely: a brake with no signal source, or whose source raises or returns data
    off the documented schema, FIRES — a brake that cannot read its signal must brake, not pass.
    Once engaged it blocks every subsequent period until `resume()` verifies an explicit,
    dispositioned proposal on the obligation ledger (material + AH-1 real gate). It READS the ledger
    via pure projection and never writes it.

    `signal_source` is a zero-arg callable returning an iterable of gap entries per the documented
    GAP_REGISTER schema: {"id": str, "scope": GREEN|YELLOW|RED, "status": OPEN|CLOSING|BLOCKED-the operator|
    DEFERRED|CLOSED}. DESIGNED-TOWARD: binding this callable to the live federation governance shard
    (breathline-federation/governance/GAP_REGISTER.md) is the deployment wiring — the shard is not
    present in this env and is never faked here; absent a source the brake brakes (fail-closed).
    """

    def __init__(self, signal_source: Optional[Callable[[], Iterable[dict]]] = None,
                 tolerance: int = 0):
        if tolerance < 0:
            raise CompoundingRefused(f"tolerance {tolerance} is negative — no negative drift budget")
        self.signal_source = signal_source
        self.tolerance = int(tolerance)
        self._engaged: bool = False
        self._fires: list = []        # the receipted fire trail (BrakeSignal, append-only)
        self._resumes: list = []      # receipted resume trail (dict receipts, append-only)

    # ── reading the signal (fail-closed on every malformation) ──────────────────
    def read_signal(self) -> dict:
        """Read the drift signal once. Returns {status, standing_material_gaps, observed, reason}.
        ANY failure to read — no source, source raises, entry off-schema — is SIGNAL_UNREADABLE."""
        if self.signal_source is None:
            return {"status": SIGNAL_UNREADABLE, "standing_material_gaps": (), "observed": None,
                    "reason": "no drift-signal source configured — fail-closed (a brake that cannot "
                              "read its signal must brake)"}
        try:
            entries = list(self.signal_source())
        except Exception as exc:  # noqa: BLE001 — fail-closed catches EVERY read failure
            return {"status": SIGNAL_UNREADABLE, "standing_material_gaps": (), "observed": None,
                    "reason": f"drift-signal source unreadable ({type(exc).__name__}: {exc}) — fail-closed"}
        standing = []
        for e in entries:
            if not isinstance(e, dict):
                return {"status": SIGNAL_UNREADABLE, "standing_material_gaps": (), "observed": None,
                        "reason": f"gap entry off-schema (not a mapping: {e!r}) — fail-closed"}
            scope, status = e.get("scope"), e.get("status")
            if scope not in GAP_SCOPES or status not in _ALL_GAP_STATUSES:
                return {"status": SIGNAL_UNREADABLE, "standing_material_gaps": (), "observed": None,
                        "reason": f"gap entry off-schema (scope={scope!r}, status={status!r}) — fail-closed"}
            if scope in MATERIAL_GAP_SCOPES and status in STANDING_GAP_STATUSES:
                standing.append(str(e.get("id", "?")))
        observed = len(standing)
        if observed > self.tolerance:
            return {"status": SIGNAL_DRIFT, "standing_material_gaps": tuple(sorted(standing)),
                    "observed": observed,
                    "reason": f"{observed} standing material gap(s) > tolerance {self.tolerance} — "
                              f"drift above the Charter's tolerance threshold"}
        return {"status": SIGNAL_CLEAN, "standing_material_gaps": tuple(sorted(standing)),
                "observed": observed, "reason": "drift within tolerance"}

    # ── the pre-period check the compounder consults ────────────────────────────
    def check(self, period: int) -> Optional[BrakeSignal]:
        """Consulted BEFORE period `period`'s roll-up lands. Returns a BrakeSignal (and engages) when
        the brake must fire; None when compounding may proceed. An already-engaged brake fires on
        every period until resumed (resume only via the proposal mechanism)."""
        if self._engaged:
            sig = BrakeSignal(period_blocked=period, status=SIGNAL_DRIFT,
                              reason="brake engaged — compounding paused pending a dispositioned "
                                     "resume proposal (compounding is a privilege the constitutional "
                                     "surface grants)",
                              standing_material_gaps=(), observed=None, tolerance=self.tolerance)
            self._fires.append(sig)
            return sig
        read = self.read_signal()
        if read["status"] == SIGNAL_CLEAN:
            return None
        self._engaged = True
        sig = BrakeSignal(period_blocked=period, status=read["status"], reason=read["reason"],
                          standing_material_gaps=read["standing_material_gaps"],
                          observed=read["observed"], tolerance=self.tolerance)
        self._fires.append(sig)
        return sig

    @property
    def engaged(self) -> bool:
        return self._engaged

    @property
    def fires(self) -> tuple:
        """The receipted fire trail — every BrakeSignal this brake ever emitted (append-only)."""
        return tuple(self._fires)

    @property
    def resumes(self) -> tuple:
        """The receipted resume trail — every verified resume receipt (append-only)."""
        return tuple(self._resumes)

    # ── resume: only via an explicit, dispositioned, real-gated proposal (AH-1) ──
    def resume(self, ledger, proposal_id: str) -> dict:
        """Release the brake against a REAL dispositioned proposal on the obligation ledger.

        The proposal must be (a) a real cylinder (never invented), (b) MATERIAL (resuming a paused
        compound is a material act — it rides the gate), and (c) approved per the AH-1-hardened
        check (material needs a real human gate; opener != approver or gate.real). Anything less is
        refused (ResumeRefused) and the brake stays engaged — a gate-less resume never releases it.
        Reads the ledger via pure projection; writes NOTHING. Returns a deterministic resume receipt.
        """
        if not self._engaged:
            raise ResumeRefused("no engaged brake to resume — resume() is the release of a fired "
                                "brake, not a no-op")
        entries = list(ledger.iter_entries())
        debit = next((e for e in entries
                      if e.get("type") == "debit" and e.get("id") == proposal_id), None)
        if debit is None:
            raise ResumeRefused(f"resume proposal '{proposal_id}' does not exist on the ledger — "
                                f"a resume rides a real cylinder, never an invented one")
        if not debit.get("material"):
            raise ResumeRefused(f"resume proposal '{proposal_id}' is not material — resuming a "
                                f"paused compound is a material act and rides the material gate")
        if not _proj.is_approved(entries, proposal_id):
            raise ResumeRefused(f"resume proposal '{proposal_id}' has not cleared the breath-gate "
                                f"(AH-1 fail-closed) — compounding resumes only after the drift is "
                                f"addressed through the proposal mechanism")
        self._engaged = False
        receipt_payload = {"resumed_via": "proposal_mechanism", "proposal_id": proposal_id,
                           "proposal_title": debit.get("title"), "money_path": "OFF"}
        receipt = {**receipt_payload, "resume_receipt_id": _sig_hash(receipt_payload)}
        self._resumes.append(receipt)
        return receipt


# ═══════════════════════════════ bounded compounding (Model 2) ═══════════════════════════════

@dataclass(frozen=True)
class PeriodInput:
    """One compounding period's inputs: the period's realized value-flows + its alignment posture.

    `flows` are ValueFlow-shaped records (duck-typed on .weighted_value / .directional — no import
    cycle); `posture` is AlignmentPosture-shaped (duck-typed on .weight, the [0,1] fidelity)."""
    flows: tuple
    posture: object

    @classmethod
    def of(cls, flows: Sequence, posture) -> "PeriodInput":
        return cls(flows=tuple(flows), posture=posture)


@dataclass(frozen=True)
class RollUp:
    """One period's sealed roll-up record — a computed posture, not a payment (money_path OFF).

    `fidelity` is the period's running alignment (the posture weight); `ceiling` is the rolling-mean
    posture bound; `effective_rate` = min(fidelity, ceiling) — the ceiling is HARD, never exceeded.
    `flat_accrual` is the excess above the ceiling that accrues WITHOUT compounding (Model 2's
    "the excess does not compound"). `yield_after` is the period's net-yield figure (the book's
    Y(n) series); `cumulative` is the running sum of per-period yields + flat accruals — the
    sidebar's "sum of the annual yields over the window, not the final-year figure"."""
    period: int
    inflow: Decimal              # this period's realized value-flow sum (summable flows only)
    yield_before: Decimal
    fidelity: Decimal
    ceiling: Decimal
    effective_rate: Decimal      # min(fidelity, ceiling) — never exceeds the ceiling
    compounded_growth: Decimal   # yield_before * effective_rate
    flat_accrual: Decimal        # yield_before * max(fidelity - ceiling, 0) — accrues, never compounds
    yield_after: Decimal         # yield_before + compounded_growth + inflow
    cumulative: Decimal
    model: str = MODEL_2_BOUNDED
    money_path: str = "OFF"

    def to_dict(self) -> dict:
        """Deterministic, JSON-friendly view — Decimals as exact strings (no float drift)."""
        return {
            "period": self.period, "inflow": str(self.inflow),
            "yield_before": str(self.yield_before), "fidelity": str(self.fidelity),
            "ceiling": str(self.ceiling), "effective_rate": str(self.effective_rate),
            "compounded_growth": str(self.compounded_growth), "flat_accrual": str(self.flat_accrual),
            "yield_after": str(self.yield_after), "cumulative": str(self.cumulative),
            "model": self.model, "money_path": self.money_path,
        }


@dataclass(frozen=True)
class CompoundingRecord:
    """The full compounding run — roll-ups actually landed, plus the brake outcome if it fired.

    money_path OFF by construction: the record attributes a compounding posture; it moves nothing.
    When the brake fired, `paused_at_period` names the period whose roll-up did NOT land (the brake
    pauses the compound BEFORE the roll-up lands) and `brake_signal` carries the structural signal."""
    model: str
    roll_ups: tuple
    cumulative: Decimal
    flat_total: Decimal
    completed: bool
    paused_at_period: Optional[int] = None
    brake_signal: Optional[BrakeSignal] = None
    money_path: str = "OFF"

    def to_dict(self) -> dict:
        return {
            "model": self.model, "roll_ups": [r.to_dict() for r in self.roll_ups],
            "cumulative": str(self.cumulative), "flat_total": str(self.flat_total),
            "completed": self.completed, "paused_at_period": self.paused_at_period,
            "brake_signal": self.brake_signal.to_dict() if self.brake_signal else None,
            "money_path": self.money_path,
        }


class BoundedCompounder:
    """Model 2 — Bounded Compounding Yield (S2-V5 Ch4), with the rolling alignment posture as the
    HARD ceiling and the DriftBrake consulted before every period's roll-up lands.

    Computes; moves nothing. There is deliberately NO transfer/settle/pay/disburse method on this
    class — the absence is the money_path-OFF invariant. Deterministic and Decimal-exact throughout.
    """

    def __init__(self, rolling_window: int = ROLLING_WINDOW_DEFAULT):
        if rolling_window < 1:
            raise CompoundingRefused(f"rolling window {rolling_window} < 1 — no empty posture window")
        self.rolling_window = int(rolling_window)

    # ── SEALED-HOST-SEAM: crypto wiring routes through yield_organism/_sealed_host_seam.py (the node
    # lane). Signing the roll-up / compounding record is the crypto-engine ring — ABSENT in this env,
    # stubbed with explicit sentinels (sign_value_flow / verify_economic_bundle), never faked here.
    # The pure compounding needs no crypto and stands alone.

    @staticmethod
    def _period_inflow(flows: Sequence, period: int) -> Decimal:
        """Sum a period's realized value-flows. A DIRECTIONAL flow is REFUSED, never summed."""
        total = Decimal("0")
        for f in flows:
            if getattr(f, "directional", False):
                raise CompoundingRefused(
                    f"period {period}: DIRECTIONAL value-flow in a compounding sum — directional/"
                    f"illustrative figures are NEVER summed (evidence law)")
            total += _dec(getattr(f, "weighted_value"))
        if total < 0:
            raise CompoundingRefused(f"period {period}: negative inflow {total} — a value-flow "
                                     f"attributes value, not debt")
        return total

    @staticmethod
    def _fidelity(posture, period: int) -> Decimal:
        w = _dec(getattr(posture, "weight"))
        if w < 0 or w > 1:
            raise CompoundingRefused(
                f"period {period}: posture weight {w} out of [0,1] — fidelity bounds yield, never "
                f"amplifies it")
        return w

    def compound(self, periods: Sequence[PeriodInput],
                 brake: Optional[DriftBrake] = None) -> CompoundingRecord:
        """Run Model 2 over the period sequence, consulting `brake` BEFORE each roll-up lands.

        Per period p: fidelity_p = posture weight; ceiling_p = rolling mean of posture weights over
        the trailing window (incl. p); effective_rate = min(fidelity, ceiling) — HARD ceiling;
        yield_p = yield_{p-1}·(1 + effective_rate) + inflow_p; the excess when fidelity > ceiling
        accrues flat (never enters the compounding base). Period 1 seeds the base (nothing to
        compound yet). When the brake fires at period p, NO roll-up lands for p (pre-period pause)
        and the record carries the structural signal.
        """
        if not periods:
            raise CompoundingRefused("no periods to compound — an empty roll-up is refused, "
                                     "never a silent zero")
        roll_ups: list = []
        weights: list = []
        yield_base = Decimal("0")
        cumulative = Decimal("0")
        flat_total = Decimal("0")
        for idx, pin in enumerate(periods, start=1):
            if brake is not None:
                signal = brake.check(period=idx)
                if signal is not None:
                    # the brake pauses the compound BEFORE this period's roll-up lands — nothing
                    # is written for this or any later period; the signal is the receipt.
                    return CompoundingRecord(
                        model=MODEL_2_BOUNDED, roll_ups=tuple(roll_ups), cumulative=cumulative,
                        flat_total=flat_total, completed=False, paused_at_period=idx,
                        brake_signal=signal)
            fidelity = self._fidelity(pin.posture, idx)
            weights.append(fidelity)
            window = weights[-self.rolling_window:]
            ceiling = sum(window, Decimal("0")) / Decimal(len(window))
            effective = fidelity if fidelity <= ceiling else ceiling
            inflow = self._period_inflow(pin.flows, idx)
            if idx == 1:
                growth = Decimal("0")
                flat = Decimal("0")
                yield_after = inflow
            else:
                growth = yield_base * effective
                flat = yield_base * (fidelity - ceiling) if fidelity > ceiling else Decimal("0")
                yield_after = yield_base + growth + inflow
            cumulative += yield_after + flat
            flat_total += flat
            roll_ups.append(RollUp(
                period=idx, inflow=inflow, yield_before=yield_base, fidelity=fidelity,
                ceiling=ceiling, effective_rate=effective, compounded_growth=growth,
                flat_accrual=flat, yield_after=yield_after, cumulative=cumulative))
            yield_base = yield_after
        return CompoundingRecord(model=MODEL_2_BOUNDED, roll_ups=tuple(roll_ups),
                                 cumulative=cumulative, flat_total=flat_total, completed=True)
