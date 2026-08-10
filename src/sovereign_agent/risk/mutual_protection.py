# -*- coding: utf-8 -*-
"""risk.mutual_protection — Sovereign Risk & Mutual Protection (Series 11, Vol 1, the OPENER:
Insurance, Credit & Reputation Without Extraction).

Insurance, credit, and reputation are the three levers an extractive middle pulls hardest: an insurer that
owns your risk and rations protection back, a credit bureau that owns your history and gates your access, a
reputation-scorer that owns your standing and sells it. This opener builds the sovereign alternative on the
same receipted rails as the rest of the stack — **mutual protection as a receipted pool, claims as proof-graded
records, credit as your own portable receipt history, and reputation as accumulated verified receipts** — and
it **composes the sealed floors, inventing no new engine**. A premium is a receipted obligation the member owns
(composing the sealed pool + income record, S10 V1/V2); a claim is a proof-graded record the claimant owns and
verifies from a receipt they hold; a claim **settles only through the sealed Port** (S6 V7), never in-node;
credit is a portable history assembled from a member's own verified receipts; reputation is a tally of verified
contributions, not a score; and **reputation-weighted matching** (the F1 beat, honoring S10 V2's ×11 mutual-
matching commitment homed here) ranks parties by their count of *verified* receipts — transparent, never an
issued authority.

**The S11 SERIES FENCE (every S11 volume; enforced here in code — `RISK_BREACH_FIELDS`):**
1. **claims settle via the Port only** — `settle_claim` composes the sealed `pool_settlement`; no in-node claim
   settlement, no reserve, no netting;
2. **no in-node pool custody** — a protection pool holds/nets/settles nothing internally (inherits the sealed
   pool-fence);
3. **credit = portable receipt history, NEVER issuance** — `credit_history` assembles a member's own verified
   receipts; it issues no credit, sets no limit, lends nothing;
4. **reputation ≠ token/score authority** — `reputation_package` is a tally of verified receipts, not a scored
   or issued standing;
5. **no underwriting engine** — no in-node underwriting or risk-pricing authority; any such field is refused;
6. **money-path OFF** — record and attribute only; value rides the sealed Port;
7. **weakest-party** — a claimant/member with no second device verifies their claim, premium, credit, or
   reputation from a receipt they hold.

KILL-TARGET: the insurer / credit-bureau / reputation-scorer that owns your risk, your credit, and your
standing — and rations them back — refused. NO TOKEN · no yield · holds no value · rolls no cryptography.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ..economy.pool import (form_pool, contribute_to_pool, verify_pool_contribution, pool_settlement,
                            Pool, PoolSettlement)                                   # S10 V2 (composes V1)
from ..economy.contribution import (record_contribution, verify_contribution,
                                    IncomeRefused, IncomeStatus)                     # S10 V1

__all__ = ["form_protection_pool", "record_premium", "verify_premium", "record_claim", "verify_claim",
           "settle_claim", "credit_history", "reputation_package", "match_by_reputation",
           "CreditHistory", "ReputationPackage", "CLAIM_CLASSES", "RISK_BREACH_FIELDS",
           "IncomeRefused", "IncomeStatus", "Pool", "PoolSettlement"]

# A claim carries a proof GRADE, never a bare meter: attested (a person attests), computed (a device/rule
# computes), or hybrid. An unknown grade is refused (deny-by-default).
CLAIM_CLASSES = frozenset({"attested", "computed", "hybrid"})

# THE S11 SERIES FENCE, in code: any field that would make the node an insurer/bureau/scorer — an in-node
# custody/reserve/settlement, an underwriting/risk-pricing authority, a credit issuance, or a reputation score
# — is refused. Mutual protection records and attributes; it never owns and rations back.
RISK_BREACH_FIELDS = frozenset({
    "custody", "pool_balance", "reserve", "reserves", "netting", "in_node_settlement", "settle_in_node",
    "underwrite", "underwriting", "risk_price", "risk_pricing", "premium_rate", "rate_engine",
    "issue_credit", "credit_issuance", "credit_limit", "lend", "loan", "extend_credit",
    "reputation_score", "rep_score", "rating", "credit_score", "score_authority",
})


def _fence(mapping: Optional[Mapping[str, Any]], where: str) -> None:
    """THE S11 FENCE: refuse any field that would make the node an insurer/bureau/scorer."""
    for k in (mapping or {}):
        if str(k).lower() in RISK_BREACH_FIELDS:
            raise IncomeRefused(
                f"{where} must carry no risk-extraction field ('{k}') — the node records and attributes; it "
                f"holds no custody/reserve, runs no underwriting, issues no credit, and scores no reputation "
                f"(S11 fence). Value settles only via the sealed Port.")


def form_protection_pool(pool_id: str, members: Sequence[str]) -> Pool:
    """Form a mutual PROTECTION pool — who is in a risk-sharing circle. Composes the sealed pool (S10 V2): it
    holds no value, has no balance, appoints no custodian, and needs at least two members (a pool of one
    protects no one). The protection is the members' mutual, receipted obligation, not a fund the node holds."""
    return form_pool(pool_id, members)


