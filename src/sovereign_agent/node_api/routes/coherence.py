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
import os
import re
from pathlib import Path

from flask import Blueprint, jsonify

from .._filecache import memoize_on
from .._jsonstore import read_json_cached
from ..auth import require_principal

bp = Blueprint("coherence", __name__, url_prefix="/api/v1")


def _registry_path() -> Path:
    repo = Path(__file__).resolve().parents[4]
    return repo / "memory" / "coherence_registry.json"


COVERAGE = Path(__file__).resolve().parents[4] / "memory" / "coherence_coverage.json"
CAPABILITIES = Path(__file__).resolve().parents[4] / "memory" / "coherence_capabilities.json"
VALIDATION_STATE = Path(__file__).resolve().parents[4] / "memory" / "extrusion_validation_state.json"


def _compute_paths(reg: dict, repo: Path) -> list:
    """The files _compute()'s result depends on: the registry + every cited book file. When none change,
    the ~948KB manuscript re-scan is skipped (audit 2026-06-13 W5 #5)."""
    paths = [_registry_path()]
    for e in reg.get("extrusions", []):
        bf = e.get("book_file")
        if bf:
            paths.append(bf)
    return paths


@memoize_on(_compute_paths)
def _compute(reg: dict, repo: Path):
    """Live per-extrusion coherence: re-read each cited passage from the book + re-check the code/hash.
    Pure (no writes); shared by /coherence and /coherence/rollup so both tell the same truth.
    Memoized on the registry + book files' (mtime,size) (audit 2026-06-13 W5 #5) — re-reads only on change."""
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
    reg = read_json_cached(p, {})   # memoized registry read (audit 2026-06-13c #33)
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
    reg = read_json_cached(p, {})   # memoized registry read (audit 2026-06-13c #33)
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
    # Honest coverage: books classified as narrative (no code spec) so the roadmap shows 📖 narrative —
    # distinct from ◌ awaiting-anchor. Read-only companion file (Tiger-authored via coherence_backfill.py).
    cov = read_json_cached(COVERAGE, {})
    narrative = cov.get("narrative", {}) if isinstance(cov, dict) else {}
    # Capability ledger (G's 2026-05-30 review harvest) — semantic Present/Partial/Missing per book,
    # folded per book_id so the roadmap shows the true coverage (not just hash-pinned passages).
    capdoc = read_json_cached(CAPABILITIES, {})
    caps = capdoc.get("capabilities", []) if isinstance(capdoc, dict) else []
    cap_by_book, cap_tot = {}, {"present": 0, "partial": 0, "missing": 0}
    for c in caps:
        b = cap_by_book.setdefault(c.get("book_id", "?"), {"present": 0, "partial": 0, "missing": 0, "rows": []})
        st = c.get("review_status", "missing")
        if st in b:
            b[st] += 1
            cap_tot[st] = cap_tot.get(st, 0) + 1
        b["rows"].append(c)
    # Extrusion-validation state (written by scripts/extrusion_validate.py — runs pytest + Merkle out of band;
    # read cheaply here so the monitor shows VALIDATED/untested/drift/fail + Merkle roots without running tests).
    val = read_json_cached(VALIDATION_STATE, {})
    return jsonify({
        "by_book": sorted(by.values(), key=lambda b: b["book"]),
        "narrative": narrative,
        "capabilities": cap_by_book,
        "validation": val,
        "overall": {"coherent": coherent, "drift": drift, "total": coherent + drift,
                    "books": len(by), "narrative": len(narrative),
                    "cap_present": cap_tot["present"], "cap_partial": cap_tot["partial"],
                    "cap_missing": cap_tot["missing"], "cap_books": len(cap_by_book)},
        "note": "Per-book coherence rollup. ✅ pinned = hash-verified passage↔code · ⚖ capability = G-review "
                "Present/Partial/Missing · 📖 narrative = no code spec · ◌ absent = awaiting. Recomputed live.",
    })
