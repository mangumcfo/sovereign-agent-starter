"""
Section — Series Pipeline (ATR-7 lens, read-only).

The Atrium "Series Pipeline" lens reads this to witness the whole hopper: every series →
its titles → stage / visibility / LGP through-line / next gate. It is a *read-only
projection* — GB is the sole writer of `series_roadmap.yaml` (two-writers fence §6); this
endpoint only renders it. No writes, no mutation; honest labels (degraded-parse + private
visibility surfaced loudly). No hardcoded principals (CONSTITUTION §1).

    GET /series   → { meta, series:[ { number, slug, name, visibility, status, titles:[…] } ] }

Robust-read: `series_roadmap.yaml`'s tail meta blocks (gb_notes / references) are GB working
notes that occasionally carry YAML the strict parser rejects. The lens never needs them, so on
a full-parse failure we fall back to the safe prefix (everything up to the first gb_notes/
references key) and flag `meta.degraded=true` so the surface tells the truth about it.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from flask import Blueprint, jsonify

from ..auth import require_principal

bp = Blueprint("series", __name__, url_prefix="/api/v1")

# Title fields the read-only card needs (everything else in the projection is GB working detail).
_TITLE_FIELDS = (
    "book_id", "vol_id", "title", "subtitle", "stage", "phase",
    "reader_order", "lgp_alignment_score", "next_gate", "drill_down",
    # Publishing lifecycle (GB authors these in the projection; the lens renders a state badge +
    # drill-through). published_date / revision / asin feed the title-card history pane.
    "publishing_state", "published_date", "revision", "asin",
)


def _roadmap_path() -> Path:
    explicit = os.environ.get("SERIES_ROADMAP")
    if explicit:
        return Path(explicit)
    repo = Path(__file__).resolve().parents[4]
    return repo / "artifacts" / "series_roadmap.yaml"


def _load(text: str):
    """Parse the roadmap; fall back to the safe prefix if GB's tail notes break strict YAML.
    Returns (data_dict, degraded_bool). data_dict is {} when even the prefix won't parse."""
    import yaml  # system python ships PyYAML 6.x; lazy so an import gap degrades, never 500s
    try:
        return yaml.safe_load(text) or {}, False
    except yaml.YAMLError:
        pass
    m = re.search(r"^(gb_notes|references):", text, re.M)
    if m:
        try:
            return yaml.safe_load(text[: m.start()]) or {}, True
        except yaml.YAMLError:
            pass
    return {}, True


def _title_card(t: dict) -> dict:
    return {k: t.get(k) for k in _TITLE_FIELDS if t.get(k) is not None}


def _series_card(s: dict) -> dict:
    titles = s.get("titles") or s.get("volumes") or []
    return {
        "number": s.get("series_number"),
        "slug": s.get("slug", ""),
        "name": s.get("name", ""),
        # absent visibility = public KDP ladder (S1/S2); private must be explicit.
        "visibility": s.get("visibility") or "public",
        "status": s.get("status", ""),
        "title_count": len(titles),
        "titles": [_title_card(t) for t in titles if isinstance(t, dict)],
    }


@bp.get("/series")
@require_principal
def series_list():
    path = _roadmap_path()
    if not path.exists():
        return jsonify({
            "meta": {"source": str(path), "ok": False, "degraded": True,
                     "note": "series_roadmap.yaml not found — GB has not produced the projection yet."},
            "series": [],
        })
    text = path.read_text(encoding="utf-8")
    data, degraded = _load(text)
    msr = data.get("multi_series_roadmap", {}) if isinstance(data, dict) else {}
    series = [_series_card(s) for s in (data.get("series") or []) if isinstance(s, dict)]
    return jsonify({
        "meta": {
            "source": str(path),
            "ok": bool(series),
            "degraded": degraded,
            "note": ("Rendered from the safe prefix — GB's gb_notes/references tail was skipped "
                     "(unparseable YAML). Roadmap data is intact; flag to GB to fix the tail.")
            if degraded else "",
            "version": data.get("version", "") if isinstance(data, dict) else "",
            "current_arc": msr.get("current_arc", ""),
            "active_series_count": msr.get("active_series_count"),
        },
        "series": series,
    })
