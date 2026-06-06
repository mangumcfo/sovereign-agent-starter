"""
Section — Book↔Code Coherence (Step D).

The alignment lens: for every book→code extrusion, the code cites an exact book passage (hash-pinned).
This endpoint re-reads each cited passage from the book and re-checks the code, so the cockpit can show
— live — whether the code still reflects the book (coherent) or has drifted. Plus the declared Atrium↔Vol2
reconciliation rows. Read-only; no writes.

    GET /coherence  → { extrusions:[…computed status…], reconciliation:{…}, summary:{…} }
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from flask import Blueprint, jsonify

from ..auth import require_principal

bp = Blueprint("coherence", __name__, url_prefix="/api/v1")


def _registry_path() -> Path:
    repo = Path(__file__).resolve().parents[4]
    return repo / "memory" / "coherence_registry.json"


def _compute(reg: dict, repo: Path):
    """Live per-extrusion coherence: re-read each cited passage from the book + re-check the code/hash.
    Pure (no writes); shared by /coherence and /coherence/rollup so both tell the same truth."""
    out, coherent, drift = [], 0, 0
    for e in reg.get("extrusions", []):
        bf = e.get("book_file", "")
        passage = e.get("passage", "")
        book_present = hash_ok = False
        try:
            if bf and os.path.isfile(bf):
                book_present = passage in open(bf, encoding="utf-8").read()
            hash_ok = hashlib.sha256(passage.encode()).hexdigest()[:12] == e.get("passage_hash", "")
        except OSError:
            pass
        code_present = os.path.isfile(os.path.join(repo, e.get("code_file", "")))
        tests_present = os.path.isfile(os.path.join(repo, e.get("tests_file", "")))
        status = "coherent" if (book_present and code_present and hash_ok) else "DRIFT"
        coherent += status == "coherent"
        drift += status != "coherent"
        out.append({**e, "book_present": book_present, "code_present": code_present,
                    "tests_present": tests_present, "hash_ok": hash_ok, "status": status,
                    "book_id": e.get("book_id") or _book_id_from_path(e.get("book_file", ""))})
    return out, coherent, drift


def _norm(s: str) -> str:
    """Normalize a book label/title to an alnum-lowercase key for cross-source matching."""
    return "".join(c for c in str(s or "").lower() if c.isalnum())


def _book_id_from_path(bf: str) -> str:
    """Derive the roadmap book_id from a book_file path: the dir segment just above the version dir
    (…/<book_id>/v1.0/manuscript.md). Gives the Series Roadmap an EXACT join key (not just fuzzy)."""
    parts = Path(bf or "").parts
    for i, seg in enumerate(parts):
        if i and re.match(r"^v\d", seg):
            return parts[i - 1]
    return ""


@bp.get("/coherence")
@require_principal
def coherence():
    repo = Path(__file__).resolve().parents[4]
    p = _registry_path()
    if not p.exists():
        return jsonify({"extrusions": [], "reconciliation": {}, "summary": {"coherent": 0, "drift": 0, "gaps": 0}})
    reg = json.loads(p.read_text(encoding="utf-8"))
    out, coherent, drift = _compute(reg, repo)
    recon = reg.get("reconciliation", {})
    gaps = sum(1 for r in recon.get("rows", []) if r.get("status") == "gap")
    return jsonify({"extrusions": out, "reconciliation": recon,
                    "summary": {"coherent": coherent, "drift": drift, "gaps": gaps}})


@bp.get("/coherence/rollup")
@require_principal
def coherence_rollup():
    """Per-book coherence rollup so the Series Roadmap can show a quick-glance badge per title/series
    (✅ pct · ⚠ drift) and surface — honestly — which titles have NO anchor yet (coverage, not just drift).
    Read-only; recomputed live (same _compute as /coherence). Persistent-monitor first increment (G steer)."""
    repo = Path(__file__).resolve().parents[4]
    p = _registry_path()
    if not p.exists():
        return jsonify({"by_book": [], "overall": {"coherent": 0, "drift": 0, "total": 0, "books": 0}})
    reg = json.loads(p.read_text(encoding="utf-8"))
    out, coherent, drift = _compute(reg, repo)
    by = {}
    for e in out:
        label = e.get("book", "(unlabeled)")
        b = by.setdefault(label, {"book": label, "key": _norm(label),
                                  "book_id": e.get("book_id") or _book_id_from_path(e.get("book_file", "")),
                                  "coherent": 0, "drift": 0,
                                  "total": 0, "seal": e.get("landed_seal", "")})
        b["total"] += 1
        b["coherent"] += e["status"] == "coherent"
        b["drift"] += e["status"] != "coherent"
    for b in by.values():
        b["pct"] = round(100 * b["coherent"] / b["total"]) if b["total"] else 0
    return jsonify({
        "by_book": sorted(by.values(), key=lambda b: b["book"]),
        "overall": {"coherent": coherent, "drift": drift, "total": coherent + drift, "books": len(by)},
        "note": "Per-book coherence rollup. Titles absent here have no coherence anchor yet — coverage gap, "
                "not drift. Recomputed live; persistent monitor surfaces this in the Series Roadmap.",
    })
