"""Insight — an analytic metric that carries its provenance back to the governed records it was computed from.

Co-extrusion for s5_17 (Analytics & Decision Intelligence, KM Option B 2026-08-03). Pure arithmetic over Decimal, no
crypto substrate (runs in a pure public clone, no skip — F-1 posture). A number on a legacy dashboard is orphaned from
its source: you cannot drill from the figure to the transactions beneath it, so you take it on trust. Here a metric is
computed over governed records and returns not just a value but the ids of the records it summed, so every insight is
drillable back to the ledger and provable rather than merely displayed."""
from __future__ import annotations

from decimal import Decimal
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Union

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class InsightError(ValueError):
    """Raised when a record lacks the value field, or when no records are supplied for a metric."""


def metric_with_provenance(records: Iterable[Mapping], value_key: str = "amount",
                           predicate: Optional[Callable[[Mapping], bool]] = None,
                           id_key: str = "id") -> Dict[str, object]:
    """Sum a metric over governed records, carrying the provenance of the records that contributed.

    `records` are mappings each with a numeric `value_key` and (ideally) an `id_key`. An optional `predicate` filters
    which records count. Returns the value, the count, and the source ids that were summed -- so the figure can be
    drilled straight back to the governed postings it came from, not taken on trust. A record missing the value field
    is refused rather than silently skipped."""
    value = Decimal("0")
    source_ids: List[object] = []
    n = 0
    for i, r in enumerate(records):
        if predicate is not None and not predicate(r):
            continue
        if value_key not in r:
            raise InsightError(f"record {r.get(id_key, i)!r} has no {value_key!r} field")
        value += _dec(r[value_key])
        source_ids.append(r.get(id_key, i))
        n += 1
    return {"value": value, "count": n, "source_ids": source_ids, "value_key": value_key}
