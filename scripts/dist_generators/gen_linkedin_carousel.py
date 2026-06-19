#!/usr/bin/env python3
"""gen_linkedin_carousel.py — derive a 6–10 slide LinkedIn carousel from a SEALED manuscript.
Portrait 1080×1350, navy/gold (the federation visual language). Self-contained SVG builder (does NOT import
the landscape book-rail svg_toolkit — additive, dependency-light); PNGs rendered opportunistically via cairosvg.
Spec: distribution_standard.yaml#asset_specs.linkedin_carousel."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dist_common as C

NAVY, GOLD, WHITE, INK, DESC = "#1B2A4A", "#C5A55A", "#FFFFFF", "#1B2A4A", "#5b6678"
W, H = 1080, 1350
FONT = "Helvetica, Arial, sans-serif"


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _wrap(s: str, width: int):
    words, lines, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width or not cur:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def _slide_svg(kicker: str, title: str, body: str, idx: int, total: int, *, cover=False) -> str:
    b = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">']
    b.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{NAVY if cover else WHITE}"/>')
    b.append(f'<rect x="72" y="120" width="120" height="14" rx="7" fill="{GOLD}"/>')  # gold accent bar
    tc = WHITE if cover else NAVY
    if kicker:
        b.append(f'<text x="72" y="108" font-size="30" fill="{GOLD}" font-weight="bold" '
                 f'letter-spacing="3">{_esc(kicker.upper())}</text>')
    y = 250
    for ln in _wrap(title, 22 if cover else 24)[:5]:
        b.append(f'<text x="72" y="{y}" font-size="{72 if cover else 58}" fill="{tc}" font-weight="bold">{_esc(ln)}</text>')
        y += (90 if cover else 74)
    if body:
        y += 30
        for ln in _wrap(body, 40)[:9]:
            b.append(f'<text x="72" y="{y}" font-size="36" fill="{DESC if not cover else "#C9D3E4"}">{_esc(ln)}</text>')
            y += 52
    # footer
    b.append(f'<text x="72" y="{H-64}" font-size="26" fill="{GOLD}" font-weight="bold">Mangum · sovereign library</text>')
    b.append(f'<text x="{W-72}" y="{H-64}" font-size="26" fill="{DESC if not cover else "#C9D3E4"}" '
             f'text-anchor="end">{idx} / {total}</text>')
    b.append("</svg>")
    return "".join(b)


def generate(book_id: str) -> dict:
    ms = C.latest_manuscript(book_id)
    if not ms:
        raise SystemExit(f"no manuscript for {book_id}")
    book = C.parse_book(ms.read_text(encoding="utf-8"))
    title, sub, chapters = book["title"], book["subtitle"], book["chapters"]
    body_ch = [c for c in chapters if c.get("first_para")][:8]
    slides = [{"kicker": "Sovereign Library", "title": title, "body": sub, "cover": True}]
    for c in body_ch:
        slides.append({"kicker": c["label"], "title": c["title"],
                       "body": C._first_sentence(c["first_para"], 160), "cover": False})
    slides.append({"kicker": "Read it", "title": "The full playbook is on Amazon / KDP.",
                   "body": "Built for lasting, generational prosperity — sovereignty over dependency.", "cover": True})
    slides = slides[:10]
    if len(slides) < 6 and sub:  # pad to floor
        slides.insert(1, {"kicker": "Why it matters", "title": sub, "body": "", "cover": False})
    total = len(slides)
    dd = C.dist_dir(book_id)
    cdir = dd / "linkedin_carousel"
    cdir.mkdir(exist_ok=True)
    rendered = 0
    try:
        import cairosvg
        have_png = True
    except Exception:
        have_png = False
    for i, s in enumerate(slides, 1):
        svg = _slide_svg(s["kicker"], s["title"], s.get("body", ""), i, total, cover=s.get("cover"))
        (cdir / f"slide_{i:02d}.svg").write_text(svg, encoding="utf-8")
        if have_png:
            try:
                cairosvg.svg2png(bytestring=svg.encode(), write_to=str(cdir / f"slide_{i:02d}.png"),
                                 output_width=W, output_height=H)
                rendered += 1
            except Exception:
                pass
    content = [{"kicker": s["kicker"], "title": s["title"], "body": s.get("body", "")} for s in slides]
    meta = {"slides": total, "dims": "1080x1350", "palette": ["navy #1B2A4A", "gold #C5A55A"],
            "png_rendered": rendered, "svg_dir": str(cdir.relative_to(C.REPO))}
    src = f"title + {len(body_ch)} chapters + CTA"
    C.write_asset(book_id, "linkedin_carousel", content, meta, src, ms)
    return {"slides": total, "png": rendered, "source": src}


if __name__ == "__main__":
    import json
    print(json.dumps(generate(sys.argv[1]), indent=2))
