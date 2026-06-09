#!/usr/bin/env python3
"""
build_book_registry.py — Helix increment #1: the deterministic title→artifacts registry.

Scans the KDP vault and writes ONE canonical map (book_id → its artifacts) that every surface reads
(book_pdf · producer · build · coherence · pipeline) — no hardcoded paths, no glob heuristics. Receipted
(sha256) + self-validating (present flags), regenerable from vault state. The file-management "helix".

    python3 scripts/build_book_registry.py            # write memory/book_artifacts_registry.json
    python3 scripts/build_book_registry.py --status    # print a status table, no write

∞Δ∞ Define once; every surface + every node reads it; every title resolves. ∞Δ∞
"""
from __future__ import annotations
import glob
import hashlib
import json
import os
import re
import sys
import time

VAULT = "/home/kmangum/work-repos/mangumcfo/breathline-books-vault/kdp"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "memory", "book_artifacts_registry.json")


def _rel(p):
    return os.path.relpath(p, VAULT) if p else None


def _newest(paths):
    paths = [p for p in paths if p and os.path.isfile(p)]
    return sorted(paths, key=os.path.getmtime, reverse=True)[0] if paths else None


def _ver_key(vdir):
    m = re.search(r"v(\d+)\.(\d+)", os.path.basename(vdir))
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def build() -> dict:
    # A book = a directory holding a v*/ subdir that contains final/ and/or a manuscript.
    bydir = {}   # book_dir -> {version_dir (newest)}
    for marker in glob.glob(os.path.join(VAULT, "**", "v*", "final"), recursive=True) + \
            glob.glob(os.path.join(VAULT, "**", "v*", "manuscript_v*.md"), recursive=True):
        vdir = marker if os.path.isdir(marker) and os.path.basename(marker) == "final" else os.path.dirname(marker)
        if os.path.basename(vdir) == "final":
            vdir = os.path.dirname(vdir)
        if not re.match(r"v\d", os.path.basename(vdir)):
            continue
        bdir = os.path.dirname(vdir)
        cur = bydir.get(bdir)
        if cur is None or _ver_key(vdir) > _ver_key(cur):
            bydir[bdir] = vdir

    reg = {}
    for bdir, vdir in sorted(bydir.items()):
        bid = os.path.basename(bdir)
        series = _rel(bdir).rsplit("/", 1)[0] if "/" in _rel(bdir) else "(top-level)"
        final = os.path.join(vdir, "final")
        pdfs = glob.glob(os.path.join(final, "*.pdf"))
        interiors = [p for p in pdfs if "cover" not in os.path.basename(p).lower()]
        pdf = _newest(interiors or pdfs)
        # Cover is an IMAGE artifact (cover_KDP.jpg|png) — KDP uploads the .jpg. Prefer jpg → png → any cover PDF.
        cover = (_newest(glob.glob(os.path.join(final, "cover*.jpg")) + glob.glob(os.path.join(final, "cover*.jpeg")))
                 or _newest(glob.glob(os.path.join(final, "cover*.png")))
                 or _newest([p for p in pdfs if "cover" in os.path.basename(p).lower()]))
        epub = _newest(glob.glob(os.path.join(final, "*.epub")))
        manuscript = _newest(glob.glob(os.path.join(vdir, "manuscript_v*.md")))
        reg[bid] = {
            "series": series,
            "version": os.path.basename(vdir),
            "dir": _rel(vdir),
            "manuscript": _rel(manuscript),
            "pdf": _rel(pdf),
            "epub": _rel(epub),
            "cover": _rel(cover),
            "present": {"pdf": bool(pdf), "manuscript": bool(manuscript),
                        "epub": bool(epub), "cover": bool(cover)},
        }
    body = {bid: reg[bid] for bid in sorted(reg)}
    receipt = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]
    return {
        "_meta": {
            "schema": "book-artifacts-registry-1.0 (Helix increment #1)",
            "vault": VAULT,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "receipt": receipt,
            "n_titles": len(body),
            "n_with_pdf": sum(1 for e in body.values() if e["present"]["pdf"]),
            "n_missing_pdf": sum(1 for e in body.values() if not e["present"]["pdf"]),
        },
        "books": body,
    }


def main():
    reg = build()
    if "--status" in sys.argv:
        m = reg["_meta"]
        print(f"registry: {m['n_titles']} titles · {m['n_with_pdf']} with PDF · {m['n_missing_pdf']} missing · receipt {m['receipt']}")
        for bid, e in reg["books"].items():
            flag = "✓pdf" if e["present"]["pdf"] else ("✓ms" if e["present"]["manuscript"] else "—")
            print(f"  {flag:5} {bid:46} {e['series']}")
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)
    m = reg["_meta"]
    print(f"wrote {os.path.relpath(OUT)} — {m['n_titles']} titles, {m['n_with_pdf']} with PDF, receipt {m['receipt']}")


if __name__ == "__main__":
    main()
