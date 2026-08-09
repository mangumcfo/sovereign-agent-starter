# -*- coding: utf-8 -*-
"""economy.pool — Sovereign Livelihood (Series 10, Vol 2: Networked Value Pools Without Extraction).

A **mutual contribution pool** lets a small, trusted group turn personal contributions into recirculating,
receipted income flows — **without a middleman that extracts, and without the node ever holding the pool's
value**. Each member's contribution into a pool is recorded as **that member's own income** (composing the
sealed contribution layer, S10 V1), tagged with the pool it serves. When value flows back, it **settles only
via the sealed Port (S6 Vol 7)** — a per-member Port directive — so the node holds **no pool balance, does no
internal netting, and performs no in-node settlement**. There is no central pool custodian; the pool is a set
of members and the receipts they each hold.

It **composes `contribution.py` (S10 V1) and nothing else** — so every pooled contribution inherits the
Income Primitive's guarantees (owned by the member, money-path OFF, human primacy, weakest-party). It adds
the pool-formation + Port-only-settlement layer and re-implements nothing.

Kill-targets: **composes contribution.py only** · **no in-node pool balance / netting / internal settlement**
(settlement is a list of Port directives; any in-node pool-value field is REFUSED — the elevated S10 V2
money-fence) · **no central pool custodian** (each member owns their own contribution receipt) ·
**weakest-party** (a member verifies their pooled contribution from the receipt they hold). OUT — reputation
& reputation-weighted matching home to Sovereign Risk & Mutual Protection (S11); federation/bridging & exit
across pools to Peerhood (S14) / Inter-Node Sovereignty (S6); a pool's money reconciles to Treasury /
Controlling / Revenue (S5); inheritance/continuity of a network to Generational Continuity (S5 Vol 29) /
Generational Transfer (S12).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .contribution import (record_contribution, verify_contribution,   # S10 V1 — composed by identity
                           IncomeRefused, IncomeStatus)

__all__ = ["form_pool", "contribute_to_pool", "pool_settlement", "verify_pool_contribution",
           "Pool", "PoolSettlement", "POOL_BREACH_FIELDS", "IncomeRefused", "IncomeStatus"]

# The elevated S10 V2 money-fence: a pool must never hold value, net internally, or settle in-node. A
# settlement instruction carrying any of these would make the node the pool's custodian — REFUSED. (Value
# settles ONLY as a per-member Port directive; the node holds no pool balance.)
POOL_BREACH_FIELDS = frozenset({
    "pool_balance", "pooled_balance", "netting", "net_position", "internal_settlement",
    "pool_ledger_balance", "held_pool", "custody_pool", "pool_float", "clearing_balance",
})


@dataclass(frozen=True)
class Pool:
    """A mutual contribution pool: a named set of members. Holds no value — it is who is in, not what is
    owed. Governance (a human gate on material pool decisions) is composed from the sealed gate per act."""
    pool_id: str
    members: Tuple[str, ...]

    def has(self, member: str) -> bool:
        return member in self.members


@dataclass(frozen=True)
class PoolSettlement:
    """A pool settlement: a list of per-member **Port directives** (`{member, port_ref, share}`). It holds
    NO value and does NO netting — it is instructions for value to cross the sealed Port, member by member."""
    pool_id: str
    directives: Tuple[Mapping[str, Any], ...]


def form_pool(pool_id: str, members: Sequence[str]) -> Pool:
    """Form a mutual contribution pool from a set of members. A pool is who is in — it holds no value, has no
    balance, and appoints no custodian. Deny-by-default: a pool needs an id and at least two members."""
    if not str(pool_id).strip():
        raise IncomeRefused("a pool needs an id")
    ms = tuple(dict.fromkeys(str(m) for m in members if str(m).strip()))   # de-duped, order-preserving
    if len(ms) < 2:
        raise IncomeRefused("a mutual pool needs at least two members — a pool of one is a solo livelihood")
    return Pool(pool_id=str(pool_id), members=ms)


def contribute_to_pool(pool: Pool, member: str, source: str, work_ref: str, *, contribution_class: str,
                       author: str, source_ref: str, at: str, registry: Any, mandate: Optional[str] = None,
                       amount: Any = None, unit: str = "credits", port_ref: Optional[str] = None,
                       extra: Optional[Mapping[str, Any]] = None, approver: Optional[str] = None,
                       approval_ref: Optional[str] = None, gate: Any = None,
                       action_class: str = "contribute_to_pool",
                       role_spec: Optional[Mapping[str, Any]] = None, mode: str = "live") -> dict:
    """Record a member's contribution INTO a pool as **that member's own income** (composes
    `record_contribution`, S10 V1), tagged with the pool it serves. The pool holds nothing — the member owns
    the receipt. Money-path OFF inherited; a gated pool contribution passes a human. Returns the member's
    receipt (its mandate defaults to the member — they own it)."""
    if not pool.has(member):
        raise IncomeRefused(f"{member!r} is not a member of pool {pool.pool_id!r} — deny-by-default")
    ex = dict(extra or {})
    ex["pool"] = pool.pool_id                       # the contribution serves this pool (an attribution field)
    return record_contribution(member, source, work_ref, contribution_class=contribution_class,
                               mandate=(mandate or member), author=author, source_ref=source_ref, at=at,
                               registry=registry, amount=amount, unit=unit, port_ref=port_ref, extra=ex,
                               approver=approver, approval_ref=approval_ref, gate=gate,
                               action_class=action_class, role_spec=role_spec, mode=mode)


def pool_settlement(pool: Pool, member_shares: Sequence[Tuple[str, Any]], *,
                    port_ref_of: Any = None) -> PoolSettlement:
    """Settle a pool back to its members **only via the sealed Port** — a per-member Port directive, member by
    member. The settlement holds NO value, does NO netting, and performs NO in-node settlement: any in-node
    pool-value field is REFUSED (the elevated S10 V2 money-fence). `port_ref_of(member)` yields the member's
    Port directive reference (else the caller supplies `port_ref` in the share tuple's mapping)."""
    directives: List[Mapping[str, Any]] = []
    for member, share in member_shares:
        if not pool.has(str(member)):
            raise IncomeRefused(f"cannot settle to {member!r} — not a member of pool {pool.pool_id!r}")
        # the elevated fence: a settlement INSTRUCTION carrying an in-node pool-value field is refused
        # (no pool balance, no netting, no internal settlement) — value settles ONLY via the Port.
        if isinstance(share, Mapping):
            for k in share:
                if str(k).lower() in POOL_BREACH_FIELDS:
                    raise IncomeRefused(
                        f"pool settlement must carry no in-node pool-value field ('{k}') — no pool balance, "
                        f"no netting, no internal settlement; value rides the sealed Port")
        d: Dict[str, Any] = {"member": str(member), "share": (str(share.get("share"))
                                                              if isinstance(share, Mapping) else str(share))}
        if callable(port_ref_of):
            pr = port_ref_of(member)
        elif isinstance(share, Mapping):
            pr = share.get("port_ref")
        else:
            pr = None
        if not pr:
            raise IncomeRefused(
                f"pool settlement to {member!r} requires a Port directive (port_ref) — a pool settles ONLY "
                f"via the sealed Port; the node holds no pool balance and does no in-node settlement")
        d["port_ref"] = str(pr)
        for k in d:
            if k.lower() in POOL_BREACH_FIELDS:
                raise IncomeRefused(f"pool settlement must carry no in-node pool-value field ('{k}') — "
                                    f"no pool balance, no netting, no internal settlement; value rides the Port")
        directives.append(d)
    if not directives:
        raise IncomeRefused("a pool settlement needs at least one member directive")
    return PoolSettlement(pool_id=pool.pool_id, directives=tuple(directives))


def verify_pool_contribution(receipt: Mapping[str, Any], pool: Pool, member: str, source: str, work_ref: str,
                             *, contribution_class: str, amount: Any = None, unit: str = "credits",
                             port_ref: Optional[str] = None,
                             extra: Optional[Mapping[str, Any]] = None) -> IncomeStatus:
    """Weakest-party check: a member confirms their pooled contribution — and that it served this pool — from
    the receipt they hold. Composes `verify_contribution` (S10 V1) over the member's record with the pool tag;
    a tampered pool, source, class, or amount flips the light. No platform, no second device."""
    ex = dict(extra or {})
    ex["pool"] = pool.pool_id
    return verify_contribution(receipt, member, work_ref, contribution_class=contribution_class, source=source,
                               amount=amount, unit=unit, port_ref=port_ref, extra=ex)
