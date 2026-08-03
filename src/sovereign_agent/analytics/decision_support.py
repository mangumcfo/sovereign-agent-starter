"""Decision support — transparent, re-runnable weighted scoring, ranking, and recommendation. No silent scores.

Co-extrusion for s5_17 (Analytics & Decision Intelligence, KM Option B 2026-08-03). Pure arithmetic over Decimal, no
crypto substrate (runs in a pure public clone, no skip — F-1 posture). A decision-support score on a legacy system is
a single number a model emits, and no one can see how it was reached. Here a score is a transparent weighted sum of
named criteria, and every option's score carries its per-criterion contribution and the weights used — so the score is
re-runnable and auditable, and a human deciding on it can see exactly why one option outranks another. Human primacy is
preserved: the module ranks and recommends, but the governed decision that acts on it is a separate human-gated act."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Mapping, Union

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class DecisionError(ValueError):
    """Raised for empty options/weights, or an option missing a weighted criterion."""


def score_options(options: List[Mapping], weights: Mapping[str, Number]) -> List[Dict[str, object]]:
    """Score each option by a transparent weighted sum of named criteria, carrying the full breakdown.

    Each option is a mapping with `id` and `criteria` (a mapping of criterion -> value). `weights` maps each criterion
    to its weight. The score is the sum of value*weight over the weighted criteria; the returned breakdown records each
    criterion's contribution and the weights, so the score is never silent -- it can be re-derived and questioned. An
    option missing a weighted criterion is refused rather than scored on a hidden default."""
    if not options:
        raise DecisionError("no options to score")
    if not weights:
        raise DecisionError("no weights")
    w = {k: _dec(v) for k, v in weights.items()}
    scored = []
    for o in options:
        crit = o.get("criteria", {})
        breakdown: Dict[str, Decimal] = {}
        total = Decimal("0")
        for c, weight in w.items():
            if c not in crit:
                raise DecisionError(f"option {o.get('id')!r} missing criterion {c!r}")
            contrib = _dec(crit[c]) * weight
            breakdown[c] = contrib
            total += contrib
        scored.append({"id": o.get("id"), "score": total, "breakdown": breakdown, "weights": dict(w)})
    return scored


def rank(options: List[Mapping], weights: Mapping[str, Number]) -> List[Dict[str, object]]:
    """Rank options by transparent score, highest first. Ties keep input order (stable), so the ranking is
    reproducible and its ordering explainable from the breakdowns."""
    scored = score_options(options, weights)
    return sorted(scored, key=lambda s: s["score"], reverse=True)


def recommend(options: List[Mapping], weights: Mapping[str, Number]) -> Dict[str, object]:
    """Recommend the top-scoring option, returning it with its full breakdown and the runner-up, so the human deciding
    sees why it leads and by how much. The recommendation is advice with its reasoning attached, not a verdict -- the
    governed decision that acts on it is a separate human-gated act."""
    ranked = rank(options, weights)
    top = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None
    margin = (top["score"] - runner_up["score"]) if runner_up else top["score"]
    return {"recommended": top["id"], "score": top["score"], "breakdown": top["breakdown"],
            "runner_up": runner_up["id"] if runner_up else None, "margin": margin, "ranking": ranked}
