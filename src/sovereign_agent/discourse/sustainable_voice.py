# -*- coding: utf-8 -*-
"""discourse.sustainable_voice — Sovereign Discourse (Series 13, Vol 4:
Sustainable Voice & Long-Term Strategy).

A voice that exhausts its author or depends on a platform's favor is not sustainable — it is a treadmill or a
lease. This volume builds a voice that is sustainable and compounding: a low-maintenance system of owned content
and receipted audience, responsible growth that never costs the author control or human primacy, and a voice
treated as a compounding, inheritable long-term asset. It does so by **composing** the sealed Sovereign Discourse
volumes (V1 owned voice · V2 reach · V3 governance) and **inventing no new engine**: `assemble_voice_system`
composes the sealed voice verification (V1) over an author's whole body of owned voice and audience;
`responsible_growth` composes the sealed multi-platform reach (V2) **and** the sealed human gate (V3), so growth
of reach passes a human hand; and `voice_as_asset` composes the sealed reputation of verified voice (V3) into a
long-term, inheritable asset whose value is the author's own verified voice — the deep generational conveyance
homing OUT to Generational Transfer (S12), with Generational Continuity (S5 Vol 29) the continuity floor.

**The S13 fence, broadened and compound-hardened:** human primacy on expression · no second discourse authority
· **no attention-capture engine** — refused not only by root but by *compound* shape, so a `feed_optimizer`,
`feed_ranker`, `growth_engine`, or `vanity_maximizer` (a carrier root + an optimize root) is refused under any
token · money-path OFF · weakest-party. KILL-TARGET: the platform that makes your voice "sustainable" only by
owning your audience and renting your reach back to you as you grow — refused. Weakest-party (loud): a creator
with no team verifies that their voice, audience, and asset endure and stay theirs from the receipts they hold.
NO TOKEN · no yield · holds no value · money-path OFF · rolls no cryptography.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .sovereign_voice import (                                                          # S13 V1 (sealed opener)
    verify_voice, DiscourseRefused, DISCOURSE_BREACH_FIELDS, _is_attention_capture as _is_attn,
)
from .advanced_reach import multi_platform_reach                                        # S13 V2 (sealed)
from .voice_governance import reputation_from_receipts, govern_expression, ReputationStanding  # S13 V3 (sealed)

__all__ = ["assemble_voice_system", "VoiceSystem", "responsible_growth", "voice_as_asset", "VoiceAsset",
           "SUSTAINABLE_BREACH_FIELDS", "DiscourseRefused"]

# The sustainable layer inherits the whole broadened + compound S13 fence, adding the long-term kill-target fields.
SUSTAINABLE_BREACH_FIELDS = DISCOURSE_BREACH_FIELDS | frozenset({
    "growth_engine", "vanity_metric", "reach_rental", "audience_lease", "sustainability_authority",
})


def _sfence(mapping: Optional[Mapping[str, Any]], where: str) -> None:
    for k in (mapping or {}):
        kl = str(k).lower()
        if _is_attn(kl):
            raise DiscourseRefused(
                f"a sustainable-voice act must carry no attention-capture / growth engine field ('{k}') — a "
                f"voice is made sustainable by compounding owned records, never a feed/growth optimizer (the "
                f"compound fence refuses a carrier root + an optimize root under any token)")
        if kl in SUSTAINABLE_BREACH_FIELDS or "rental" in kl or "lease" in kl:
            raise DiscourseRefused(
                f"a sustainable-voice act must carry no reach-rental / audience-lease / second-authority field "
                f"('{k}') — the platform makes your voice sustainable only by owning your audience and renting "
                f"your reach back; that is refused, the voice is the author's own")


# --- Designing sustainable content & audience systems (Ch 2) -----------------------------------------------

@dataclass(frozen=True)
class VoiceSystem:
    """A sustainable voice system: the author's whole body of owned voice and receipted audience, verified as
    theirs and self-contained. `self_sustaining` is true iff every record verifies as the author's own — a
    system that depends on no platform's favor and no engine, low-maintenance because it is owned records that
    compound rather than a treadmill of feeding an algorithm."""
    author: str
    verified: int
    total: int
    self_sustaining: bool
    reason: str = ""


def assemble_voice_system(author: str, records: Sequence[Mapping[str, Any]], *,
                          extra: Optional[Mapping[str, Any]] = None) -> VoiceSystem:
    """Assemble a sustainable voice system from the author's whole body of owned voice — verify each record is
    the author's own and intact (composes the sealed `verify_voice`, V1). `self_sustaining` is true only when
    every record verifies, because a system that depends on unverifiable or foreign content is not the author's
    to sustain. Deny-by-default: an empty body is not a system; an attention-capture / reach-rental field is
    refused. Low-maintenance and compounding because it is owned records, not a fed algorithm."""
    _sfence(extra, "a voice system")
    total = 0
    verified = 0
    for rec in records:
        _sfence(rec, "a system record")
        total += 1
        if verify_voice(rec["receipt"], author, rec["work_ref"], content_ref=rec["content_ref"]):
            verified += 1
    ok = total > 0 and verified == total
    reason = ("every part of the voice is verified as the author's own — a self-sustaining, compounding system"
              if ok else f"{verified}/{total} parts verify as the author's own" if total
              else "an empty body of voice is not a sustainable system")
    return VoiceSystem(author=author, verified=verified, total=total, self_sustaining=ok, reason=reason)


# --- Responsible growth while maintaining sovereignty (Ch 3, "scaling" fold -> growth) --------------------

def responsible_growth(receipt: Mapping[str, Any], platforms: Sequence[str], content_ref: str,
                       constitution: Any, growth_class: str, author: str, work_ref: str, *, gate: Any, at: str,
                       author_name: str, source_ref: str, registry: Any, approver: Optional[str] = None,
                       approval_ref: Optional[str] = None, extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Grow a voice's reach responsibly — **without losing control or human primacy.** A growth decision passes
    the author's content constitution and the sealed human gate (composes `govern_expression`, V3), and only
    then does the reach extend across platforms with ownership retained on every one (composes
    `multi_platform_reach`, V2). Deny-by-default: a gated growth decision is refused without a named human; an
    attention-capture / growth-engine field is refused (the compound fence). Returns the governed growth
    receipt; the reach it authorizes is diversified and owned. Growth is a human-gated act, never an engine's."""
    _sfence(extra, "a growth decision")
    ex = dict(extra or {}); ex["responsible_growth"] = True; ex["platforms"] = len([p for p in platforms])
    decision = govern_expression(constitution, str(growth_class), author, work_ref, gate=gate, at=at,
                                 author_name=author_name, source_ref=source_ref, registry=registry,
                                 approver=approver, approval_ref=approval_ref, extra=ex)
    # only after the human-gated decision does the reach extend (composes V2; ownership retained on every surface)
    multi_platform_reach(receipt, platforms, content_ref)
    return decision


