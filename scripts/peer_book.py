#!/usr/bin/env python3
"""peer_book.py — the operator's LOCAL peer book (P0-4, AA_DAY1_NODE_SOVEREIGNTY_PATH §2/§4/§6).

What this IS
------------
A single append-only file under the operator's OWN home:  $HOME/.sovereign_peer_book.jsonl
Each line records a peer you met OUT-OF-BAND: its ``public_hex`` (128-hex) and a human ``label``
you chose, plus an optional ``where_met`` note. That is the whole of it.

What this is NOT (by construction — these are the Sovereign Peerhood kill-targets)
---------------------------------------------------------------------------------
- NOT a directory / name service / discovery beacon. It is a private file on one machine.
- NOT served, synced, or shipped. There is deliberately NO node_api route that writes, syncs,
  or serves this file; a peer book behind an HTTP route is the "network directory" capture.
  The console MAY read the file to DISPLAY it (read-only); it must never POST to a writer route,
  because there is none.
- NOT shipped with default peers. A fresh book is EMPTY. A repo that ships peer keys has shipped
  a default trust root — the opposite of sovereignty.
- NOT recognition and NOT standing. Adding a label here means "I wrote down who I think this key
  is." It confers no recognition, no peerhood, no standing. Recognition is a signed two-party act
  proven elsewhere (peerhood/recognition.py + a declared transport); a written label is just a note.

Usage
-----
  scripts/peer_book.py add  --label "Beard (vmi3366092)" --public-hex <128hex> [--where-met "in person 2026-08-13"]
  scripts/peer_book.py list [--json]
  scripts/peer_book.py path            # print the book's location and exit

The file is created 0600 under $HOME. Nothing here reaches the network.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys

# The book lives under the operator's OWN home, never inside the repo, a web root, or a shared dir.
BOOK_ENV = "SOVEREIGN_PEER_BOOK"        # test/override hook; must still resolve under a real home
BOOK_NAME = ".sovereign_peer_book.jsonl"
_HEX128 = re.compile(r"\A[0-9a-fA-F]{128}\Z")


def book_path() -> str:
    """Resolve the book path: $SOVEREIGN_PEER_BOOK if set, else $HOME/.sovereign_peer_book.jsonl.

    Refuses obviously-poisoned homes (unset, or a literal placeholder) fail-loud rather than
    silently writing the book somewhere the operator will never look.
    """
    override = os.environ.get(BOOK_ENV)
    if override:
        return os.path.abspath(os.path.expanduser(override))
    home = os.environ.get("HOME", "")
    if not home or "/path/to" in home or home.strip() in ("", "~"):
        raise SystemExit(
            "peer_book: $HOME is unset or a placeholder — refusing to guess where your peer book lives.\n"
            "  set HOME to your real home, or export SOVEREIGN_PEER_BOOK=/abs/path/to/book.jsonl")
    return os.path.join(os.path.expanduser(home), BOOK_NAME)


def _load(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    out: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for ln, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                out.append(json.loads(raw))
            except json.JSONDecodeError:
                print(f"peer_book: skipping unparseable line {ln}", file=sys.stderr)
    return out


def cmd_add(args: argparse.Namespace) -> int:
    ph = args.public_hex.strip().lower()
    if not _HEX128.match(ph):
        print("peer_book: --public-hex must be exactly 128 hex chars (an secp256k1 public_hex). "
              "This is an OUT-OF-BAND value the peer gave you — this tool never fetches one.",
              file=sys.stderr)
        return 2
    label = args.label.strip()
    if not label:
        print("peer_book: --label must be non-empty (a human name you chose; not recognition, not standing).",
              file=sys.stderr)
        return 2
    path = book_path()
    existing = _load(path)
    for e in existing:
        if str(e.get("public_hex", "")).lower() == ph:
            print(f"peer_book: that public_hex is already in the book as {e.get('label')!r} "
                  f"(a label is a note you wrote, not recognition — edit the file by hand to relabel).",
                  file=sys.stderr)
            return 1
    # append-only; timestamp passed in so the tool has no ambient clock surprises in tests
    at = args.at or datetime.datetime.now(datetime.timezone.utc).isoformat()
    row = {"public_hex": ph, "label": label, "where_met": (args.where_met or "").strip(), "added_utc": at}
    newfile = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    if newfile:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    print(f"peer_book: noted {label!r} → {ph[:16]}…  ({path})")
    print("  (a written label — NOT recognition, NOT standing. Recognition is a signed two-party act.)")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    path = book_path()
    rows = _load(path)
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    if not rows:
        print(f"peer_book: empty ({path}). A fresh book ships with NO peers — you add each one out-of-band.")
        return 0
    print(f"# Known peers — labels YOU assigned, out-of-band. Not recognition, not standing.  ({path})")
    for e in rows:
        wm = f"  · {e['where_met']}" if e.get("where_met") else ""
        print(f"  {e.get('label','?'):32s} {str(e.get('public_hex',''))[:16]}…{wm}")
    print(f"# {len(rows)} peer(s). This file is local-only: never served, synced, or shipped.")
    return 0


def cmd_path(_args: argparse.Namespace) -> int:
    print(book_path())
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Local-only peer book (public_hex + label). Never networked.")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="note a peer's public_hex + a label (obtained out-of-band)")
    a.add_argument("--label", required=True)
    a.add_argument("--public-hex", required=True)
    a.add_argument("--where-met", default="")
    a.add_argument("--at", default="", help="ISO timestamp (default: now); explicit for reproducible runs")
    a.set_defaults(fn=cmd_add)
    li = sub.add_parser("list", help="show the book")
    li.add_argument("--json", action="store_true")
    li.set_defaults(fn=cmd_list)
    pa = sub.add_parser("path", help="print the book's file path")
    pa.set_defaults(fn=cmd_path)
    ns = p.parse_args(argv)
    return ns.fn(ns)


if __name__ == "__main__":
    raise SystemExit(main())
