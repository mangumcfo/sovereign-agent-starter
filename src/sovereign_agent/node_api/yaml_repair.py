"""Resilient roadmap YAML loader (audit 2026-06-13 — extracted from routes/series.py).

The PEER (roadmap owner) owns series_roadmap.yaml; this node NEVER writes it. A common gotcha is an unquoted scalar carrying an inner
": " (e.g. `drill_down: Published; KDP evidence: Live $19.99 ...`) which breaks strict YAML and can blank
the whole lens. `load_roadmap()` quotes ONLY such values (and ONLY when not inside a multi-line
quoted/block scalar), then falls back to the safe prefix — returning (data, degraded, detail) so callers
surface the degradation honestly instead of crashing or silently emptying.

This logic was duplicated nowhere and lived inline in the HTTP lens (pushing series.py over the 500-line
ceiling); now it is one shared module the lens AND the roadmap derivers import, so they parse the
degraded roadmap identically instead of crashing on raw yaml.safe_load.
"""
from __future__ import annotations

import re

_KV = re.compile(r"^(\s*(?:-\s+)?[A-Za-z_][\w./-]*:[ \t]+)(\S.*?)[ \t]*$")


def _sq_open(s: str) -> bool:        # value starts with ' — still open at line end? ('' = escaped quote)
    i = 1
    while i < len(s):
        if s[i] == "'":
            if i + 1 < len(s) and s[i + 1] == "'":
                i += 2; continue
            return False
        i += 1
    return True


def _sq_closes(line: str) -> bool:   # inside a '…' scalar — does it close on this line?
    i = 0
    while i < len(line):
        if line[i] == "'":
            if i + 1 < len(line) and line[i + 1] == "'":
                i += 2; continue
            return True
        i += 1
    return False


def _dq_open(s: str) -> bool:
    i = 1
    while i < len(s):
        if s[i] == "\\":
            i += 2; continue
        if s[i] == '"':
            return False
        i += 1
    return True


def _dq_closes(line: str) -> bool:
    i = 0
    while i < len(line):
        if line[i] == "\\":
            i += 2; continue
        if line[i] == '"':
            return True
        i += 1
    return False


def repair_unquoted_colons(text: str):
    """Return (repaired_text, count). Quotes unquoted scalar values containing ': '; skips lines inside
    multi-line single/double-quoted or block (|/>) scalars so valid multi-line values are never touched."""
    out, n = [], 0
    in_block = in_sq = in_dq = False
    block_indent = 0
    for line in text.split("\n"):
        indent = len(line) - len(line.lstrip(" "))
        if in_sq:
            out.append(line)
            if _sq_closes(line):
                in_sq = False
            continue
        if in_dq:
            out.append(line)
            if _dq_closes(line):
                in_dq = False
            continue
        if in_block:
            if line.strip() == "" or indent > block_indent:
                out.append(line); continue
            in_block = False
        m = _KV.match(line)
        if m:
            val = m.group(2); c0 = val[:1]
            if c0 in ("|", ">"):
                in_block = True; block_indent = indent; out.append(line); continue
            if c0 in ("[", "{", "&", "*", "#"):
                out.append(line); continue
            if c0 == "'":
                if _sq_open(val):
                    in_sq = True
                out.append(line); continue
            if c0 == '"':
                if _dq_open(val):
                    in_dq = True
                out.append(line); continue
            if ": " in val:
                qv = '"' + val.replace("\\", "\\\\").replace('"', '\\"') + '"'
                out.append(m.group(1) + qv); n += 1; continue
        out.append(line)
    return "\n".join(out), n


def load_roadmap(text: str):
    """Parse the roadmap. On failure, attempt an in-memory quote-repair of unquoted ':'-bearing values
    (the peer's file is never modified); else fall back to the safe prefix. Returns (data, degraded, detail)."""
    import yaml  # system python ships PyYAML 6.x; lazy so an import gap degrades, never 500s
    try:
        return yaml.safe_load(text) or {}, False, ""
    except yaml.YAMLError:
        pass
    repaired, n = repair_unquoted_colons(text)
    if n:
        try:
            data = yaml.safe_load(repaired) or {}
            if data.get("series"):
                return data, True, (
                    f"Auto-repaired {n} unquoted value(s) carrying an inner ': ' (e.g. 'KDP evidence: …') "
                    "so the lens renders. The owner's file is unchanged in place — flag the roadmap owner to quote them at source.")
        except yaml.YAMLError:
            pass
    # Accept the peer working-notes tail under its current key (peer_notes) or the legacy gb_notes key.
    m = re.search(r"^(peer_notes|gb_notes|references):", text, re.M)
    if m:
        try:
            return (yaml.safe_load(text[: m.start()]) or {}, True,
                    "Rendered from the safe prefix — the roadmap's notes/references tail is unparseable YAML "
                    "(data above intact). Flag the roadmap owner to fix the tail.")
        except yaml.YAMLError:
            pass
    return {}, True, "Roadmap unparseable — even the safe prefix failed; the roadmap owner must fix the YAML."
