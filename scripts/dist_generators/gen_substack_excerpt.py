#!/usr/bin/env python3
"""gen_substack_excerpt.py — derive an 800–1500 word Substack excerpt + newsletter draft from a SEALED
manuscript. Pure extraction of a self-contained section of KM's prose + a light templated frame; records
provenance. Spec: distribution_standard.yaml#asset_specs.substack_excerpt."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dist_common as C

LO, HI = 800, 1500


def _trim_words(text: str, n: int) -> str:
    words = text.split()
    if len(words) <= n:
        return text
    cut = " ".join(words[:n])
    # back off to a sentence boundary
    m = list(re.finditer(r"[.!?]\s", cut))
    return (cut[: m[-1].end()].strip() if m else cut.strip())


def generate(book_id: str) -> dict:
    ms = C.latest_manuscript(book_id)
    if not ms:
        raise SystemExit(f"no manuscript for {book_id}")
    book = C.parse_book(ms.read_text(encoding="utf-8"))
    title, sub, chapters = book["title"], book["subtitle"], book["chapters"]
    # assemble a self-contained excerpt from the first substantive chapter(s)
    paras, wc, used = [], 0, None
    for c in chapters:
        if used is None and c.get("body"):
            used = c["label"]
        for p in c["body"]:
            p = re.sub(r"^[#>*\-\s]+", "", p).strip()
            if not p:
                continue
            w = C.word_count(p)
            if wc + w > HI and wc >= LO:
                break
            paras.append(p); wc += w
        if wc >= LO:
            break
    excerpt = "\n\n".join(paras)
    if C.word_count(excerpt) > HI:
        excerpt = _trim_words(excerpt, HI - 30)
    words = C.word_count(excerpt)
    intro = (f"# {title}\n\n*{sub}*\n\n"
             "This week's excerpt from the sovereign library — the working sections KM actually uses:\n\n---\n\n")
    outro = ("\n\n---\n\nRead the full book on Amazon / KDP. From the Mangum sovereign library — "
             "built for lasting, generational prosperity, sovereignty over dependency.")
    newsletter = intro + excerpt + outro
    dd = C.dist_dir(book_id)
    (dd / "substack_excerpt.md").write_text(newsletter, encoding="utf-8")
    content = {"title": title, "subtitle": sub, "excerpt": excerpt, "newsletter": newsletter}
    meta = {"words": words, "section": used or "opening"}
    src = f"{used or 'opening'} (self-contained section)"
    C.write_asset(book_id, "substack_excerpt", content, meta, src, ms)
    return {"words": words, "section": used, "source": src}


if __name__ == "__main__":
    import json
    print(json.dumps(generate(sys.argv[1]), indent=2))
