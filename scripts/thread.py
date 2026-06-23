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
    # Tolerant read via the ONE package gateway (Universalize Wave §1/G2): a THREAD truncated mid-append
    # no longer raises and bricks the CLI. scripts→package import is the allowed direction (G4).
    import sys
    src = str(Path(__file__).resolve().parents[1] / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from sovereign_agent.ndjson import read_ndjson
    return read_ndjson(NDJSON).entries


def _hash(prev: str, frm: str, to: str, ref: str, msg: str) -> str:
    return hashlib.sha256(("|".join([prev, frm, to, ref, msg])).encode("utf-8")).hexdigest()


def _render(entries: list) -> None:
    out = ["# THREAD — Tiger ↔ GB (receipted coordination)", "",
           "Hash-chained async thread. Tiger and GB append; each reads the other's notes here "
           "(reduces KM relay). Append: `scripts/thread.py append`. Verify: `scripts/thread.py verify`.", ""]
    for idx, e in enumerate(entries):
        prevh = e.get("prev", "GENESIS")
        prev = prevh[:16] if prevh != "GENESIS" else "GENESIS"
        n = e.get("n", idx + 1)   # robust: tolerate entries written without an explicit 'n'
        out += [f"## [{n}] {e.get('ts','')} · {e.get('from','?')} → {e.get('to','?')}",
                f"*ref: {e.get('ref','')}*", "", e.get("msg", ""), "",
                f"`receipt sha256:{str(e.get('hash',''))[:16]}… · prev:{prev}`", "", "---", ""]
    MD.write_text("\n".join(out), encoding="utf-8")


def append(frm: str, to: str, ref: str, msg: str) -> None:
    # Audit 2026-06-19 HIGH #1 (fork-race): fence read-prev → write under the SAME exclusive lock the node
    # uses (node_api/thread_channel.py: <thread>.lock). The CLI is the documented-primary writer; without a
    # matching lock a CLI append racing a node /relay append both read the same prev and FORK the genesis
    # chain (TOCTOU) → verify() breaks. flock makes the critical section atomic across processes.
    import fcntl  # noqa: PLC0415 — POSIX advisory lock, shared with the node so both writers serialize
    ROOT.mkdir(parents=True, exist_ok=True)
    lock = NDJSON.with_name(NDJSON.name + ".lock")   # MUST equal thread_channel's lock path
    with lock.open("w", encoding="utf-8") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            entries = _load()
            prev = entries[-1]["hash"] if entries else "GENESIS"
            ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            h = _hash(prev, frm, to, ref, msg)
            e = {"n": len(entries) + 1, "ts": ts, "from": frm, "to": to, "ref": ref, "msg": msg,
                 "prev": prev, "hash": h}
            with NDJSON.open("a", encoding="utf-8") as f:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
            _render(_load())
            print(f"appended [{e['n']}] {frm}→{to} ref:{ref} · receipt sha256:{h[:16]}… prev:{prev[:16]}")
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def verify() -> bool:
    entries = _load()
    prev, ok = "GENESIS", True
    for idx, e in enumerate(entries):
        h = _hash(prev, e.get("from", ""), e.get("to", ""), e.get("ref", ""), e.get("msg", ""))
        if h != e.get("hash") or e.get("prev") != prev:
            ok = False
            print(f"  ✗ entry [{e.get('n', idx + 1)}] ({e.get('ref','?')}) doesn't recompute — re-append via thread.py to repair the chain")
        prev = e.get("hash", prev)
    print(f"thread verify: {len(entries)} entries · chain {'OK' if ok else 'BROKEN'}")
    return ok


def show() -> None:
    # robust: tolerate older/malformed entries missing 'n' etc. (was crashing GB's start-ritual replay)
    for idx, e in enumerate(_load()):
        n = e.get("n", idx + 1)
        msg = str(e.get("msg", ""))[:80]
        print(f"[{n}] {e.get('ts','')} {e.get('from','?')}→{e.get('to','?')} ({e.get('ref','')}): {msg}")


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
