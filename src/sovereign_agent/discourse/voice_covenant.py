# -*- coding: utf-8 -*-
"""discourse.voice_covenant — Sovereign Discourse (Series 13, Vol 5, CAPSTONE:
The Voice as Living Covenant).

The series closes where it was always going: a whole public voice held as one **living covenant** — owned,
governed, reaching, sustaining, and inheritable — that a creator, a family, or a small organization keeps and
hands on across generations. This capstone builds ONE load-bearing composition, `assemble_voice_covenant`, that
folds the **whole sealed Sovereign Discourse stack (V01–V04)** into a single honest indicator: it composes the
sealed owned-voice verification (V1, through the sealed voice system), the sealed reputation of verified voice
(V3, through the sealed voice asset), and the sealed sustainable-voice layer (V4 `assemble_voice_system` +
`voice_as_asset`) into four pillars — **owned · self-sustaining · governed/reputed · inheritable** — and reports
the voice a *living covenant* only when EVERY pillar verifies as the author's own. `verify_covenant_element`
dispatches any single layer by kind, composing the matching sealed verifier (voice → V1, reach → V2, reputation
→ V3, system/asset → V4). It **invents no new engine** and **imports V1–V4 only** — the capstone is the
composition, not a new mechanism.

**Weakest-party (the series' final test, LOUD):** a creator or heir with no team, no agency, and no platform
reads ONE honest indicator — `is_living` — that the whole voice inheritance (its content, audience, reach,
governance, and standing) passed to them intact and is theirs to keep and hand on, from the receipts they hold.
KILL-TARGET: the media dynasty that owns a family's voice across the generations and rations it back to them —
refused. The whole S13 fence holds, broadened and compound-hardened: human primacy on expression · no second
discourse authority · **no attention-capture engine** (root + compound shape; a feed/growth optimizer refused
under any token) · money-path OFF · weakest-party. NO TOKEN · no yield · holds no value · rolls no cryptography.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from .sovereign_voice import (                                                          # S13 V1 (sealed opener)
    verify_voice, DiscourseRefused, DISCOURSE_BREACH_FIELDS, _is_attention_capture as _is_attn,
)
from .advanced_reach import multi_platform_reach                                        # S13 V2 (sealed)
from .voice_governance import (                                                         # S13 V3 (sealed)
    reputation_from_receipts, load_voice_constitution, fork_voice_constitution, govern_expression,
)
from .sustainable_voice import (                                                        # S13 V4 (sealed)
    assemble_voice_system, voice_as_asset, SUSTAINABLE_BREACH_FIELDS,
)

__all__ = ["assemble_voice_covenant", "VoiceCovenant", "verify_covenant_element",
           "COVENANT_BREACH_FIELDS", "DiscourseRefused"]

# The capstone inherits the whole broadened + compound S13 fence (through V4) and adds the dynasty kill-target.
COVENANT_BREACH_FIELDS = SUSTAINABLE_BREACH_FIELDS | frozenset({
    "voice_dynasty", "media_dynasty", "discourse_trust", "voice_custodian", "covenant_authority", "legacy_broker",
})

_COVENANT_KINDS = ("voice", "reach", "governance", "reputation", "system", "asset")


def _cfence(mapping: Optional[Mapping[str, Any]]) -> None:
    for k in (mapping or {}):
        kl = str(k).lower()
        if _is_attn(kl):
            raise DiscourseRefused(
                f"a voice covenant must carry no attention-capture / growth engine field ('{k}') — a voice "
                f"endures as a living covenant of owned records, never a fed feed/growth optimizer (the "
                f"compound fence refuses a carrier root + an optimize root under any token)")
        if kl in COVENANT_BREACH_FIELDS or "rental" in kl or "lease" in kl or "dynasty" in kl:
            raise DiscourseRefused(
                f"a voice covenant must carry no dynasty / second-authority / reach-rental field ('{k}') — the "
                f"media dynasty that owns a family's voice across generations and rations it back is refused; "
                f"the voice is the family's own to keep and hand on")


# --- The living covenant: the whole sealed stack as one indicator (Ch 2 · Final Synthesis Ch 8) ------------

@dataclass(frozen=True)
class VoiceCovenant:
    """A whole public voice held as one **living covenant**: owned, self-sustaining, governed/reputed, and
    inheritable — composed from the sealed Sovereign Discourse stack (V1–V4). `is_living` is the weakest-party
    indicator a creator or heir reads: the whole voice inheritance passed to them intact and is theirs to keep
    and hand on. Deny-by-default: a tampered, foreign, or empty layer means the covenant is not fully living.
    It holds no value; the covenant is verified owned records, not a held estate or a platform's grant."""
    author: str
    pillars_verified: int
    pillars_total: int
    is_living: bool
    reason: str = ""


