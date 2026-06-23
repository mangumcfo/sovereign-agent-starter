#!/usr/bin/env python3
"""outline_from_pipeline.py — render a volume's CANONICAL outline FROM the series pipeline (the leader).

KM 2026-06-23: "the outline we signed on in the series pipeline is the leader; we don't want outlines that
deviate." The G-locked chapter cards in series_roadmap.yaml (title · promise · beats · keywords per chapter)
are the SINGLE SOURCE OF TRUTH. This emits a clean outline.md (linked TOC + per-chapter detail) sourced ONLY
from the pipeline, and builds it to PDF with a clickable TOC — so the outline a volume drafts against can never
drift from the pipeline (no hand-maintained outline_v1.0.md to deviate).

Usage:
  python3 scripts/outline_from_pipeline.py <book_id>            # write outline_from_pipeline.md + .pdf in the vol dir
  python3 scripts/outline_from_pipeline.py <book_id> --md-only  # markdown only (no PDF)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
ROADMAP = REPO / "artifacts" / "series_roadmap.yaml"
KDP = Path("/home/kmangum/work-repos/mangumcfo/breathline-books-vault/kdp")


def _find_volume(book_id: str) -> dict | None:
    data = yaml.safe_load(ROADMAP.read_text(encoding="utf-8"))

    def walk(o):
        if isinstance(o, dict):
            if o.get("book_id") == book_id:
                return o
            for v in o.values():
                r = walk(v)
                if r:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = walk(v)
                if r:
                    return r
        return None
    return walk(data)


def _vol_dir(book_id: str) -> Path | None:
    for root in [KDP] + sorted(KDP.glob("series_*")) + [KDP / "agentic_playbooks"]:
        d = root / book_id
        vers = sorted((v for v in d.glob("v*") if v.is_dir()), reverse=True)
        if vers:
            return vers[0]
    return None


def render_md(vol: dict) -> str:
    title = vol.get("title", vol.get("book_id", ""))
    chs = vol.get("chapters") or []
    L = [f"# {title} — Canonical Outline", "",
         "*Source of truth: the series pipeline (`series_roadmap.yaml`). This outline is generated FROM the "
         "G-locked chapter cards — the leader. Volume drafts conform to THIS; they do not deviate.*", ""]
    if vol.get("one_line"):
        L += [f"**Volume:** {vol['one_line']}", ""]
    L += [f"**book_id:** `{vol.get('book_id')}` · **stage:** {vol.get('stage','?')} · **chapters:** {len(chs)}", ""]
    # linked TOC (markdown anchors)
    L += ["## Contents", ""]
    for c in chs:
        n = c.get("n"); t = c.get("title", "")
        anchor = f"chapter-{n}-{t.lower()}"
        anchor = "".join(ch if ch.isalnum() or ch == "-" else ("-" if ch == " " else "") for ch in anchor)
        L.append(f"- [Chapter {n}: {t}](#{anchor})")
    L += [""]
    for c in chs:
        n = c.get("n"); t = c.get("title", "")
        L += [f"## Chapter {n}: {t}", ""]
        if c.get("promise"):
            L += [f"**Promise:** {c['promise']}", ""]
        beats = c.get("beats") or []
        if beats:
            L += ["**Beats:**", ""] + [f"- {b}" for b in beats] + [""]
        kws = c.get("keywords") or []
        if kws:
            L += [f"**Keywords (targets):** {' · '.join(kws)}", ""]
        if c.get("coherence_pin"):
            L += [f"*Coherence anchor:* {c['coherence_pin']}", ""]
    L += ["", "∞Δ∞ Pipeline is the leader. Draft to this; reconcile to this; never deviate. ∞Δ∞", ""]
    return "\n".join(L)


def render_pdf(md_path: Path, pdf_path: Path, title: str):
    """Build the outline PDF with a CLICKABLE TOC (weasyprint honors in-document #anchors)."""
    import markdown as _md  # python-markdown → anchors via 'toc'/'attr_list'
    html_body = _md.markdown(md_path.read_text(encoding="utf-8"),
                             extensions=["toc", "attr_list", "tables", "fenced_code"])
    css = """
      @page { size: Letter; margin: 22mm 20mm; }
      body { font-family: 'Georgia','Times New Roman',serif; color:#1B2A4A; line-height:1.5; font-size:11pt; }
      h1 { font-size:22pt; border-bottom:2px solid #C5A55A; padding-bottom:6px; }
      h2 { font-size:15pt; color:#1B2A4A; margin-top:22px; border-bottom:1px solid #E0D6BE; padding-bottom:3px; }
      a { color:#1B2A4A; text-decoration:none; }
      ul { margin:4px 0; } li { margin:3px 0; }
      strong { color:#0C172C; }
      em { color:#5b6678; }
    """
    from weasyprint import HTML, CSS
    HTML(string=f"<html><head><meta charset='utf-8'><title>{title}</title></head><body>{html_body}</body></html>"
         ).write_pdf(str(pdf_path), stylesheets=[CSS(string=css)])


def main() -> int:
    ap = argparse.ArgumentParser(description="Render a volume's canonical outline FROM the series pipeline")
    ap.add_argument("book_id")
    ap.add_argument("--md-only", action="store_true")
    a = ap.parse_args()
    vol = _find_volume(a.book_id)
    if not vol or not vol.get("chapters"):
        print(f"✗ {a.book_id}: not found in the pipeline (or has no chapter cards) — lock its outline first."); return 2
    vdir = _vol_dir(a.book_id)
    if not vdir:
        print(f"✗ {a.book_id}: no volume dir on disk."); return 2
    md = render_md(vol)
    md_path = vdir / "outline_from_pipeline.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  wrote {md_path}  ({len(vol['chapters'])} chapters from the pipeline)")
    if not a.md_only:
        pdf_path = vdir / "final" / "Outline.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        render_pdf(md_path, pdf_path, vol.get("title", a.book_id) + " — Outline")
        print(f"  wrote {pdf_path}  (linked TOC)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
