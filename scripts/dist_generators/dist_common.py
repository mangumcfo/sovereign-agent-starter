#!/usr/bin/env python3
"""dist_common.py — shared helpers for the v1 distribution asset generators (Tiger lane, [445]).

DERIVE-FROM-SEALED: every generator reads the SEALED manuscript and EXTRACTS/condenses KM's own prose — it
never re-authors. Each asset records its source_section + the sealed_commit so distribution_contract.py's
derive_provenance gate can prove the trace. Mirrors the toolchain.json provenance pattern of the book rail.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
KDP = Path("/home/kmangum/work-repos/mangumcfo/breathline-books-vault/kdp")
AGENTIC = KDP / "agentic_playbooks"
DIST_ROOT = REPO / "artifacts" / "distribution"


def _vkey(p: Path) -> tuple:
    return tuple(int(n) for n in re.findall(r"\d+", p.name)) or (0,)


def book_dir(book_id: str) -> Path | None:
    """Resolve a sealed book's latest version dir (KDP root for S0 + agentic_playbooks + series_*)."""
    for root in [KDP, AGENTIC] + sorted(KDP.glob("series_*")):
        d = root / book_id
        vers = sorted((v for v in d.glob("v*") if v.is_dir()), key=_vkey, reverse=True)
        if vers:
            return vers[0]
    return None


def latest_manuscript(book_id: str) -> Path | None:
    bd = book_dir(book_id)
    if not bd:
        return None
    mss = sorted((p for p in bd.glob("manuscript_v*.md")
                  if re.match(r"manuscript_v[0-9.]+\.md$", p.name)), key=_vkey)
    return mss[-1] if mss else None


def sealed_commit(path: Path) -> str:
    """The git commit that last sealed the manuscript (the sealed state the asset derives from)."""
    try:
        out = subprocess.run(["git", "-C", str(path.parent), "log", "-1", "--format=%H", "--", str(path.name)],
                             capture_output=True, text=True, timeout=15)
        h = out.stdout.strip()
        if h:
            return h
        out = subprocess.run(["git", "-C", str(path.parent), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=15)
        return out.stdout.strip() or "uncommitted"
    except Exception:
        return "uncommitted"


def parse_book(md: str) -> dict:
    """Extract title, subtitle, and chapters (heading + first substantive paragraph) — pure extraction."""
    md = md.replace(" -- ", " — ").replace("--", "—")  # normalize source double-hyphen → em dash
    lines = md.splitlines()
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), "")
    # subtitle: first '## ' before the first chapter, that isn't boilerplate
    skip = ("table of contents", "dedication", "acknowledgments", "about this series", "before you begin",
            "preface", "copyright")
    subtitle = ""
    for l in lines:
        if l.startswith("## "):
            t = l[3:].strip()
            if t.lower() not in skip:
                subtitle = t
                break
    chapters = []
    cur = None
    for l in lines:
        m = re.match(r"^#\s+(Chapter\s+\d+|Appendix\s+[A-Z0-9]+)\s*[:\-—]?\s*(.*)$", l, re.I)
        if m:
            if cur:
                chapters.append(cur)
            label = m.group(1).strip()
            cur = {"label": label, "title": (m.group(2).strip() or label), "body": []}
        elif cur is not None:
            if l.startswith("#"):
                continue
            if l.strip():
                cur["body"].append(l.strip())
    if cur:
        chapters.append(cur)
    for c in chapters:
        c["first_para"] = _first_sentence(" ".join(c["body"]))
        c["text"] = " ".join(c["body"])
    return {"title": title, "subtitle": subtitle, "chapters": chapters}


def _first_sentence(text: str, max_chars: int = 240) -> str:
    text = re.sub(r"\s+", " ", re.sub(r"[*_`>#]", "", text)).strip()
    if not text:
        return ""
    # first 1–2 sentences, capped
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = parts[0]
    if len(out) < 90 and len(parts) > 1:
        out = (out + " " + parts[1]).strip()
    return out[:max_chars].rstrip()


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def aha_line(chapter: dict, n: int = 200) -> str:
    """The chapter's scroll-stopper (GB [454]): pull-quote > number/contrast bold callout > stat sentence >
    first sentence. What a human would actually quote — not the opener."""
    body = chapter.get("body", []) or []
    text = " ".join(body)
    for ln in body:
        m = re.search(r'>\s*\*?"([^"]{18,190})"', ln)
        if m:
            return m.group(1).strip()
    bolds = [b.strip(" .") for b in re.findall(r"\*\*([^*]{16,180})\*\*", text)]
    for b in bolds:
        if re.search(r"\d|\binstead of\b|\bnot\b.*\bbut\b|\bcannot\b", b, re.I):
            return _clean_plain(b, n)
    if bolds:
        return _clean_plain(bolds[0], n)
    for s in re.split(r"(?<=[.!?])\s+", re.sub(r"[*_`>#]", "", text)):
        if re.search(r"\b\d+\s?%|\$\d|\b\d+\s*(hours?|weeks?|days?|minutes|seconds)\b", s) and 20 < len(s) < n:
            return s.strip()
    return _clean_plain(chapter.get("first_para", ""), n)


def viral_pool(md_text: str) -> list[str]:
    """Standalone punchy lines for the X thread — pull-quotes + Industry-Signal stats — DISTINCT from the
    carousel's per-chapter aha (GB [454] A1: per-channel-distinct). Dedup, source-stripped."""
    out = []
    for m in re.finditer(r'>\s*\*?"([^"]{18,210})"', md_text):
        out.append(m.group(1).strip())
    for m in re.finditer(r"Industry Signal:\**\s*([^\n]{30,240})", md_text):
        out.append(re.sub(r"\s*\(Source.*$|\*", "", m.group(1)).strip())
    seen, res = set(), []
    for x in out:
        k = re.sub(r"\W", "", x[:48]).lower()
        if k and k not in seen:
            seen.add(k); res.append(x)
    return res


def _clean_plain(s: str, n: int) -> str:
    s = re.sub(r"\s+", " ", re.sub(r"[*_`>#]", "", s)).strip()
    if len(s) <= n:
        return s
    cut = s[:n]; m = list(re.finditer(r"[.!?]\s", cut))
    return cut[: m[-1].end()].strip() if m else cut.rsplit(" ", 1)[0] + "…"


def dist_dir(book_id: str) -> Path:
    d = DIST_ROOT / book_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_asset(book_id: str, name: str, content, meta: dict, source_section: str, manuscript: Path) -> Path:
    """Write <dist>/<name>.json (content + meta + provenance) and update the aggregate dist_provenance.json."""
    dd = dist_dir(book_id)
    sealed = sealed_commit(manuscript)
    asset = {"type": name, "book_id": book_id, "content": content, "meta": meta,
             "provenance": {"source_section": source_section, "sealed_commit": sealed,
                            "source_manuscript": str(manuscript.relative_to(KDP.parent))}}
    (dd / f"{name}.json").write_text(json.dumps(asset, indent=2, ensure_ascii=False), encoding="utf-8")
    # aggregate provenance
    pf = dd / "dist_provenance.json"
    prov = {}
    if pf.exists():
        try:
            prov = json.loads(pf.read_text(encoding="utf-8"))
        except Exception:
            prov = {}
    prov.setdefault("book_id", book_id)
    prov["sealed_commit"] = sealed
    prov["source_manuscript"] = str(manuscript.relative_to(KDP.parent))
    prov["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    prov.setdefault("assets", {})[name] = {"source_section": source_section}
    pf.write_text(json.dumps(prov, indent=2, ensure_ascii=False), encoding="utf-8")
    return dd / f"{name}.json"
