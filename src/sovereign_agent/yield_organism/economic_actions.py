"""economic_actions — the B4 wiring adapter: Breath-26 economic engines -> the receipted substrate.

Slice 2.1 (spec artifacts/specs/yield_organism_v0.1.yaml, the B4 Tiger half). This module WIRES the
extracted Breath-26 engines (yield_organism/engines/) onto the crypto-free ObligationLedger: an engine
COMPUTES an economic quantity (a constant-product swap output, a payout/recirc allocation) and this
adapter records it as a BALANCED set of dr/cr obligations — attribution, never payment.

HONEST SEAMS (stated up front — the whole point of the receipted organism is that a gap is NAMED, never
invented):

  · **money_path OFF, absolutely.** This adapter attributes value; it never moves it. There is
    deliberately NO transfer / settle / pay / disburse / wire / send method anywhere in this module.
    An AMM `pool.swap()` mutates the pool's OWN reserve model (the engine's internal state) — that is a
    computation, not a fund movement — and it runs ONLY on the sealed, receipted proceed path.

  · **Fee model + pool-balance bands are NOT implemented (Ch3 spec gap, register B3).** The extracted
    constant-product engine has NO fee and NO rebalancing bands, and this adapter invents neither. It
    therefore makes NO cross-denomination value-equality claim about a swap (that would require a price
    model / oracle the spec does not define). "Balanced" for a swap means the ledger's OWN dr/cr
    discipline — every debit leg (open) is matched by a credit leg (close), receipted — not a fabricated
    token_x==token_y valuation. The value-conservation that IS honest (a distribution's legs sum to the
    total drawn) is asserted for distributions, where the engine guarantees it.

  · **Token-typed schema (stake / reward / release) is AA's S4-G2 lane.** This module exposes the SEAM
    for it — `denomination_in` / `denomination_out` on a swap, `denomination` on a distribution, and the
    normalized `(recipient, amount)` allocation form — but does NOT build the typed substrate adapters.
    A downstream token-typed ledger plugs in behind these parameters without changing the wiring here.

  · **crypto-free.** No breathline_primitives dependency; any crypto site routes through the
    _sealed_host_seam adapter (none is needed to attribute value; this ring stands alone).

DECLARED-PARAMETER DISCIPLINE (fail-closed, no silent large moves): every gating bound is an OPERATOR-
DECLARED parameter with NO default that clears a large move. `threshold` (swap) and `approval_threshold`
(distribution) are REQUIRED keyword parameters — there is no hardcoded materiality constant. Above the
declared threshold the action is MATERIAL: it is recorded as a PROPOSED obligation that waits for a
human breath-gate (AH-1 idiom: the ledger's injected real gate + a named `approver`) and FAILS CLOSED
if unapproved. Below the threshold it still seals as receipted obligations (never a claim-only E0).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional, Sequence

from ..obligations import projection as _proj
from ..obligations.ledger import ObligationLedger


class EconomicActionRefused(PermissionError):
    """Fail-closed refusal to record an economic action — mirrors the ledger's PermissionError idiom
    (and ValueFlowRefused / ResumeRefused in the sibling rings).

    Raised for a bad engine input (loud, never a silent zero), a materially-gated action that has not
    cleared the human breath-gate (fail-closed unapproved), or a forced-unbalanced distribution. The
    adapter records value or it refuses — never fabricates a half-entry.
    """


def _dec(value) -> Decimal:
    """Coerce to an exact Decimal (evidence law — no float drift in any surfaced number)."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise EconomicActionRefused(f"not a decimal: {value!r}") from exc


def _receipt_hash(payload: dict) -> str:
    """Deterministic content hash (sha256) over a canonical payload — the E1/E2 verification material."""
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


# ── the balanced double-entry primitive: open (dr) + close (cr), or leave proposed + fail closed ──

@dataclass(frozen=True)
class ActionLeg:
    """One leg of a balanced economic action = one obligation (its dr=open, and cr=close when sealed).

    `side` names the accounting direction (debit = value attributed TO the principal; credit = value
    relinquished BY the principal). `receipt_id` is set only when the leg is sealed (closed). money_path
    is OFF: a leg attributes value, it never moves it.
    """
    side: str
    obligation_id: str
    title: str
    value: Decimal
    denomination: str
    material: bool
    receipt_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "side": self.side, "obligation_id": self.obligation_id, "title": self.title,
            "value": str(self.value), "denomination": self.denomination,
            "material": self.material, "receipt_id": self.receipt_id, "money_path": "OFF",
        }


