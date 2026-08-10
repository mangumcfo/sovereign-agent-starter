# -*- coding: utf-8 -*-
"""discourse.sovereign_voice — Sovereign Discourse (Series 13, Vol 1, the OPENER:
Owning Your Voice, Audience & Attention).

A platform that can deplatform you never gave you a voice — it rented you one, and it can end the lease. This
opener builds a voice you own: your ideas published as signed, content-addressed governed objects from your own
node, distributed to platforms that carry the artifact but never the ownership, an audience of direct receipted
relationships platforms cannot sever, and discovery ranked by meaning you declare rather than an engagement
engine that optimizes for outrage. It does so by **composing** the sealed floors below it and **inventing no new
engine**: content is a governed object (Object Model, S5 Vol 5) recorded and verified through the sealed
governed-record surface (S10 Vol 1); high-impact expression passes the sealed breath-gate (Interface
Sovereignty, S8 Vol 2); the read surface is the sealed Lens (S8 Vol 1); the sealed discourse home is the UX
Covenant (S8 Vol 8).

**The S13 fence, enforced in code (`DISCOURSE_BREACH_FIELDS`):** human primacy on expression · no second
discourse authority · **NO attention-capture engine** — content is meaning-ranked by the author's own declared
rule, never an in-node engagement / recommendation / virality / outrage engine (that is the breach) · the
platform carries the artifact, never the ownership (an ownership-transfer field is refused) · money-path OFF ·
weakest-party. KILL-TARGET: the platform that owns your voice, deplatforms you, and rents your own audience back
to you through an engagement algorithm — refused. Weakest-party: an author with no platform verifies their own
ideas and audience are theirs from the receipts they hold, and can lose any account without losing the content
or the proof. NO TOKEN · no yield · holds no value · money-path OFF · rolls no cryptography.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from ..economy.contribution import record_contribution, verify_contribution, IncomeRefused   # S10 V1 / Object Model S5 V5

__all__ = ["publish_voice", "verify_voice", "Syndication", "syndicate", "record_subscription",
           "sever_subscription", "meaning_rank", "DISCOURSE_BREACH_FIELDS", "DiscourseRefused"]


class DiscourseRefused(Exception):
    """A sovereign-discourse act was refused (the S13 fence: attention-capture engine / second authority /
    ownership transfer / money-path / seal-key)."""


# THE S13 FENCE: a voice is the author's own — meaning-ranked by the author's own rule, never an engagement
# engine; carried by platforms, never owned by them; no second discourse authority; money-path OFF; and (seal-
# key-closed) no press/seal key. Any of these fields is a breach — refused.
DISCOURSE_BREACH_FIELDS = frozenset({
    "engagement_engine", "recommendation_engine", "ranking_engine", "engagement_score", "attention_score",
    "virality_engine", "outrage_optimizer", "engagement_optimizer", "addiction_loop",
    "discourse_authority", "platform_authority", "second_authority", "reach_authority", "audience_owner",
    "moderation_authority", "content_authority",
    "ownership_transfer", "platform_ownership", "rent_audience",
    "held_value", "custody", "seal_key", "press_key", "sealing_key",
})

# Fence-breadth (S13 Wave A · KM/GB): root-token probes. Any field NAME containing one of these roots is an
# attention-capture attempt, refused even under a novel variant name (engagement_ranker, virality_score,
# recommendation_feed, attention_farm, doomscroll_loop, rage_bait_score, watch_time_optimizer, …). This
# broadens the explicit set above by substring root, so a synthetic in-node engine cannot evade the fence by
# renaming its field. Additive — it only ever refuses MORE, never less (the sealed V01 claim holds, stronger).
ATTENTION_CAPTURE_ROOTS = frozenset({
    "engagement", "virality", "viral_", "recommendation", "recommender", "outrage", "addiction", "addictive",
    "clickbait", "doomscroll", "attention_farm", "attention_capture", "dark_pattern", "rage_bait", "ragebait",
    "hook_loop", "infinite_scroll", "watch_time", "time_on_platform", "algo_feed", "algofeed", "attention_score",
})

__all__ += ["ATTENTION_CAPTURE_ROOTS"]


def _is_attention_capture(name: str) -> bool:
    kl = str(name).lower()
    return (kl in ("engagement_engine", "recommendation_engine", "ranking_engine", "engagement_score",
                   "attention_score", "virality_engine", "outrage_optimizer", "engagement_optimizer",
                   "addiction_loop")
            or any(r in kl for r in ATTENTION_CAPTURE_ROOTS))


def _dfence(mapping: Optional[Mapping[str, Any]], where: str) -> None:
    for k in (mapping or {}):
        kl = str(k).lower()
        if kl in ("seal_key", "press_key", "sealing_key"):
            raise DiscourseRefused(
                f"a sovereign-discourse act must carry no press/seal key field ('{k}') — a voice is the "
                f"author's own, never the press seal key")
        if _is_attention_capture(kl):
            raise DiscourseRefused(
                f"discovery must carry no attention-capture engine field ('{k}') — content is meaning-ranked "
                f"by the AUTHOR'S OWN declared rule, never an in-node engagement / recommendation / virality "
                f"engine that optimizes for outrage or addiction (the kill-target of the attention economy); "
                f"the broadened fence refuses any field carrying an attention-capture root, under any name")
        if kl in DISCOURSE_BREACH_FIELDS:
            raise DiscourseRefused(
                f"a sovereign-discourse act must carry no second-authority / ownership-transfer / custody "
                f"field ('{k}') — the platform carries the artifact, never the ownership; the voice is the "
                f"author's own, and no second discourse / reach / moderation authority stands over it (money-"
                f"path OFF)")


# --- Voice as sovereign node output (Ch 2) -----------------------------------------------------------------

def publish_voice(author: str, content_ref: str, work_ref: str, *, author_name: str, source_ref: str, at: str,
                  registry: Any, extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Publish an idea as a **signed, content-addressed governed object** the author owns — provenance as
    default (composes the sealed governed-record surface, S10 Vol 1, over the Object Model, S5 Vol 5). The
    content is identified by its content address (`content_ref`), recorded as a hash-chained, mandate-scoped
    object owned by the author. Deny-by-default: a publication needs an author and a content address; an
    attention-capture engine / ownership-transfer / seal-key field is refused. Returns the author's receipt —
    the proof they can keep even if every account is lost."""
    _dfence(extra, "a publication")
    if not str(author).strip():
        raise DiscourseRefused("a publication needs an author — the voice is the author's own")
    if not str(content_ref).strip():
        raise DiscourseRefused("a publication needs a content address — content is addressed and signed at origin")
    ex = dict(extra or {}); ex["content_ref"] = str(content_ref); ex["sovereign_voice"] = True
    return record_contribution(author, "voice_content", work_ref, contribution_class="attested", mandate=author,
                               author=author_name, source_ref=source_ref, at=at, registry=registry, extra=ex)


