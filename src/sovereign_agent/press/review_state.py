#!/usr/bin/env python3
"""review_state — human-review VISIBILITY for the Press (R-1, schema RS-1).

Records which human review layers (board rounds, alignment lenses, fidelity
traces, operator reads) have touched a volume, and lets the Press PROJECT that
state in the Series Status Report and the harden proposal.

VISIBILITY ONLY, by design ruling: missing or incomplete review state never
blocks a build, a floor, or a promotion. The human seal remains the only
non-automatable gate; this layer exists so the hand that speaks the word can
see, at the moment of the word, which human lenses have and have not run.

Storage (RS-1): one append-only ndjson file per volume at
    {PRESS_DATA_ROOT|cwd}/artifacts/review_state/<volume>.ndjson
Each line is a self-contained event:
    {"ts": "...Z", "volume": "S0-06", "layer": "board_r1",
     "status": "run" | "findings_open" | "closed",
     "hand": "who", "artifact": "path-or-ref", "artifact_sha": "sha256[:16]",
     "note": "optional", "line_sha256": "hash of the line minus this field"}
Later lines supersede earlier ones per layer (append-friendly; nothing is
ever rewritten). Unknown layers are allowed (the registry below is the
recommended vocabulary, not a cage); unknown statuses are refused on write
and skipped-with-count on read.

CLI:
    python -m sovereign_agent.press.review_state record <volume> <layer> <status>
        --hand H [--artifact PATH] [--note ...]
    python -m sovereign_agent.press.review_state show <volume>
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

from ..ndjson import read_ndjson

# Recommended layer vocabulary (WORKFLOW.md board rounds + the four alignment
# lenses + the two independent hands). Free-form layers are permitted.
LAYER_REGISTRY = [
    "board_r1", "board_r2", "board_r3",
    "lens_book_platform", "lens_book_ux", "lens_book_book", "lens_author_imposition",
    "gb_fidelity", "km_read",
]
_LENSES = {l for l in LAYER_REGISTRY if l.startswith("lens_")}
STATUSES = ("run", "findings_open", "closed")
_GLYPH = {"closed": "✓", "run": "run", "findings_open": "OPEN", None: "—"}
# Compact labels for the six summary slots (lenses aggregate into one slot).
_SUMMARY_SLOTS = [("board_r1", "R1"), ("board_r2", "R2"), ("board_r3", "R3"),
                  ("LENSES", "LENS"), ("gb_fidelity", "GB"), ("km_read", "KM")]


def _dir():
    root = Path(os.environ.get("PRESS_DATA_ROOT") or Path.cwd())
    return root / "artifacts" / "review_state"


def _path(volume):
    safe = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in volume)
    return _dir() / f"{safe}.ndjson"


def append_event(volume, layer, status, hand, artifact=None, note=None):
    """Append one review event. Fails loud on an unknown status."""
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r} — one of {STATUSES}")
    ev = {"ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
          "volume": volume, "layer": layer, "status": status, "hand": hand}
    if artifact:
        ev["artifact"] = str(artifact)
        p = Path(artifact)
        if p.is_file():
            ev["artifact_sha"] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    if note:
        ev["note"] = note
    ev["line_sha256"] = hashlib.sha256(
        json.dumps(ev, sort_keys=True).encode()).hexdigest()[:16]
    _dir().mkdir(parents=True, exist_ok=True)
    with open(_path(volume), "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, sort_keys=True) + "\n")
    return ev


def load_events(volume):
    """All well-formed events for a volume, plus a skipped count.

    Reads through the kernel's tolerant ndjson gateway (§1 — the ONE chain-read
    parser): a truncated trailing line is quarantined and repairable; a corrupt
    middle line is LOUD at the gateway and counts as skipped here. Entries that
    parse but fail the RS-1 shape (unknown status / missing layer) also count
    as skipped — visible in `show`, never silently dropped."""
    res = read_ndjson(_path(volume))
    events, skipped = [], len(res.quarantined)
    for ev in res.entries:
        if isinstance(ev, dict) and ev.get("status") in STATUSES and ev.get("layer"):
            events.append(ev)
        else:
            skipped += 1
    return events, skipped


def derive(volume):
    """Latest status per layer: {layer: event}. Later lines supersede."""
    events, _ = load_events(volume)
    state = {}
    for ev in events:  # file order IS time order (append-only)
        state[ev["layer"]] = ev
    return state


def _worst(statuses):
    """Aggregate several layers: any OPEN dominates, then run, then closed."""
    s = set(statuses)
    if not s:
        return None
    for pick in ("findings_open", "run", "closed"):
        if pick in s:
            return pick
    return None


def summary(volume):
    """Compact one-line projection, e.g. 'R1:✓ R2:run R3:— LENS:OPEN GB:✓ KM:—'."""
    state = derive(volume)
    if not state:
        return "no review state recorded"
    parts, known = [], set()
    for layer, label in _SUMMARY_SLOTS:
        if layer == "LENSES":
            lens_state = [ev["status"] for l, ev in state.items() if l in _LENSES]
            known |= {l for l in state if l in _LENSES}
            parts.append(f"{label}:{_GLYPH[_worst(lens_state)]}")
        else:
            ev = state.get(layer)
            if ev:
                known.add(layer)
            parts.append(f"{label}:{_GLYPH[ev['status'] if ev else None]}")
    extra = [l for l in state if l not in known]
    if extra:
        parts.append(f"+{len(extra)} other")
    return " ".join(parts)


def detail_lines(volume):
    """Full projection, one line per recorded layer, for reports/receipts."""
    state = derive(volume)
    if not state:
        return ["(no review state recorded)"]
    out = []
    for layer in sorted(state, key=lambda l: (LAYER_REGISTRY.index(l)
                                              if l in LAYER_REGISTRY else 99, l)):
        ev = state[layer]
        bits = [f"{layer}: {ev['status']}", f"ts {ev['ts']}", f"hand {ev.get('hand', '?')}"]
        if ev.get("artifact"):
            bits.append(f"artifact {ev['artifact']}"
                        + (f" ({ev['artifact_sha']})" if ev.get("artifact_sha") else ""))
        out.append(" · ".join(bits))
    return out


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in ("record", "show"):
        sys.exit(__doc__.strip().splitlines()[0] + "\nusage: record|show — see module docstring")
    cmd = args.pop(0)
    if cmd == "show":
        if len(args) != 1:
            sys.exit("usage: review_state show <volume>")
        vol = args[0]
        print(f"review_state {vol}: {summary(vol)}")
        for line in detail_lines(vol):
            print("  " + line)
        _, skipped = load_events(vol)
        if skipped:
            print(f"  WARNING: {skipped} malformed line(s) skipped — inspect the file")
        return 0
    # record
    def opt(name):
        if name in args:
            i = args.index(name)
            v = args[i + 1]
            del args[i:i + 2]
            return v
        return None
    hand, artifact, note = opt("--hand"), opt("--artifact"), opt("--note")
    if len(args) != 3:
        sys.exit("usage: review_state record <volume> <layer> <run|findings_open|closed> --hand H [--artifact P] [--note ...]")
    if not hand:
        sys.exit("record refused: --hand is required — every review names its hand")
    vol, layer, status = args
    if layer not in LAYER_REGISTRY:
        print(f"note: {layer!r} is not in the recommended registry {LAYER_REGISTRY} — recording anyway")
    ev = append_event(vol, layer, status, hand, artifact, note)
    print(f"recorded {vol} {layer} -> {status} (hand {hand}, line {ev['line_sha256']})")
    print(f"  projection now: {summary(vol)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