def record_premium(pool: Pool, member: str, work_ref: str, *, contribution_class: str, author: str,
                   source_ref: str, at: str, registry: Any, mandate: Optional[str] = None, amount: Any = None,
                   unit: str = "credits", port_ref: Optional[str] = None,
                   extra: Optional[Mapping[str, Any]] = None, approver: Optional[str] = None,
                   approval_ref: Optional[str] = None, gate: Any = None,
                   role_spec: Optional[Mapping[str, Any]] = None, mode: str = "live") -> dict:
    """Record a premium as a **receipted obligation the member OWNS**, contributed into the protection pool
    (composes `contribute_to_pool`, S10 V2 → V1). The premium is a proof-graded, owned record — not a payment
    into a fund the node holds. Money-path OFF inherited (the premium is an attribution; value rides the Port).
    The S11 fence refuses any custody/underwriting/issuance field. Returns the member's receipt."""
    _fence(extra, "a premium")
    return contribute_to_pool(pool, member, "premium", work_ref, contribution_class=contribution_class,
                              author=author, source_ref=source_ref, at=at, registry=registry, mandate=mandate,
                              amount=amount, unit=unit, port_ref=port_ref, extra=extra, approver=approver,
                              approval_ref=approval_ref, gate=gate, action_class="record_premium",
                              role_spec=role_spec, mode=mode)


def verify_premium(receipt: Mapping[str, Any], pool: Pool, member: str, work_ref: str, *,
                   contribution_class: str, amount: Any = None, unit: str = "credits",
                   port_ref: Optional[str] = None, extra: Optional[Mapping[str, Any]] = None) -> IncomeStatus:
    """Weakest-party check: a member confirms their premium — a receipted obligation into this pool — from the
    receipt they hold (composes `verify_pool_contribution`, S10 V2). No platform, no second device."""
    return verify_pool_contribution(receipt, pool, member, "premium", work_ref,
                                    contribution_class=contribution_class, amount=amount, unit=unit,
                                    port_ref=port_ref, extra=extra)


