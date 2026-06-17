#!/usr/bin/env python3
"""roadmap_sealed_guard — the generator-MERGE rule as an enforceable guard.

Bug finding:projection-generator-merge-sealed-titles (f77db98c, GB→Tiger [390]):
`pipeline/active.yaml` tracks only in-flight books, so regenerating `series_roadmap.yaml`
from it ALONE silently drops sealed/published titles (S0 dropped CYL 201; Series 1 Books
01-09 dropped, restored CYL 218). The fix is a MERGE: the projection must union the
sealed/published titles from vault metadata so they persist across regenerations.

GB is the sole writer of series_roadmap.yaml (two-writers fence §6); Tiger owns pipeline
tooling. So this is the rule as TOOLING, not a roadmap edit: a persisted baseline of every
(book_id) that has ever reached stage `published`/`sealed` is the merge source-of-truth.
The guard FAILS (exit 1) if any baseline-sealed title is missing from the current roadmap —
catching a drop before GB writes. `--update` folds newly published/sealed titles into the
baseline (append-only; never removes — a title, once sealed, persists forever).

    python3 scripts/roadmap_sealed_guard.py            # check: roadmap keeps every sealed title
    python3 scripts/roadmap_sealed_guard.py --update   # fold new published/sealed titles into the baseline

SOURCE: baseline keyed by book_id (sovereign id, not a label). TRUTH: union from the
projection's own stage field — published/sealed are facts, not in-flight state. INTEGRITY:
append-only baseline + exit-coded guard; a sealed title can never be silently dropped again.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
ROADMAP = REPO / "artifacts" / "series_roadmap.yaml"
BASELINE = REPO / "artifacts" / "roadmap_sealed_baseline.yaml"
SEALED_STAGES = {"published", "sealed"}


def _titles(roadmap: dict):
    """Yield (series_name, book_id, title, stage) for every title in the projection."""
    for s in roadmap.get("series", []) or []:
        if not isinstance(s, dict):
            continue
        sname = s.get("name", "?")
        for t in (s.get("titles") or s.get("books") or []):
            if isinstance(t, dict):
                yield sname, t.get("book_id") or t.get("id") or t.get("title"), t.get("title"), (t.get("stage") or "").lower()


def _sealed_now(roadmap: dict) -> dict:
    """book_id -> {series, title} for every title currently at a sealed/published stage."""
    out = {}
    for sname, bid, title, stage in _titles(roadmap):
        if stage in SEALED_STAGES and bid:
            out[bid] = {"series": sname, "title": title, "stage": stage}
    return out


def _load(p: Path, default):
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else default


def main() -> int:
    update = "--update" in sys.argv
    if not ROADMAP.exists():
        print(f"FAIL — roadmap not found: {ROADMAP}")
        return 1
    roadmap = _load(ROADMAP, {})
    sealed_now = _sealed_now(roadmap)
    baseline = _load(BASELINE, {}) or {}
    base_ids = baseline.get("sealed_book_ids", {}) or {}

    if update:
        added = []
        for bid, meta in sealed_now.items():
            if bid not in base_ids:
                base_ids[bid] = meta
                added.append(bid)
        baseline = {"_doc": "Append-only baseline of every book_id that reached published/sealed. "
                            "The merge source-of-truth for the series_roadmap projection (f77db98c). "
                            "roadmap_sealed_guard.py fails if a regeneration drops any of these.",
                    "sealed_book_ids": dict(sorted(base_ids.items()))}
        BASELINE.write_text(yaml.safe_dump(baseline, sort_keys=False, allow_unicode=True), encoding="utf-8")
        print(f"baseline updated: +{len(added)} new sealed/published titles ({len(base_ids)} total)")
        for a in added:
            print(f"  + {a}")
        return 0

    # CHECK: every baseline-sealed title must still be present in the roadmap.
    present_ids = {bid for _, bid, _, _ in _titles(roadmap) if bid}
    dropped = [bid for bid in base_ids if bid not in present_ids]
    print(f"roadmap: {len(present_ids)} titles · sealed/published now: {len(sealed_now)} · baseline-sealed: {len(base_ids)}")
    if not base_ids:
        print("NOTE — baseline empty. Initialize it: roadmap_sealed_guard.py --update")
        return 0
    if dropped:
        print(f"\nFAIL — {len(dropped)} sealed/published title(s) DROPPED from the roadmap (merge bug):")
        for bid in dropped:
            m = base_ids[bid]
            print(f"  ✗ {bid}  ({m.get('series','?')} · {m.get('title','?')})")
        print("\nThe projection must UNION sealed/published titles — restore them before writing the roadmap.")
        return 1
    print("OK — every sealed/published title persists in the roadmap (no drop).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
