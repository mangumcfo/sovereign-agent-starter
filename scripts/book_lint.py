#!/usr/bin/env python3
"""book_lint — enforce the S2 "pen" production standards on a manuscript (+ built PDF).

Why (KM 2026-06-18): S2 absorbed weeks of human typographic discipline that was never written as an
enforceable standard, so S3 silently drifted (TOC, bullets, callouts, editing artifacts, chapter structure).
This lint reads `book_standards/book_standard.yaml#production_standards` (the machine source of truth) and
checks the manuscript against it, so the discipline scales to every future volume without re-litigation.
Companion to pdf_parity_lint.py (fonts/raw-markup) — this one covers structure/layout.

CLI: book_lint.py <manuscript.md> [--json]
Exit 0 GREEN / 1 RED. Read-only.
"""
import sys, re, json
from pathlib import Path

_DEFAULT = {
    "banned_manuscript_artifacts": [r"no ISBN required", r"RATIFIED by KM", r"(?m)^---\s*$", r"(?m)^\*\*\*\s*$"],
    "toc_require_preflight_line": True,
    "chapter_end_order": ["Industry Signal", "Your Next Steps", "Receipt"],
}


def _load() -> dict:
    here = Path(__file__).resolve()
    for root in here.parents:
        for cand in [root / "breathline-books-vault" / "book_standards" / "book_standard.yaml",
                     *root.glob("*/breathline-books-vault/book_standards/book_standard.yaml")]:
            if cand.exists():
                try:
                    import yaml
                    ps = (yaml.safe_load(cand.read_text(encoding="utf-8")) or {}).get("production_standards", {})
                    return {
                        "banned": ps.get("banned_manuscript_artifacts", _DEFAULT["banned_manuscript_artifacts"]),
                        "preflight": ps.get("toc", {}).get("require_preflight_line", True),
                        "end_order": ps.get("chapter_end_order", _DEFAULT["chapter_end_order"]),
                        "_source": str(cand),
                    }
                except Exception:
                    pass
    return {"banned": _DEFAULT["banned_manuscript_artifacts"], "preflight": True,
            "end_order": _DEFAULT["chapter_end_order"], "_source": "built-in default"}


def _toc_block(t: str) -> str:
    m = re.search(r"(?ms)^##+ Table of Contents\s*\n(.*?)(?=\n\\newpage|\n##+ )", t)
    return m.group(1) if m else ""


def check_banned_artifacts(t: str, crit: dict) -> dict:
    hits = {pat: len(re.findall(pat, t)) for pat in crit["banned"] if re.findall(pat, t)}
    return {"check": "banned_artifacts", "pass": not hits,
            "detail": ("found: " + ", ".join(f"{p}×{n}" for p, n in hits.items())) if hits else "no editing artifacts"}


def check_toc_format(t: str, crit: dict) -> dict:
    toc = _toc_block(t)
    issues = []
    if not toc:
        return {"check": "toc_format", "pass": False, "detail": "no TOC section found"}
    bullets = len(re.findall(r"(?m)^- ", toc))
    numbered = len(re.findall(r"(?m)^\d+\. ", toc))
    grouped = len(re.findall(r"(?m)^\*\*(Front Matter|Chapters|Back Matter)\*\*", toc))
    if grouped:
        issues.append(f"grouped bold headers ({grouped}) — S2 uses a flat list")
    if numbered:
        issues.append(f"numbered entries ({numbered}) — use '- Chapter N: Title'")
    # chapter entries must read "Chapter N: Title" (matches the heading so links resolve)
    chap_headings = re.findall(r"(?m)^#{1,2} (Chapter \d+: .+)$", t)
    for h in chap_headings:
        if f"- {h}" not in toc and h not in toc:
            issues.append(f"TOC missing/!=heading: '{h[:40]}'")
    if crit["preflight"] and "Preflight" not in toc:
        issues.append("Preflight line missing from TOC")
    return {"check": "toc_format", "pass": not issues,
            "detail": (f"bullets={bullets} numbered={numbered} grouped={grouped} · " +
                       ("; ".join(issues[:3]) if issues else "flat bulleted, entries match headings"))[:88]}


def check_chapter_end_order(t: str, crit: dict) -> dict:
    """Receipt must close the chapter — after Industry Signal + Your Next Steps (not float mid-chapter)."""
    lines = t.splitlines()
    chap_idx = [i for i, l in enumerate(lines) if re.match(r"^# Chapter \d+", l)]
    bad = []
    for k, start in enumerate(chap_idx):
        end = chap_idx[k + 1] if k + 1 < len(chap_idx) else len(lines)
        body = lines[start:end]
        def pos(pat):
            for j, l in enumerate(body):
                if re.search(pat, l):
                    return j
            return None
        sig, steps, rec = pos(r"^## Industry Signal"), pos(r"^## Your Next Steps"), pos(r"^> \*\*RECEIPT")
        cnum = re.match(r"^# Chapter (\d+)", lines[start]).group(1)
        if rec is None:
            bad.append(f"Ch{cnum}:no-receipt")
        elif (steps is not None and rec < steps) or (sig is not None and rec < sig):
            bad.append(f"Ch{cnum}:receipt-mid-chapter")
    return {"check": "chapter_end_order", "pass": not bad,
            "detail": ("; ".join(bad) if bad else f"{len(chap_idx)} chapters: receipt closes each")[:88]}


def check_callout_clumping(t: str) -> dict:
    """Consecutive '**Label:**' lines with no blank between clump into one paragraph (Markdown). S2 separates."""
    lines = t.splitlines()
    clumps = 0
    label = re.compile(r"^\*\*[^*]+:\*\*")
    for i in range(len(lines) - 1):
        if label.match(lines[i].strip()) and label.match(lines[i + 1].strip()):
            clumps += 1
    return {"check": "callout_clumping", "pass": clumps == 0,
            "detail": (f"{clumps} clumped label-list lines (need blank-line separation)" if clumps
                       else "no clumped lists")}


def check_figure_placement(t: str) -> dict:
    """No >=2 [VISUAL:] markers back-to-back — each figure sits beside the prose it illustrates."""
    lines = t.splitlines()
    vis = [i for i, l in enumerate(lines) if l.startswith("[VISUAL:")]
    adjacent = sum(1 for a, b in zip(vis, vis[1:]) if b - a <= 2)
    return {"check": "figure_placement", "pass": adjacent == 0,
            "detail": (f"{adjacent} figure markers clumped (<=2 lines apart)" if adjacent
                       else f"{len(vis)} figures, each beside its prose")}


def lint(md: str) -> dict:
    crit = _load()
    t = Path(md).read_text(encoding="utf-8", errors="ignore")
    checks = [check_banned_artifacts(t, crit), check_toc_format(t, crit),
              check_chapter_end_order(t, crit), check_callout_clumping(t), check_figure_placement(t)]
    return {"manuscript": Path(md).name, "criteria_source": crit["_source"],
            "pass": all(c["pass"] for c in checks), "checks": checks}


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: book_lint.py <manuscript.md> [--json]"); return 2
    r = lint(args[0])
    if "--json" in args:
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        mark = "GREEN ✓" if r["pass"] else "RED ✗"
        print(f"\n== book_lint: {r['manuscript']} == [{mark}]  (criteria: {r['criteria_source']})")
        for c in r["checks"]:
            print(f"  [{'✓' if c['pass'] else '✗ RED':>6}] {c['check']:<20} {c['detail']}")
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
