"""Revenue recognition — a value-conserving schedule by a named method.

Co-extrusion for s5_15 (Revenue & Order-to-Cash). Pure arithmetic over Decimal, no crypto substrate (F-1
pure-clone-clean). Revenue recognition spreads a contract's value across time by a NAMED method -- recognized at a
point in time, ratably over N periods, or as milestones complete -- and it is value-conserving by construction: the
amounts recognized over the schedule sum EXACTLY to the contract value, and at every point recognized plus deferred
equals the contract value. The schedule is a derived projection carrying its method and inputs, re-runnable -- not a
maintained deferral table. A method this volume does not implement is refused, and milestones that over-recognize
(sum to more than the contract) are refused, not silently truncated -- an honest recognition names its method, or it
declines."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Sequence, Tuple, Union

Number = Union[int, float, str, Decimal]

POINT_IN_TIME = "point_in_time"
RATABLE = "ratable"
MILESTONE = "milestone"
_CENTS = Decimal("0.01")


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class RecognitionError(ValueError):
    """Raised for a non-positive contract value, an unknown method, a bad period count, or over-recognizing milestones."""


def _finalize(total: Decimal, amounts: List[Decimal]) -> List[Decimal]:
    """Make the recognized amounts conserve value exactly: the final period absorbs the rounding residual."""
    amounts = [a.quantize(_CENTS) for a in amounts]
    amounts[-1] = (total - sum(amounts[:-1], Decimal("0"))).quantize(_CENTS)
    return amounts


def recognize(contract_value: Number, method: str = RATABLE, periods: int = None,
              milestones: Sequence[Tuple[str, Number]] = None) -> Dict[str, object]:
    """Build a value-conserving recognition schedule for a contract by a named method.

    - point_in_time: the whole contract value is recognized in a single period.
    - ratable: the contract value is spread in equal amounts across `periods` periods (last absorbs rounding).
    - milestone: recognized as each named milestone completes; the milestone amounts must sum to the contract value.

    Returns the method, the per-period (or per-milestone) recognized amounts, and the running deferred balance; the
    schedule satisfies `sum(recognized) == contract_value` and, at every step, `recognized + deferred == contract`."""
    cv = _dec(contract_value)
    if cv <= 0:
        raise RecognitionError(f"contract value must be > 0 (got {cv})")
    if method == POINT_IN_TIME:
        recognized = [cv.quantize(_CENTS)]
        labels = ["at_completion"]
    elif method == RATABLE:
        if not periods or periods < 1:
            raise RecognitionError("ratable recognition needs periods >= 1")
        per = (cv / Decimal(periods)).quantize(_CENTS)
        recognized = _finalize(cv, [per] * periods)
        labels = [f"period_{i + 1}" for i in range(periods)]
    elif method == MILESTONE:
        if not milestones:
            raise RecognitionError("milestone recognition needs a list of (name, amount)")
        recognized = [_dec(a).quantize(_CENTS) for _, a in milestones]
        if sum(recognized, Decimal("0")) != cv:
            raise RecognitionError(f"milestone amounts sum to {sum(recognized, Decimal('0'))}, not the contract {cv}")
        labels = [str(n) for n, _ in milestones]
    else:
        raise RecognitionError(f"unknown method {method!r} (known: {POINT_IN_TIME}, {RATABLE}, {MILESTONE})")
    deferred: List[Decimal] = []
    run = cv
    for r in recognized:
        run -= r
        deferred.append(run)
    return {"method": method, "contract_value": cv,
            "schedule": [{"label": l, "recognized": r, "deferred": d}
                         for l, r, d in zip(labels, recognized, deferred)],
            "total_recognized": sum(recognized, Decimal("0")), "steps": len(recognized)}
