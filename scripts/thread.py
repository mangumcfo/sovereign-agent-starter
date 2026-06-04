#!/usr/bin/env python3
"""Receipted Tiger <-> GB coordination thread (hash-chained).

Reduces KM's relay load: Tiger and GB append notes here and each picks up the other's
by reading the thread — async, no chat-tax, integrity-checked.

  append:  python3 scripts/thread.py append --from Tiger --to GB --ref <ref> --msg "<text>"
  verify:  python3 scripts/thread.py verify
  show:    python3 scripts/thread.py show

Store of record:  memory/coordination/THREAD_Tiger_GB.ndjson  (hash-chained; GENESIS-anchored)
Human mirror:     memory/coordination/THREAD_Tiger_GB.md      (re-rendered on each append)

Each entry's receipt = sha256(prev_hash | from | to | ref | msg), chained from "GENESIS".
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "memory" / "coordination"
NDJSON = ROOT / "THREAD_Tiger_GB.ndjson"
MD = ROOT / "THREAD_Tiger_GB.md"


def _load() -> list:
    if not NDJSON.exists():
        return []
    return [json.loads(l) for l in NDJSON.read_text(encoding="utf-8").splitlines() if l.strip()]


def _hash(prev: str, frm: str, to: str, ref: str, msg: str) -> str:
    return hashlib.sha256(("|".join([prev, frm, to, ref, msg])).encode("utf-8")).hexdigest()


def _render(entries: list) -> None:
    out = ["# THREAD — Tiger ↔ GB (receipted coordination)", "",
           "Hash-chained async thread. Tiger and GB append; each reads the other's notes here "
           "(reduces KM relay). Append: `scripts/thread.py append`. Verify: `scripts/thread.py verify`.", ""]
    for e in entries:
        prev = e["prev"][:16] if e["prev"] != "GENESIS" else "GENESIS"
        out += [f"## [{e['n']}] {e['ts']} · {e['from']} → {e['to']}",
                f"*ref: {e['ref']}*", "", e["msg"], "",
                f"`receipt sha256:{e['hash'][:16]}… · prev:{prev}`", "", "---", ""]
    MD.write_text("\n".join(out), encoding="utf-8")


def append(frm: str, to: str, ref: str, msg: str) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    entries = _load()
    prev = entries[-1]["hash"] if entries else "GENESIS"
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    h = _hash(prev, frm, to, ref, msg)
    e = {"n": len(entries) + 1, "ts": ts, "from": frm, "to": to, "ref": ref, "msg": msg, "prev": prev, "hash": h}
    with NDJSON.open("a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
    _render(_load())
    print(f"appended [{e['n']}] {frm}→{to} ref:{ref} · receipt sha256:{h[:16]}… prev:{prev[:16]}")


def verify() -> bool:
    entries = _load()
    prev, ok = "GENESIS", True
    for e in entries:
        h = _hash(prev, e["from"], e["to"], e["ref"], e["msg"])
        if h != e["hash"] or e["prev"] != prev:
            ok = False
            print(f"  ✗ entry [{e.get('n')}] broken")
        prev = e["hash"]
    print(f"thread verify: {len(entries)} entries · chain {'OK' if ok else 'BROKEN'}")
    return ok


def show() -> None:
    for e in _load():
        print(f"[{e['n']}] {e['ts']} {e['from']}→{e['to']} ({e['ref']}): {e['msg'][:80]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Receipted Tiger<->GB coordination thread")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("append")
    a.add_argument("--from", dest="frm", required=True)
    a.add_argument("--to", required=True)
    a.add_argument("--ref", required=True)
    a.add_argument("--msg", required=True)
    sub.add_parser("verify")
    sub.add_parser("show")
    args = ap.parse_args()
    if args.cmd == "append":
        append(args.frm, args.to, args.ref, args.msg)
    elif args.cmd == "verify":
        verify()
    elif args.cmd == "show":
        show()
