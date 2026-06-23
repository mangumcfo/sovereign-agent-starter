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

# Crafted lead-hooks (the generation-aid step, GB [462]/[456]) — for books where pure extraction is too dry
# to stop a scroll. Each hook is DERIVED FROM the book's own thesis (its core tension), human-phrased, not
# verbatim — the supporting beats below it stay extracted-from-sealed. Keyed by book_id; absent → auto hook.
CRAFTED_HOOKS = {
    "01_strategic_finance": ("Most founders run their company like it's one business.\n\nIt's actually four — "
                             "and the finance that wins Stage 1 will sink you by Stage 3."),
    "12_agentic_enterprise": ("By 2030, \"AI-powered\" won't be an edge.\n\nIt'll be the cost of staying open. "
                              "Here's the executive roadmap most firms will wish they'd started in 2026."),
}

# Crafted BEATS (generation-aid) for books too dense/reference-style for extraction to carry a coherent thread.
# Each beat is a tight paraphrase of the book's OWN structure (not invented) — GB judges virality; KM approves.
# strategic_finance: the book IS the Stage 1→4 growth journey; walk it (the chapter spine, not stray sentences).
CRAFTED_BEATS = {
    "01_strategic_finance": [
        "Stage 1 — Start-Up. Cash is oxygen and you ARE the finance team. One metric rules: months until you run out.",
        "Stage 2 — Growth. The phone won't stop ringing — that's the danger. Growth burns cash faster than profit refills it. More companies die of success here than of failure.",
        "Stage 3 — Maturity. The champagne years end. The job flips from chasing growth to defending the moat — and that needs a different CFO than the one who got you here.",
        "Stage 4 — Decline & Renewal. A flat P&L on the screen. This is where finance decides: reinvent, or quietly wind down. Founders rarely see it coming. The numbers always do.",
    ],
}
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
    # 1 — HOOK (carries the image): a crafted lead-hook if the book needs one, else the strongest extracted line
    crafted = CRAFTED_HOOKS.get(book_id)
    if crafted:
        posts.append(_clip(f"{crafted}\n\n🧵 on {title} —", n=MAX + 60))   # hook may run slightly long (it's the stopper)
        beats = ordered[:6]   # crafted hook didn't consume an extracted line → keep all beats
    else:
        hook = ordered[0] if ordered else (book["subtitle"] or title)
        posts.append(_clip(f"{hook}\n\n🧵 on {title} —"))
        beats = ordered[1:7]
    # 2..n — beats. Crafted beats (already self-contained) for reference-dense books; else extracted aha + connectors.
    crafted_beats = CRAFTED_BEATS.get(book_id)
    if crafted_beats:
        for b in crafted_beats:
            posts.append(_clip(b, n=MAX + 40))
    else:
        for i, a in enumerate(beats, 0):
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