def _claim_extra(pool_id: str, extra: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    ex = dict(extra or {})
    ex["pool"] = pool_id
    ex["claim"] = True
    return ex


def record_claim(claimant: str, pool: Pool, work_ref: str, *, claim_class: str, author: str, source_ref: str,
                 at: str, registry: Any, mandate: Optional[str] = None, amount: Any = None,
                 unit: str = "credits", port_ref: Optional[str] = None,
                 extra: Optional[Mapping[str, Any]] = None, approver: Optional[str] = None,
                 approval_ref: Optional[str] = None, gate: Any = None,
                 role_spec: Optional[Mapping[str, Any]] = None, mode: str = "live") -> dict:
    """Record a claim against the protection pool as a **proof-graded record the claimant OWNS** (composes
    `record_contribution`, S10 V1, source `claim`, tagged with the pool). The claim carries a proof grade —
    attested, computed, or hybrid — so it can be verified, not merely asserted; an unknown grade is refused.
    The claim RECORDS the event; the payout SETTLES only via `settle_claim` → the Port. The S11 fence refuses
    any underwriting/custody/issuance field. A material claim passes a human (the sealed gate). Returns the
    claimant's receipt."""
    if str(claim_class).strip().lower() not in CLAIM_CLASSES:
        raise IncomeRefused(
            f"unknown claim proof grade {claim_class!r} — a claim is {sorted(CLAIM_CLASSES)} (attested by a "
            f"person, computed by a device/rule, or hybrid); a claim is proof-graded, never merely asserted")
    _fence(extra, "a claim")
    return record_contribution(claimant, "claim", work_ref, contribution_class=claim_class,
                               mandate=(mandate or claimant), author=author, source_ref=source_ref, at=at,
                               registry=registry, amount=amount, unit=unit, port_ref=port_ref,
                               extra=_claim_extra(pool.pool_id, extra), approver=approver,
                               approval_ref=approval_ref, gate=gate, action_class="record_claim",
                               role_spec=role_spec, mode=mode)


def verify_claim(receipt: Mapping[str, Any], claimant: str, pool: Pool, work_ref: str, *, claim_class: str,
                 amount: Any = None, unit: str = "credits", port_ref: Optional[str] = None,
                 extra: Optional[Mapping[str, Any]] = None) -> IncomeStatus:
    """Weakest-party check: a claimant with no second device and no expertise confirms their claim — its proof
    grade and the pool it is against — from the receipt they hold (composes `verify_contribution`, S10 V1). A
    tampered grade, pool, or amount flips the light. The claim is the claimant's own and provably unaltered —
    exactly what an honest mutual-aid pool rewards."""
    return verify_contribution(receipt, claimant, work_ref, contribution_class=claim_class, source="claim",
                               amount=amount, unit=unit, port_ref=port_ref,
                               extra=_claim_extra(pool.pool_id, extra))


def settle_claim(pool: Pool, claimant: str, share: Any, *, port_ref: Optional[str] = None) -> PoolSettlement:
    """Settle a verified claim back to the claimant **only through the sealed Port** — a single per-member Port
    directive (composes `pool_settlement`, S10 V2). The settlement holds NO value, does NO netting, keeps NO
    reserve, and performs NO in-node settlement: the S11 fence (inheriting the sealed pool-fence) refuses any
    in-node pool-value field. `share` may be a mapping carrying its own `port_ref`, or `port_ref` is supplied.
    The node instructs the Port; it never holds or releases the funds."""
    if isinstance(share, Mapping):
        _fence(share, "a claim settlement")
        member_share: Any = share
    else:
        member_share = {"share": share, "port_ref": port_ref}
    return pool_settlement(pool, [(claimant, member_share)])


@dataclass(frozen=True)
class CreditHistory:
    """A member's PORTABLE credit history: their own verified receipts, assembled into a record they carry —
    NOT a bureau file, NOT a score, and NOT an issuance. It issues no credit, sets no limit, and lends nothing;
    it is complete only when every receipt in it verifies as the member's own. Credit here is proof you hold,
    not access an authority grants."""
    member: str
    complete: bool
    verified_count: int
    reason: str = "a portable history of your own verified receipts — issues nothing"


def credit_history(member: str, records: Sequence[Mapping[str, Any]]) -> CreditHistory:
    """Assemble a member's PORTABLE credit history from their OWN verified receipts (composes
    `verify_contribution`, S10 V1, over each record `{receipt, work_ref, contribution_class, source, ...}`).
    Complete iff every record verifies as the member's own — a foreign or tampered record breaks it. It ISSUES
    NO credit, sets no limit, and holds no value (the S11 fence): credit is a portable history you carry to a
    lender, not a line the node extends. Deny-by-default: an empty history is not complete."""
    verified = 0
    reason: List[str] = []
    for i, rec in enumerate(records):
        _fence(rec, "a credit-history record")
        st = verify_contribution(rec["receipt"], member, rec["work_ref"],
                                 contribution_class=rec["contribution_class"], source=rec["source"],
                                 amount=rec.get("amount"), unit=rec.get("unit", "credits"),
                                 port_ref=rec.get("port_ref"), extra=rec.get("extra"))
        if not st.provisioned:
            reason.append(f"record {i} ({rec.get('source')}) does not verify as {member}'s own: {st.reason}")
            continue
        verified += 1
    ok = bool(records) and not reason
    return CreditHistory(member=member, complete=ok, verified_count=verified,
                         reason="; ".join(reason) or "a portable history of your own verified receipts — issues nothing")


@dataclass(frozen=True)
class ReputationPackage:
    """Reputation as accumulated VERIFIED receipts: a tally of a party's own verified contributions, by proof
    grade — NOT a score, NOT a rating, NOT an issued standing. The `reputation_weight` is simply how many of
    the party's receipts verify; it is transparent and re-derivable, never an authority's number. Reputation
    here is earned proof you carry, not a standing someone else owns and sells."""
    party: str
    reputation_weight: int
    verified_count: int
    by_class: Dict[str, int] = field(default_factory=dict)
    reason: str = "reputation is a tally of your own verified receipts — not a score"


def reputation_package(party: str, records: Sequence[Mapping[str, Any]]) -> ReputationPackage:
    """Assemble a party's reputation as accumulated VERIFIED receipts (composes `verify_contribution`, S10 V1,
    over each record), tallied by proof grade. The `reputation_weight` is the count of receipts that verify as
    the party's own — a transparent, re-derivable number, NOT a score or issued authority (the S11 fence
    refuses any score/rating field). Reputation is proof the party carries, not a standing an authority owns."""
    by_class: Dict[str, int] = {}
    verified = 0
    for rec in records:
        _fence(rec, "a reputation record")
        st = verify_contribution(rec["receipt"], party, rec["work_ref"],
                                 contribution_class=rec["contribution_class"], source=rec["source"],
                                 amount=rec.get("amount"), unit=rec.get("unit", "credits"),
                                 port_ref=rec.get("port_ref"), extra=rec.get("extra"))
        if st.provisioned:
            verified += 1
            by_class[rec["contribution_class"]] = by_class.get(rec["contribution_class"], 0) + 1
    return ReputationPackage(party=party, reputation_weight=verified, verified_count=verified, by_class=by_class)


def match_by_reputation(candidates: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Reputation-weighted matching (the F1 beat, honoring S10 V2's ×11 mutual-matching commitment homed here):
    rank parties by their reputation weight — the count of their OWN verified receipts — most-proven first.
    Each candidate is `{party, records}`; the weight is computed transparently by `reputation_package` (verified
    receipts only), so the ranking is re-derivable by anyone and is NOT an issued score or a scoring authority
    (the S11 fence). A tie holds input order (stable). Matching rewards proven mutual contribution, not a number
    someone sells you."""
    ranked: List[Dict[str, Any]] = []
    for i, c in enumerate(candidates):
        rep = reputation_package(c["party"], c.get("records", []))
        ranked.append({"party": c["party"], "reputation_weight": rep.reputation_weight,
                       "verified_count": rep.verified_count, "_order": i})
    ranked.sort(key=lambda r: (-r["reputation_weight"], r["_order"]))
    for r in ranked:
        del r["_order"]
    return ranked
