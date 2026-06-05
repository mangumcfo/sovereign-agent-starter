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


# --- In-memory read-repair (GB owns the file; we NEVER write it). A common GB gotcha is an unquoted
# scalar value carrying an inner ": " (e.g.  drill_down: Published; KDP evidence: Live $19.99 ...) which
# breaks strict YAML and can blank the whole lens. We quote ONLY such values, and ONLY when not inside a
# multi-line quoted/block scalar (so a valid multi-line value is never corrupted). Verified to touch only
# the offending lines on the live roadmap. ---
_KV = re.compile(r"^(\s*(?:-\s+)?[A-Za-z_][\w./-]*:[ \t]+)(\S.*?)[ \t]*$")


def _sq_open(s: str) -> bool:        # value starts with ' — still open at line end? ('' = escaped quote)
    i = 1
    while i < len(s):
        if s[i] == "'":
            if i + 1 < len(s) and s[i + 1] == "'":
                i += 2; continue
            return False
        i += 1
    return True


def _sq_closes(line: str) -> bool:   # inside a '…' scalar — does it close on this line?
    i = 0
    while i < len(line):
        if line[i] == "'":
            if i + 1 < len(line) and line[i + 1] == "'":
                i += 2; continue
            return True
        i += 1
    return False


def _dq_open(s: str) -> bool:
    i = 1
    while i < len(s):
        if s[i] == "\\":
            i += 2; continue
        if s[i] == '"':
            return False
        i += 1
    return True


def _dq_closes(line: str) -> bool:
    i = 0
    while i < len(line):
        if line[i] == "\\":
            i += 2; continue
        if line[i] == '"':
            return True
        i += 1
    return False


def _repair_unquoted_colons(text: str):
    """Return (repaired_text, count). Quotes unquoted scalar values containing ': '; skips lines inside
    multi-line single/double-quoted or block (|/>) scalars so valid multi-line values are never touched."""
    out, n = [], 0
    in_block = in_sq = in_dq = False
    block_indent = 0
    for line in text.split("\n"):
        indent = len(line) - len(line.lstrip(" "))
        if in_sq:
            out.append(line)
            if _sq_closes(line):
                in_sq = False
            continue
        if in_dq:
            out.append(line)
            if _dq_closes(line):
                in_dq = False
            continue
        if in_block:
            if line.strip() == "" or indent > block_indent:
                out.append(line); continue
            in_block = False
        m = _KV.match(line)
        if m:
            val = m.group(2); c0 = val[:1]
            if c0 in ("|", ">"):
                in_block = True; block_indent = indent; out.append(line); continue
            if c0 in ("[", "{", "&", "*", "#"):
                out.append(line); continue
            if c0 == "'":
                if _sq_open(val):
                    in_sq = True
                out.append(line); continue
            if c0 == '"':
                if _dq_open(val):
                    in_dq = True
                out.append(line); continue
            if ": " in val:
                qv = '"' + val.replace("\\", "\\\\").replace('"', '\\"') + '"'
                out.append(m.group(1) + qv); n += 1; continue
        out.append(line)
    return "\n".join(out), n


def _load(text: str):
    """Parse the roadmap. On failure, attempt an in-memory quote-repair of unquoted ':'-bearing values
    (GB's file is never modified); else fall back to the safe prefix. Returns (data, degraded, detail)."""
    import yaml  # system python ships PyYAML 6.x; lazy so an import gap degrades, never 500s
    try:
        return yaml.safe_load(text) or {}, False, ""
    except yaml.YAMLError:
        pass
    repaired, n = _repair_unquoted_colons(text)
    if n:
        try:
            data = yaml.safe_load(repaired) or {}
            if data.get("series"):
                return data, True, (
                    f"Auto-repaired {n} unquoted value(s) carrying an inner ': ' (e.g. 'KDP evidence: …') "
                    "so the lens renders. GB's file is unchanged in place — flag GB to quote them at source.")
        except yaml.YAMLError:
            pass
    m = re.search(r"^(gb_notes|references):", text, re.M)
    if m:
        try:
            return (yaml.safe_load(text[: m.start()]) or {}, True,
                    "Rendered from the safe prefix — GB's gb_notes/references tail is unparseable YAML "
                    "(data above intact). Flag GB to fix the tail.")
        except yaml.YAMLError:
            pass
    return {}, True, "Roadmap unparseable — even the safe prefix failed; GB must fix the YAML."


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
    data, degraded, detail = _load(text)
    msr = data.get("multi_series_roadmap", {}) if isinstance(data, dict) else {}
    series = [_series_card(s) for s in (data.get("series") or []) if isinstance(s, dict)]
    return jsonify({
        "meta": {
            "source": str(path),
            "ok": bool(series),
            "degraded": degraded,
            "note": detail if degraded else "",
            "version": data.get("version", "") if isinstance(data, dict) else "",
            "current_arc": msr.get("current_arc", ""),
            "active_series_count": msr.get("active_series_count"),
        },
        "series": series,
    })
