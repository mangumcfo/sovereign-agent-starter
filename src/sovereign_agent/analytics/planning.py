"""Planning — transparent net requirements, capacity scheduling, and priority allocation. No hidden solver.

Co-extrusion for s5_17 (Analytics & Decision Intelligence, KM Option B 2026-08-03). Pure arithmetic over Decimal, no
crypto substrate (runs in a pure public clone, no skip — F-1 posture). This discharges the planning/scheduling/
optimization debt the sealed wave homed here (supply demand planning, manufacturing production planning & scheduling,
project planning & resource/portfolio optimization): a net requirement is demand minus available on-hand, a schedule
packs jobs into periods by a transparent capacity rule ordered by due/priority, and a scarce supply allocates across
prioritized demands fill-first, value-conserving. Every rule is named and reproducible — a planner can re-derive the
plan, not accept a black-box optimizer's output."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Mapping, Union

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class PlanningError(ValueError):
    """Raised for a negative demand/on-hand/capacity, or a malformed job/demand."""


def net_requirements(demand: Mapping[str, Number], on_hand: Mapping[str, Number]) -> Dict[str, Decimal]:
    """Net requirement per item: demand minus available on-hand, floored at zero (never a negative requirement).

    An MRP primitive made governed: the requirement is computed from the demand and the on-hand the ledger holds, so a
    build or purchase is planned against provable stock, not a maintained figure that can go phantom."""
    out: Dict[str, Decimal] = {}
    for item, d in demand.items():
        dd = _dec(d)
        oh = _dec(on_hand.get(item, 0))
        if dd < 0 or oh < 0:
            raise PlanningError(f"demand and on-hand must be non-negative for {item!r}")
        net = dd - oh
        out[item] = net if net > 0 else Decimal("0")
    return out


def schedule(jobs: List[Mapping], capacity_per_period: Number) -> Dict[str, object]:
    """Pack jobs into periods by a transparent capacity rule: jobs are ordered by `due` then `priority`, then filled
    greedily into periods each holding `capacity_per_period` units of work.

    No hidden solver: the ordering rule is named and the packing is deterministic, so a planner re-derives the same
    schedule. A job whose size exceeds a whole period's capacity is refused (it cannot be scheduled by this rule)."""
    cap = _dec(capacity_per_period)
    if cap <= 0:
        raise PlanningError("capacity_per_period must be > 0")
    ordered = sorted(jobs, key=lambda j: (j.get("due", 0), -_priority(j)))
    periods: List[List[str]] = [[]]
    used = [Decimal("0")]
    for j in ordered:
        size = _dec(j["units"])
        if size <= 0:
            raise PlanningError(f"job {j.get('id')!r} has non-positive units")
        if size > cap:
            raise PlanningError(f"job {j.get('id')!r} ({size}) exceeds one period's capacity ({cap})")
        placed = False
        for p in range(len(periods)):
            if used[p] + size <= cap:
                periods[p].append(j["id"]); used[p] += size; placed = True; break
        if not placed:
            periods.append([j["id"]]); used.append(size)
    return {"capacity_per_period": cap, "periods": periods,
            "used_per_period": used, "job_order": [j["id"] for j in ordered]}


def _priority(j: Mapping) -> Decimal:
    return _dec(j.get("priority", 0))


def allocate_by_priority(supply: Number, demands: List[Mapping]) -> Dict[str, object]:
    """Allocate a scarce supply across prioritized demands, fill-first in the given order, value-conserving.

    `demands` is an ordered list (highest priority first) of {id, qty}. Each demand is filled as far as the remaining
    supply allows; the total allocated never exceeds the supply, and any unmet demand and leftover supply are reported.
    A transparent, re-derivable allocation -- the 'optimization' done as a named priority rule, not a black box."""
    remaining = _dec(supply)
    if remaining < 0:
        raise PlanningError("supply must be non-negative")
    alloc: Dict[str, Decimal] = {}
    unmet: Dict[str, Decimal] = {}
    for d in demands:
        want = _dec(d["qty"])
        if want < 0:
            raise PlanningError(f"demand {d.get('id')!r} has negative qty")
        give = want if want <= remaining else remaining
        alloc[d["id"]] = give
        remaining -= give
        if give < want:
            unmet[d["id"]] = want - give
    return {"supply": _dec(supply), "allocated": alloc, "unmet": unmet, "leftover": remaining}
