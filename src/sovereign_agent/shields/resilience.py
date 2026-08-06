"""Resilience & Recovery Shields — a node survives failure and recovers authority by COMPOSITION of sealed
floors, never a new recovery engine, a standing escrow, or a central trust service.

Co-extrusion for s7_06 (Resilience & Recovery Shields, KM S7 Vol 6, MUST-SOLO capstone of Zero-Trust
Sovereignty). A sovereign node must be able to lose an operator surface (a phone, a laptop) and recover
its authority WITHOUT handing a copy of its root to a custodian who could be compromised or coerced.
This module builds that as a composition: the recovery POLICY is a governed constitution (composing the
sealed `open_constitution`, Constitutions S5 Vol 30, over the sealed Object Model S5 Vol 5); a governed
SNAPSHOT of a resource carries a sealed-P5 Merkle integrity root (Object Model + the sealed P5 Merkle via
`_lazy_bp`); and RECOVERY of authority is a human-gated M-of-N ceremony (composing the sealed
`HumanApprovalGate`, Compliance & Audit S5 Vol 16) whose succession follows the sealed Generational
Continuity handoff discipline (S5 Vol 29) — deny-by-default, fail-closed.

Three governed acts:
  * `declare_recovery_plan` — declare the recovery constitution for a resource: the NAMED guardians who
    may authorize recovery and the M-of-N `threshold` (composing `open_constitution`). The plan holds NO
    keys and NO escrow — only the governed policy of WHO may authorize recovery and how many must assent.
  * `snapshot_resource` — take a governed, integrity-proven snapshot of a resource as the owner's own
    governed object carrying a Merkle root over its state (composing the sealed object registry + the
    sealed P5 `MerkleTree`). No central backup store; the snapshot is verifiable from its own bytes.
  * `recover_authority` — the key-recovery CEREMONY: restore authority over a resource ONLY when the
    declared `threshold` of NAMED guardians give a human-gated assent (each an approver + an approval
    reference, the sealed human-gate convention), ratified as a governed succession. A `dry_run` verifies
    the ceremony WOULD succeed without ratifying anything — it never touches the live root. Fewer than
    the threshold, an unnamed guardian, or an assent with no reference is refused.

No second recovery authority, no standing escrow, no central trust service: the root stays on the owner's
own iron; the recovery plan is the owner's own governed constitution; the ceremony is the named guardians'
own human assent. This module composes the sealed floors and adds only the deny-by-default binding."""
from __future__ import annotations

from typing import Dict, List, Mapping, Sequence

from ..objects.registry import ObjectRegistry  # noqa: F401  (type reference for the composed registry)
from ..constitution.templates import open_constitution  # Constitutions (S5 Vol 30), over the sealed Object Model
from ..compliance.human_approval_gate import HumanApprovalGate  # Compliance & Audit (S5 Vol 16)
from .._lazy_bp import MerkleTree  # sealed P5 integrity substrate via the runtime boundary (fail-loud)


class ResilienceError(ValueError):
    """Raised when a resilience shield cannot be declared or a recovery cannot proceed honestly: an empty
    resource or guardian set, an out-of-range threshold, an empty snapshot, a recovery of no real plan,
    fewer than the threshold of named guardians, or a guardian assent with no approval reference —
    fail-closed, recovery is a human-gated M-of-N ceremony over a governed plan, never an escrow's key."""


def _merkle_root(chunks: Sequence[bytes]) -> str:
    return MerkleTree([bytes(c) for c in chunks]).get_root().hex()


def declare_recovery_plan(reg, resource_id: str, guardians: Sequence[str], *, threshold: int, mandate: str,
                          author: str, source_ref: str, at: str) -> Dict[str, object]:
    """Declare the recovery constitution for a resource — composing the sealed `open_constitution`
    (Constitutions S5 Vol 30, over the sealed Object Model S5 Vol 5). The `guardians` are the NAMED
    principals who may authorize recovery, and `threshold` is how many of them must assent (M-of-N). The
    plan is a governed constitution under the owner's OWN mandate that holds NO keys and NO escrow — only
    the policy of who may authorize recovery and how many. An empty resource or guardian set, or a
    threshold below 1 or above the number of guardians, is refused."""
    if not resource_id:
        raise ResilienceError("a recovery plan needs the resource it governs")
    gs = [g for g in guardians if str(g).strip()]
    if not gs:
        raise ResilienceError("a recovery plan needs at least one named guardian (no anonymous recovery)")
    if threshold < 1 or threshold > len(gs):
        raise ResilienceError(f"threshold must be between 1 and the guardian count ({len(gs)}), not {threshold}")
    articles = {"resource": resource_id, "guardians": list(gs), "threshold": int(threshold),
                "holds_keys": False, "escrow": False}
    return open_constitution(reg, f"recovery:{resource_id}", articles, mandate=mandate,
                             author=author, source_ref=source_ref, at=at)


