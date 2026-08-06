"""Node onboarding — a new node joins the federation by adopting its constitution and passing a human-gated admission.

Co-extrusion for s6_06 (Node Onboarding, KM S6 wave 2026-08-05). Pure / structural, no crypto substrate beyond the
sealed hashlib object model (F-1 import-clean AND bare-clone-clean). A new node does not join a federation by a central
trust service adding it to a list: it proposes to join by ADOPTING the federation's constitution as a governed object it
authors, and it is admitted only when a NAMED human approves. No central admission authority, no automatic enrolment: a
node becomes part of the federation by its own governed adoption of the shared constitution and a human's deliberate
assent.

Two governed acts:
  * `propose_onboarding` opens a joining node's adoption of the federation's constitution as a governed object --
    composing the sealed constitution templates (`open_constitution`, itself over the sealed object registry): the
    articles the node adopts become an authored, provenance-carrying governed object under the node's mandate, so the
    node's commitment to the federation's rules is on the record, not a verbal agreement. An empty node id or empty
    articles is refused.
  * `admit_node` admits a proposed node DENY-BY-DEFAULT, fail-closed, in order: the proposal must be a real governed
    constitution adoption (carrying a `version_hash`); node onboarding must be a HUMAN-GATED action class (composing the
    sealed `HumanApprovalGate` -- admitting a node to the federation is high-materiality); and a NAMED human must approve
    (an approver and a non-empty approval reference naming the admission). Only then is the node admitted, returning the
    admission carrying the adopted constitution's root. No central trust service admits a node -- a human does, over the
    node's own governed adoption.

Human primacy and the sovereignty boundary hold: the node's adoption is its own governed object, and admission is a
named human's deliberate assent. This module builds no membership registry, no central admission service, and no
enrolment engine of its own -- the adoption is the sealed constitution templates' governed object, and the admission is
the sealed compliance human-gate, composed."""
from __future__ import annotations

from typing import Dict, Mapping

from ..objects.registry import ObjectRegistry  # noqa: F401  (type reference for the composed registry)
from ..constitution.templates import open_constitution
from ..compliance.human_approval_gate import HumanApprovalGate


class OnboardingError(ValueError):
    """Raised when a node cannot be onboarded honestly: a proposal with no node id or no articles, or an admission of no
    real governed adoption, of an ungoverned class, or with no named human -- fail-closed, a node joins the federation
    only by its own governed adoption of the constitution and a named human's assent, never a central service's enrolment."""


def propose_onboarding(reg, node_id: str, articles: Mapping, *, mandate: str, author: str,
                       source_ref: str, at: str) -> Dict[str, object]:
    """Open a joining node's adoption of the federation's constitution as a governed object -- composing the sealed
    constitution templates (`open_constitution`). The `articles` the node adopts become an authored, provenance-carrying
    governed object under the node's own mandate, so the node's commitment to the federation's rules is on the record. An
    empty `node_id` or empty `articles` is refused. Returns the governed constitution-adoption object."""
    if not node_id:
        raise OnboardingError("an onboarding proposal needs a node id")
    if not articles:
        raise OnboardingError("an onboarding proposal needs the federation articles the node adopts")
    return open_constitution(reg, f"onboarding:{node_id}", dict(articles), mandate=mandate,
                             author=author, source_ref=source_ref, at=at)


def admit_node(proposal: Mapping, *, approver: str, approval_ref: str,
               gate: HumanApprovalGate = None) -> Dict[str, object]:
    """Admit a proposed node to the federation -- DENY-BY-DEFAULT, fail-closed, in order:

      1. the `proposal` must be a real governed constitution adoption -- carrying a `version_hash` (its integrity); an
         admission of nothing, or of an ungoverned proposal, is refused;
      2. node onboarding must be a HUMAN-GATED action class -- composing the sealed `HumanApprovalGate` (deny-by-default:
         admitting a node is high-materiality, so approval is required);
      3. a NAMED human must approve -- an `approver` and a non-empty `approval_ref` naming the admission; an admission
         with no named approver or no approval reference is refused.

    Only when the proposal is a real governed adoption AND the class is gated AND a human has approved is the node
    admitted, returning the admission carrying the adopted constitution's root. No central trust service admits a node --
    a named human does, over the node's own governed adoption of the constitution."""
    if not (proposal and proposal.get("version_hash")):
        raise OnboardingError("admission refused: no real governed constitution adoption to admit")
    gate = gate or HumanApprovalGate(policy={"high_materiality_classes": ["node_onboarding"]})
    if not gate.requires_approval(
        "node_onboarding",
        {"charter_v7_forbidden_classes": ["node_onboarding"]},
        "corporate_regulated",
    ):
        raise OnboardingError("admission refused: node onboarding must be a human-gated action class (deny-by-default)")
    if not str(approver).strip():
        raise OnboardingError("admission refused: a named human approver is required (no silent node admission)")
    if not str(approval_ref).strip():
        raise OnboardingError("admission refused: an approval reference naming the admission is required")
    return {"admitted": True, "node": proposal.get("object_id"),
            "constitution_root": proposal.get("version_hash"), "approver": approver, "approval_ref": approval_ref}
