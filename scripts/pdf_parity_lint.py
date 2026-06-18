#!/usr/bin/env python3
"""pdf_parity_lint — validate a book PDF at the RENDERED-PAGE level against the S2 "pen."

Why this exists (KM 2026-06-18): every book gate to date reasons at the .md / marker level. NOTHING ever
looked at what the page actually renders. That gap let S3 V3 (Helix) ship a stray DejaVu-Serif-Bold font (the
U+25A3 receipt icon forced a font fallback the body serif fonts don't cover) and raw `**` markdown leaking to
the reader — divergences invisible to the content gates but glaring in the rendered PDF. This lint closes that
gap: it reads the actual PDF (pdffonts + pdftotext) and the source manuscript, and reports vs the approved S2
render profile. Same data-driven shape as seeit_lint.py / outline_lock_lint.py.

Criteria load from book_standards/book_standard.yaml#render_fidelity when present (the machine source of truth);
a documented built-in default is used otherwise so the lint always runs.

CLI:
  pdf_parity_lint.py <book.pdf> [--source <manuscript.md>] [--json]
  pdf_parity_lint.py --compare <s1.pdf> <s2.pdf> <s3.pdf>   # the "see the differences" table
Exit 0 = GREEN (matches the pen) · 1 = RED (a divergence). Read-only; never writes.
"""
import sys, os, re, json, subprocess, shutil
from pathlib import Path

# --- built-in defaults (used if book_standard.yaml#render_fidelity is absent) -------------------------------
# Approved font FAMILY ROOTS, measured from the S2 reference build (Sovereign_Inference_and_Memory.pdf):
# Noto-Serif* + Liberation* only. DejaVu, Noto-Color-Emoji, etc. are OUT (S2 never embeds them).
_DEFAULT = {
    "approved_font_roots": ["Noto-Serif", "Liberation"],
    # reader-facing artifacts that must NEVER reach the page (raw markup / build scaffolding).
    # CALIBRATED to PASS the S2 pen: ∞Δ∞ is NOT banned — the published S2 book carries it 5× as an
    # intentional seal mark; a check must pass S2, never exceed it (the standing rail discipline).
    "banned_reader_artifacts": [
        r"\*\*",            # raw bold markers (incl the :**** typo tail)
        r"(?m)^#{1,6}\s",   # raw markdown headers
        r"\[VISUAL:",       # un-replaced figure markers
        r"```",             # raw code fences
        r"(?m)^\s*[-*]\s",  # raw markdown bullets that never became •
    ],
    # source-level glyphs known to fall outside the approved serif coverage -> force a font fallback:
    "banned_source_glyphs": ["▣"],  # ▣ WHITE SQUARE CONTAINING BLACK SMALL SQUARE (the receipt-icon defect)
}


def _load_criteria() -> dict:
    """Load render_fidelity from book_standard.yaml (machine source of truth); fall back to built-in default."""
    here = Path(__file__).resolve()
    for root in here.parents:
        y = root / "breathline-books-vault" / "book_standards" / "book_standard.yaml"
        if not y.exists():
            # also try a sibling vault layout (mangumcfo/breathline-books-vault)
            for cand in root.glob("*/breathline-books-vault/book_standards/book_standard.yaml"):
                y = cand
                break
        if y.exists():
            try:
                import yaml
                data = yaml.safe_load(y.read_text(encoding="utf-8")) or {}
                rf = data.get("render_fidelity")
                if rf:
                    return {
                        "approved_font_roots": rf.get("approved_font_roots", _DEFAULT["approved_font_roots"]),
                        "banned_reader_artifacts": rf.get("banned_reader_artifacts", _DEFAULT["banned_reader_artifacts"]),
                        "banned_source_glyphs": rf.get("banned_source_glyphs", _DEFAULT["banned_source_glyphs"]),
                        "_source": str(y),
                    }
            except Exception:
                pass
    d = dict(_DEFAULT)
    d["_source"] = "built-in default (book_standard.yaml#render_fidelity not found)"
    return d


