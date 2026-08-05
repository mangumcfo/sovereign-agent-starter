"""Social & External Distribution (s5_30 / reading Vol 32) — governed content distribution with provenance.

When a family or an enterprise pushes content out to the world -- a post, a document, a public statement -- the usual
tools lose two things at once: the content's PROVENANCE (who authored it, from what source, unaltered) and the GOVERNANCE
(a human deciding, deliberately, to publish it externally). The legacy path is a copy-paste into a platform that owns the
distribution and keeps no verifiable record. This module refuses that. It makes an external distribution a governed act on
a provenance-carrying object, gated by a human.

It builds **one new act -- publishing content as a governed, provenance-carrying object and gating its external
distribution, fail-closed** -- by composing the sealed object registry and the sealed compliance human-gate, not by
building a content store or a channel engine of its own:

  * `publish_content` -- register content as a governed object under a mandate (composing the sealed object registry):
    its payload authored and provenance-checked, so the content carries a verifiable author and source from its first
    version; an empty id or empty payload is refused.
  * `govern_distribution` -- external distribution is **deny-by-default human-gated**: it proceeds ONLY IF the content is
    a real governed object (carrying its version identity and provenance) AND external distribution is a human-gated action
    class (composing the sealed `HumanApprovalGate`) AND a **named human** approves (an approver + a non-empty approval
    reference naming the act). The receipted distribution event carries the content's provenance forward.

No content store, no channel engine -- only the distribution governance over the sealed floors. The channels, audience
surfaces, and multi-channel propagation UI are the sovereign surface; scoped audience delivery composes the sealed
Federation floor; distribution exceptions compose the sealed Exception floor. Pure composition (the human-gate is stdlib
dataclass/enum; the object model is hashlib-based): runs green on a bare clone."""
from __future__ import annotations

from typing import Dict, Mapping

from ..compliance.human_approval_gate import HumanApprovalGate


class DistributionError(ValueError):
    """Raised when an external distribution cannot proceed honestly: content with no id or no payload, or a distribution
    with no real governed content / no named human approver / no approval reference. Fail-closed -- content is published
    externally as a provenance-carrying object through a human gate, or it is not published."""


def publish_content(reg, content_id: str, payload: Mapping, *, mandate: str, author: str,
                    source_ref: str, at: str) -> Dict[str, object]:
    """Register content as a governed object under a mandate -- composing the sealed object registry. Its `payload`
    becomes the object's authored, provenance-checked payload, registered under exactly one mandate, so the content
    carries a verifiable author and source (its `source_ref`) from its first version -- not an anonymous copy in a
    platform's store. An empty `content_id` or empty `payload` is refused."""
    if not content_id:
        raise DistributionError("content needs an id")
    if not payload:
        raise DistributionError("content needs a payload to publish")
    obj_id = f"content:{content_id}"
    return reg.append(obj_id, dict(payload), author=author, source_ref=source_ref, at=at,
                      mandate=mandate, kind="ratify")


def govern_distribution(content: Mapping, *, approver: str, approval_ref: str,
                        gate: HumanApprovalGate = None) -> Dict[str, object]:
    """Govern an external distribution -- FAIL-CLOSED, deny-by-default, on three conditions in order:

      1. the content must be a real GOVERNED OBJECT -- carrying a `version_hash` (its integrity identity); a distribution
         of nothing, or of un-governed content, is refused;
      2. external distribution must be a HUMAN-GATED action class -- composing the sealed `HumanApprovalGate`
         (deny-by-default: external distribution is high-materiality, so approval is required);
      3. a NAMED human must approve -- an `approver` and a non-empty `approval_ref` naming the act; a distribution with no
         named approver or no approval reference is refused.

    Only when the content is governed AND the class is gated AND a human has approved does the distribution proceed,
    returning a receipted event that carries the content's PROVENANCE forward (its version identity and source). The
    provenance is the object model's; the gating policy is the sealed compliance floor's; the human assent is the
    operator's; this adds only the fail-closed binding -- a provenance-carrying object AND a human, or no distribution."""
    if not (content and content.get("version_hash")):
        raise DistributionError(
            "distribution refused: no governed content to distribute -- content is a provenance-carrying object, not a raw payload"
        )
    gate = gate or HumanApprovalGate(policy={"high_materiality_classes": ["external_distribution"]})
    if not gate.requires_approval(
        "external_distribution",
        {"charter_v7_forbidden_classes": ["external_distribution"]},
        "corporate_regulated",
    ):
        raise DistributionError(
            "distribution refused: external distribution must be a human-gated action class (deny-by-default)"
        )
    if not str(approver).strip():
        raise DistributionError("distribution refused: a named human approver is required (no silent external distribution)")
    if not str(approval_ref).strip():
        raise DistributionError("distribution refused: an approval reference naming the act is required")
    return {
        "distributed": True,
        "content_root": content.get("version_hash"),
        "provenance": content.get("source_ref"),
        "approver": approver,
        "approval_ref": approval_ref,
    }