def _open_leg(ledger: ObligationLedger, *, side: str, title: str, value: Decimal,
              denomination: str, principal: str, material: bool, category: str) -> ActionLeg:
    """Open one obligation (the debit) carrying the leg's attributed value in its lgp block."""
    ob = ledger.open(
        title, owner=principal, material=material,
        lgp={"economic_value": str(value), "denomination": denomination,
             "engine_category": category, "money_path": "OFF"},
        intent=f"{category}:{side}",
    )
    return ActionLeg(side=side, obligation_id=ob["id"], title=title, value=value,
                     denomination=denomination, material=material)


def _try_gate(ledger: ObligationLedger, legs: Sequence[ActionLeg], approver: Optional[str]) -> bool:
    """Attempt the human breath-gate for every material leg (AH-1 idiom: the ledger's injected real gate
    + a named approver). Returns True only when EVERY leg clears is_approved; any denial / absent
    approver is fail-closed False. Never self-approves — the ledger enforces AH-1."""
    if approver is None:
        return False  # no named human at the gate — a material action cannot proceed (fail-closed)
    for leg in legs:
        try:
            ledger.approve(leg.obligation_id, approved_by=approver)
        except PermissionError:
            return False  # gate DENIED (recorded on the chain by approve()) — fail-closed
    entries = list(ledger.iter_entries())
    return all(_proj.is_approved(entries, leg.obligation_id) for leg in legs)


def _seal_leg(ledger: ObligationLedger, leg: ActionLeg, evidence: str) -> ActionLeg:
    """Close the obligation (the credit) with an E1 hash-bearing receipt — the leg's dr/cr pair completes."""
    credit = ledger.close(leg.obligation_id, evidence=evidence, evidence_tier="E1")
    receipt_id = (credit.get("receipt") or {}).get("receipt_id")
    return ActionLeg(side=leg.side, obligation_id=leg.obligation_id, title=leg.title,
                     value=leg.value, denomination=leg.denomination, material=leg.material,
                     receipt_id=receipt_id)


def ledger_leg_balance(ledger: ObligationLedger, obligation_ids: Iterable[str]) -> tuple[int, int]:
    """Count (debit_entries, credit_entries) on the chain for the given obligation ids — the ledger-level
    balance proof. A sealed balanced action has debit_entries == credit_entries (every open was closed);
    a proposed-but-unsealed (fail-closed) action has credit_entries < debit_entries (legs left open)."""
    ids = set(obligation_ids)
    entries = list(ledger.iter_entries())
    debits = sum(1 for e in entries if e.get("type") == "debit" and e.get("id") in ids)
    credits = sum(1 for e in entries if e.get("type") == "credit" and e.get("closes") in ids)
    return debits, credits


# ═══════════════════════════════ swap wiring (constant-product engine) ═══════════════════════════════

@dataclass(frozen=True)
class SwapRecord:
    """A constant-product swap, recorded as a balanced dr/cr pair of receipted obligations.

    money_path OFF: the record attributes the swapped value; it moves nothing. NO cross-denomination
    value-equality is claimed (fee model / price oracle is spec gap B3 — deliberately absent). `balanced`
    here is the ledger's dr/cr discipline: two legs (out=debit, in=credit), each opened and — when
    sealed — closed with a receipt.
    """
    amount_in: Decimal
    amount_out: Decimal
    k: Decimal
    denomination_in: str
    denomination_out: str
    material: bool
    sealed: bool
    legs: tuple
    money_path: str = "OFF"

    @property
    def obligation_ids(self) -> tuple:
        return tuple(leg.obligation_id for leg in self.legs)

    @property
    def balanced(self) -> bool:
        """A sealed swap balances when every leg (debit=open) carries a credit=close receipt; the two
        legs (out + in) are the dr/cr pair. (The fee/price gap means NO token_x==token_y claim is made.)"""
        if not self.sealed:
            return False
        return len(self.legs) == 2 and all(leg.receipt_id for leg in self.legs)

    def to_dict(self) -> dict:
        return {
            "amount_in": str(self.amount_in), "amount_out": str(self.amount_out), "k": str(self.k),
            "denomination_in": self.denomination_in, "denomination_out": self.denomination_out,
            "material": self.material, "sealed": self.sealed, "balanced": self.balanced,
            "legs": [leg.to_dict() for leg in self.legs], "money_path": self.money_path,
            "honest_seam": "fee/pool-balance-bands NOT implemented (Ch3 spec gap B3); no x==y value claim",
        }


