"""Double-entry posting + cost allocation — the financial-accounting invariants a governed ledger entry
must satisfy. Pure arithmetic over Decimal; no crypto substrate (runs in a pure public clone).

The immutability, governance (gate/mandate/receipt/time) and replay of a posting come from the existing
ObligationLedger + projection. This module is the layer that makes such a record a *general-ledger* posting
rather than a bare journal line: debits must equal credits (fail-closed), a trial balance nets to zero, and a
cost pool allocates across objects without creating or destroying value.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Mapping, Union

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


@dataclass(frozen=True)
class Line:
    """One line of a double-entry posting. Exactly one of debit/credit is non-zero (both >= 0)."""
    account: str
    debit: Decimal = field(default=Decimal("0"))
    credit: Decimal = field(default=Decimal("0"))

    @staticmethod
    def dr(account: str, amount: Number) -> "Line":
        return Line(account, debit=_dec(amount))

    @staticmethod
    def cr(account: str, amount: Number) -> "Line":
        return Line(account, credit=_dec(amount))


class UnbalancedPostingError(ValueError):
    """Raised when total debits != total credits — a posting that would break the ledger identity."""


class AllocationError(ValueError):
    """Raised when an allocation would create or destroy value (weights invalid, or residual != 0)."""


def validate_balanced(lines: List[Line]) -> None:
    """Fail-closed: total debits must equal total credits, and no line may carry both/neither side negative."""
    total_dr = Decimal("0")
    total_cr = Decimal("0")
    for ln in lines:
        d, c = _dec(ln.debit), _dec(ln.credit)
        if d < 0 or c < 0:
            raise UnbalancedPostingError(f"negative amount on account {ln.account!r} — dr={d} cr={c}")
        if d != 0 and c != 0:
            raise UnbalancedPostingError(f"line on {ln.account!r} carries both a debit and a credit")
        total_dr += d
        total_cr += c
    if total_dr != total_cr:
        raise UnbalancedPostingError(f"debits {total_dr} != credits {total_cr}")
    if total_dr == 0:
        raise UnbalancedPostingError("empty posting — no debits or credits")


def post(lines: List[Line], memo: str = "") -> Dict:
    """Validate a balanced double-entry posting and return its normalized, ledger-ready form.

    Does NOT itself persist — the caller records the returned dict on the immutable ObligationLedger, which
    supplies the hash chain, the approval gate, and the receipt. This function supplies the accounting truth:
    the posting balances, or it is refused."""
    validate_balanced(lines)
    total = sum((_dec(l.debit) for l in lines), Decimal("0"))
    return {
        "memo": memo,
        "lines": [{"account": l.account, "debit": str(_dec(l.debit)), "credit": str(_dec(l.credit))}
                  for l in lines],
        "amount": str(total),
        "balanced": True,
    }


def trial_balance(postings: List[Dict]) -> Dict[str, Decimal]:
    """Net movement per account across a set of balanced postings. The sum of all nets is exactly zero —
    the trial balance balances by construction, because every posting did."""
    nets: Dict[str, Decimal] = {}
    for p in postings:
        for ln in p["lines"]:
            nets[ln["account"]] = nets.get(ln["account"], Decimal("0")) + _dec(ln["debit"]) - _dec(ln["credit"])
    return nets


def allocate(pool: Number, weights: Mapping[str, Number]) -> Dict[str, Decimal]:
    """Allocate a cost pool across objects by weight, conserving value: the allocated amounts sum to the pool
    exactly (the largest-remainder method places any rounding residual, so nothing is created or lost)."""
    pool_d = _dec(pool)
    w = {k: _dec(v) for k, v in weights.items()}
    if not w:
        raise AllocationError("no allocation targets")
    total_w = sum(w.values(), Decimal("0"))
    if total_w <= 0:
        raise AllocationError(f"total weight must be > 0 (got {total_w})")
    if any(v < 0 for v in w.values()):
        raise AllocationError("negative weight")
    cents = Decimal("0.01")
    raw = {k: (pool_d * v / total_w) for k, v in w.items()}
    alloc = {k: r.quantize(cents) for k, r in raw.items()}
    residual = pool_d - sum(alloc.values(), Decimal("0"))
    if residual != 0:
        # largest-remainder: give the residual to the target with the biggest fractional part
        frac = {k: (raw[k] - alloc[k]) for k in raw}
        target = max(frac, key=lambda k: frac[k]) if residual > 0 else min(frac, key=lambda k: frac[k])
        alloc[target] += residual
    if sum(alloc.values(), Decimal("0")) != pool_d:
        raise AllocationError("allocation did not conserve the pool")  # defensive; should never trip
    return alloc
