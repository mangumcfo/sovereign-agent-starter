"""AlignmentScorer — the S4 Yield Engine's four-component alignment scorer (spec yield_organism_v0.1.yaml,
slice 1.2, autonomy-ledgers ring).

The sealed books name the model exactly (S2-V5 Ch3 "What the Autonomy Ledgers Score"; S4-V3 Ch1). For each
agentic action the Autonomy Ledgers produce a FOUR-component alignment score, each component in {-1, 0, +1}:

  1. In-scope?              +1 within operator-authorized scope · 0 marginal · -1 out-of-scope.
  2. Class-respected?       +1 respected the GREEN/YELLOW/RED taxonomy · -1 attempted to demote a class.
  3. Evidence-producing?    +1 sealed audit-chainable evidence · 0 marginal · -1 incomplete.
  4. Long-arc constitutional? +1 strengthening · -1 weakening · 0 neutral.

"The four components aggregate per-role, per-mandate, per-federation, per-period. The aggregate becomes the
role's running alignment posture" (S2-V5 Ch3). The book is explicit about the seam this slice sits on:
the EVIDENCE the score reads — sealed cylinders, the GREEN/YELLOW/RED class taxonomy — RUNS TODAY; the
SCORER that turns it into a compounding posture is the build. That build is this module.

What this scorer READS (never invents): the append-only obligation ledger — the same crypto-free, verified
substrate slice 1.1 reads. Each sealed cylinder (debit) + its approval/close/veto chain IS the evidence.
The GREEN/YELLOW/RED taxonomy is live on the cylinder as `classification` + `material` (arc_guardrail.py:
GREEN == {"C2","GREEN"} non-material; material == the RED/YELLOW gated class). The scorer reads via the
pure `obligations.projection` functions — it NEVER mutates the ledger.

Invariants (constitutional, non-negotiable):
  · reads evidence, never mutates it (pure projection reads only);
  · deterministic — same evidence set -> same posture (no timestamp/random read into the posture);
  · bounded output — the posture weight is clamped to [0, 1]; fidelity scales yield DOWN, never amplifies
    ("growth cannot outrun the alignment that earned it", S4-V3 Ch8);
  · conservative degrade / fail-safe — thin or missing evidence degrades the posture DOWN and is EXPLICIT
    about sufficiency; a non-positive or thin alignment never fabricates a positive weight;
  · money_path OFF — it scores, nothing more. There is no fund path here at all;
  · crypto-free — no breathline_primitives dependency (the crypto ring is the sealed-host seam, not needed
    to score; the scorer stands alone).

The posture plugs into slice 1.1's weight seam: `WeightBasis.from_posture(posture)` turns this posture into
the alignment-fidelity weight the ValueFlowProjector consumes (and, later, the compounding ceiling — slice
1.3, NOT built here).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from ..obligations import projection as _proj

# ── GREEN/YELLOW/RED taxonomy — read from the live cylinder, mirrors obligations/arc_guardrail.py. ──
# A non-material cylinder in this set is a GREEN (routine, Tier-1) class; `material=True` is the RED/YELLOW
# gated class. The scorer reads this taxonomy off the cylinder; it does not define a new one.
GREEN_CLASSIFICATIONS = frozenset({"C2", "GREEN"})

# ── Posture bounds + degrade policy (declared, so the ceiling/weight consumers can rely on them). ──
WEIGHT_MIN = Decimal("0")            # a non-positive alignment posture floors the weight at 0 (fail-safe).
WEIGHT_MAX = Decimal("1")            # fidelity NEVER amplifies beyond 1 (bounded — no unbounded multiplier).
SUFFICIENT_MIN = 3                   # fewer than this many scored cylinders => THIN evidence (degrade down).
THIN_CEILING = Decimal("0.5")        # thin evidence can NEVER exceed this weight (conservative cap).

# Sufficiency labels — the posture is EXPLICIT about how much evidence it stands on.
SUFFICIENT = "SUFFICIENT"
THIN = "THIN"
MISSING = "MISSING"

_COMPONENTS = ("in_scope", "class_respected", "evidence_producing", "long_arc_constitutional")


@dataclass(frozen=True)
class ComponentScore:
    """One cylinder's four-component score, each in {-1, 0, +1}, with the evidence read for each.

    Immutable and provenance-carrying: `reasons` records WHY each component scored as it did, so the posture
    is auditable (a replay, never a dashboard assertion). The scorer computes this from the ledger; it does
    not write it back.
    """
    cylinder_id: str
    in_scope: int
    class_respected: int
    evidence_producing: int
    long_arc_constitutional: int
    reasons: dict = field(default_factory=dict)

    @property
    def total(self) -> int:
        """Per-cylinder alignment in [-4, +4] — the sum of the four components."""
        return (self.in_scope + self.class_respected
                + self.evidence_producing + self.long_arc_constitutional)


@dataclass(frozen=True)
class AlignmentPosture:
    """A bounded alignment posture over an evidence set — what the compounding ceiling + value-flow weight
    consume.

    `weight` is the [0,1] alignment-fidelity weight (WeightBasis.from_posture reads it). `posture_raw` is the
    normalized mean four-component score in [-1,+1] BEFORE the fail-safe floor/thin-cap — surfaced so the
    consumer can see the raw alignment separately from the degrade policy applied to it. `sufficiency` and
    `degraded` make the evidence basis explicit; `components` is the per-component aggregate; `notes` records
    any conservative degrade that was applied.
    """
    weight: Decimal
    posture_raw: Decimal
    components: dict
    n_cylinders: int
    sufficiency: str
    degraded: bool
    basis: str = "alignment_fidelity"
    notes: tuple = ()

    def to_dict(self) -> dict:
        """Deterministic, JSON-friendly view — Decimals as exact strings (evidence law: no float drift)."""
        return {
            "weight": str(self.weight),
            "posture_raw": str(self.posture_raw),
            "components": dict(self.components),
            "n_cylinders": self.n_cylinders,
            "sufficiency": self.sufficiency,
            "degraded": self.degraded,
            "basis": self.basis,
            "notes": list(self.notes),
        }


class AlignmentScorer:
    """Computes the four-component alignment posture from the sealed obligation ledger.

    Reads the ledger (crypto-free, via pure projection); computes; mutates NOTHING. There is deliberately no
    settle/pay/transfer method and no ledger-write method on this class — the absence is the money_path-OFF +
    read-only invariants. The crypto ring is the sealed-host seam (_sealed_host_seam.py); scoring needs none
    of it and never calls it.
    """

    def __init__(self, ledger):
        # Duck-typed on the read API only (iter_entries) — the scorer never touches a write method.
        self.ledger = ledger

    # ── public API ────────────────────────────────────────────────────────────────
    def score(self, owner: Optional[str] = None,
              cylinder_ids: Optional[list] = None) -> AlignmentPosture:
        """Score the evidence set into a bounded alignment posture.

        `owner` scopes to one holder/role's cylinders (per-role posture); `cylinder_ids` scopes to an
        explicit set (per-mandate/period). With neither, scores every sealed cylinder on the ledger.
        Missing evidence yields the conservative MISSING posture (weight 0) — never fabricates alignment.
        """
        entries = list(self.ledger.iter_entries())          # read-only snapshot
        debits = [e for e in entries
                  if e.get("type") == "debit"
                  and (owner is None or e.get("owner") == owner)
                  and (cylinder_ids is None or e.get("id") in set(cylinder_ids))]

        per_cylinder = [self._score_cylinder(entries, d) for d in debits]
        return self._aggregate(per_cylinder)

    def score_cylinder(self, cylinder_id: str) -> ComponentScore:
        """Score a single named cylinder (raises KeyError if it is not on the ledger — never fabricates)."""
        entries = list(self.ledger.iter_entries())
        debit = next((e for e in entries
                      if e.get("type") == "debit" and e.get("id") == cylinder_id), None)
        if debit is None:
            raise KeyError(f"cylinder '{cylinder_id}' is not on the ledger — no evidence to score")
        return self._score_cylinder(entries, debit)

    # ── the four components — each reads a distinct LIVE evidence signal, each in {-1, 0, +1}. ──
    def _score_cylinder(self, entries: list, debit: dict) -> ComponentScore:
        oid = debit.get("id")
        approved = _proj.is_approved(entries, oid)
        denied = self._is_denied(entries, oid)
        closed = _proj.is_closed(entries, oid)
        material = bool(debit.get("material"))
        credit = self._credit(entries, oid)
        att = _proj.attestation_status(entries, oid, set(debit.get("requires_attestation") or []))
        reopened = self._was_reopened(entries, oid)
        reasons: dict = {}

        c1 = self._component_in_scope(approved, denied, debit, reasons)
        c2 = self._component_class_respected(entries, oid, material, denied, approved, reasons)
        c3 = self._component_evidence_producing(closed, credit, reasons)
        c4 = self._component_long_arc(approved, closed, credit, att, reopened, reasons)

        return ComponentScore(cylinder_id=oid, in_scope=c1, class_respected=c2,
                              evidence_producing=c3, long_arc_constitutional=c4, reasons=reasons)

    @staticmethod
    def _component_in_scope(approved: bool, denied: bool, debit: dict, reasons: dict) -> int:
        """In-scope? Reads the cylinder's scope-admission. A DENIED disposition is the operator/gate ruling
        the action out of authorized scope (-1). An APPROVED cylinder was affirmatively admitted into scope
        (+1). An undispositioned draft is not yet admitted (0, marginal).

        NOTE (conservative, honest): the full role+capability scope registry (S2-V3 §1) is a sealed-host
        input not present in this env, so the scorer does NOT assume +1 from mere existence — only an
        affirmatively-admitted (approved) cylinder scores +1; everything unconfirmed degrades toward 0.
        """
        if denied:
            reasons["in_scope"] = "denied disposition — ruled out of authorized scope"
            return -1
        if approved:
            reasons["in_scope"] = "approved — affirmatively admitted into operator-authorized scope"
            return 1
        reasons["in_scope"] = "undispositioned draft — not yet admitted (marginal; scope registry absent)"
        return 0

    @staticmethod
    def _component_class_respected(entries: list, oid: str, material: bool,
                                   denied: bool, approved: bool, reasons: dict) -> int:
        """Class-respected? Reads the GREEN/YELLOW/RED taxonomy discipline (material + real human gate,
        AH-1). A material (RED/YELLOW) cylinder self-approved WITHOUT a real human gate is a class-demotion
        attempt (-1) — the exact AH-1 bar. A material cylinder that rode a real gate (+1); a non-material
        GREEN action that correctly ran gate-free and was not denied (+1). Undispositioned => 0.
        """
        if material and AlignmentScorer._material_self_approved_without_gate(entries, oid):
            reasons["class_respected"] = "material self-approved without a real gate — class-demotion attempt (AH-1)"
            return -1
        if material:
            if approved:
                reasons["class_respected"] = "material rode the real human breath-gate — class respected"
                return 1
            reasons["class_respected"] = "material not yet gate-dispositioned — marginal"
            return 0
        # non-material GREEN
        if denied:
            reasons["class_respected"] = "GREEN action denied — treated as marginal on class discipline"
            return 0
        reasons["class_respected"] = "non-material GREEN ran gate-free within class — class respected"
        return 1

    @staticmethod
    def _component_evidence_producing(closed: bool, credit: Optional[dict], reasons: dict) -> int:
        """Evidence-producing? Reads the close credit's evidence_tier (E0/E1/E2). Closed with an
        artifact/verified tier (E1/E2) => +1; closed claim-only (E0) or still open (no evidence yet) =>
        0 marginal; closed but evidence missing/empty => -1 incomplete.
        """
        if not closed or credit is None:
            reasons["evidence_producing"] = "not sealed yet — no evidence produced (marginal)"
            return 0
        tier = credit.get("evidence_tier")
        evidence = credit.get("evidence")
        if not evidence:
            reasons["evidence_producing"] = "closed with missing/empty evidence — incomplete"
            return -1
        if tier in ("E1", "E2"):
            reasons["evidence_producing"] = f"sealed audit-chainable evidence (tier {tier})"
            return 1
        reasons["evidence_producing"] = f"closed claim-only (tier {tier or 'E0'}) — marginal"
        return 0

    @staticmethod
    def _component_long_arc(approved: bool, closed: bool, credit: Optional[dict],
                            att: dict, reopened: bool, reasons: dict) -> int:
        """Long-arc constitutional? Over the rolling window, did the action strengthen or weaken the
        surface. Reads the LIVE constitutional-health signals: a standing veto (att.vetoed) or a corrective
        reopen is a weakening/drift signal (-1); an approved+closed cylinder that sealed real evidence with
        no standing veto is strengthening (+1); otherwise neutral (0).

        NOTE (designed-toward): the federation-scale GAP_REGISTER drift-audit shard the book names for this
        component (S2-V5 Ch3/Ch4) is a sealed-host input not present here; when wired it feeds this component
        directly. Until then the scorer reads the per-cylinder constitutional-health signals that ARE live.
        """
        if att.get("vetoed"):
            reasons["long_arc_constitutional"] = "standing veto — weakening (drift signal)"
            return -1
        if reopened:
            reasons["long_arc_constitutional"] = "corrective reopen after close — weakening"
            return -1
        if approved and closed and credit is not None and credit.get("evidence") \
                and credit.get("evidence_tier") in ("E1", "E2"):
            reasons["long_arc_constitutional"] = "approved + evidenced + no veto — strengthening"
            return 1
        reasons["long_arc_constitutional"] = "in-flight / neutral — no long-arc signal yet"
        return 0

    # ── aggregation into the bounded, evidence-explicit posture ─────────────────────
    def _aggregate(self, scored: list) -> AlignmentPosture:
        n = len(scored)
        agg = {c: sum(getattr(s, c) for s in scored) for c in _COMPONENTS}

        if n == 0:
            # MISSING evidence: the conservative floor. Weight 0, and say so — never fabricate alignment.
            return AlignmentPosture(
                weight=WEIGHT_MIN, posture_raw=Decimal("0"), components=agg, n_cylinders=0,
                sufficiency=MISSING, degraded=True,
                notes=("no evidence on the ledger for this scope — posture floored to 0 (fail-safe)",))

        # posture_raw = normalized mean four-component score in [-1, +1].
        mean_total = Decimal(sum(s.total for s in scored)) / Decimal(n)   # [-4, +4], exact
        posture_raw = mean_total / Decimal(4)                            # [-1, +1]

        # Fail-safe floor: a non-positive alignment yields weight 0 (yield does not compound on drift).
        natural = posture_raw if posture_raw > 0 else Decimal("0")
        if natural > WEIGHT_MAX:            # defensive: bounded, never amplifies (cannot exceed 1)
            natural = WEIGHT_MAX

        notes: list = []
        degraded = False
        if posture_raw <= 0:
            degraded = True
            notes.append("non-positive alignment — weight floored to 0 (fail-safe; never compounds on drift)")

        # Conservative degrade on THIN evidence: a small sample can NEVER buy full weight (cap DOWN).
        sufficiency = SUFFICIENT if n >= SUFFICIENT_MIN else THIN
        weight = natural
        if sufficiency == THIN and weight > THIN_CEILING:
            weight = THIN_CEILING
            degraded = True
            notes.append(f"thin evidence (n={n} < {SUFFICIENT_MIN}) — weight capped down to {THIN_CEILING}")

        return AlignmentPosture(
            weight=weight, posture_raw=posture_raw, components=agg, n_cylinders=n,
            sufficiency=sufficiency, degraded=degraded, notes=tuple(notes))

    # ── read-only helpers over the chain (never mutate) ─────────────────────────────
    @staticmethod
    def _credit(entries: list, oid: str) -> Optional[dict]:
        # The LAST close credit for the cylinder (order-aware; a later re-close governs).
        found = None
        for e in entries:
            if e.get("type") == "credit" and e.get("closes") == oid:
                found = e
        return found

    @staticmethod
    def _is_denied(entries: list, oid: str) -> bool:
        """A standing denial: the last approval disposition for the cylinder is 'denied'."""
        state = None
        for e in entries:
            if e.get("type") == "approval" and e.get("approves") == oid:
                state = e.get("disposition", "approved")
        return state == "denied"

    @staticmethod
    def _was_reopened(entries: list, oid: str) -> bool:
        """True when the cylinder currently reads reopened-after-close (order-aware; a corrective reopen
        that is the last close/reopen event => a weakening signal for long-arc)."""
        state = None
        for e in entries:
            if e.get("type") == "credit" and e.get("closes") == oid:
                state = "closed"
            elif e.get("type") == "reopen" and e.get("reopens") == oid:
                state = "reopened"
        return state == "reopened"

    @staticmethod
    def _material_self_approved_without_gate(entries: list, oid: str) -> bool:
        """A material cylinder whose approval entry is a self-approval (approved_by == owner) with no real
        human gate — the AH-1 class-demotion the ledger bars. Read-only mirror of projection.is_approved's
        material branch, surfaced as a class-discipline signal for component 2.
        """
        debit = next((e for e in entries
                      if e.get("type") == "debit" and e.get("id") == oid), None)
        owner = debit.get("owner") if debit else None
        for e in entries:
            if e.get("type") != "approval" or e.get("approves") != oid:
                continue
            if e.get("disposition", "approved") != "approved":
                continue
            if owner is not None and e.get("approved_by") == owner:
                gate = e.get("gate")
                if not (isinstance(gate, dict) and gate.get("real")):
                    return True   # self-approved material without a real gate — class demotion
        return False
