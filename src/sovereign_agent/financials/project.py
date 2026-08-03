"""Project budget/cost governance — the budget views a governed project ledger must satisfy.

Co-extrusion for s5_11 (Project & Portfolio Management, KM GO WAVE 2026-08-03). Pure arithmetic over Decimal, no
crypto substrate (pure-clone-clean, F-1 posture). Budget status compares a project's budget against committed and
actual cost (both governed obligations/postings on the immutable ledger), reporting consumption, remaining, and an
honest over-budget flag — so a project's financial position is a fact, not an assertion. A portfolio roll-up sums
per-project budget status without blending currencies. Governance/immutability of a project, task, or cost = the
existing ObligationLedger + object model + financials/posting; planning and scheduling stay designed-toward."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Mapping, Union

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def budget_status(budget: Number, committed: Number, actual: Number) -> Dict[str, object]:
    """A project's budget position: consumed (committed + actual), remaining, over-budget flag, variance.

    Committed = approved-but-unspent obligations; actual = spent. The position is a fact computed from governed
    records, not a forecast: it reports the real over-budget condition rather than a hopeful projection. Negative
    inputs are refused — a budget, commitment, or actual below zero is a data error, not a valid position."""
    b, c, a = _dec(budget), _dec(committed), _dec(actual)
    if b < 0 or c < 0 or a < 0:
        raise ValueError("budget, committed and actual must be non-negative")
    consumed = c + a
    remaining = b - consumed
    return {
        "budget": b,
        "committed": c,
        "actual": a,
        "consumed": consumed,
        "remaining": remaining,
        "over_budget": remaining < 0,
        "overrun": (-remaining) if remaining < 0 else Decimal("0"),
    }


def portfolio_roll_up(projects: Iterable[Mapping], currency: str = "USD") -> Dict[str, object]:
    """Roll up per-project budget status to a portfolio total for one currency (currencies are not blended).

    Each project is a mapping with budget/committed/actual (same currency). The roll-up is a sum of governed
    positions, and the count of over-budget projects is surfaced rather than hidden inside a net figure."""
    tot_b = tot_c = tot_a = Decimal("0")
    over = 0
    n = 0
    for p in projects:
        st = budget_status(p["budget"], p.get("committed", 0), p.get("actual", 0))
        tot_b += st["budget"]; tot_c += st["committed"]; tot_a += st["actual"]
        over += 1 if st["over_budget"] else 0
        n += 1
    consumed = tot_c + tot_a
    return {
        "currency": currency,
        "projects": n,
        "budget": tot_b,
        "consumed": consumed,
        "remaining": tot_b - consumed,
        "over_budget_projects": over,
    }
