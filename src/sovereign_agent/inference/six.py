"""
SIX — the Sovereign Inference Exchange (co-extrusion of *Sovereign Inference & Memory* Ch 2).

Routes every inference request through a sensitivity-class lane (GREEN/YELLOW/RED), enforces the
structural rule that RED-class material NEVER routes externally, and produces a receipt for every routing
decision. The classification is a constitutional act; the enforcement is structural (in code), not operator
vigilance — exactly the "Structural Enforcement, Not Operator Vigilance" discipline Ch 2 teaches.

Book ↔ code anchor (Tech/Arch 17.6):
  Ch 2 "Three Canonical Sensitivity Classes"        → SensitivityClass + LANES
  Ch 2 "The Lane-to-Platform Mapping"               → route()
  Ch 2 "Structural Enforcement / RED barred"        → SIXExchange.route() raises on RED→external (default-deny K2)
  Ch 2 "The Classification Layer" (3 checks)        → classify()
  Ch 2 "Every routing decision produces a receipt"  → SIXExchange.run() → receipts.build_receipt
"""
from __future__ import annotations

from enum import Enum

from .receipts import build_receipt


class SensitivityClass(str, Enum):
    GREEN = "GREEN"    # routine observation — auto, no breath
    YELLOW = "YELLOW"  # proposal — operator breath at the gate
    RED = "RED"        # constitutional-surface material — local sovereign only, never external


# Lane → platform posture. RED's platform is structurally local; external is barred (Ch 2 table).
LANES = {
    SensitivityClass.GREEN: {"lane": "routine_inference_lane", "external_allowed": True},
    SensitivityClass.YELLOW: {"lane": "proposal_inference_lane", "external_allowed": True},
    SensitivityClass.RED: {"lane": "constitutional_inference_lane", "external_allowed": False},
}


class RedRoutingBarred(PermissionError):
    """Raised when RED-class material is asked to route to an external platform — the structural refusal
    is itself a constitutional act (Ch 2). INTEGRITY: a gated, loud failure, never a silent leak."""


def classify(*, has_sensitive_content: bool, touches_constitutional_surface: bool,
             role_authorized_class: str, charter_default: str = "YELLOW") -> SensitivityClass:
    """The classification layer (Ch 2's three checks): constitutional-surface → RED; sensitive content or a
    proposal → YELLOW; otherwise GREEN — bounded by the role's authorized ceiling and the Charter default
    (default-deny K2: ambiguous lands at the breath-gate, never auto)."""
    if touches_constitutional_surface:
        decided = SensitivityClass.RED
    elif has_sensitive_content:
        decided = SensitivityClass.YELLOW
    else:
        decided = SensitivityClass.GREEN
    # role ceiling: a role authorized only to YELLOW cannot request RED routing (Ch 2 check 2)
    order = {SensitivityClass.GREEN: 0, SensitivityClass.YELLOW: 1, SensitivityClass.RED: 2}
    ceiling = SensitivityClass(role_authorized_class) if role_authorized_class in SensitivityClass.__members__ else SensitivityClass.YELLOW
    if order[decided] > order[ceiling] and decided != SensitivityClass.RED:
        # never silently downgrade a RED; only cap non-RED escalations to the role ceiling
        decided = ceiling
    if decided == SensitivityClass.GREEN and charter_default == "YELLOW" and has_sensitive_content:
        decided = SensitivityClass.YELLOW
    return decided


def route(sensitivity_class: SensitivityClass, *, external: bool = False) -> dict:
    """Map a class to its lane; refuse RED→external structurally (Ch 2 'RED is structurally barred')."""
    lane = LANES[sensitivity_class]
    if external and not lane["external_allowed"]:
        raise RedRoutingBarred(
            f"{sensitivity_class.value}-class material refused external routing — "
            f"local sovereign infrastructure only. The refusal is the constitutional act."
        )
    return {"lane": lane["lane"], "platform": ("external" if external else "local_sovereign"),
            "sensitivity_class": sensitivity_class.value}


class SIXExchange:
    """The routing fabric: classify → route (with structural RED enforcement) → produce a receipt."""

    def __init__(self, *, operator_identity: str, charter_clause: str = "charter#six_lane_mapping"):
        self.operator_identity = operator_identity      # SOURCE: flows in, never hardcoded
        self.charter_clause = charter_clause
        self._prior = "genesis"

    def run(self, *, model_identity: str, input_content: str, output_content: str,
            has_sensitive_content: bool, touches_constitutional_surface: bool,
            role_authorized_class: str, role_spec: str, external_requested: bool = False) -> dict:
        cls = classify(has_sensitive_content=has_sensitive_content,
                       touches_constitutional_surface=touches_constitutional_surface,
                       role_authorized_class=role_authorized_class)
        routing = route(cls, external=external_requested)   # raises RedRoutingBarred on RED→external
        receipt = build_receipt(
            model_identity=model_identity, input_content=input_content, output_content=output_content,
            sensitivity_class=cls.value, routing_decision=routing, operator_identity=self.operator_identity,
            constitutional_reference={"role_spec": role_spec, "charter_clause": self.charter_clause},
            prior_hash=self._prior,
        )
        self._prior = receipt["chain_reference"]["receipt_hash"]
        return receipt
