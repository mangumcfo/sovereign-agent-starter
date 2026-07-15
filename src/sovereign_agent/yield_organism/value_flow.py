"""ValueFlowProjector — the S4 Yield Engine's value-flow projector (spec yield_organism_v0.1.yaml, slice 1.1).

A *value-flow* is a RECEIPT projected to a weighted economic value: the economic value a sealed obligation
attributes to a holder, scaled by an alignment-fidelity weight. The book's model, exactly:

  - yield "is not a number an engine asserts but an obligation the ledger records", weighted by "alignment —
    how faithfully the earning work strengthened the constitution" (Ch1).
  - a reward "attributes value to a holder ... It does NOT move money" (Ch2, the attribution-not-payment seam).
  - "no reward exists and no supply moves" until a named human approves it (Ch2) — so no value-flow projects
    from an unapproved/unsealed cylinder either.

This projector READS the obligation ledger + projection (both crypto-free, verified substrate) and COMPUTES.
It holds NO fund-moving path — money_path is OFF, absolutely (settlement stays on the operator's own regulated
rails). The crypto ring (signing the value-flow record, bl-verify of the economic bundle) is a typed SEAM
stubbed for the sealed host; it is ABSENT in this env and never faked here.

Scope is the projector only — the alignment scorer (which will COMPUTE the weight this projector takes as an
input), the compounding rings, and the drift brake are later slices per the Authoritative Pattern Rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

from ..obligations import projection as _proj
from ..obligations.ledger import ObligationLedger


class ValueFlowRefused(PermissionError):
    """Fail-closed refusal to project a value-flow — mirrors the ledger's PermissionError failure idiom.

    Raised when a cylinder has not cleared the breath-gate (AH-1), seals no economic value, or seals an
    invalid one. A refusal is loud and never a silent zero: the projector attributes value or it refuses.
    """


def _dec(value) -> Decimal:
    """Coerce to an exact Decimal (evidence law — no float drift in any surfaced number)."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"not a decimal: {value!r}") from exc


@dataclass(frozen=True)
class WeightBasis:
    """The alignment-fidelity weight applied to a base value, with its provenance.

    weight is bounded to [0, 1]: fidelity scales yield DOWN toward the drifting and never AMPLIFIES it — the
    book's "growth cannot outrun the alignment that earned it" (Ch8). For THIS slice the weight is SUPPLIED;
    the alignment scorer that computes and seals it is the next slice (the autonomy-ledgers ring).
    """
    weight: Decimal
    basis: str
    source: str

    @classmethod
    def supplied(cls, weight, basis: str = "alignment_fidelity") -> "WeightBasis":
        w = _dec(weight)
        if w < 0 or w > 1:
            raise ValueError(
                f"alignment weight {w} out of [0,1] — yield is bounded by fidelity, never amplified"
            )
        return cls(weight=w, basis=basis, source="supplied")

    @classmethod
    def from_posture(cls, posture) -> "WeightBasis":
        """The seam slice 1.2 fills: take the weight from an AlignmentScorer posture (autonomy-ledgers ring).

        Duck-typed on `.weight` (+ optional `.basis`) so value_flow carries NO import of the scorer (no
        cycle) and stays crypto-free. The posture's own bound is [0,1]; this re-checks it (a WeightBasis
        never trusts an unvalidated weight) and stamps provenance `alignment_scorer` — so the value-flow
        record's weight_source truthfully names where the weight came from.
        """
        w = _dec(getattr(posture, "weight"))
        if w < 0 or w > 1:
            raise ValueError(
                f"posture weight {w} out of [0,1] — yield is bounded by fidelity, never amplified"
            )
        basis = getattr(posture, "basis", "alignment_fidelity")
        return cls(weight=w, basis=basis, source="alignment_scorer")


@dataclass(frozen=True)
class ValueFlow:
    """A value-only projection of one sealed cylinder to a weighted economic value.

    Immutable and money_path-OFF by construction: it records who earned what, denominated in what, under
    which sealed cylinder — it moves nothing. `directional` marks a figure that must never be summed; a
    realized value-flow (projected from a sealed, approved cylinder) is directional=False and thus summable.
    """
    source_cylinder_id: str
    holder: Optional[str]
    base_value: Decimal
    weight: Decimal
    weighted_value: Decimal
    basis: str
    weight_source: str
    denomination: str
    material: bool
    receipt_id: Optional[str] = None
    money_path: str = "OFF"
    directional: bool = False

    @property
    def summable(self) -> bool:
        """DIRECTIONAL figures are never summed (evidence law). A realized attribution may be."""
        return not self.directional

    def to_dict(self) -> dict:
        """JSON-friendly, deterministic view — Decimals as exact strings (no float drift)."""
        return {
            "source_cylinder_id": self.source_cylinder_id,
            "holder": self.holder,
            "base_value": str(self.base_value),
            "weight": str(self.weight),
            "weighted_value": str(self.weighted_value),
            "basis": self.basis,
            "weight_source": self.weight_source,
            "denomination": self.denomination,
            "material": self.material,
            "receipt_id": self.receipt_id,
            "money_path": self.money_path,
            "directional": self.directional,
        }


