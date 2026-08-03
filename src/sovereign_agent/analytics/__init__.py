"""Analytics & Decision Intelligence — governed, transparent foresight and decision support over the immutable core.

Co-extrusion for s5_17 (KM Option B 2026-08-03). Everything here is PURE (no crypto substrate): metrics carry their
provenance back to the governed postings, projections and scenarios name their method and inputs, planning is a
transparent net-requirement / schedule / priority-allocation, and decision support is a re-runnable weighted score
that carries its full breakdown. The volume does transparent, receipted, re-runnable foresight and refuses opaque
black-box scoring by construction. External data feeds are homed in S6-V07; consolidation in S5-V18; reporting and
compliance in the sealed S5-V14."""
from .insight import metric_with_provenance, InsightError
from .forecast import project, scenario, ForecastError, MOVING_AVERAGE, LINEAR_TREND
from .planning import net_requirements, schedule, allocate_by_priority, PlanningError
from .decision_support import score_options, rank, recommend, DecisionError

__all__ = [
    "metric_with_provenance", "InsightError",
    "project", "scenario", "ForecastError", "MOVING_AVERAGE", "LINEAR_TREND",
    "net_requirements", "schedule", "allocate_by_priority", "PlanningError",
    "score_options", "rank", "recommend", "DecisionError",
]
