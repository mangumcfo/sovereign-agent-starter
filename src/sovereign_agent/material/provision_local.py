# -*- coding: utf-8 -*-
"""material.provision_local — The Material Primitive (Series 9, Vol 1, the S9 opener).

`provision_local` provisions a **material good** as a receipted, mandate-scoped **governed object** — the
receipt/provenance harness (Series 3–5) extended from data to matter. It composes the sealed floors: the
**Object Model** (S5 Vol 5, `ObjectRegistry` — a hash-chained, mandate-scoped, provenance-checked version
record), the **receipts/provenance** rule (P5 — a source citation is never written false), the **mandate**
scope (S5 Vol 28 — one object belongs to exactly one mandate), and the **HumanApprovalGate** (S5 Vol 16 —
human primacy over a material act). It adds one thing: provisioning matter, locally, into a node's own
registry, verifiable by its receipt.

Kill-targets: **no central provisioner** (each node provisions into its OWN local registry, passed in —
there is no global registry or singleton) · **human primacy in physical systems** (a gated material
provision is REFUSED without a human approval) · **verify by receipt, not a registry** (`verify_provision`
re-derives the receipt from its own fields via the sealed `make_version` and confirms the good — a receiver
holding only the receipt checks it, no registry lookup, no second device) · **mandate-scoped** (a good
belongs to exactly one mandate; the registry refuses to move it) · **provenance never false** (the
`source_ref` must resolve; enforced by the composed Object Model) · **rolls no cryptography** (it composes
the sealed floor's hashing; it adds none). The good's economic value homes OUT to Sovereign Economy (S10),
the material estate to Generational Transfer (S12); energy/food+water/shelter/logistics/covenant home to
S9 Vols 2–6.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from ..objects.identity import object_id, make_version   # Object Model (S5 Vol 5) — composed by identity

__all__ = ["provision_local", "verify_provision", "ProvisionRefused", "ProvisionStatus", "PROVISION_KIND"]

PROVISION_KIND = "provision"

# The field set the Object Model's version_hash covers (make_version, S5 Vol 5). `mandate` is added by
# ObjectRegistry.append AFTER hashing, so it is intentionally excluded here — verify_provision re-derives
# the hash over exactly these fields via the sealed make_version, never a hand-rolled digest.
_RECEIPT_FIELDS = ("object_id", "seq", "kind", "at", "payload",
                   "author", "source_ref", "approver", "approval_ref", "prev_hash")


class ProvisionRefused(PermissionError):
    """A material provision that would bypass human primacy, or lacks a natural key, is refused."""


@dataclass(frozen=True)
class ProvisionStatus:
    """The weakest-party verdict for a provision receipt: a plain green light a receiver can read."""
    provisioned: bool
    reason: str


def provision_local(good: Mapping[str, Any], *, mandate: str, author: str, source_ref: str, at: str,
                    registry: Any, good_key: Optional[str] = None,
                    approver: Optional[str] = None, approval_ref: Optional[str] = None,
                    gate: Any = None, action_class: str = "provision_material",
                    role_spec: Optional[Mapping[str, Any]] = None, mode: str = "live") -> dict:
    """Provision a material good as a receipted, mandate-scoped governed object into the node's LOCAL
    registry, and return its receipt (the Object Model version).

    * **No central provisioner** — `registry` is this node's own `ObjectRegistry`; there is no global one.
    * **Human primacy** — if `gate` requires approval for `action_class` and no `approver`+`approval_ref`
      is supplied, the provision is REFUSED before anything is recorded.
    * **Receipted / mandate-scoped / provenance-checked** — composes `ObjectRegistry.append`, which
      hash-chains the version, binds it to exactly one `mandate` (S5 Vol 28), and refuses a false
      `source_ref` (P5). Rolls no cryptography of its own.
    """
    if gate is not None and gate.requires_approval(action_class, dict(role_spec or {}), mode):
        if not (approver and approval_ref):
            raise ProvisionRefused(
                "material provision requires a human approval (HumanApprovalGate, S5 Vol 16) before it is "
                "recorded — none supplied; human primacy holds over a physical act")
    key = good_key or (good.get("id") or good.get("name") if isinstance(good, Mapping) else None)
    if not key:
        raise ProvisionRefused("a material good needs a natural key (good_key, or good['id']/['name'])")
    obj_id = object_id("MaterialGood", str(key))
    # receipted + mandate-scoped + provenance-checked governed object, into the LOCAL node's registry
    receipt = registry.append(obj_id, dict(good), author=author, source_ref=source_ref, at=at,
                              mandate=mandate, kind=PROVISION_KIND,
                              approver=approver, approval_ref=approval_ref)
    return receipt


def verify_provision(receipt: Mapping[str, Any], good: Mapping[str, Any]) -> ProvisionStatus:
    """Verify a provisioned good **by its receipt, not a registry** — a weakest-party green light.

    A receiver holding only the receipt (the slip that came with the good) and the good itself confirms,
    with no registry lookup, no second device, and no expertise: the receipt is a provision receipt, it is
    mandate-scoped, the good matches it, and its hash re-derives (via the sealed `make_version`) — so any
    tamper to the good or the receipt flips the light. Returns a plain fresh/tampered verdict.
    """
    reasons = []
    if receipt.get("kind") != PROVISION_KIND:
        reasons.append("not a provision receipt")
    if not receipt.get("mandate"):
        reasons.append("receipt is not mandate-scoped")
    if dict(receipt.get("payload") or {}) != dict(good):
        reasons.append("the good does not match its receipt")
    # verify BY RECEIPT: re-derive the version_hash from the receipt's own fields via the sealed
    # make_version (Object Model, S5 Vol 5) — composes the floor's hashing, rolls none of its own.
    try:
        rebuilt = make_version(
            receipt["object_id"], receipt["seq"], dict(receipt["payload"]),
            author=receipt["author"], source_ref=receipt["source_ref"], at=receipt["at"],
            kind=receipt["kind"], approver=receipt.get("approver"),
            approval_ref=receipt.get("approval_ref"), prev_hash=receipt.get("prev_hash"))
        if rebuilt["version_hash"] != receipt.get("version_hash"):
            reasons.append("receipt hash does not verify — the receipt or good was altered")
    except Exception as e:  # a receipt that will not rebuild (missing field, false provenance) fails closed
        reasons.append(f"receipt does not rebuild: {e}")
    return ProvisionStatus(provisioned=not reasons, reason="; ".join(reasons) or "provisioned")
