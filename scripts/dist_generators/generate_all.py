#!/usr/bin/env python3
"""generate_all.py — run the v1 distribution asset generators (x_thread · linkedin_carousel · substack_excerpt)
for one book_id (derive-from-sealed). Usage: python3 generate_all.py <book_id>"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_x_thread, gen_linkedin_carousel, gen_substack_excerpt  # noqa: E401


def generate(book_id: str) -> dict:
    out = {}
    out["x_thread"] = gen_x_thread.generate(book_id)
    out["linkedin_carousel"] = gen_linkedin_carousel.generate(book_id)
    out["substack_excerpt"] = gen_substack_excerpt.generate(book_id)
    return out


if __name__ == "__main__":
    import json
    bid = sys.argv[1]
    res = generate(bid)
    print(f"generated v1 asset set for {bid}:")
    print(json.dumps(res, indent=2))
