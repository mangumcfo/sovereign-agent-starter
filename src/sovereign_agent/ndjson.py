"""
Tolerant NDJSON reader — the ONE chain-read line parser (Universalize Wave §1, guards G1+G2+G3).

Before this primitive, every ndjson reader in the tree (the obligation ledger, the Tiger↔GB THREAD,
the hopper feed, the evidence-export scripts, GB's meta-cylinder) re-implemented `json.loads(line)` per
line — and a single malformed line (a write truncated mid-flush) raised and **bricked the whole chain**,
including `repair_chain` itself. This is the single home for that parse, with the one distinction the
guards make constitutional:

  • a **truncated TRAILING line** (an interrupted append) is QUARANTINED and flagged repairable — the
    chain still loads on its clean prefix, and `repair_chain` can rewrite it (we SURVIVE).
  • a **corrupt MIDDLE line** is LOUD — `chain_corrupt=True`, `repair_required=True`, and the parseable
    entries are still returned so a reader can *report and degrade*, never silent-skip a hole in the chain.

Tolerance means "survive corruption long enough to report and repair it," NOT "the chain forgets
politely." Pure stdlib — importable by `obligations/`, `node_api/`, AND `scripts/` alike (no Flask, no
node_api drag), so there is exactly one reader for the whole tree.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)

PathLike = Union[str, "Path"]


@dataclass
class NdjsonRead:
    """The result of a tolerant ndjson read.

    entries        — parsed dicts, in file order (the clean, usable chain).
    ok             — True unless a MIDDLE line was corrupt (a truncated tail still reads ok=True).
    chain_corrupt  — a non-trailing line failed to parse: there is a hole; callers must degrade loudly.
    repair_required— at least one line was quarantined (truncated tail OR corrupt middle) → repair_chain.
    quarantined    — the raw lines we could not parse (preserved for the audit / repair backup).
    bad_line       — 1-based line number of the FIRST middle-corruption (None if only a trailing tail).
    """

    entries: list = field(default_factory=list)
    ok: bool = True
    chain_corrupt: bool = False
    repair_required: bool = False
    quarantined: list = field(default_factory=list)
    bad_line: Optional[int] = None


def read_ndjson(path: PathLike) -> NdjsonRead:
    """Tolerantly read an ndjson file into an NdjsonRead (see the dataclass for the contract).

    A missing/empty file is a clean empty read (ok=True). A trailing truncated line is quarantined and
    repairable. A corrupt middle line flags chain_corrupt (loud) while still returning the parseable
    entries so the caller can report the hole instead of pretending it isn't there."""
    p = Path(path)
    if not p.exists():
        return NdjsonRead()
    # errors="replace": a partially-written multibyte tail becomes a replacement char and then fails the
    # per-line json parse below — caught and quarantined, never an uncaught UnicodeDecodeError that bricks.
    raw = p.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()
    nonempty_idx = [i for i, ln in enumerate(lines) if ln.strip()]
    last_idx = nonempty_idx[-1] if nonempty_idx else -1

    res = NdjsonRead()
    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        try:
            res.entries.append(json.loads(s))
        except ValueError:
            res.repair_required = True
            res.quarantined.append(line)
            if i == last_idx:
                # Truncated TRAILING line — an interrupted append. Survive: the clean prefix is the chain;
                # repair_chain rewrites it. NOT chain_corrupt (the committed chain is intact).
                logger.warning("ndjson %s: truncated trailing line quarantined (repairable, line %d)",
                               p, i + 1)
            else:
                # Corrupt MIDDLE line — a hole in the committed chain. LOUD: never silent-skip.
                res.chain_corrupt = True
                res.ok = False
                if res.bad_line is None:
                    res.bad_line = i + 1
                logger.error("ndjson %s: CORRUPT middle line %d — chain_corrupt (repair required)",
                             p, i + 1)
    return res


# ── Memoized variant for polled callers (stat-key cache, mirrors node_api/_filecache) ───────────────
_CACHE: dict = {}


def _stat_key(p: Path) -> tuple:
    try:
        st = p.stat()
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return (0, 0)


def read_ndjson_cached(path: PathLike) -> NdjsonRead:
    """`read_ndjson` memoized on the file's (mtime_ns, size) — re-parses only when the file changes.
    For polled surfaces (routes, chain views) that read the same ndjson many times between writes."""
    p = Path(path)
    key = _stat_key(p)
    hit = _CACHE.get(str(p))
    if hit is not None and hit[0] == key:
        return hit[1]
    val = read_ndjson(p)
    _CACHE[str(p)] = (key, val)
    return val
