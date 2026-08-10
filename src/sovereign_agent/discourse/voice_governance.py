# -*- coding: utf-8 -*-
"""discourse.voice_governance — Sovereign Discourse (Series 13, Vol 3:
Governance, Risk Management & Human Primacy in Public Voice).

Most creators and thought leaders grow a voice with no governance over it — no rules for what they will and will
not say through which channel, no human gate on the statements that could harm, no owned record of their own
standing. This volume builds that governance, and it does so by **composing** the sealed layers and **inventing
no new engine**: `load_voice_constitution` composes the sealed policy-as-code governance skin (Sovereign Risk &
Mutual Protection, Vol 4) into the author's own content constitution; `govern_expression` routes a high-impact
statement through the sealed human gate (composing the sealed enforce path, S11 V4 / S8 V2), so the consequential
words pass a human hand; and `reputation_from_receipts` composes the sealed voice verification (Sovereign
Discourse, Vol 1) so the author's standing is **verified receipts they hold**, not a platform's score.

**The S13 fence, sharpened for governance:** human primacy on expression · the author governs their own voice by
their own rules · **no moderation authority owns the rules of the voice** · no attention-capture engine (the
broadened root-token fence) · money-path OFF · weakest-party. KILL-TARGET: the moderation authority that owns the
rules of your voice and enforces them on its terms — refused; the rules are the author's own, and only a human
the author trusts gates their consequential expression. Weakest-party: a creator with no platform proves their
own standing from receipts they hold, governed by rules they wrote. NO TOKEN · no yield · holds no value ·
money-path OFF · rolls no cryptography.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .sovereign_voice import (                                                          # S13 V1 (sealed opener)
    verify_voice, DiscourseRefused, DISCOURSE_BREACH_FIELDS, ATTENTION_CAPTURE_ROOTS,
)
from ..risk.governance import (                                                         # S11 V4 (governance skin)
    load_governance_skin, fork_governance_skin, enforce_decision, GovernanceSkin,
)

__all__ = ["load_voice_constitution", "fork_voice_constitution", "govern_expression", "ReputationStanding",
           "reputation_from_receipts", "VOICE_GOV_BREACH_FIELDS", "DiscourseRefused"]

# The voice-governance layer inherits the broadened S13 fence and adds the moderation-authority kill-target.
VOICE_GOV_BREACH_FIELDS = DISCOURSE_BREACH_FIELDS | frozenset({
    "moderation_authority", "content_authority", "censor_authority", "reputation_score_engine", "shadow_ban",
})


def _gfence(mapping: Optional[Mapping[str, Any]], where: str) -> None:
    for k in (mapping or {}):
        kl = str(k).lower()
        if any(r in kl for r in ATTENTION_CAPTURE_ROOTS):
            raise DiscourseRefused(
                f"voice governance must carry no attention-capture engine field ('{k}') — governance is human "
                f"primacy over expression, never an engagement engine")
        if kl in VOICE_GOV_BREACH_FIELDS or "moderation" in kl or "censor" in kl or "shadow_ban" in kl:
            raise DiscourseRefused(
                f"voice governance must carry no moderation-authority / second-authority field ('{k}') — the "
                f"author governs their OWN voice by their own rules; no moderation authority owns the rules of "
                f"the voice, and only a human the author trusts gates their consequential expression")


# --- Constitutional governance for content and voice (Ch 2) ------------------------------------------------

def load_voice_constitution(author: str, *, gated_classes: Sequence[str],
                            limits: Optional[Mapping[str, Any]] = None,
                            extra: Optional[Mapping[str, Any]] = None) -> GovernanceSkin:
    """Load the author's own **content constitution** — living policy-as-code naming which classes of public
    expression require a human gate (composes the sealed governance skin, Sovereign Risk & Mutual Protection Vol
    4). Deny-by-default: a constitution needs an author and at least one gated class (a voice that gates nothing
    governs nothing); a moderation-authority / attention-capture field is refused. Enforcement only — it prices
    and optimizes nothing (the inherited fence). The rules are the author's own to write and fork."""
    _gfence(extra, "a voice constitution")
    if not str(author).strip():
        raise DiscourseRefused("a voice constitution needs an author — the rules are the author's own")
    return load_governance_skin(f"voice:{author}", gated_classes=gated_classes, limits=limits)