def snapshot_resource(reg, resource_id: str, chunks: Sequence[bytes], *, mandate: str, author: str,
                      source_ref: str, at: str) -> Dict[str, object]:
    """Take a governed, integrity-proven snapshot of a resource — a governed object under the owner's OWN
    mandate (composing the sealed object registry `reg.append` kind=ratify) carrying a Merkle root over the
    resource's canonical state `chunks` (composing the sealed P5 `MerkleTree`, via `_lazy_bp`), so the
    snapshot's integrity is provable from its own bytes and no central backup store vouches for it. An
    empty resource or empty state is refused."""
    if not resource_id:
        raise ResilienceError("a snapshot needs the resource it captures")
    if not chunks:
        raise ResilienceError("a snapshot needs resource state to capture (no empty snapshot)")
    root = _merkle_root(chunks)
    payload = {"resource": resource_id, "root": root, "kind": "snapshot"}
    return reg.append(f"snapshot:{resource_id}:{root[:12]}", payload, author=author,
                      source_ref=source_ref, at=at, mandate=mandate, kind="ratify")


def recover_authority(reg, plan: Mapping, approvals: Sequence[Mapping], *, mandate: str, author: str,
                      source_ref: str, at: str, dry_run: bool = False) -> Dict[str, object]:
    """The key-recovery CEREMONY — restore authority over a resource, DENY-BY-DEFAULT, fail-closed:

      1. the `plan` must be a real governed recovery constitution (a `version_hash` + object id carrying
         `guardians` and `threshold`); a recovery of no real plan is refused;
      2. each assent in `approvals` must name a guardian IN the plan AND carry an `approval_ref` (the
         sealed human-gate convention — composing `HumanApprovalGate`, S5 Vol 16); an unnamed guardian or
         an assent with no reference does not count;
      3. the count of DISTINCT valid named-guardian assents must reach the plan's `threshold` (M-of-N).

    On a met threshold: if `dry_run`, return that the ceremony WOULD recover WITHOUT ratifying anything —
    it never touches the live root. Otherwise ratify the recovery as a governed succession (composing the
    object registry, the sealed Generational Continuity handoff discipline, S5 Vol 29). Fewer than the
    threshold, an unnamed guardian, or an assent with no reference is refused. No second recovery
    authority, no standing escrow — the recovery is the owner's own governed plan and the guardians' own
    human assent."""
    articles = dict((plan.get("payload") or {}))
    guardians = set(str(g) for g in (articles.get("guardians") or []))
    threshold = int(articles.get("threshold") or 0)
    if not (plan and plan.get("version_hash") and plan.get("object_id") and guardians and threshold):
        raise ResilienceError("recovery refused: no real governed recovery plan to recover under")
    # a recovery is a high-materiality, human-gated action-class (compose the sealed HumanApprovalGate)
    gate = HumanApprovalGate({"high_materiality_classes": ["key_recovery"]})
    if not gate.requires_approval("key_recovery", {"charter_v7_forbidden_classes": []}, "corporate_regulated"):
        raise ResilienceError("recovery refused: the key-recovery action-class is not gated for human approval")
    assented = set()
    for a in approvals:
        approver = str((a or {}).get("approver", "")).strip()
        approval_ref = str((a or {}).get("approval_ref", "")).strip()
        if approver in guardians and approval_ref:  # named guardian AND a reference naming the assent
            assented.add(approver)
    if len(assented) < threshold:
        raise ResilienceError(
            f"recovery refused: {len(assented)} of the required {threshold} named guardians assented "
            "(a human-gated M-of-N ceremony, never an escrow's key)")
    if dry_run:
        return {"would_recover": True, "resource": articles.get("resource"), "assented": sorted(assented),
                "threshold": threshold, "ratified": False}
    grant = reg.append(f"recovery:{articles.get('resource')}:{plan['object_id']}",
                       {"resource": articles.get("resource"), "recovered_by": sorted(assented),
                        "threshold": threshold, "kind": "recovery-succession"},
                       author=author, source_ref=source_ref, at=at, mandate=mandate, kind="ratify")
    return {"recovered": True, "resource": articles.get("resource"), "assented": sorted(assented),
            "threshold": threshold, "succession": grant.get("object_id"), "ratified": True}