def assemble_voice_covenant(author: str, records: Sequence[Mapping[str, Any]], *,
                            extra: Optional[Mapping[str, Any]] = None) -> VoiceCovenant:
    """Assemble the whole sovereign voice as ONE **living covenant** by composing the sealed Sovereign Discourse
    stack (V1–V4) into four pillars: **owned** (the body is a real corpus of the author's own verified voice —
    the sealed `assemble_voice_system` over V1 `verify_voice`), **self-sustaining** (that system compounds
    without a fed engine — V4), **governed/reputed** (its value is the author's own verified voice — the sealed
    `voice_as_asset` over V3 `reputation_from_receipts`), and **inheritable** (the asset endures and can pass on
    — V4, homing OUT to Generational Transfer, S12, with Generational Continuity, S5 Vol 29, the floor). The
    voice is a living covenant (`is_living`) **only when every pillar verifies as the author's own** — a
    tampered/foreign/empty layer fails the whole. Weakest-party (LOUD): a creator or heir reads this one honest
    indicator that their whole voice inheritance is intact and theirs to hand on. Imports V1–V4 only; invents no
    engine; holds no value; rolls no cryptography."""
    _cfence(extra)
    system = assemble_voice_system(author, records)                    # V4 (composes V1 verify_voice)
    asset = voice_as_asset(author, records)                            # V4 (composes V3 reputation_from_receipts)
    pillars = {
        "owned": system.total > 0 and system.verified == system.total,  # a real corpus, every part the author's own
        "self_sustaining": system.self_sustaining,                      # compounds without a fed engine (V4)
        "inheritable": asset.inheritable,                               # the asset can pass on (V4 / S12)
        "endures": asset.endures,                                       # the asset endures intact (V4 / V3)
    }
    verified = sum(1 for ok in pillars.values() if ok)
    is_living = verified == len(pillars)
    reason = ("this voice is a living covenant — owned, self-sustaining, governed, and inheritable, mine and my "
              "heirs' to keep and hand on" if is_living
              else f"{verified}/{len(pillars)} covenant pillars verify as the author's own"
              if system.total else "an empty body of voice is not a living covenant")
    return VoiceCovenant(author=author, pillars_verified=verified, pillars_total=len(pillars),
                         is_living=is_living, reason=reason)


# --- Dispatch any single covenant layer by kind (Ch 1 · the complete architecture) ------------------------

def verify_covenant_element(element: Mapping[str, Any], kind: str, author: str, *,
                            extra: Optional[Mapping[str, Any]] = None) -> bool:
    """Verify any single layer of the voice covenant by kind, composing the matching **sealed** verifier — the
    complete Sovereign Discourse architecture reachable through one uniform check: `voice` → the sealed
    `verify_voice` (V1), `reach` → the sealed `multi_platform_reach` with ownership retained on every surface
    (V2), `reputation` → the sealed `reputation_from_receipts` intact (V3), `system` → the sealed
    `assemble_voice_system` self-sustaining (V4), `asset` → the sealed `voice_as_asset` endures (V4). Deny-by-
    default: an unknown kind is refused (the covenant composes only the sealed layers); an attention-capture /
    dynasty field is refused."""
    _cfence(extra)
    _cfence(element)
    k = str(kind).lower()
    if k == "voice":
        return bool(verify_voice(element["receipt"], author, element["work_ref"],
                                 content_ref=element["content_ref"]))
    if k == "reach":
        reach = multi_platform_reach(element["receipt"], element["platforms"], element["content_ref"])
        return bool(reach) and all(s.ownership_retained for s in reach)      # V2: carried, ownership retained
    if k == "governance":
        # V3 living governance: the author's own constitution (loaded or given), forked as a living revision
        # (Ch 2 versioning), gates the consequential expression through the sealed human gate.
        cls = str(element["statement_class"])
        con = element.get("constitution") or load_voice_constitution(author, gated_classes=[cls])  # V3
        con = fork_voice_constitution(con, str(element.get("revision", "rev-1")), add_gated=[cls])  # V3 versioning
        decision = govern_expression(con, cls, author, element["work_ref"], gate=element["gate"],   # V3 human gate
                                     at=element["at"], author_name=element["author_name"],
                                     source_ref=element["source_ref"], registry=element["registry"],
                                     approver=element.get("approver"), approval_ref=element.get("approval_ref"))
        return decision.get("mandate") == author
    if k == "reputation":
        return reputation_from_receipts(author, element["records"]).intact   # V3
    if k == "system":
        return assemble_voice_system(author, element["records"]).self_sustaining  # V4
    if k == "asset":
        return voice_as_asset(author, element["records"]).endures            # V4
    raise DiscourseRefused(
        f"unknown covenant element kind '{kind}' — the living covenant composes only the sealed Sovereign "
        f"Discourse layers ({', '.join(_COVENANT_KINDS)}); it invents no new element")