def verify_voice(receipt: Mapping[str, Any], author: str, work_ref: str, *, content_ref: str,
                 extra: Optional[Mapping[str, Any]] = None) -> bool:
    """Weakest-party check: an author (or a reader) with no platform verifies the idea is the author's own and
    intact from the receipt they hold — provenance from the record, not a platform's word (composes
    `verify_contribution`, S10 Vol 1). A tampered content address or author flips the light. This is what lets
    an author lose any account without losing the content or the proof."""
    ex = dict(extra or {}); ex["content_ref"] = str(content_ref); ex["sovereign_voice"] = True
    return verify_contribution(receipt, author, work_ref, contribution_class="attested", source="voice_content",
                               extra=ex).provisioned


# --- Distribution without capture (Ch 3) -------------------------------------------------------------------

@dataclass(frozen=True)
class Syndication:
    """A syndication of a voice to a platform: the platform **carries the artifact, not the ownership**. The
    author's receipt travels with it as proof — lose the account, keep the content and the proof. Ownership is
    always retained by the author; a platform never owns the voice."""
    author: str
    platform: str
    content_ref: str
    ownership_retained: bool = True
    receipt_ref: Optional[str] = None


def syndicate(receipt: Mapping[str, Any], platform: str, content_ref: str, *,
              extra: Optional[Mapping[str, Any]] = None) -> Syndication:
    """Syndicate a published voice to an existing platform **without transferring ownership** — the adapter
    pattern: the platform carries the artifact, the author keeps the content and the proof (the receipt). Deny-
    by-default: syndication needs a platform and the content address; an `ownership_transfer` / `platform_
    ownership` / attention-capture field is refused, so a platform can never come to own the voice. Ownership is
    always retained by the author."""
    _dfence(extra, "a syndication")
    if not str(platform).strip():
        raise DiscourseRefused("a syndication names the platform that carries the artifact (not its owner)")
    if not str(content_ref).strip():
        raise DiscourseRefused("a syndication carries the content address — the platform carries the artifact")
    return Syndication(author=str(receipt.get("mandate", receipt.get("earner", ""))), platform=str(platform),
                       content_ref=str(content_ref), ownership_retained=True,
                       receipt_ref=str(receipt.get("object_id", "")))


