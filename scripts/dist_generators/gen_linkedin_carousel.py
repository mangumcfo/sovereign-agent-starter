#!/usr/bin/env python3
"""gen_linkedin_carousel.py — LinkedIn carousel from a SEALED manuscript (PIL, 1080x1350).

Design matches the published book cover (navy gradient · gold tag · Breathline Books), per KM feedback:
  - NOT 1990s: gradient background, gold accent tags, generous margins, modern type hierarchy. NO frame border.
  - NO border/text overlap: everything inside an 84px safe margin; footer has bottom clearance.
  - REAL COVER ART on slide 1 (final/cover_KDP.png), fitted on the brand gradient.
  - BRAND: canonical series + "Breathline Books"; book title from the cover/manuscript.
  - NO TRUNCATION: shrink-to-fit + full wrap. VISUALS: real book figures interleaved. CTA: Amazon close.
Derive-from-sealed; records provenance. (GB [454] §B + distribution_quality_board.)
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dist_common as C

# palette sampled from the cover
NAVY_TOP, NAVY_BOT = (0x0C, 0x17, 0x2C), (0x1E, 0x30, 0x52)
GOLD, WHITE, MUT = (0xC9, 0xA9, 0x5E), (0xF4, 0xF6, 0xFA), (0xAE, 0xBA, 0xCE)
CARD = (0xF6, 0xF7, 0xFA)
W, H, M = 1080, 1350, 84
FR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FB = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
PUBLISHER = "Breathline Books"
SERIES_CANONICAL = {"agentic_playbooks": "Agentic AI Playbooks for Executives", "kdp_root": "The Executive Series"}
AMAZON_CTA = 'Search "AI Agents for CFOs — Mangum" on Amazon'


def _font(sz, bold=True):
    return ImageFont.truetype(FB if bold else FR, sz)


def _series(book_id: str) -> str:
    p = str(C.book_dir(book_id) or "")
    return SERIES_CANONICAL["agentic_playbooks"] if "agentic_playbooks" in p else SERIES_CANONICAL["kdp_root"]


def _grad():
    col = Image.new("RGB", (1, H))
    for y in range(H):
        t = y / H
        col.putpixel((0, y), tuple(int(NAVY_TOP[i] + (NAVY_BOT[i] - NAVY_TOP[i]) * t) for i in range(3)))
    return col.resize((W, H))


def _wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit(d, text, x, y, maxw, maxh, start, fill, *, bold=True, min_sz=30, lh=1.2):
    sz = start
    while sz > min_sz:
        f = _font(sz, bold); lines = _wrap(d, text, f, maxw); h = int(sz * lh)
        if len(lines) * h <= maxh:
            break
        sz -= 4
    f = _font(sz, bold); lines = _wrap(d, text, f, maxw); h = int(sz * lh)
    for i, ln in enumerate(lines):
        d.text((x, y + i * h), ln, font=f, fill=fill)
    return y + len(lines) * h


def _tag(d, text):
    """gold 'PLAYBOOK'-style tag at top-left."""
    f = _font(26, True)
    tw = d.textlength(text.upper(), font=f)
    d.rectangle([M, 96, M + 64, 102], fill=GOLD)              # short accent bar
    d.text((M, 116), text.upper(), font=f, fill=GOLD)
    return tw


def _footer(d, series, idx, total, light=True):
    d.text((M, H - 104), series, font=_font(25, True), fill=GOLD)
    d.text((M, H - 72), PUBLISHER, font=_font(23, False), fill=MUT)
    n = f"{idx} / {total}"; f = _font(25, True)
    d.text((W - M - d.textlength(n, font=f), H - 88), n, font=f, fill=MUT)


def _cover_slide(cover_path, series):
    bg = _grad(); d = ImageDraw.Draw(bg)
    if cover_path and os.path.exists(cover_path):
        im = Image.open(cover_path).convert("RGB")
        r = min((W - 2 * 70) / im.width, (H - 250) / im.height)
        im = im.resize((int(im.width * r), int(im.height * r)))
        bg.paste(im, ((W - im.width) // 2, 70))
    _footer(d, series, 1, 0, light=False)  # total filled by caller via re-draw; keep simple
    return bg


def _text_slide(kicker, title, body, idx, total, series, cover=False):
    bg = _grad(); d = ImageDraw.Draw(bg)
    _tag(d, kicker or series)
    y = _fit(d, title, M, 280, W - 2 * M, 460, 70 if cover else 60, WHITE, bold=True, min_sz=40)
    d.rectangle([M, y + 24, M + 120, y + 30], fill=GOLD)     # gold rule under title
    if body:
        _fit(d, body, M, y + 70, W - 2 * M, H - (y + 70) - 170, 38, MUT, bold=False, min_sz=28)
    _footer(d, series, idx, total)
    return bg


def _figure_slide(kicker, caption, fig_path, idx, total, series):
    bg = _grad(); d = ImageDraw.Draw(bg)
    _tag(d, kicker)
    card = [70, 250, W - 70, 980]
    d.rounded_rectangle(card, radius=26, fill=CARD)
    fig = Image.open(fig_path).convert("RGB")
    fw, fh = card[2] - card[0] - 60, card[3] - card[1] - 60
    r = min(fw / fig.width, fh / fig.height); fig = fig.resize((int(fig.width * r), int(fig.height * r)))
    bg.paste(fig, (card[0] + 30 + (fw - fig.width) // 2, card[1] + 30 + (fh - fig.height) // 2))
    _fit(d, caption, M, 1015, W - 2 * M, 150, 38, WHITE, bold=True, min_sz=28)
    _footer(d, series, idx, total)
    return bg


def _clean(s: str, n: int = 150) -> str:
    s = re.sub(r"\s+", " ", re.sub(r"[*_`>#]", "", s)).strip()
    if len(s) <= n:
        return s
    cut = s[:n]; m = list(re.finditer(r"[.!?]\s", cut))
    return cut[: m[-1].end()].strip() if m else cut.rsplit(" ", 1)[0] + "…"


def _aha_line(chapter: dict, n: int = 165) -> str:
    """Pull the chapter's scroll-stopper — what a human would quote — not its first sentence (GB [454]).
    Priority: pull-quote > bold callout (prefer one with a number/contrast) > stat sentence > first sentence."""
    body = chapter.get("body", []) or []
    text = " ".join(body)
    # 1. pull-quote  > *"..."*  /  > "..."
    for ln in body:
        m = re.search(r'>\s*\*?"([^"]{18,170})"', ln)
        if m:
            return m.group(1).strip()
    bolds = [b.strip(" .") for b in re.findall(r"\*\*([^*]{16,150})\*\*", text)]
    # 2. bold callout WITH a number/contrast (the most viral)
    for b in bolds:
        if re.search(r"\d|\binstead of\b|\bnot\b.*\bbut\b", b, re.I):
            return _clean(b, n)
    # 3. any bold callout
    if bolds:
        return _clean(bolds[0], n)
    # 4. stat-bearing sentence
    for s in re.split(r"(?<=[.!?])\s+", re.sub(r"[*_`>#]", "", text)):
        if re.search(r"\b\d+\s?%|\$\d|\b\d+\s*(hours?|weeks?|days?|minutes|seconds)\b", s) and 20 < len(s) < n + 10:
            return s.strip()
    return _clean(chapter.get("first_para", ""), n)


def generate(book_id: str) -> dict:
    ms = C.latest_manuscript(book_id)
    if not ms:
        raise SystemExit(f"no manuscript for {book_id}")
    book = C.parse_book(ms.read_text(encoding="utf-8"))
    title, chapters = book["title"], book["chapters"]
    series = _series(book_id)
    bd = C.book_dir(book_id)
    cover = next((str(bd / "final" / n) for n in ("cover_KDP.png", "cover_v2_hero.png", "cover_front_KDP.png")
                  if bd and (bd / "final" / n).exists()), None)
    figs = sorted((bd / "images").glob("fig_*.png")) if bd and (bd / "images").exists() else []

    slides = [("cover", {})]
    body_ch = [c for c in chapters if c.get("first_para")]
    fi = 0
    for i, c in enumerate(body_ch):
        if len(slides) >= 9:
            break
        slides.append(("text", {"kicker": c["label"], "title": c["title"], "body": _aha_line(c)}))
        if figs and i % 3 == 1 and fi < len(figs) and len(slides) < 9:
            slides.append(("fig", {"kicker": "How it works", "caption": c["title"], "fig": str(figs[fi])})); fi += 1
    slides.append(("cta", {}))
    total = len(slides)

    dd = C.dist_dir(book_id)
    cdir = dd / "linkedin_carousel"; cdir.mkdir(exist_ok=True)
    for f in cdir.glob("slide_*.png"):
        f.unlink()
    content = []
    for i, (kind, s) in enumerate(slides, 1):
        if kind == "cover":
            img = _cover_slide(cover, series)
            d = ImageDraw.Draw(img); _footer(d, series, i, total)  # correct total
            content.append({"kicker": series, "title": title, "cover_art": os.path.basename(cover) if cover else None})
        elif kind == "cta":
            img = _text_slide("Read it", "Bring this playbook into your operation.", AMAZON_CTA, i, total, series, cover=True)
            content.append({"kicker": "Read it", "title": "Bring this playbook into your operation.", "body": AMAZON_CTA})
        elif kind == "fig":
            img = _figure_slide(s["kicker"], s["caption"], s["fig"], i, total, series)
            content.append({"kicker": s["kicker"], "title": s["caption"], "figure": os.path.basename(s["fig"])})
        else:
            img = _text_slide(s["kicker"], s["title"], s.get("body", ""), i, total, series)
            content.append({"kicker": s["kicker"], "title": s["title"], "body": s.get("body", "")})
        img.save(cdir / f"slide_{i:02d}.png")
    meta = {"slides": total, "dims": "1080x1350", "palette": ["navy gradient", "gold #C9A95E"],
            "series": series, "book": title, "publisher": PUBLISHER, "cover_art": bool(cover),
            "figures_used": fi, "cta": AMAZON_CTA, "png_rendered": total, "svg_dir": str(cdir.relative_to(C.REPO))}
    src = f"cover art + {len(body_ch)} chapters + {fi} book figures + CTA"
    C.write_asset(book_id, "linkedin_carousel", content, meta, src, ms)
    return {"slides": total, "figures": fi, "cover_art": bool(cover), "series": series, "book": title}


if __name__ == "__main__":
    import json
    print(json.dumps(generate(sys.argv[1]), indent=2))