class ValueFlowProjector:
    """Projects a sealed obligation/receipt from the ledger to a weighted economic value-flow.

    Reads the obligation ledger + projection (crypto-free); computes; moves nothing. There is deliberately
    NO transfer / settle / pay / disburse method on this class — the absence is the money_path-OFF invariant.
    """

    def __init__(self, ledger: ObligationLedger):
        self.ledger = ledger

    def project(self, obligation_id: str, weight_basis: WeightBasis) -> ValueFlow:
        """Project the sealed cylinder `obligation_id` to a weighted value-flow under `weight_basis`.

        Refuses (raises) rather than fabricating a flow when the cylinder is missing, unapproved/unsealed
        (AH-1 fail-closed), or seals no valid economic value. Never moves funds.
        """
        entries = list(self.ledger.iter_entries())
        debit = next(
            (e for e in entries if e.get("type") == "debit" and e.get("id") == obligation_id), None
        )
        if debit is None:
            # sealed_source_only: every value-flow references a REAL cylinder — never invent one.
            raise KeyError(f"obligation '{obligation_id}' does not exist — no cylinder to project")

        # material_rides_the_gate (AH-1 fail-closed): a value-flow projects only from a SEALED, approved
        # cylinder. is_approved is the AH-1-hardened check (material needs a real human gate; opener !=
        # approver). "no reward exists until a person wills it" (Ch2) — so no value-flow does either.
        if not _proj.is_approved(entries, obligation_id):
            raise ValueFlowRefused(
                f"'{obligation_id}' has not cleared the breath-gate (AH-1 fail-closed) — cannot project a "
                f"value-flow from an unapproved/unsealed cylinder"
            )

        base_value, denomination = self._read_attributed_value(debit, obligation_id)
        weighted_value = base_value * weight_basis.weight  # Decimal-exact

        return ValueFlow(
            source_cylinder_id=obligation_id,
            holder=debit.get("owner"),
            base_value=base_value,
            weight=weight_basis.weight,
            weighted_value=weighted_value,
            basis=weight_basis.basis,
            weight_source=weight_basis.source,
            denomination=denomination,
            material=bool(debit.get("material")),
            receipt_id=self._receipt_id_if_closed(entries, obligation_id),
            money_path="OFF",
            directional=False,
        )

    # ── SEALED-HOST-SEAM: crypto wiring routes through yield_organism/_sealed_host_seam.py (the node lane). ──
    # The crypto engine ring (sign_value_flow, verify_economic_bundle) is ABSENT in this env
    # (breathline_primitives ships as a sealed tarball, installed on the sealed host). The seam adapter's
    # stubs return explicit sentinels (SEALED_HOST_PENDING / UNVERIFIED) — NEVER a fake True. When the sealed
    # host wires the real primitives behind that one adapter, the signed/attested record rides on top of this
    # pure projection; the projection itself needs no crypto and stands alone.

    @staticmethod
    def _read_attributed_value(debit: dict, oid: str) -> tuple[Decimal, str]:
        """Read the economic value the sealed obligation attributes — from its lgp block, never invented.

        The reward/stake/distribution seals its attributed economic value WITH the obligation (lgp travels
        with it). A value-flow is a replay of that sealed value, not a dashboard assertion — so a cylinder
        with no economic_value is refused, loudly.
        """
        lgp = debit.get("lgp") or {}
        raw = lgp.get("economic_value")
        if raw is None:
            raise ValueFlowRefused(
                f"'{oid}' seals no economic_value in its lgp attribution block — nothing to project "
                f"(a value-flow is a sealed attribution, never a dashboard assertion)"
            )
        try:
            value = _dec(raw)
        except ValueError as exc:
            raise ValueFlowRefused(f"'{oid}' economic_value {raw!r} is not a number") from exc
        if value < 0:
            raise ValueFlowRefused(
                f"'{oid}' economic_value {value} is negative — a reward attributes value, not debt"
            )
        return value, str(lgp.get("denomination") or "units")

    @staticmethod
    def _receipt_id_if_closed(entries: list[dict], oid: str) -> Optional[str]:
        """The minted credit-receipt id when the cylinder is closed (else None) — extra sealed provenance."""
        for e in entries:
            if e.get("type") == "credit" and e.get("closes") == oid:
                return (e.get("receipt") or {}).get("receipt_id")
        return None
