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

LO, HI = 600, 1100   # GB [454]: shorter + scannable, Reader's-Digest discipline (was 800-1500)
SERIES = {"agentic_playbooks": "Agentic AI Playbooks for Executives", "kdp_root": "The Executive Series"}


def _clean_para(p: str) -> str:
    """Strip only BLOCK markers (heading/blockquote/list bullet) — never inline emphasis. The old greedy
    ^[#>*\\-\\s]+ ate the leading * / ** of full-line pullquotes & bold callouts, orphaning the closer
    (the reader-facing slop GB's sample read caught). Bullets are '* '/'- ' (marker+SPACE); emphasis is
    '*word'/'**word' (no space) — so a space-anchored bullet strip leaves emphasis intact."""
    p = p.rstrip()
    p = re.sub(r"^\s{0,3}#{1,6}\s+", "", p)     # ATX heading
    p = re.sub(r"^\s{0,3}>\s?", "", p)          # blockquote
    p = re.sub(r"^\s{0,3}[-+]\s+", "", p)       # list bullet - / +
    p = re.sub(r"^\s{0,3}\*\s+", "", p)         # list bullet '* ' (star THEN space, not emphasis)
    return _balance(p.strip())


def _balance(p: str) -> str:
    """Safety net: no orphaned emphasis reaches the reader. Odd ** (or odd single *) → strip the strays."""
    if p.count("**") % 2:
        p = p.replace("**", "")
    if len(re.findall(r"(?<!\*)\*(?!\*)", p)) % 2:
        p = re.sub(r"(?<!\*)\*(?!\*)", "", p)
    return p


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
        in_code = False
        for raw in c["body"]:
            st = raw.strip()
            if st.startswith("```"):           # code-fence toggle — skip code blocks entirely
                in_code = not in_code
                continue
            if in_code or st.startswith("|") or st.startswith("[VISUAL"):  # code / table / figure marker
                continue
            p = re.sub(r"\[VISUAL:[^\]]*\]", "", raw)   # inline figure markers
            p = _clean_para(p)
            if not p or "```" in p:
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
    series = SERIES["agentic_playbooks"] if "agentic_playbooks" in str(C.book_dir(book_id) or "") else SERIES["kdp_root"]
    # reader-in-center (GB [454]): never the author; speak to the executive reading this.
    intro = (f"# {title}\n\n*{sub}*\n\n"
             "**If your team still builds forecasts the slow way, this is for you.** Here is the shift, in plain "
             "terms — read the bolded lines and you have the whole argument:\n\n---\n\n")
    outro = (f"\n\n---\n\nThis is **{title}**, part of *{series}*. Get the full playbook on Amazon — "
             f"search **\"{title} Mangum.\"** New playbook every week.")
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
