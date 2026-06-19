#!/usr/bin/env python3
"""gen_x_thread.py — derive a 5–9 post X thread from a SEALED manuscript (hook → point-per-chapter → CTA).
Pure extraction of KM's prose; records provenance. Spec: distribution_standard.yaml#asset_specs.x_thread."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dist_common as C

MAX_POST = 280


def _clip(s: str, n: int = MAX_POST) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def generate(book_id: str) -> dict:
    ms = C.latest_manuscript(book_id)
    if not ms:
        raise SystemExit(f"no manuscript for {book_id}")
    book = C.parse_book(ms.read_text(encoding="utf-8"))
    title, sub, chapters = book["title"], book["subtitle"], book["chapters"]
    body_ch = [c for c in chapters if c.get("first_para")][:7]  # cap so total stays ≤9
    posts = []
    hook = f"{title}" + (f" — {sub}" if sub else "")
    posts.append(_clip(f"{hook}\n\nThe through-line, in one thread 🧵"))
    for i, c in enumerate(body_ch, 1):
        posts.append(_clip(f"{i}/ {c['title']}\n\n{c['first_para']}"))
    posts.append(_clip("From the Mangum sovereign-finance library — built for lasting, "
                       "generational prosperity, not dependency. Full playbook on Amazon/KDP."))
    # guarantee 5–9
    while len(posts) < 5 and sub:
        posts.insert(1, _clip(sub))
        sub = ""
    posts = posts[:9]
    meta = {"posts": len(posts), "char_limit": MAX_POST,
            "max_len": max(len(p) for p in posts)}
    src = f"title + {len(body_ch)} chapter openers + CTA"
    C.write_asset(book_id, "x_thread", posts, meta, src, ms)
    return {"posts": len(posts), "source": src}


if __name__ == "__main__":
    import json
    print(json.dumps(generate(sys.argv[1]), indent=2))