# --- Voice as a long-term, inheritable asset (Ch 4) ------------------------------------------------------

@dataclass(frozen=True)
class VoiceAsset:
    """The voice as a compounding, inheritable long-term asset: its value is the author's own **verified voice**
    (composed from the sealed reputation of verified receipts), and it is inheritable through the sealed
    generational transfer. `endures` is the weakest-party indicator a creator reads: their voice, audience, and
    asset are verified as theirs and will pass to their heirs. It holds no monetary value; the asset is verified
    records, not a platform's number."""
    author: str
    value: int
    inheritable: bool
    endures: bool
    reason: str = ""


def voice_as_asset(author: str, records: Sequence[Mapping[str, Any]], *,
                   extra: Optional[Mapping[str, Any]] = None) -> VoiceAsset:
    """Treat the author's voice, content library, and audience as a **compounding, inheritable long-term asset**
    — its value is the count of the author's own verified voice (composes the sealed `reputation_from_receipts`,
    V3), and it is inheritable through Generational Transfer (S12), with Generational Continuity (S5 Vol 29) the
    continuity floor. Weakest-party (loud): a creator with no team reads one honest indicator — `endures` — that
    their voice asset is verified as theirs and will pass to their heirs, from the receipts they hold. Deny-by-
    default: an empty body is no asset; a vanity-metric / attention-capture field is refused. Holds no monetary
    value; the asset is verified records, not a platform score."""
    _sfence(extra, "a voice asset")
    standing: ReputationStanding = reputation_from_receipts(author, records)
    endures = standing.intact                                  # every recorded part verifies as the author's own
    return VoiceAsset(author=author, value=standing.standing, inheritable=endures, endures=endures,
                      reason=("this voice endures and is mine to hand on — a verified, inheritable asset" if endures
                              else standing.reason))
