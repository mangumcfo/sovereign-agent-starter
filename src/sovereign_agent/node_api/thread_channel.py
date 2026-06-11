"""Agent Channel — node-side adapter onto the receipted Tiger↔GB THREAD (A1).

GB's meta-review #1 (GB_Atrium_Change_Mgmt_MetaReview_2026-06-11): "KM is the message bus … the
single largest burden." A1 removes him: an agent's prompt lands as an Atrium card, KM clicks Relay,
and THIS appends it to the THREAD directly — no copy-paste. The reply surfaces back off the same THREAD.

The on-disk format is IDENTICAL to scripts/thread.py (hash-chained, GENESIS-anchored, same receipt
formula and entry shape + re-rendered .md mirror) so GB's start-ritual replay + `thread.py verify` keep
working on one shared record. The only addition is an env override (BREATHLINE_THREAD_FILE) so tests
write a tmp thread instead of the live coordination record.

Receipt = sha256("prev|from|to|ref|msg"); chained from "GENESIS". Mirrors scripts/thread.py exactly.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path


def _thread_path() -> Path:
    """The THREAD ndjson. Defaults to the live coordination record; tests override via env."""
    env = os.environ.get("BREATHLINE_THREAD_FILE")
    if env:
        return Path(env).expanduser()
    # node_api/thread_channel.py -> node_api -> sovereign_agent -> src -> <repo root>
    return Path(__file__).resolve().parents[3] / "memory" / "coordination" / "THREAD_Tiger_GB.ndjson"


def _hash(prev: str, frm: str, to: str, ref: str, msg: str) -> str:
    return hashlib.sha256("|".join([prev, frm, to, ref, msg]).encode("utf-8")).hexdigest()


def load() -> list[dict]:
    p = _thread_path()
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _render_md(entries: list[dict]) -> None:
    """Re-render the human-readable .md mirror beside the ndjson (mirrors scripts/thread.py)."""
    out = ["# THREAD — Tiger ↔ GB (receipted coordination)", "",
           "Hash-chained async thread. Tiger and GB append; each reads the other's notes here "
           "(reduces KM relay). Append: `scripts/thread.py append`. Verify: `scripts/thread.py verify`.", ""]
    for idx, e in enumerate(entries):
        prevh = e.get("prev", "GENESIS")
        prev = prevh[:16] if prevh != "GENESIS" else "GENESIS"
        n = e.get("n", idx + 1)
        out += [f"## [{n}] {e.get('ts','')} · {e.get('from','?')} → {e.get('to','?')}",
                f"*ref: {e.get('ref','')}*", "", e.get("msg", ""), "",
                f"`receipt sha256:{str(e.get('hash',''))[:16]}… · prev:{prev}`", "", "---", ""]
    p = _thread_path()
    p.with_suffix(".md").write_text("\n".join(out), encoding="utf-8")


def append(frm: str, to: str, ref: str, msg: str) -> dict:
    """Append a receipted entry to the THREAD and return it. Same chain math as scripts/thread.py."""
    p = _thread_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    entries = load()
    prev = entries[-1]["hash"] if entries else "GENESIS"
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    h = _hash(prev, frm, to, ref, msg)
    e = {"n": len(entries) + 1, "ts": ts, "from": frm, "to": to, "ref": ref, "msg": msg, "prev": prev, "hash": h}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
    _render_md(load())
    return e


def find_reply(to_agent: str, from_agent: str, after_n: int, ref_contains: str = "") -> dict | None:
    """Surface the answer to a relayed prompt: the first THREAD entry FROM the relayed-to agent back to
    the relayed-from agent, after the relay entry (by n). Optional ref filter. Returns None until it lands."""
    for e in load():
        if e.get("n", 0) <= after_n:
            continue
        if e.get("from") == to_agent and e.get("to") == from_agent:
            if not ref_contains or ref_contains in (e.get("ref") or ""):
                return e
    return None