def fork_voice_constitution(constitution: GovernanceSkin, revision: str, *, add_gated: Sequence[str] = (),
                            remove_gated: Sequence[str] = (),
                            extra: Optional[Mapping[str, Any]] = None) -> GovernanceSkin:
    """Fork the voice constitution into a new revision — governance is living and versioned (composes the sealed
    `fork_governance_skin`, Vol 4). The author adds or removes gated expression classes as their voice matures;
    history is preserved by keeping both. A moderation-authority / pricing field is refused."""
    _gfence(extra, "a constitution fork")
    if not str(revision).strip():
        raise DiscourseRefused("a constitution fork needs a revision id")
    return fork_governance_skin(constitution, f"{constitution.skin_id}:{revision}",
                                add_gated=add_gated, remove_gated=remove_gated)


# --- Human primacy in content & audience decisions (Ch 3) --------------------------------------------------

def govern_expression(constitution: GovernanceSkin, statement_class: str, author: str, work_ref: str, *,
                      gate: Any, at: str, author_name: str, source_ref: str, registry: Any,
                      approver: Optional[str] = None, approval_ref: Optional[str] = None,
                      extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Route a **high-impact public statement** through the author's content constitution and the sealed human
    gate (composes the sealed `enforce_decision`, Vol 4, over the gate, S5 Vol 16 / Interface Sovereignty Vol
    2). A statement whose class the constitution gates is refused without a named human's approval — human
    primacy over the consequential expression, never an automated authority publishing for the author. Returns
    the governed statement's receipt (the author owns it). A moderation-authority field is refused."""
    _gfence(extra, "a governed statement")
    ex = dict(extra or {}); ex["voice_governed"] = True
    return enforce_decision(constitution, str(statement_class), author, work_ref, gate=gate, at=at,
                            author=author_name, source_ref=source_ref, registry=registry, approver=approver,
                            approval_ref=approval_ref, extra=ex)


# --- Reputation & risk management for public voice (Ch 4) --------------------------------------------------

@dataclass(frozen=True)
class ReputationStanding:
    """The author's standing as **verified receipts they hold** — not a platform's score. `standing` is the
    count of the author's own expression receipts that verify as theirs and intact; a reputation is a history of
    verified voice, portable and owned, that no platform can revoke or inflate."""
    author: str
    standing: int
    total: int
    intact: bool
    reason: str = ""


def reputation_from_receipts(author: str, records: Sequence[Mapping[str, Any]]) -> ReputationStanding:
    """Assemble the author's reputation from **verified expression receipts** (composes the sealed `verify_voice`,
    Vol 1) — the author's standing is a history of their own verified voice, held by them, never a platform's
    reputation score. Each record is `{receipt, work_ref, content_ref}`; the standing counts those that verify as
    the author's own and intact. Deny-by-default: an empty history has no standing; a moderation-authority /
    reputation-score-engine field on a record is refused. Reputation is verified receipts, not an engine's number."""
    total = 0
    standing = 0
    for rec in records:
        _gfence(rec, "a reputation record")
        total += 1
        if verify_voice(rec["receipt"], author, rec["work_ref"], content_ref=rec["content_ref"]):
            standing += 1
    intact = total > 0 and standing == total
    reason = ("every recorded statement verifies as the author's own — a standing of verified voice" if intact
              else f"{standing}/{total} statements verify as the author's own" if total
              else "an empty history has no standing")
    return ReputationStanding(author=author, standing=standing, total=total, intact=intact, reason=reason)
