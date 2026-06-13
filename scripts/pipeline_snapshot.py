#!/usr/bin/env python3
"""Series Pipeline Snapshot — dated, immutable, content-hashed capture of the FULL merged pipeline.

WHY: drop-off protection + point-in-time record. The roadmap (lean) + extraction index + manuscripts
stay the source-of-truth; this snapshot is a DERIVED capture of exactly what the Atrium Series Pipeline
lens renders on a given day — so you can say "this is what it was today / a week ago", diff two days,
and catch any silent drop (a chapter/title/KW that vanished) at a glance.

It reuses the lens merge (routes/series.py) — same data Atrium shows — so the snapshot never drifts
from the live view. NOT a build source (a competing canonical is what causes drop-off); it's an audit
artifact: read-only over the canonical files, write-once per date.

  python3 scripts/pipeline_snapshot.py [YYYY-MM-DD]   # default: today
  diff two snapshots:  diff artifacts/pipeline_snapshots/series_pipeline_<old>.yaml <new>.yaml

Output: artifacts/pipeline_snapshots/series_pipeline_<date>.yaml  (header: date · content_hash · coverage health)
"""
from __future__ import annotations
import sys, os, json, hashlib, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from sovereign_agent.node_api.routes.series import _load, _series_card, _chapter_index, _roadmap_path  # reuse lens


def build_snapshot() -> tuple[dict, dict]:
    text = _roadmap_path().read_text(encoding="utf-8")
    data, degraded, detail = _load(text)
    idx = _chapter_index()
    series = [_series_card(s, idx) for s in (data.get("series") or []) if isinstance(s, dict)]
    # coverage health — the drop-off detector
    n_series = len(series)
    n_titles = sum(len(s["titles"]) for s in series)
    n_ch = sum(len(t.get("chapters") or []) for s in series for t in s["titles"])
    n_ch_kw = sum(1 for s in series for t in s["titles"] for c in (t.get("chapters") or []) if c.get("keywords"))
    titles_with_outline = sum(1 for s in series for t in s["titles"] if t.get("chapters"))
    cov = {"series": n_series, "titles": n_titles, "chapters": n_ch,
           "chapters_with_kw": n_ch_kw, "titles_with_outline": titles_with_outline,
           "degraded": degraded}
    content_hash = hashlib.sha256(json.dumps(series, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {"series": series}, {"coverage": cov, "content_hash": content_hash, "degraded_detail": detail}


def _prior_snapshot(outdir: Path, date: str):
    """Most-recent snapshot DATED BEFORE the run date (ISO dates sort lexicographically)."""
    pri = []
    for p in outdir.glob("series_pipeline_*.yaml"):
        d = p.stem.replace("series_pipeline_", "")
        if d < date:
            pri.append((d, p))
    return max(pri)[1] if pri else None


def _coverage_of(path: Path) -> dict:
    import yaml
    try:
        d = yaml.safe_load(path.read_text(encoding="utf-8"))
        return d.get("coverage", {}) if isinstance(d, dict) else {}
    except Exception:
        return {}


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    body, meta = build_snapshot()
    outdir = REPO / "artifacts" / "pipeline_snapshots"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"series_pipeline_{date}.yaml"
    import yaml

    # Idempotency: if today's snapshot already matches this content, do nothing (no churn).
    if out.exists():
        prev = _coverage_of(out)
        if yaml.safe_load(out.read_text(encoding="utf-8")).get("content_hash") == meta["content_hash"]:
            print(f"unchanged — {out.name} already current (content_hash {meta['content_hash'][:16]})")
            return 0

    # DROP-OFF GUARD: compare coverage vs the most-recent prior snapshot; warn loudly if anything decreased.
    cov = meta["coverage"]
    prior = _prior_snapshot(outdir, date)
    drops = []
    if prior:
        pc = _coverage_of(prior)
        for k in ("series", "titles", "chapters", "chapters_with_kw", "titles_with_outline"):
            if isinstance(pc.get(k), int) and cov.get(k, 0) < pc[k]:
                drops.append(f"{k}: {pc[k]} -> {cov[k]}  (DROPPED {pc[k]-cov[k]})")
    cov = meta["coverage"]
    header = (
        f"# Series Pipeline Snapshot — {date}\n"
        f"# Immutable point-in-time capture of the FULL merged pipeline (Atrium lens output). Drop-off protection.\n"
        f"# content_hash: {meta['content_hash']}\n"
        f"# coverage: series={cov['series']} titles={cov['titles']} chapters={cov['chapters']} "
        f"chapters_with_kw={cov['chapters_with_kw']} titles_with_outline={cov['titles_with_outline']} degraded={cov['degraded']}\n"
        f"# source: derived from series_roadmap.yaml + extracted_chapter_outlines (lens merge). NOT a build source.\n"
        f"# diff vs another day:  diff <this> artifacts/pipeline_snapshots/series_pipeline_<other>.yaml\n"
    )
    snap = {"snapshot_date": date, "content_hash": meta["content_hash"], "coverage": cov, **body}
    out.write_text(header + yaml.safe_dump(snap, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")
    print(f"wrote {out}")
    print(f"coverage: {cov}")
    print(f"content_hash: {meta['content_hash'][:16]}")
    if drops:
        print("\n" + "!" * 64)
        print("!!  DROP-OFF GUARD — pipeline coverage DECREASED vs %s:" % prior.name)
        for d in drops:
            print("!!    " + d)
        print("!!  Investigate before sealing — something was dropped.")
        print("!" * 64)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