def _font_family(raw: str) -> str:
    """Strip the 6-char subset prefix (XXXXXX+) -> the embedded family+style name."""
    return re.sub(r"^[A-Z]{6}\+", "", raw).strip()


def _pdffonts(pdf: str) -> list[str]:
    out = subprocess.run(["pdffonts", pdf], capture_output=True, text=True).stdout
    fams = []
    for line in out.splitlines()[2:]:
        if not line.strip():
            continue
        fams.append(_font_family(line.split()[0]))
    return sorted(set(fams))


def _pdftext(pdf: str) -> str:
    return subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout


def check_fonts(pdf: str, crit: dict) -> dict:
    fams = _pdffonts(pdf)
    roots = crit["approved_font_roots"]
    stray = [f for f in fams if not any(f.startswith(r) for r in roots)]
    return {"check": "font_set", "pass": not stray, "families": fams, "stray": stray,
            "detail": (f"stray font families: {stray}" if stray else f"{len(fams)} fonts, all within {roots}")}


def check_reader_artifacts(pdf: str, crit: dict) -> dict:
    txt = _pdftext(pdf)
    hits = {}
    for pat in crit["banned_reader_artifacts"]:
        n = len(re.findall(pat, txt))
        if n:
            hits[pat] = n
    return {"check": "reader_artifacts", "pass": not hits, "hits": hits,
            "detail": ("leaked: " + ", ".join(f"{p}×{n}" for p, n in hits.items()) if hits else "no raw-markup leaks")}


def check_source_glyphs(source: str | None, crit: dict) -> dict:
    if not source or not Path(source).exists():
        return {"check": "source_glyphs", "pass": True, "detail": "no source provided (skipped)", "skipped": True}
    t = Path(source).read_text(encoding="utf-8", errors="ignore")
    found = {g: t.count(g) for g in crit["banned_source_glyphs"] if g in t}
    return {"check": "source_glyphs", "pass": not found,
            "found": {f"U+{ord(g):04X}": n for g, n in found.items()},
            "detail": ("fallback-forcing glyphs: " + ", ".join(f"U+{ord(g):04X}×{n}" for g, n in found.items())
                       if found else "no fallback-forcing glyphs in source")}


def lint(pdf: str, source: str | None = None) -> dict:
    crit = _load_criteria()
    checks = [check_fonts(pdf, crit), check_reader_artifacts(pdf, crit), check_source_glyphs(source, crit)]
    return {"pdf": os.path.basename(pdf), "criteria_source": crit["_source"],
            "pass": all(c["pass"] for c in checks), "checks": checks}


def _print_report(r: dict):
    mark = "GREEN ✓" if r["pass"] else "RED ✗"
    print(f"\n== pdf_parity_lint: {r['pdf']} == [{mark}]  (criteria: {r['criteria_source']})")
    for c in r["checks"]:
        m = "✓" if c["pass"] else ("· skip" if c.get("skipped") else "✗ RED")
        print(f"  [{m:>6}] {c['check']:<17} {c['detail']}")


def main():
    args = sys.argv[1:]
    if not args or not shutil.which("pdffonts"):
        print("usage: pdf_parity_lint.py <book.pdf> [--source <md>] [--json] | --compare <a.pdf> <b.pdf> ...")
        print("       (requires poppler: pdffonts, pdftotext)")
        return 2
    if args[0] == "--compare":
        results = [lint(p) for p in args[1:]]
        for r in results:
            _print_report(r)
        print("\n--- comparison summary ---")
        for r in results:
            strays = next((c["stray"] for c in r["checks"] if c["check"] == "font_set"), [])
            arts = next((c["hits"] for c in r["checks"] if c["check"] == "reader_artifacts"), {})
            print(f"  {r['pdf']:<42} stray_fonts={strays or 'none'}  artifacts={sum(arts.values()) if arts else 0}")
        return 0 if all(r["pass"] for r in results) else 1
    pdf = args[0]
    source = None
    if "--source" in args:
        source = args[args.index("--source") + 1]
    r = lint(pdf, source)
    if "--json" in args:
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        _print_report(r)
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