# --- Audience as direct, receipted relationships (Ch 4) ----------------------------------------------------

def record_subscription(author: str, subscriber: str, work_ref: str, *, author_name: str, source_ref: str,
                        at: str, registry: Any, extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Record an audience relationship as a **direct, receipted** connection the author owns (composes the
    sealed governed-record surface, S10 Vol 1) — portable across platforms and severable by consent only. Deny-
    by-default: a subscription needs an author and a subscriber; an attention-capture / ownership-transfer /
    second-authority field is refused. Returns the receipt — an audience connection no platform can sever."""
    _dfence(extra, "a subscription")
    if not str(author).strip() or not str(subscriber).strip():
        raise DiscourseRefused("a subscription is a direct relationship — it needs both an author and a subscriber")
    ex = dict(extra or {}); ex["subscriber"] = str(subscriber); ex["audience_relationship"] = True
    return record_contribution(author, "audience_subscription", work_ref, contribution_class="attested",
                               mandate=author, author=author_name, source_ref=source_ref, at=at,
                               registry=registry, extra=ex)


def sever_subscription(subscriber: str, by: str, *, consent: bool = False) -> bool:
    """Sever an audience relationship — **by the subscriber's consent only.** A subscription is the subscriber's
    to end; it is severed when the subscriber themselves acts (`by == subscriber`) or explicitly consents. Deny-
    by-default: a third party (a platform) cannot sever a relationship without the subscriber's consent — that is
    refused, which is exactly what makes the audience uncapturable. Returns True when severed."""
    if str(by) != str(subscriber) and not consent:
        raise DiscourseRefused(
            "an audience relationship is severable by the subscriber's consent ONLY — a platform or third "
            "party cannot cut the connection between an author and their audience (that is what makes it "
            "uncapturable)")
    return True


# --- Meaning over extraction — the attention economy (Ch 6, resonance fold applied) ------------------------

def meaning_rank(items: Sequence[Mapping[str, Any]], *, meaning_key: str,
                 extra: Optional[Mapping[str, Any]] = None) -> List[Mapping[str, Any]]:
    """Rank content for discovery by **the author's own declared meaning** — not an engagement engine. `items`
    are content records each carrying the author's own `meaning_key` value; `meaning_rank` orders them by that
    declared value, highest first, deterministically. It computes NO engagement, virality, or attention score —
    an item or an `extra` carrying an engagement / recommendation / virality / outrage field is refused (the
    attention-capture engine is the breach). Deny-by-default: an item missing the author's meaning value is
    refused. This is meaning over extraction: the author ranks their own voice, the platform does not rank it for
    them."""
    _dfence(extra, "a discovery ranking")
    scored: List[tuple] = []
    for i, it in enumerate(items):
        _dfence(it, "a content item")
        if meaning_key not in it:
            raise DiscourseRefused(
                f"content item {i} carries no author-declared meaning value ('{meaning_key}') — discovery ranks "
                f"by the author's OWN meaning, so every item must declare it (no engagement engine supplies it)")
        scored.append((float(it[meaning_key]), i, it))
    # deterministic: by declared meaning desc, then original order (index) — no engagement signal anywhere
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [t[2] for t in scored]
