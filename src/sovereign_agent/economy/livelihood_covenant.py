# -*- coding: utf-8 -*-
"""economy.livelihood_covenant — Sovereign Livelihood (Series 10, Vol 5, the CAPSTONE:
Designing Income Systems That Outlive You).

A livelihood that dies with its creator was never sovereign. This capstone makes a whole livelihood
**inheritable** — forkable, verifiable, and continuable by a successor — by composing the sealed S10
volumes and **inventing no new engine**. Inheritance here is **re-attribution of ownership records across
generations, not a held value released by an authority**: the covenant verifies that every income stream a
person built — their contributions (V1), their pooled contributions (V2), their productivity (V3), and their
compliance records (V4) — is genuine and owned, so a successor can take it up. It composes the four sealed
verify functions and nothing that holds value or vouches a handoff.

`inherit_livelihood` is the one covenant a successor reads: it dispatches each stream to its own sealed
verifier (contribution → `verify_contribution` (S10 V1) · pool → `verify_pool_contribution` (S10 V2) ·
productivity → `verify_intent` (S10 V3) · tax → `verify_tax_event` (S10 V4)) and returns **one uniform green
light** — *this is mine now* — true iff every stream verifies. It records nothing, holds no value, and rolls
no cryptography (it composes the sealed hash-chained receipts, which make the inherited records
*cryptographically verifiable* without this layer rolling any of its own).

**The SUCCESSION-FENCE** (the capstone's sharpest constraint): **no second succession authority · no standing
escrow of livelihood · composition-not-engine**. An in-node escrow, a held value awaiting release, a
recovery/succession engine, or a second authority vouching the handoff is a breach → refused
(`SUCCESSION_BREACH_FIELDS`). Kill-target: **the fund-custodian your heirs must beg to release — refused**;
inheritance is records the heir verifies, not value an authority releases. Weakest-party — the series'
sharpest test: **a resourceless heir sees "this is mine now" on a single honest indicator.** The actual
conveyance (re-attributing the mandate to the heir, the estate) homes OUT to Generational Continuity
(S5 Vol 29) and Generational Transfer (S12); this covenant proves the livelihood is genuine and inheritable,
it does not perform the transfer. NO TOKEN · no yield · rolls no cryptography.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Sequence

from .contribution import verify_contribution, IncomeRefused, IncomeStatus   # S10 V1
from .pool import verify_pool_contribution                                    # S10 V2
from .productivity import verify_intent                                       # S10 V3
from .compliance import verify_tax_event                                      # S10 V4

__all__ = ["inherit_livelihood", "verify_stream", "livelihood_stream_kinds",
           "LivelihoodStatus", "SUCCESSION_BREACH_FIELDS", "IncomeRefused", "IncomeStatus"]

# The four sealed S10 streams a livelihood is made of — each verified by its own sealed floor. The covenant
# COMPOSES these; it re-implements none of them.
_STREAM_KINDS = ("contribution", "pool", "productivity", "tax")

# The SUCCESSION-FENCE: inheritance is re-attribution of ownership records — NOT a held value released by an
# authority. Any in-node escrow, standing-held value, recovery/succession engine, or second authority
# vouching the handoff is a breach — refused. The kill-target is the fund-custodian your heirs must beg.
SUCCESSION_BREACH_FIELDS = frozenset({
    "escrow", "standing_escrow", "held_in_escrow", "escrow_release", "release_authority",
    "releasing_authority", "second_authority", "succession_authority", "recovery_engine",
    "succession_engine", "vouching_authority", "fund_custodian", "held_value", "custodian_release",
})


def livelihood_stream_kinds() -> List[str]:
    """The stream kinds a livelihood covenant composes — one per sealed S10 volume (V1–V4)."""
    return list(_STREAM_KINDS)


@dataclass(frozen=True)
class LivelihoodStatus:
    """The one honest indicator a successor reads: *this is mine now* — inherited iff every income stream of
    the livelihood verifies as genuine and owned. Holds no value; a by-kind tally shows the shape of the
    inheritance. A resourceless heir needs nothing but this single green light."""
    inherited: bool
    reason: str
    owner: str
    verified_count: int
    by_kind: Dict[str, int] = field(default_factory=dict)


def verify_stream(owner: str, stream: Mapping[str, Any]) -> IncomeStatus:
    """Verify ONE income stream of a livelihood by composing its own sealed S10 verifier. `stream` is
    `{kind, receipt, ...}` where kind ∈ contribution|pool|productivity|tax and the remaining fields are the
    kwargs that kind's sealed verifier needs. The SUCCESSION-FENCE refuses any escrow / second-authority /
    recovery-engine field on the stream — inheritance is a verified record, not a released value."""
    kind = str(stream.get("kind", "")).strip().lower()
    if kind not in _STREAM_KINDS:
        raise IncomeRefused(
            f"unknown livelihood stream kind {stream.get('kind')!r} — a covenant composes one of "
            f"{list(_STREAM_KINDS)} (S10 V1–V4); it invents no new stream")
    for k in stream:                                      # THE SUCCESSION-FENCE
        if str(k).lower() in SUCCESSION_BREACH_FIELDS:
            raise IncomeRefused(
                f"a livelihood stream must carry no succession-authority/escrow field ('{k}') — inheritance "
                f"is re-attribution of ownership RECORDS, not a held value released by an authority; the "
                f"covenant composes Continuity/Constitutions/the gate, it invents no recovery/escrow engine")
    r = stream["receipt"]
    if kind == "contribution":
        return verify_contribution(r, owner, stream["work_ref"], contribution_class=stream["contribution_class"],
                                   source=stream["source"], amount=stream.get("amount"),
                                   unit=stream.get("unit", "credits"), port_ref=stream.get("port_ref"),
                                   extra=stream.get("extra"))
    if kind == "pool":
        return verify_pool_contribution(r, stream["pool"], owner, stream["source"], stream["work_ref"],
                                        contribution_class=stream["contribution_class"],
                                        amount=stream.get("amount"), unit=stream.get("unit", "credits"),
                                        port_ref=stream.get("port_ref"), extra=stream.get("extra"))
    if kind == "productivity":
        return verify_intent(r, owner, stream["intent"], stream["work_ref"],
                             contribution_class=stream["contribution_class"], amount=stream.get("amount"),
                             unit=stream.get("unit", "credits"), port_ref=stream.get("port_ref"),
                             extra=stream.get("extra"))
    # kind == "tax"
    return verify_tax_event(r, owner, stream["work_ref"], category=stream["category"],
                            references_income=stream.get("references_income"), amount=stream.get("amount"),
                            unit=stream.get("unit", "credits"), port_ref=stream.get("port_ref"),
                            extra=stream.get("extra"))


def inherit_livelihood(owner: str, streams: Sequence[Mapping[str, Any]]) -> LivelihoodStatus:
    """The Sovereign Livelihood Covenant: verify that a WHOLE livelihood is genuine and inheritable by
    composing each stream's own sealed S10 verifier (V1–V4) — one uniform check over any stream kind. Returns
    ONE honest indicator, `inherited`, true iff every stream verifies as `owner`'s own (*this is mine now*),
    with a by-kind tally. It records nothing, holds no value, invents no engine, and rolls no cryptography.
    Deny-by-default: an empty livelihood is not inherited; a foreign or tampered stream fails the whole; an
    escrow/second-authority field is refused (the SUCCESSION-FENCE). The actual re-attribution of the mandate
    to the heir homes OUT to Generational Continuity (S5 Vol 29) / Generational Transfer (S12)."""
    by_kind = {k: 0 for k in _STREAM_KINDS}
    verified = 0
    reason: List[str] = []
    for i, stream in enumerate(streams):
        st = verify_stream(owner, stream)                # composes the sealed floor; raises on fence/kind breach
        if not st.provisioned:
            reason.append(f"stream {i} ({stream.get('kind')}) does not verify as {owner}'s own: {st.reason}")
            continue
        verified += 1
        by_kind[str(stream.get("kind")).strip().lower()] += 1
    ok = bool(streams) and not reason
    return LivelihoodStatus(inherited=ok,
                            reason="; ".join(reason) or "this is mine now — the whole livelihood verifies",
                            owner=owner, verified_count=verified, by_kind=by_kind)
