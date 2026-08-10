# -*- coding: utf-8 -*-
"""risk.group_applications — Sovereign Risk & Mutual Protection (Series 11, Vol 3:
Industry, Group & Affinity Applications).

For most groups and small enterprises, protection is a recurring cost center that quietly captures margin and
data every year. This volume turns it into an advantage by applying the mutual-protection primitive (S11 V1)
to real contexts — professional groups, affinity networks, small businesses, cooperatives, and families — and
**composes the sealed floors, inventing no new engine**. A group forms a protection pool tagged with its kind
(`form_group_pool`, composing S11 V1's `form_protection_pool`): professional · affinity · enterprise ·
cooperative · family · network — an unknown kind is refused. Members record **group premiums** and
**proof-graded group claims** they own (`group_premium` / `group_claim`, composing S11 V1's `record_premium` /
`record_claim`), settling only through the sealed Port. A group's standing is its members' accumulated proof:
`group_reputation` aggregates members' **verified receipts** into a portable GROUP reputation — a transparent
tally, never a group score — and `cross_entity_match` ranks entities by that proof, giving shared visibility
without shared control.

Everything inherits the seven-part **S11 series fence** from S11 V1: claims settle via the Port only · no
in-node pool custody · credit = portable receipt history, never issuance · reputation ≠ token/score authority
· no underwriting engine · money-path OFF · weakest-party. This volume composes the sealed S11 V1 base
(pooling, claims, credit, reputation) and the S10 floors — it does NOT depend on the advanced-mechanics volume
(S11 V2); an application composes the base, not the other application-tier mechanics. KILL-TARGET (inherited):
the affinity platform / group insurer that owns the group's protection and professional reputation and rations
them back — refused in code. NO TOKEN · no yield · holds no value · rolls no cryptography.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .mutual_protection import (form_protection_pool, record_premium, verify_premium, record_claim,
                                verify_claim, reputation_package, match_by_reputation, _fence,
                                RISK_BREACH_FIELDS, IncomeRefused, IncomeStatus, Pool)   # S11 V1 (composes S10)

__all__ = ["form_group_pool", "group_premium", "group_claim", "group_reputation", "cross_entity_match",
           "GroupReputation", "GROUP_CLASSES", "RISK_BREACH_FIELDS", "IncomeRefused", "IncomeStatus", "Pool"]

# The kinds of group a mutual-protection pool can serve. Deny-by-default: an unknown kind is refused — a group
# operates under a kind it chose and can prove, not a platform's default.
GROUP_CLASSES = frozenset({"professional", "affinity", "enterprise", "cooperative", "family", "network"})


def _require_group_class(group_class: str) -> str:
    gc = str(group_class).strip().lower()
    if gc not in GROUP_CLASSES:
        raise IncomeRefused(
            f"unknown group kind {group_class!r} — a group is {sorted(GROUP_CLASSES)}; a group operates under "
            f"a kind it chose and can prove, not a platform's default")
    return gc


def form_group_pool(group_id: str, members: Sequence[str], *, group_class: str) -> Pool:
    """Form a group/affinity mutual PROTECTION pool of a chosen kind (composes `form_protection_pool`, S11 V1 /
    S10 V2): professional · affinity · enterprise · cooperative · family · network. An unknown kind is refused.
    Like every protection pool it holds no value, has no balance, and appoints no custodian; it needs at least
    two members. Group governance is a skin the members set over the sealed gate."""
    _require_group_class(group_class)
    return form_protection_pool(group_id, members)


def group_premium(pool: Pool, member: str, work_ref: str, *, group_class: str, contribution_class: str,
                  author: str, source_ref: str, at: str, registry: Any, amount: Any = None,
                  extra: Optional[Mapping[str, Any]] = None, gate: Any = None,
                  role_spec: Optional[Mapping[str, Any]] = None, mode: str = "live") -> dict:
    """Record a member's group premium as **their own receipted obligation**, tagged with the group kind
    (composes `record_premium`, S11 V1). Specialized contribution patterns ride the group kind + the proof
    grade; the S11 fence refuses any extraction field. Returns the member's receipt."""
    gc = _require_group_class(group_class)
    _fence(extra, "a group premium")
    ex = dict(extra or {}); ex["group_class"] = gc
    return record_premium(pool, member, work_ref, contribution_class=contribution_class, author=author,
                          source_ref=source_ref, at=at, registry=registry, amount=amount, extra=ex, gate=gate,
                          role_spec=role_spec, mode=mode)


