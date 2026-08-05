"""Situational Supply (s5_38 / reading Vol 40) — pooled demand as formation capital, gated by a human.

When normal supply fails -- nonexistent, disrupted, priced-out, or blocked -- the pool acts: collective demand is
aggregated into formation capital, and the decision to commit that capital (a venture, an acquisition, a production
run) is **DENY-BY-DEFAULT human-gated**. Human primacy on capital is the invariant: the pool may prove the demand is
real, but no capital is committed without a named person's assent.

It builds **one new act -- gating situational formation on a cleared pool AND a named human** -- by composing the
sealed compliance human-approval gate and recording the pooled aggregate, not by building a marketplace, a ventures
engine, or a confidentiality shield of its own:

  * `pool_demand` -- aggregate member commitments into a pooled order book and prove it clears a stated minimum:
    formation capital is real only if the pool clears. Returns the aggregate total and the clearance signal. The
    per-member **ZK-shielded** form (proving the pool clears without exposing any member's budget) homes at the
    **Zero-Trust Sovereignty series (S7)** -- it is not built here; this records the aggregate in the clear.
  * `gate_formation` -- **fail-closed**: capital formation proceeds ONLY IF (1) the pool clears its minimum, (2)
    capital commitment is a human-gated action class (composing the sealed `HumanApprovalGate` -- deny-by-default),
    and (3) a **named human** approves it (an approver + a non-empty approval reference naming the act). An uncleared
    pool, or a formation with no named human, is refused.

No marketplace, no ventures engine, no confidentiality shield -- only the situational-formation governance over the
sealed floors. Pure composition (the human-approval gate is stdlib dataclass/enum): runs green on a bare clone."""
from __future__ import annotations

from typing import Dict, Mapping, Sequence

from ..compliance.human_approval_gate import HumanApprovalGate


class SituationalError(ValueError):
    """Raised when situational formation cannot proceed honestly: a pool that does not clear its minimum, or a capital
    commitment with no named human approver / no approval reference. Fail-closed -- the pool acts only on proven demand
    through a human gate, or it does not act. Human primacy on capital is never waived."""


def pool_demand(commitments: Sequence[Mapping], *, minimum: float) -> Dict[str, object]:
    """Aggregate member demand commitments into a pooled order book and prove it clears a stated minimum. Each
    commitment names a member and an amount; the pool records the aggregate total and whether it clears the minimum
    that makes formation viable. Formation capital is real only if the pool clears -- an uncleared pool is honest
    about not yet being a market. The per-member **ZK-shielded** form (clearance proven without exposing any member's
    budget) homes at the Zero-Trust Sovereignty series (S7); this function records the aggregate in the clear."""
    if not commitments:
        raise SituationalError("a pool needs at least one demand commitment")
    if minimum is None or float(minimum) < 0:
        raise SituationalError("a pool needs a non-negative minimum to clear")
    total = 0.0
    members = []
    for c in commitments:
        if "amount" not in c:
            raise SituationalError("each commitment must name an amount")
        total += float(c["amount"])
        members.append(c.get("member"))
    return {
        "total": total,
        "minimum": float(minimum),
        "clears": total >= float(minimum),
        "count": len(list(commitments)),
        "members": members,
    }


def gate_formation(pool: Mapping, *, approver: str, approval_ref: str,
                   gate: HumanApprovalGate = None) -> Dict[str, object]:
    """Gate a situational capital formation -- FAIL-CLOSED on three conditions, in order:

      1. the pool must CLEAR its minimum -- an uncleared pool is not formation capital; the formation is refused;
      2. capital commitment must be a HUMAN-GATED action class -- composing the sealed `HumanApprovalGate`
         (deny-by-default: capital commitment is high-materiality, so approval is required);
      3. a NAMED human must approve -- an `approver` and a non-empty `approval_ref` naming the act (a pool vote, a
         board minute); a formation with no named approver or no approval reference is refused.

    Only when the pool clears AND capital commitment is a gated class AND a human has approved does the formation
    proceed, returning a receipted result. The clearance is the pool's, the gating policy is the sealed compliance
    floor's, the human assent is the operator's; this adds only the fail-closed binding -- proven demand AND a human,
    or no capital is committed."""
    if not pool.get("clears"):
        raise SituationalError(
            "formation refused: the pool does not clear its minimum "
            f"(total {pool.get('total')!r} < minimum {pool.get('minimum')!r}) -- formation capital is not yet real"
        )
    gate = gate or HumanApprovalGate(policy={"high_materiality_classes": ["capital_commitment"]})
    if not gate.requires_approval(
        "capital_commitment",
        {"charter_v7_forbidden_classes": ["capital_commitment"]},
        "corporate_regulated",
    ):
        raise SituationalError(
            "formation refused: capital commitment must be a human-gated action class (deny-by-default)"
        )
    if not str(approver).strip():
        raise SituationalError("formation refused: a named human approver is required (no silent capital commitment)")
    if not str(approval_ref).strip():
        raise SituationalError("formation refused: an approval reference naming the act is required")
    return {
        "formed": True,
        "total": pool.get("total"),
        "cleared": True,
        "approver": approver,
        "approval_ref": approval_ref,
    }
