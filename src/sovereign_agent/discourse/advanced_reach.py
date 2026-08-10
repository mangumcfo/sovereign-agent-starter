# -*- coding: utf-8 -*-
"""discourse.advanced_reach — Sovereign Discourse (Series 13, Vol 2:
Advanced Reach, Discovery & Platform Independence).

Basic platform independence — one owned home, a handful of adapters — takes a voice only so far. Deeper
independence means reaching audiences across many surfaces at once, discovering content across a federation of
the author's own sources, and bridging to platforms with sophisticated adapters that translate the artifact
without ever surrendering it — all while ownership and the audience stay the author's. This volume builds that,
and it does so by **composing** the sealed opener (Vol 1) and **inventing no new engine**: `discover_across_sources`
composes the opener's meaning ranking over a federation of the author's own sources; `multi_platform_reach`
composes the opener's syndication across many platforms at once; and `bridge_adapter` composes the opener's
syndication into a translating bridge whose deep transport homes OUT to Inter-Node Sovereignty (S6) and
Zero-Trust Sovereignty (S7).

**The S13 fence holds, broadened for reach:** discovery is meaning-ranked by the author's own rule, never an
attention-capture engine — and the fence now refuses any field carrying an attention-capture *root* (engagement,
virality, recommendation, outrage, addiction, watch-time, …), so a synthetic reach engine cannot evade it by
renaming. No second discourse or **reach** authority stands over the voice; the platform carries the artifact,
never the ownership; money-path OFF; weakest-party. KILL-TARGET: the reach-algorithm that owns your audience and
decides who sees you — refused. Weakest-party: an author reaches across many platforms and loses none of them at
once, because ownership and the audience are theirs on every surface. NO TOKEN · no yield · holds no value ·
money-path OFF · rolls no cryptography.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .sovereign_voice import (                                                          # S13 V1 (sealed opener)
    syndicate, meaning_rank, Syndication, DiscourseRefused, DISCOURSE_BREACH_FIELDS, ATTENTION_CAPTURE_ROOTS,
)

__all__ = ["discover_across_sources", "multi_platform_reach", "bridge_adapter", "PlatformBridge",
           "REACH_BREACH_FIELDS", "DiscourseRefused"]

# The reach layer inherits the whole broadened S13 fence and adds the reach-specific kill-target fields.
REACH_BREACH_FIELDS = DISCOURSE_BREACH_FIELDS | frozenset({
    "reach_authority", "audience_owner", "feed_authority", "distribution_authority", "amplification_engine",
})


def _rfence(mapping: Optional[Mapping[str, Any]], where: str) -> None:
    for k in (mapping or {}):
        kl = str(k).lower()
        if any(r in kl for r in ATTENTION_CAPTURE_ROOTS) or "amplification" in kl:
            raise DiscourseRefused(
                f"reach must carry no attention-capture / amplification engine field ('{k}') — reach is the "
                f"author's owned distribution across surfaces, meaning-ranked by the author's rule, never an "
                f"engine that amplifies for engagement (the reach-algorithm that owns your audience is refused)")
        if kl in REACH_BREACH_FIELDS:
            raise DiscourseRefused(
                f"reach must carry no reach/second-authority or ownership-transfer field ('{k}') — no reach "
                f"authority owns the audience; each platform carries the artifact, never the ownership")


# --- Advanced reach & discovery mechanics (Ch 2, resonance fold applied -> meaning) -------------------------

def discover_across_sources(sources: Sequence[Sequence[Mapping[str, Any]]], *, meaning_key: str,
                            extra: Optional[Mapping[str, Any]] = None) -> List[Mapping[str, Any]]:
    """Discover content across a **federation of the author's own sources** — merge the items from several owned
    sources and rank the whole set by the author's declared meaning (composes the sealed `meaning_rank`, Vol 1).
    It computes no engagement or amplification signal; the broadened fence refuses any attention-capture field in
    any item. Deny-by-default: an item missing the author's declared meaning is refused (by the composed
    meaning_rank). Advanced discovery is meaning across many owned sources, never an engagement engine across a
    platform's inventory."""
    _rfence(extra, "a federated discovery")
    merged: List[Mapping[str, Any]] = []
    for src in sources:
        merged.extend(src)
    return meaning_rank(merged, meaning_key=meaning_key, extra=extra)


# --- Multi-platform strategy without capture (Ch 3) --------------------------------------------------------

def multi_platform_reach(receipt: Mapping[str, Any], platforms: Sequence[str], content_ref: str, *,
                         extra: Optional[Mapping[str, Any]] = None) -> List[Syndication]:
    """Reach across **many platforms at once** without capture — syndicate a published voice to each of several
    platforms, ownership retained on every surface (composes the sealed `syndicate`, Vol 1, per platform). Deny-
    by-default: a reach needs at least one platform; an ownership-transfer / reach-authority / attention-capture
    field is refused. Because ownership stays the author's on every platform, losing one account never loses the
    voice — the reach is diversified and no single surface holds it hostage."""
    _rfence(extra, "a multi-platform reach")
    pls = [str(p) for p in platforms if str(p).strip()]
    if not pls:
        raise DiscourseRefused("a multi-platform reach needs at least one platform to carry the artifact")
    return [syndicate(receipt, p, content_ref) for p in dict.fromkeys(pls)]


# --- Sophisticated adapter & bridge patterns (Ch 4) --------------------------------------------------------

@dataclass(frozen=True)
class PlatformBridge:
    """A sophisticated adapter that bridges a voice to a platform: it **translates** the artifact into the
    platform's format and carries it, but ownership is always retained by the author. The deep transport and any
    cryptography home OUT to Inter-Node Sovereignty (S6) and Zero-Trust Sovereignty (S7); this bridge rolls none
    and holds nothing."""
    author: str
    platform: str
    content_ref: str
    fmt: str
    ownership_retained: bool = True


def bridge_adapter(receipt: Mapping[str, Any], platform: str, content_ref: str, *, fmt: str = "native",
                   extra: Optional[Mapping[str, Any]] = None) -> PlatformBridge:
    """Bridge a voice to a platform with a sophisticated adapter — it translates the artifact into the platform's
    `fmt` and carries it, composing the sealed `syndicate` (Vol 1) so ownership is retained; the deep transport
    homes OUT (Inter-Node Sovereignty, S6; Zero-Trust Sovereignty, S7). Deny-by-default: a bridge needs a
    platform and a format; an ownership-transfer / attention-capture field is refused. The bridge maximizes
    independence — it uses the platform fully while giving it nothing."""
    _rfence(extra, "a platform bridge")
    if not str(platform).strip() or not str(fmt).strip():
        raise DiscourseRefused("a platform bridge names the platform and the format it translates into")
    syn = syndicate(receipt, platform, content_ref)              # composes the sealed opener; ownership retained
    return PlatformBridge(author=syn.author, platform=str(platform), content_ref=str(content_ref), fmt=str(fmt),
                          ownership_retained=syn.ownership_retained)
