#!/usr/bin/env python3
"""board_findings_archive.py — the PERMANENT, aggregated home for adversarial-board findings (KM 2026-06-23).

The per-volume board `.md` files are the human artifact (and are git-committed), but they are scattered across
volume dirs and not queryable as one record. This is the durable, append-only, hash-chained ledger that
aggregates every board's findings across all volumes — so the Forward Feedback Loop can see recurring
finding-types (and promote them to canon, the way the adversarial-boards standard itself became canon), and so the
"iron-clad aligned-intelligence memory" discipline holds: a replayable record of what the boards found, when, and
how it was disposed.

Each board `.md` carries an embedded ```rigor``` block ({board, book_id, findings[], section_coverage[]}). This
script harvests those findings and appends one hash-chained row per finding to memory/board_findings/ledger.ndjson.

Usage:
  python3 scripts/board_findings_archive.py archive <book_id> [--at YYYY-MM-DDTHH:MM]   # harvest + append
  python3 scripts/board_findings_archive.py verify                                       # recompute the chain
  python3 scripts/board_findings_archive.py query [--book B] [--severity S] [--board BD] # filter
  python3 scripts/board_findings_archive.py recurring [--min 2]                          # FFL: repeated finding-types
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LEDGER = REPO / "memory" / "board_findings" / "ledger.ndjson"
KDP = Path("/home/kmangum/work-repos/mangumcfo/breathline-books-vault/kdp")
BOARD_GLOBS = ["*editorial_board_review*.md", "*virality_to_ux_translation*.md", "*tech_arch_review*.md"]


def _vol_dir(book_id: str) -> Path | None:
    """Resolve a volume's latest v* dir from the book_id, wherever it lives in the kdp tree."""
    hits = sorted(glob.glob(str(KDP / "**" / book_id / "v*"), recursive=True))
    dirs = [Path(h) for h in hits if Path(h).is_dir()]
    return sorted(dirs)[-1] if dirs else None


def _rigor_block(text: str) -> dict | None:
    m = re.search(r"```rigor\s*\n(.*?)\n```", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        return None


def _row_hash(prev_hash: str, payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256((prev_hash + body).encode("utf-8")).hexdigest()


def _read_chain() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]


def _existing_keys(rows: list[dict]) -> set:
    # idempotent re-archive: a finding is keyed by (book_id, board, finding_id)
    return {(r["book_id"], r["board"], r["finding_id"]) for r in rows}


def archive(book_id: str, at: str | None) -> int:
    vdir = _vol_dir(book_id)
    if not vdir:
        print(f"✗ no volume dir for {book_id}")
        return 1
    boards = sorted({p for g in BOARD_GLOBS for p in vdir.glob(g)})
    if not boards:
        print(f"✗ no board .md files in {vdir}")
        return 1
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    rows = _read_chain()
    seen = _existing_keys(rows)
    prev = rows[-1]["hash"] if rows else "genesis"
    sealed_at = at or "unstamped"   # pass --at for a real timestamp (kept out of hash-free determinism otherwise)
    added = 0
    with LEDGER.open("a", encoding="utf-8") as fh:
        for bpath in boards:
            data = _rigor_block(bpath.read_text(encoding="utf-8"))
            if not data:
                print(f"  ! {bpath.name}: no rigor block — skipped")
                continue
            board = data.get("board", "?")
            for fd in data.get("findings", []):
                key = (book_id, board, fd.get("id", "?"))
                if key in seen:
                    continue
                payload = {
                    "book_id": book_id, "board": board, "finding_id": fd.get("id", "?"),
                    "severity": fd.get("severity", "?"), "disposition": fd.get("disposition", ""),
                    "obligation_id": fd.get("obligation_id", ""), "detail": fd.get("detail", ""),
                    "lgp_alignment": fd.get("lgp_alignment", ""), "source": bpath.name, "sealed_at": sealed_at,
                }
                h = _row_hash(prev, payload)
                row = {**payload, "prev_hash": prev, "hash": h}
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                prev = h
                seen.add(key)
                added += 1
    print(f"✓ archived {added} finding(s) from {len(boards)} board(s) for {book_id} → {LEDGER.relative_to(REPO)}")
    return 0


def verify() -> int:
    rows = _read_chain()
    prev = "genesis"
    for i, r in enumerate(rows):
        payload = {k: r[k] for k in ("book_id", "board", "finding_id", "severity", "disposition",
                                     "obligation_id", "detail", "lgp_alignment", "source", "sealed_at")}
        if r["prev_hash"] != prev or _row_hash(prev, payload) != r["hash"]:
            print(f"✗ chain broken at row {i} ({r.get('book_id')}/{r.get('finding_id')})")
            return 1
        prev = r["hash"]
    books = sorted({r["book_id"] for r in rows})
    mat = sum(1 for r in rows if r["severity"] == "material")
    print(f"✓ chain OK — {len(rows)} findings across {len(books)} volume(s); {mat} material. books={books}")
    return 0


def query(book: str | None, severity: str | None, board: str | None) -> int:
    rows = _read_chain()
    out = [r for r in rows
           if (not book or r["book_id"] == book)
           and (not severity or r["severity"] == severity)
           and (not board or r["board"] == board)]
    for r in out:
        print(f"  {r['book_id']} · {r['board']} · {r['finding_id']} [{r['severity']}/{r['disposition']}] "
              f"{r['detail'][:80]}")
    print(f"— {len(out)} finding(s)")
    return 0


def recurring(min_n: int) -> int:
    """FFL surface: finding-type keywords recurring across >= min_n DISTINCT volumes — promotion candidates."""
    rows = _read_chain()
    KW = ["sod", "segregation", "anchor", "key custody", "overclaim", "circular", "fails closed", "software",
          "forward-map", "forward map", "double-entry", "double entry", "legibility", "strawman", "figure",
          "see it work", "hook", "atrium", "evidence tier", "scale"]
    hits: dict[str, set] = {k: set() for k in KW}
    for r in rows:
        d = (r["detail"] + " " + r["finding_id"]).lower()
        for k in KW:
            if k in d:
                hits[k].add(r["book_id"])
    flagged = {k: sorted(v) for k, v in hits.items() if len(v) >= min_n}
    if not flagged:
        print(f"— no finding-type recurs across ≥{min_n} volumes yet")
        return 0
    print(f"FFL promotion candidates (recur across ≥{min_n} volumes — consider codifying into book_standard.yaml):")
    for k, books in sorted(flagged.items(), key=lambda x: -len(x[1])):
        print(f"  · '{k}' — {len(books)} volumes: {books}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Permanent hash-chained home for adversarial-board findings")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("archive"); a.add_argument("book_id"); a.add_argument("--at", default=None)
    sub.add_parser("verify")
    q = sub.add_parser("query"); q.add_argument("--book"); q.add_argument("--severity"); q.add_argument("--board")
    rc = sub.add_parser("recurring"); rc.add_argument("--min", type=int, default=2)
    args = ap.parse_args()
    if args.cmd == "archive":
        return archive(args.book_id, args.at)
    if args.cmd == "verify":
        return verify()
    if args.cmd == "query":
        return query(args.book, args.severity, args.board)
    if args.cmd == "recurring":
        return recurring(args.min)
    return 2


if __name__ == "__main__":
    sys.exit(main())
