"""Controlling primitives — Chart of Accounts, cost/profit centers, and value-conserving allocation across them.

Co-extrusion for s5_40 (Sovereign Controlling & Financial Close, KM CLOSE-do-not-defer 2026-08-03). Pure arithmetic
over Decimal, no crypto substrate (runs in a pure public clone, no skip — F-1 posture). This is the *controlling
floor*: a Chart of Accounts is a validated hierarchy, leaf balances roll up it conserving value, a cost pool
allocates across cost/profit centers conserving value exactly (composing the sealed `posting.allocate`), and a
center's costs total per currency without blending. The governance/immutability of the underlying postings comes
from the existing ObligationLedger + financials/posting; this module adds the controlling views over them.

Framing A (exists != wired): the *floor* here is PRESENT and tested. The fuller dimension-modeling engine and the
driver-model template library that would sit on this hierarchy are designed-toward THIS volume's own growth path —
not re-homed. Reporting packs (S5-V14), forecasting (S5-V17), bank connectivity (S6-V07), and consolidation
(S5-V18) are elsewhere and deliberately not here."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Mapping, Tuple, Union

from .posting import allocate

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class CoAError(ValueError):
    """Raised when a Chart of Accounts is structurally invalid — a missing parent, a cycle, or a balance for an
    account the chart does not define."""


def validate_coa(coa: Mapping[str, Mapping]) -> None:
    """Fail-closed validation of a Chart of Accounts as a governed hierarchy.

    Each account maps to metadata carrying an optional `parent` (an account id, or None for a root). A CoA is
    valid only if every named parent exists and no account's parent-chain forms a cycle — an unvalidated chart is
    a structure you cannot trust to roll up. (The dimension-modeling engine over this hierarchy is designed-toward;
    this is the constitutional structure it rests on.)"""
    if not coa:
        raise CoAError("empty chart of accounts")
    for acct, meta in coa.items():
        parent = meta.get("parent")
        if parent is not None and parent not in coa:
            raise CoAError(f"account {acct!r} names a missing parent {parent!r}")
    for acct in coa:
        seen = set()
        cur = acct
        while cur is not None:
            if cur in seen:
                raise CoAError(f"cycle in chart of accounts through {cur!r}")
            seen.add(cur)
            cur = coa[cur].get("parent")


def roll_up_accounts(leaf_balances: Mapping[str, Number], coa: Mapping[str, Mapping]) -> Dict[str, Decimal]:
    """Roll balances up the CoA hierarchy: each account's rolled balance is its own plus all its descendants'.

    Value-conserving: the sum over root accounts equals the sum of the supplied balances exactly, because each
    balance propagates up to exactly one root — nothing is created or lost. A balance for an account the chart
    does not define is refused (it would have nowhere to roll to)."""
    validate_coa(coa)
    for acct in leaf_balances:
        if acct not in coa:
            raise CoAError(f"balance for unknown account {acct!r}")
    rolled: Dict[str, Decimal] = {a: Decimal("0") for a in coa}
    for acct, bal in leaf_balances.items():
        b = _dec(bal)
        cur = acct
        while cur is not None:
            rolled[cur] += b
            cur = coa[cur].get("parent")
    return rolled


def allocate_cost_pool(pool: Number, centers: Mapping[str, Number]) -> Dict[str, Decimal]:
    """Distribute a shared cost pool across cost/profit centers by weight, conserving value exactly.

    A first-class controlling act composing the sealed value-conserving `allocate` primitive: the allocations sum
    to the pool (the largest-remainder method places any rounding residual, so nothing is created or lost). The
    driver-model *library* that would choose these weights from business drivers is designed-toward; here the
    weights are given."""
    return allocate(pool, centers)


def roll_up_center_costs(allocations: Iterable[Mapping]) -> Dict[Tuple[str, str], Decimal]:
    """Total cost per (center, currency) across many pool allocations — a cost-center cost view.

    Each allocation is a mapping with `center`, `amount`, and an optional `currency` (default USD). Currencies are
    never blended: a center's USD and EUR costs stay distinct totals, for the same reason treasury never nets
    across currencies — summing them would invent an exchange rate this module does not hold."""
    totals: Dict[Tuple[str, str], Decimal] = {}
    for a in allocations:
        key = (a["center"], a.get("currency", "USD"))
        totals[key] = totals.get(key, Decimal("0")) + _dec(a["amount"])
    return totals