def verify_group_premium(receipt: Mapping[str, Any], pool: Pool, member: str, work_ref: str, *,
                         group_class: str, contribution_class: str, amount: Any = None) -> IncomeStatus:
    """Weakest-party check: a group member confirms their group premium from the receipt they hold (composes
    `verify_premium`, S11 V1). A tampered group kind, grade, or amount flips the light."""
    gc = _require_group_class(group_class)
    return verify_premium(receipt, pool, member, work_ref, contribution_class=contribution_class, amount=amount,
                          extra={"group_class": gc})


def group_claim(claimant: str, pool: Pool, work_ref: str, *, group_class: str, claim_class: str, author: str,
                source_ref: str, at: str, registry: Any, amount: Any = None,
                extra: Optional[Mapping[str, Any]] = None, gate: Any = None,
                role_spec: Optional[Mapping[str, Any]] = None, mode: str = "live") -> dict:
    """Record a proof-graded group claim the claimant OWNS, tagged with the group kind (composes `record_claim`,
    S11 V1). A high-value group claim passes a human (the sealed gate); the claim settles only via the Port
    (S11 V1's `settle_claim`). The S11 fence refuses any extraction field. Returns the claimant's receipt."""
    gc = _require_group_class(group_class)
    _fence(extra, "a group claim")
    ex = dict(extra or {}); ex["group_class"] = gc
    return record_claim(claimant, pool, work_ref, claim_class=claim_class, author=author, source_ref=source_ref,
                        at=at, registry=registry, amount=amount, extra=ex, gate=gate, role_spec=role_spec,
                        mode=mode)


@dataclass(frozen=True)
class GroupReputation:
    """A group's reputation: the accumulated VERIFIED receipts of its members, aggregated into a portable group
    standing — NOT a group score, NOT a rating. The `group_weight` is the sum of members' verified-receipt
    counts; it is transparent and re-derivable, never an issued authority. A member whose records do not verify
    adds nothing — the group's standing is only its members' provable contribution."""
    group_id: str
    group_weight: int
    member_count: int
    by_class: Dict[str, int] = field(default_factory=dict)
    reason: str = "a group's reputation is the sum of its members' verified receipts — not a score"


def group_reputation(group_id: str, member_records: Sequence[Mapping[str, Any]]) -> GroupReputation:
    """Aggregate a group's reputation from its members' VERIFIED receipts (composes `reputation_package`, S11
    V1, per member). Each entry is `{party, records}`. The group weight is the sum of members' verified-receipt
    counts, tallied by proof grade — a transparent, re-derivable standing, NOT a group score (a score/rating
    field is refused by the composed layer). A member whose records do not verify does not inflate the group."""
    total = 0
    by_class: Dict[str, int] = {}
    members = 0
    for entry in member_records:
        members += 1
        rep = reputation_package(entry["party"], entry.get("records", []))
        total += rep.reputation_weight
        for k, v in rep.by_class.items():
            by_class[k] = by_class.get(k, 0) + v
    return GroupReputation(group_id=str(group_id), group_weight=total, member_count=members, by_class=by_class)


def cross_entity_match(entities: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Coordinate across related entities by ranking them on their reputation weight — the count of their
    members' verified receipts (composes `group_reputation` → `reputation_package`, S11 V1). Each entity is
    `{entity, member_records}`. The ranking is transparent and re-derivable by anyone (shared visibility)
    while each entity's underlying receipts stay its own (no shared control) — most-proven first, ties in input
    order. Not an issued score (the S11 fence). This gives cross-entity coordination without a central owner."""
    ranked: List[Dict[str, Any]] = []
    for i, e in enumerate(entities):
        rep = group_reputation(str(e.get("entity", i)), e.get("member_records", []))
        ranked.append({"entity": str(e.get("entity", i)), "reputation_weight": rep.group_weight,
                       "member_count": rep.member_count, "_order": i})
    ranked.sort(key=lambda r: (-r["reputation_weight"], r["_order"]))
    for r in ranked:
        del r["_order"]
    return ranked
