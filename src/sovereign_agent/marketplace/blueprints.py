"""Federation Marketplace (s5_31 / reading Vol 33) — verified blueprints published and consumed under governance.

A federation of sovereign nodes accelerates when it can share what works -- proven patterns and blueprints -- without
losing control of what it adopts. The legacy marketplace is a platform that owns the listings, ranks them opaquely, and
lets anyone consume anything. This module refuses that. It makes a blueprint a governed, verified object, published and
consumed only through a human gate, so a node adopts a pattern deliberately and can verify what it received.

It builds **one new act -- publishing a verified blueprint as a governed object and gating its consumption, fail-closed**
-- by composing the sealed object registry and the sealed compliance human-gate, not by building a marketplace platform of
its own:

  * `publish_blueprint` -- register a blueprint as a governed object under a mandate (composing the sealed object
    registry): its pattern authored and provenance-checked, so a published blueprint carries a verifiable author and
    source -- a receipted publication, not an anonymous listing; an empty id or empty pattern is refused.
  * `govern_consumption` -- adopting a published blueprint is **deny-by-default human-gated**: it proceeds ONLY IF the
    blueprint exists as a governed object AND consuming a marketplace blueprint is a human-gated action class (composing
    the sealed `HumanApprovalGate`) AND a **named human** approves (an approver + a non-empty approval reference naming
    the act). A node adopts a pattern by a person's deliberate assent, never silently.

No marketplace platform, no reputation engine, no payment rail -- only the publish/consume governance over the sealed
floors. Forking and adapting a consumed blueprint composes the sealed federated-BOM primitive; reputation and quality
signals and monetization/licensing are homed at their sealed floors; the marketplace UI is the sovereign surface. Pure
composition (the human-gate is stdlib dataclass/enum; the object model is hashlib-based): runs green on a bare clone."""
from __future__ import annotations

from typing import Dict, Mapping

from ..compliance.human_approval_gate import HumanApprovalGate


class MarketplaceError(ValueError):
    """Raised when a marketplace act cannot proceed honestly: a blueprint with no id or no pattern, or a consumption of a
    blueprint that does not exist / with no named human approver / no approval reference. Fail-closed -- a blueprint is
    published and adopted as a governed object through a human gate, or it is not."""


def publish_blueprint(reg, blueprint_id: str, pattern: Mapping, *, mandate: str, author: str,
                     source_ref: str, at: str) -> Dict[str, object]:
    """Publish a blueprint as a governed object under a mandate -- composing the sealed object registry. Its `pattern`
    becomes the object's authored, provenance-checked payload, registered under exactly one mandate, so a published
    blueprint carries a verifiable author and source -- a receipted publication, not an anonymous marketplace listing.
    An empty `blueprint_id` or empty `pattern` is refused."""
    if not blueprint_id:
        raise MarketplaceError("a blueprint needs an id")
    if not pattern:
        raise MarketplaceError("a blueprint needs a pattern to publish")
    obj_id = f"blueprint:{blueprint_id}"
    return reg.append(obj_id, {"pattern": dict(pattern)}, author=author, source_ref=source_ref, at=at,
                      mandate=mandate, kind="ratify")


def govern_consumption(reg, blueprint_id: str, *, approver: str, approval_ref: str,
                       gate: HumanApprovalGate = None) -> Dict[str, object]:
    """Govern the consumption (adoption) of a published blueprint -- FAIL-CLOSED, deny-by-default, in order:

      1. the blueprint must EXIST as a governed object in the marketplace registry; consuming a blueprint that was never
         published is refused;
      2. consuming a marketplace blueprint must be a HUMAN-GATED action class -- composing the sealed `HumanApprovalGate`
         (deny-by-default: adopting an external pattern is high-materiality, so approval is required);
      3. a NAMED human must approve -- an `approver` and a non-empty `approval_ref` naming the act; a consumption with no
         named approver or no approval reference is refused.

    Only when the blueprint exists AND the class is gated AND a human has approved does the consumption proceed, returning
    a receipted result naming the blueprint and the exact version adopted. The registry and the version are the object
    model's; the gating policy is the sealed compliance floor's; the human assent is the operator's; this adds only the
    fail-closed binding -- a real published blueprint AND a human, or no adoption. (Forking and adapting the adopted
    blueprint composes the sealed federated-BOM primitive; it is not reimplemented here.)"""
    bp = reg.current().get(f"blueprint:{blueprint_id}")
    if bp is None:
        raise MarketplaceError(f"cannot consume {blueprint_id!r}: no such published blueprint")
    gate = gate or HumanApprovalGate(policy={"high_materiality_classes": ["blueprint_consumption"]})
    if not gate.requires_approval(
        "blueprint_consumption",
        {"charter_v7_forbidden_classes": ["blueprint_consumption"]},
        "corporate_regulated",
    ):
        raise MarketplaceError(
            "consumption refused: adopting a marketplace blueprint must be a human-gated action class (deny-by-default)"
        )
    if not str(approver).strip():
        raise MarketplaceError("consumption refused: a named human approver is required (no silent blueprint adoption)")
    if not str(approval_ref).strip():
        raise MarketplaceError("consumption refused: an approval reference naming the act is required")
    return {
        "consumed": True,
        "blueprint": blueprint_id,
        "version": bp.get("version_hash"),
        "approver": approver,
        "approval_ref": approval_ref,
    }