def swap_via_pool(ledger: ObligationLedger, pool, amount_in, *, threshold, principal: str,
                  denomination_in: str = "TOKEN_X", denomination_out: str = "TOKEN_Y",
                  approver: Optional[str] = None, commit_pool: bool = True) -> SwapRecord:
    """Compute a constant-product swap via the engine, then record it as a BALANCED dr/cr pair.

    `threshold` is a REQUIRED, operator-declared materiality bound (no default that silently clears a
    large move). When amount_in > threshold the swap is MATERIAL: it is recorded as PROPOSED obligations
    and must clear the human breath-gate (a named `approver` acting through the ledger's injected real
    gate, AH-1); unapproved, it FAILS CLOSED (EconomicActionRefused) with the proposed obligations left
    open on the chain, and the pool is NOT mutated. Below the threshold it seals as receipted obligations.

    money_path OFF: `pool.swap()` mutates only the engine's own reserve model, and only on the sealed
    proceed path. The fee model / pool-balance bands are the documented spec gap (B3) — absent here.
    """
    amount_in = _dec(amount_in)
    threshold = _dec(threshold)  # DECLARED — the caller states the materiality bound explicitly
    # Compute the output WITHOUT mutating the pool (pure) — a bad input is refused loudly, never a zero.
    try:
        amount_out = pool.calculate_output_amount(amount_in)
    except (ValueError, ArithmeticError) as exc:
        raise EconomicActionRefused(f"swap refused by the constant-product engine: {exc}") from exc

    material = amount_in > threshold
    # Book the balanced pair: out-leg (debit = value attributed) + in-leg (credit = value relinquished).
    out_leg = _open_leg(ledger, side="debit",
                        title=f"amm swap-out {amount_out} {denomination_out}", value=amount_out,
                        denomination=denomination_out, principal=principal, material=material,
                        category="amm_swap")
    in_leg = _open_leg(ledger, side="credit",
                       title=f"amm swap-in {amount_in} {denomination_in}", value=amount_in,
                       denomination=denomination_in, principal=principal, material=material,
                       category="amm_swap")
    legs = [out_leg, in_leg]

    if material and not _try_gate(ledger, legs, approver):
        # FAIL CLOSED: the proposed obligations stay OPEN on the chain (awaiting a real disposition);
        # nothing seals and the pool is untouched. The refusal names the proposed cylinders.
        raise EconomicActionRefused(
            f"swap of {amount_in} > declared threshold {threshold} is MATERIAL and has not cleared the "
            f"human breath-gate (AH-1 fail-closed) — proposed obligations {[l.obligation_id for l in legs]} "
            f"remain open; supply a named approver acting through the ledger's real gate to proceed"
        )

    # Proceed: seal both legs (dr/cr pair complete, receipted) and commit the engine's reserve update.
    evidence_base = {"engine": "constant_product_amm", "amount_in": str(amount_in),
                     "amount_out": str(amount_out), "k": str(pool.k), "invariant": "x*y=k"}
    sealed_legs = tuple(
        _seal_leg(ledger, leg,
                  evidence=f"amm-swap {leg.side} {leg.value} {leg.denomination} "
                           f"sha256:{_receipt_hash({**evidence_base, 'leg': leg.side})}")
        for leg in legs
    )
    k = pool.k
    if commit_pool:
        pool.swap(amount_in)  # engine-internal reserve update (computation, not a fund movement)
    return SwapRecord(amount_in=amount_in, amount_out=amount_out, k=k,
                      denomination_in=denomination_in, denomination_out=denomination_out,
                      material=material, sealed=True, legs=sealed_legs)


# ═══════════════════════════════ distribution wiring (payout / recirc engines) ═══════════════════════

@dataclass(frozen=True)
class DistributionRecord:
    """A payout / recirc distribution, recorded as balanced distribution obligations.

    Unlike a swap, a distribution's legs share ONE denomination, so value-conservation IS honest and is
    asserted: the legs sum to the total drawn (`balanced`). money_path OFF: the record attributes each
    allocation; it moves nothing.
    """
    total: Decimal
    denomination: str
    material: bool
    sealed: bool
    legs: tuple
    money_path: str = "OFF"

    @property
    def obligation_ids(self) -> tuple:
        return tuple(leg.obligation_id for leg in self.legs)

    @property
    def legs_sum(self) -> Decimal:
        return sum((leg.value for leg in self.legs), Decimal("0"))

    @property
    def balanced(self) -> bool:
        """Value-conserving: the distribution legs sum EXACTLY to the total drawn (single denomination),
        and — when sealed — every leg carries a close receipt."""
        if self.legs_sum != self.total:
            return False
        if not self.sealed:
            return False
        return all(leg.receipt_id for leg in self.legs)

    def to_dict(self) -> dict:
        return {
            "total": str(self.total), "denomination": self.denomination, "material": self.material,
            "sealed": self.sealed, "balanced": self.balanced, "legs_sum": str(self.legs_sum),
            "legs": [leg.to_dict() for leg in self.legs], "money_path": self.money_path,
        }


def payout_allocations(mint_engine) -> list[tuple[str, Decimal]]:
    """Normalize a MintEngine's generated payouts to the seam form `[(recipient, amount)]` (Decimal)."""
    return [(p["principal_id"], _dec(p["amount"])) for p in mint_engine.generate_payouts()]


