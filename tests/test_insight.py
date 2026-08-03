"""Insight-provenance invariants — co-extrusion for s5_17 (Analytics & Decision Intelligence).

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves a metric that carries
its provenance -- the value plus the ids of the governed records it summed -- so an insight is drillable back to the
ledger, not orphaned."""
from decimal import Decimal

import pytest

from sovereign_agent.analytics import metric_with_provenance, InsightError

RECORDS = [
    {"id": "p1", "amount": "100.00", "dept": "ops"},
    {"id": "p2", "amount": "250.00", "dept": "sales"},
    {"id": "p3", "amount": "50.00", "dept": "ops"},
]


def test_metric_sums_and_carries_source_ids():
    m = metric_with_provenance(RECORDS)
    assert m["value"] == Decimal("400.00")
    assert m["count"] == 3
    assert m["source_ids"] == ["p1", "p2", "p3"]


def test_predicate_filters_and_provenance_reflects_it():
    m = metric_with_provenance(RECORDS, predicate=lambda r: r["dept"] == "ops")
    assert m["value"] == Decimal("150.00")
    assert m["source_ids"] == ["p1", "p3"]   # only the contributing records


def test_missing_value_field_refused():
    with pytest.raises(InsightError):
        metric_with_provenance([{"id": "x", "dept": "ops"}])   # no amount


def test_empty_selection_is_zero_with_no_sources():
    m = metric_with_provenance(RECORDS, predicate=lambda r: False)
    assert m["value"] == Decimal("0") and m["count"] == 0 and m["source_ids"] == []
