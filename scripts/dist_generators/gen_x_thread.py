#!/usr/bin/env python3
"""gen_x_thread.py — viral X thread from a SEALED manuscript (GB [454] §A).

Distinct from the carousel (an argument thread, not chapter slides): a scroll-stopping HOOK (carries the cover
image) -> aha/stat per post woven with thread connectors -> Amazon CTA. Each post is one value/aha beat.
Pulls the book's real aha lines (stats, bold callouts, pull-quotes), not first sentences. Series-canonical brand.
Spec: distribution_standard.yaml#asset_specs.x_thread + #distribution_quality_board.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dist_common as C

MAX = 280
SERIES = {"agentic_playbooks": "Agentic AI Playbooks for Executives", "kdp_root": "The Executive Series"}
CONNECTORS = ["Here's the problem 👇", "The shift:", "The number that matters:", "What actually changes:",
              "Why it compounds:", "The part executives miss:", "What this unlocks:"]


def _series(book_id):
    return SERIES["agentic_playbooks"] if "agentic_playbooks" in str(C.book_dir(book_id) or "") else SERIES["kdp_root"]


def _clip(s, n=MAX):
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def generate(book_id: str) -> dict:
    ms = C.latest_manuscript(book_id)
    if not ms:
        raise SystemExit(f"no manuscript for {book_id}")
    book = C.parse_book(ms.read_text(encoding="utf-8"))
    title, series = book["title"], _series(book_id)
    chapters = [c for c in book["chapters"] if c.get("first_para")]
    bd = C.book_dir(book_id)
    cover = next((str(bd / "final" / n) for n in ("cover_KDP.png", "cover_v2_hero.png")
                 if bd and (bd / "final" / n).exists()), None)

    # X draws from the book's pull-quotes + Industry-Signal STATS (distinct from the carousel's chapter aha).
    md = ms.read_text(encoding="utf-8")
    pool = [p for p in C.viral_pool(md) if p]
    if len(pool) < 5:   # fall back to chapter aha to reach thread length
        pool += [a for a in (C.aha_line(c) for c in chapters) if a and a not in pool]
    # most viral first: a number/$ / stark contrast
    viral = [a for a in pool if re.search(r"\d|\bcannot\b|\binstead of\b", a, re.I)]
    rest = [a for a in pool if a not in viral]
    ordered = viral + rest

    posts = []
    # 1 — HOOK (carries the image): the single strongest line
    hook = ordered[0] if ordered else (book["subtitle"] or title)
    posts.append(_clip(f"{hook}\n\n🧵 on {title} —"))
    # 2..n — one aha per post, thread connectors (punctuation separators; no header bleed)
    for i, a in enumerate(ordered[1:7], 0):
        conn = CONNECTORS[i % len(CONNECTORS)]
        posts.append(_clip(f"{conn}\n\n{a}"))
    # CTA — clickable Amazon + the series
    posts.append(_clip(f"This is {title}, Book 1 of \"{series}.\"\n\n"
                       f"Get the full playbook on Amazon — search \"{title} Mangum.\""))
    posts = posts[:9]
    while len(posts) < 5:
        posts.append(_clip(CONNECTORS[len(posts) % len(CONNECTORS)] + "\n\n" + (rest[len(posts)] if len(rest) > len(posts) else title)))

    meta = {"posts": len(posts), "char_limit": MAX, "max_len": max(len(p) for p in posts),
            "starting_image": (Path(cover).name if cover else None), "series": series,
            "cta": "Amazon — search the title + Mangum"}
    src = f"hook + {len(posts)-2} aha beats + Amazon CTA (book stats/quotes)"
    C.write_asset(book_id, "x_thread", posts, meta, src, ms)
    return {"posts": len(posts), "starting_image": bool(cover), "series": series, "source": src}


if __name__ == "__main__":
    import json
    print(json.dumps(generate(sys.argv[1]), indent=2))
