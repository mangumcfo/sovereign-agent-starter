# -*- coding: utf-8 -*-
"""risk.advanced_pooling — Sovereign Risk & Mutual Protection (Series 11, Vol 2:
Advanced Pooling, Credit Mechanics & Proof Systems).

Basic pools protect their members until they hit a coordination or capital ceiling. This volume takes the
mutual-protection primitive (S11 V1) past that wall — **federated pools, selective-disclosure credit, and
multi-party attestation chains** — while keeping the whole thing receipted, human-gated, and un-captured, and
**composing the sealed floors, inventing no new engine and rolling no cryptography of its own**. A federation
is a set of protection pools bridged together (`federate_pools`) that, like each pool, **holds no value** — a
member settles across the federation **only through the sealed Port** (`bridge_settlement`, composing S11 V1's
`settle_claim`). Credit is proven with **selective disclosure** (`selective_disclosure`): a member discloses a
chosen subset of their own verified receipts, proving what a counterparty needs without revealing the rest —
the underlying range-proof *cryptography* (proving a hidden amount sits in a range) homes OUT to the sealed
ZK shield (Zero-Trust Sovereignty, S7); this layer rolls none. A claim is verified through a **multi-party
attestation chain** (`build_attestation_chain` / `verify_attestation_chain`): the claim plus an ordered chain
of attestors, each of whose attestation verifies from a receipt they hold.

Everything inherits the seven-part **S11 series fence** from S11 V1: claims settle via the Port only · no
in-node pool custody · credit = portable receipt history, never issuance · reputation ≠ token/score authority
· no underwriting engine · money-path OFF · weakest-party. Federation adds no custody and no central control —
it is anti-capture bridging, not a bigger fund. KILL-TARGET (inherited): the insurer/bureau/scorer that owns
your risk, credit, and standing and rations them back — refused in code. NO TOKEN · no yield · holds no value
· rolls no cryptography.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .mutual_protection import (form_protection_pool, settle_claim, record_claim, verify_claim,
                                credit_history, CreditHistory, CLAIM_CLASSES, RISK_BREACH_FIELDS,
                                _fence, IncomeRefused, IncomeStatus, Pool, PoolSettlement)   # S11 V1
from ..economy.contribution import record_contribution, verify_contribution                 # S10 V1

__all__ = ["federate_pools", "bridge_settlement", "selective_disclosure", "build_attestation_chain",
           "verify_attestation_chain", "Federation", "DisclosedCredit",
           "RISK_BREACH_FIELDS", "IncomeRefused", "IncomeStatus", "Pool", "PoolSettlement"]


@dataclass(frozen=True)
class Federation:
    """A federation of mutual protection pools — bridged, not merged. It holds no value, keeps no balance, and
    exercises no central control: it is the union of who is in its member pools, so obligations can be shared
    across pools while each pool stays sovereign. Anti-capture bridging, never a bigger fund."""
    federation_id: str
    pools: tuple
    members: tuple

    def has(self, party: str) -> bool:
        return str(party) in self.members


def federate_pools(federation_id: str, pools: Sequence[Pool]) -> Federation:
    """Federate two or more protection pools into a bridge (composes the sealed pools, S11 V1 / S10 V2). The
    federation holds no value and appoints no custodian; its members are the union of the pooled members.
    Deny-by-default: a federation needs an id and at least two pools (a federation of one is just a pool)."""
    if not str(federation_id).strip():
        raise IncomeRefused("a federation needs an id")
    ps = tuple(pools)
    if len(ps) < 2:
        raise IncomeRefused("a federation bridges at least two pools — one pool is not a federation")
    members: List[str] = []
    for p in ps:
        for m in p.members:
            if m not in members:
                members.append(m)
    return Federation(federation_id=str(federation_id), pools=ps, members=tuple(members))


def bridge_settlement(federation: Federation, member: str, share: Any, *,
                      port_ref: Optional[str] = None) -> PoolSettlement:
    """Settle a member across the federation **only through the sealed Port** (composes `settle_claim`, S11 V1
    → `pool_settlement`, S10 V2). The federation holds no value, nets nothing, and keeps no reserve: the S11
    fence refuses any in-node pool-value field. The member must belong to one of the federated pools."""
    if not federation.has(str(member)):
        raise IncomeRefused(f"{member!r} is not a member of any pool in federation {federation.federation_id!r}")
    # settle through the member's home pool via the sealed Port — one directive, no in-node custody
    home = next(p for p in federation.pools if p.has(str(member)))
    return settle_claim(home, member, share, port_ref=port_ref)


@dataclass(frozen=True)
class DisclosedCredit:
    """A selectively-disclosed credit view: the member reveals a chosen SUBSET of their own verified receipts
    and withholds the rest, proving what a counterparty needs without exposing their whole history. It issues
    nothing and holds no value (the S11 fence). The count of withheld receipts is disclosed; their contents are
    not. The range-proof cryptography (proving a hidden amount in a range) homes OUT to the sealed ZK shield."""
    member: str
    disclosed_count: int
    withheld_count: int
    complete: bool
    reason: str = "a selectively-disclosed subset of your own verified receipts — issues nothing"


def selective_disclosure(member: str, records: Sequence[Mapping[str, Any]],
                         disclose: Sequence[int]) -> DisclosedCredit:
    """Prove creditworthiness with **selective disclosure**: reveal only the receipts at the `disclose` indices
    (composes `credit_history`, S11 V1, over that subset), withholding the rest — so a member proves what a
    counterparty needs without exposing their whole record. Complete iff every DISCLOSED receipt verifies as the
    member's own; the withheld receipts' count is shown, their contents are not. Issues nothing, holds no value.
    The range-proof *cryptography* (proving a hidden amount sits in a range) homes OUT to the sealed ZK shield
    (Zero-Trust Sovereignty, S7); this layer rolls none. Deny-by-default: disclosing nothing is not complete."""
    idx = sorted(set(int(i) for i in disclose))
    n = len(records)
    for i in idx:
        if i < 0 or i >= n:
            raise IncomeRefused(f"disclosure index {i} is out of range — cannot disclose a receipt you did not provide")
    subset = [records[i] for i in idx]
    h = credit_history(member, subset)   # composes verify over the disclosed subset only
    return DisclosedCredit(member=member, disclosed_count=(h.verified_count if h.complete else len(subset)),
                           withheld_count=n - len(subset), complete=h.complete,
                           reason=("a selectively-disclosed subset of your own verified receipts — issues nothing"
                                   if h.complete else h.reason))


def build_attestation_chain(claimant: str, pool: Pool, work_ref: str, *, claim_class: str,
                            attestors: Sequence[Mapping[str, Any]], registry: Any, at: str, author: str,
                            source_ref: str, amount: Any = None, gate: Any = None,
                            extra: Optional[Mapping[str, Any]] = None) -> List[dict]:
    """Build a multi-party attestation chain for a claim: the claimant's proof-graded claim (composes
    `record_claim`, S11 V1) followed by an ordered chain of attestations, each attestor vouching the claim as
    their own attested record (composes `record_contribution`, S10 V1, source `attestation`) that references
    the prior link. Each `attestor` is `{party, work_ref}`. Returns the chain, base claim first. The S11 fence
    refuses any extraction field; each attestation is a record its attestor owns and can verify."""
    if str(claim_class).strip().lower() not in CLAIM_CLASSES:
        raise IncomeRefused(f"unknown claim proof grade {claim_class!r} — {sorted(CLAIM_CLASSES)}")
    _fence(extra, "an attestation chain")
    base = record_claim(claimant, pool, work_ref, claim_class=claim_class, author=author, source_ref=source_ref,
                        at=at, registry=registry, amount=amount, gate=gate, extra=extra)
    chain: List[dict] = [base]
    for i, a in enumerate(attestors):
        party, a_work = str(a["party"]), str(a["work_ref"])
        rec = record_contribution(party, "attestation", a_work, contribution_class="attested",
                                  mandate=party, author=author, source_ref=source_ref, at=at, registry=registry,
                                  extra=_link_extra(work_ref, pool.pool_id, i))
        chain.append(rec)
    return chain


def _link_extra(claim_work_ref: str, pool_id: str, link_index: int) -> Dict[str, Any]:
    # a deterministic chain link: an attestation is bound to the claim, the pool, and its ordered position,
    # so a tampered or reordered chain fails verification (the position no longer matches).
    return {"attests_claim": str(claim_work_ref), "attests_pool": str(pool_id), "link_index": int(link_index)}


def verify_attestation_chain(chain: Sequence[Mapping[str, Any]], claimant: str, pool: Pool, work_ref: str, *,
                             claim_class: str, attestors: Sequence[Mapping[str, Any]],
                             amount: Any = None) -> bool:
    """Verify a whole attestation chain end to end: the base claim verifies as the claimant's own (composes
    `verify_claim`, S11 V1), and each attestation verifies as its attestor's own at its ordered position
    (composes `verify_contribution`, S10 V1). Deny-by-default: an empty chain, a wrong length, a reordered
    chain, or any link that does not verify fails the whole. A resourceless verifier confirms the entire chain
    from the receipts alone (weakest-party)."""
    if not chain or len(chain) != len(attestors) + 1:
        return False
    if not verify_claim(chain[0], claimant, pool, work_ref, claim_class=claim_class, amount=amount).provisioned:
        return False
    for i, a in enumerate(attestors):
        st = verify_contribution(chain[i + 1], str(a["party"]), str(a["work_ref"]),
                                 contribution_class="attested", source="attestation",
                                 extra=_link_extra(work_ref, pool.pool_id, i))
        if not st.provisioned:
            return False
    return True
