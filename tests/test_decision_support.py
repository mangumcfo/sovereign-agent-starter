"""Decision-support invariants — co-extrusion for s5_17 (Analytics & Decision Intelligence).

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves transparent weighted
scoring that carries its full per-criterion breakdown (no silent scores), a reproducible ranking, and a recommendation
that surfaces the runner-up and margin -- advice with its reasoning attached, for a human-gated decision."""
from decimal import Decimal

import pytest

from sovereign_agent.analytics import score_options, rank, recommend, DecisionError

OPTIONS = [
    {"id": "vendor-A", "criteria": {"cost": 8, "quality": 6, "risk": 9}},
    {"id": "vendor-B", "criteria": {"cost": 5, "quality": 9, "risk": 7}},
]
WEIGHTS = {"cost": 2, "quality": 3, "risk": 1}


def test_score_carries_full_breakdown():
    scored = {s["id"]: s for s in score_options(OPTIONS, WEIGHTS)}
    a = scored["vendor-A"]
    # 8*2 + 6*3 + 9*1 = 16 + 18 + 9 = 43
    assert a["score"] == Decimal("43")
    assert a["breakdown"] == {"cost": Decimal("16"), "quality": Decimal("18"), "risk": Decimal("9")}
    assert a["weights"] == {"cost": Decimal("2"), "quality": Decimal("3"), "risk": Decimal("1")}


def test_rank_orders_by_score():
    r = rank(OPTIONS, WEIGHTS)
    # A=43; B = 5*2+9*3+7*1 = 10+27+7 = 44 -> B first
    assert [s["id"] for s in r] == ["vendor-B", "vendor-A"]


def test_recommend_surfaces_runner_up_and_margin():
    rec = recommend(OPTIONS, WEIGHTS)
    assert rec["recommended"] == "vendor-B"
    assert rec["runner_up"] == "vendor-A"
    assert rec["margin"] == Decimal("1")   # 44 - 43
    assert rec["breakdown"]["quality"] == Decimal("27")


def test_missing_criterion_refused_not_silently_defaulted():
    bad = [{"id": "X", "criteria": {"cost": 5}}]   # no quality/risk
    with pytest.raises(DecisionError):
        score_options(bad, WEIGHTS)


def test_empty_options_or_weights_refused():
    with pytest.raises(DecisionError):
        score_options([], WEIGHTS)
    with pytest.raises(DecisionError):
        score_options(OPTIONS, {})