def recirc_allocations(allocator) -> list[tuple[str, Decimal]]:
    """Normalize a RecircAllocator's post-allocate band balances to `[(band, amount)]` for the non-DAO
    bands (the DAO band is the SOURCE drawn down — not a distribution destination)."""
    return [(name, _dec(bal)) for name, bal in allocator.get_balances().items()
            if name != "DAO" and _dec(bal) != 0]


def _normalize_allocations(engine_result) -> list[tuple[str, Decimal]]:
    """Accept the seam form `[(recipient, amount)]`, a MintEngine payout list `[{principal_id, amount}]`,
    or a band-balance dict `{name: amount}`; return the normalized `[(recipient, Decimal)]`."""
    if isinstance(engine_result, dict):
        return [(str(k), _dec(v)) for k, v in engine_result.items()]
    out: list[tuple[str, Decimal]] = []
    for item in engine_result:
        if isinstance(item, dict):
            out.append((str(item.get("principal_id") or item.get("name") or item.get("recipient")),
                        _dec(item["amount"])))
        else:
            recipient, amount = item
            out.append((str(recipient), _dec(amount)))
    return out


def distribute_via_payout(ledger: ObligationLedger, engine_result, *, principal: str,
                          approval_threshold, floor=None, cap=None,
                          denomination: str = "units", approver: Optional[str] = None,
                          total: Optional[object] = None) -> DistributionRecord:
    """Record a payout/recirc distribution as balanced distribution obligations (attribution, not payment).

    `approval_threshold` is a REQUIRED, operator-declared bound: when the distribution TOTAL exceeds it
    the distribution is MATERIAL and human-gated (same AH-1 fail-closed discipline as a swap). `floor`
    and `cap` are OPTIONAL operator-declared per-recipient bounds — a leg below `floor` or above `cap`
    is REFUSED loudly (never silently clamped; e.g. the senior $25 payout floor). `total`, if supplied,
    is a DECLARED expected total: a mismatch against the summed legs is a forced-unbalanced input and is
    refused loudly (the negative-control guard). money_path OFF absolutely.
    """
    approval_threshold = _dec(approval_threshold)  # DECLARED materiality bound (no silent default)
    floor_d = _dec(floor) if floor is not None else None
    cap_d = _dec(cap) if cap is not None else None
    allocations = _normalize_allocations(engine_result)
    if not allocations:
        raise EconomicActionRefused("no allocations to distribute — an empty distribution is refused, "
                                    "never a silent zero")
    computed_total = sum((amt for _, amt in allocations), Decimal("0"))
    # Negative control: a declared total that does not equal the summed legs is a forced-unbalanced input.
    if total is not None and _dec(total) != computed_total:
        raise EconomicActionRefused(
            f"distribution is UNBALANCED: declared total {total} != summed legs {computed_total} — "
            f"a distribution's legs must conserve value (refused loudly, never booked)"
        )
    for recipient, amount in allocations:
        if amount < 0:
            raise EconomicActionRefused(
                f"allocation to '{recipient}' is {amount} < 0 — a distribution attributes value, not debt")
        if floor_d is not None and amount < floor_d:
            raise EconomicActionRefused(
                f"allocation to '{recipient}' is {amount} < declared floor {floor_d} — refused loudly "
                f"(a below-floor distribution is never silently booked)")
        if cap_d is not None and amount > cap_d:
            raise EconomicActionRefused(
                f"allocation to '{recipient}' is {amount} > declared cap {cap_d} — refused loudly "
                f"(an over-cap distribution is never silently clamped)")

    material = computed_total > approval_threshold
    legs = [
        _open_leg(ledger, side="debit", title=f"distribution to {recipient}: {amount} {denomination}",
                  value=amount, denomination=denomination, principal=principal, material=material,
                  category="distribution")
        for recipient, amount in allocations
    ]

    if material and not _try_gate(ledger, legs, approver):
        raise EconomicActionRefused(
            f"distribution total {computed_total} > declared approval_threshold {approval_threshold} is "
            f"MATERIAL and has not cleared the human breath-gate (AH-1 fail-closed) — proposed obligations "
            f"{[l.obligation_id for l in legs]} remain open; supply a named approver acting through the "
            f"ledger's real gate to proceed"
        )

    sealed_legs = tuple(
        _seal_leg(ledger, leg,
                  evidence=f"distribution {leg.value} {leg.denomination} to {leg.title} "
                           f"sha256:{_receipt_hash({'recipient': leg.title, 'value': str(leg.value), 'denomination': denomination})}")
        for leg in legs
    )
    return DistributionRecord(total=computed_total, denomination=denomination, material=material,
                              sealed=True, legs=sealed_legs)
