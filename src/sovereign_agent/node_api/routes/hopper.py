"""
Section — Hopper lane (read → one-gate write).

The "hopper" is the Series Pipeline's intake: raw B51 voice-delta captures surface here as
cards, and a single human action — **Send to Packet** — turns a card into a B32 obligation
(a DRAFT debit) on the node ledger, where the governed loop picks it up. Capture → card →
packet → (the existing review/apply loop). One human gate; reversible; honest labels.

    GET  /hopper          → { meta, cards:[ {id, ts, source, preview, text, cyl} ] }
    POST /hopper/packet   → open a B32 obligation seeded from a card → { obligation, … }

Delta feed (TRUTH, honest mock-first per the ratified design note):
  - If env HOPPER_SOURCE points at a B51 `session.yaml`, we render its real entries (live=True).
  - Otherwise we render a small, clearly-labelled MOCK set (live=False) so the lane is usable
    before the live HMC delta feed is wired. The *Send to Packet* write is REAL either way —
    it opens a real obligation through the ledger seam (no fabricated state).

No hardcoded principals (CONSTITUTION §1); the packet owner flows from the request principal.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from flask import Blueprint, jsonify, request

from ..auth import current_principal, require_principal
from ..deps import get_obligation_ledger

bp = Blueprint("hopper", __name__, url_prefix="/api/v1")

_MAX_CARDS = 8
_PREVIEW = 180
_TEXT_CAP = 4000

# Honest mock deltas — drawn from the real recent ideation theme so the lane is meaningful before
# the live feed is wired. Loudly labelled MOCK in meta so nothing reads as a real capture.
_MOCK_CARDS = [
    {"id": "mock_delta_1", "ts": "2026-06-03T17:16Z", "source": "Voice Note (MOCK)",
     "text": "Continuous book→code loop: an agent scans the book series, finds a concept not yet "
             "built into the code, and extrudes the YAML/spec for it — book-writing and code-writing "
             "move together with a clean NLP handoff, gated through the governed loop."},
    {"id": "mock_delta_2", "ts": "2026-06-03T17:19Z", "source": "Voice Note (MOCK)",
     "text": "I want to write a book chapter and SEE the resulting code processed, approved or gated, "
             "so we move through the series faster without giving up the human gate."},
    {"id": "mock_delta_3", "ts": "2026-06-03T17:24Z", "source": "Voice Note (MOCK)",
     "text": "Keep the Atrium lightweight and honest — the human stays at the stillpoint; agents do "
             "the coding/alignment in the background; only meaningful, grouped decisions reach me."},
]


def _preview(text: str) -> str:
    t = " ".join(str(text or "").split())
    return t[:_PREVIEW] + ("…" if len(t) > _PREVIEW else "")


def _cards_from_session(path: Path):
    """Parse a B51 capture into hopper cards. Handles BOTH formats:
      - export session.yaml  (export.session_id + entries[].source)
      - live HMC json        (top-level id/name + entries[].source_guess + tombstone fields)
    yaml.safe_load reads JSON too (JSON ⊂ YAML). Returns (cards, session_id) or ([], None)."""
    import yaml
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return [], None
    sid = ((data.get("export") or {}).get("session_id")) or data.get("id") or data.get("name") or path.stem
    entries = [e for e in (data.get("entries") or []) if isinstance(e, dict)]
    # Skip deleted/tombstoned entries (live HMC) — never surface a retracted thought.
    entries = [e for e in entries if not e.get("tombstoned_at")]

    def _src(e):
        return e.get("source") or e.get("source_guess") or e.get("content_type") or "capture"

    # Voice-delta lane: prefer the operator's voice captures (a mixed session/cylinder also carries
    # Tiger/G/screenshot/text entries — not hopper deltas). Fall back to all entries if none are voice.
    def _is_voice(e):
        return (str(e.get("content_type", "")).lower() == "voice"
                or str(_src(e)).lower().startswith("voice"))
    voiced = [e for e in entries if _is_voice(e)]
    use = voiced if voiced else entries
    cards = []
    for e in reversed(use):  # newest first
        text = str(e.get("content") or e.get("preview") or "")
        if not text.strip():
            continue
        cards.append({
            "id": e.get("id") or f"entry_{len(cards)}",
            "ts": e.get("timestamp") or "",
            "source": _src(e),
            "preview": _preview(text),
            "text": text[:_TEXT_CAP],
            "cyl": sid,
        })
        if len(cards) >= _MAX_CARDS:
            break
    return cards, sid


def _cards_from_feed(path: Path):
    """Read GB's iron-clad structured-suggestion feed (artifacts/GB_Hopper_Feed.ndjson). GB is the
    sole writer (fence); this only consumes. Each line is a curated suggestion already targeted to a
    lane/series — so Send-to-Packet routes correctly (no more Book-11 mis-route). Skips the _genesis
    schema line. Returns a list of cards carrying lane/series_ref/lgp_hint/priority/ref for traceability."""
    import json as _json
    cards = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = _json.loads(line)
        except ValueError:
            continue
        if r.get("_genesis") or not r.get("one_line_intent"):
            continue
        cards.append({
            "id": r.get("ref") or r.get("source_entry_hash") or f"feed_{len(cards)}",
            "ts": r.get("ts", ""),
            "source": r.get("series_ref") or r.get("lane") or "GB feed",
            "preview": _preview(r.get("one_line_intent", "")),
            "text": str(r.get("one_line_intent", ""))[:_TEXT_CAP],
            "cyl": r.get("source_cyl", ""),
            "lane": r.get("lane", ""),
            "series_ref": r.get("series_ref", ""),
            "lgp_hint": r.get("lgp_hint", ""),
            "priority": r.get("priority", "normal"),
            "ref": r.get("ref", ""),
            "source_entry_hash": r.get("source_entry_hash", ""),
        })
        if len(cards) >= _MAX_CARDS * 2:  # curated feed → allow a few more than raw
            break
    # priority high first, then by recency (feed order)
    cards.sort(key=lambda c: 0 if c.get("priority") == "high" else (1 if c.get("priority") == "normal" else 2))
    return cards


def _packeted_refs():
    """Refs of obligations already opened from hopper cards — so a card that's been Sent-to-Packet
    DISAPPEARS from the feed (no more re-approving the same card → no duplicate-obligation pileup)."""
    import json as _json
    root = os.environ.get("OBLIGATION_LEDGER_ROOT", "")
    refs = set()
    if root:
        p = Path(root) / "obligations.ndjson"
        if p.is_file():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    e = _json.loads(line)
                except ValueError:
                    continue
                if e.get("type") == "debit" and e.get("ref"):
                    refs.add(e["ref"])
    return refs


def _card_packeted(card: dict, packeted: set) -> bool:
    """Has this feed card already become an obligation? Mirrors hopper_to_packet's ref derivation."""
    cid = card.get("id") or ""
    sref = card.get("series_ref") or ""
    lane = card.get("lane") or ""
    if lane == "tooling":
        cands = {"tooling:" + (sref or cid)}
    elif lane == "private-learning":
        cands = {"private:" + (sref or cid)}
    else:  # coordination / book → src_ref = card ref (= id) or b51:<id>
        cands = {cid, "b51:" + cid}
    return any(c in packeted for c in cands if c)


@bp.get("/hopper")
@require_principal
def hopper_list():
    # PREFERRED: GB's iron-clad structured feed (clean, lane-targeted). Falls through to raw/mock.
    feed = os.environ.get("HOPPER_FEED", "").strip()
    if feed and Path(feed).is_file():
        cards = _cards_from_feed(Path(feed))
        # Hide cards you've already Sent-to-Packet (the re-approval loop fix) — fence-clean: GB's feed file
        # is untouched; the lens just stops showing a card once an obligation exists for it.
        packeted = _packeted_refs()
        cards = [c for c in cards if not _card_packeted(c, packeted)]
        return jsonify({
            "meta": {"live": True, "iron_clad": True, "source": feed,
                     "note": ("GB iron-clad feed — structured, lane-targeted suggestions distilled from your "
                              "raw captures. Send to Packet routes to each card's lane/series.")
                     if cards else
                     ("GB iron-clad feed is wired but empty — GB seeds structured suggestions from your "
                      "captures; they appear here.")},
            "cards": cards,
        })
    src = os.environ.get("HOPPER_SOURCE", "").strip()
    if src and Path(src).is_file():
        cards, sid = _cards_from_session(Path(src))
        if cards:
            return jsonify({
                "meta": {"live": True, "source": src, "session_id": sid,
                         "note": "Live B51 capture session. Delta/unsealed tracking (only-new-since-last) "
                                 "is forward; this shows the session's recent entries."},
                "cards": cards,
            })
    # honest mock fallback
    cards = [{"id": c["id"], "ts": c["ts"], "source": c["source"],
              "preview": _preview(c["text"]), "text": c["text"], "cyl": "mock"} for c in _MOCK_CARDS]
    return jsonify({
        "meta": {"live": False, "source": src or None,
                 "note": "MOCK delta feed — set HOPPER_SOURCE to a B51 session.yaml to render real "
                         "captures. 'Send to Packet' is REAL (opens an obligation) regardless."},
        "cards": cards,
    })


@bp.post("/hopper/packet")
@require_principal
def hopper_to_packet():
    """Send to Packet — the one human action. Opens a B32 obligation (DRAFT debit) seeded from a
    hopper card; the governed loop (review → accept → apply) takes it from there. Reversible."""
    body = request.get_json(silent=True) or {}
    text = str(body.get("text") or "").strip()
    card_id = str(body.get("card_id") or "").strip()
    if not text:
        return jsonify({
            "error": "missing_text",
            "what": "A packet needs the delta text to seed the obligation.",
            "next_step": "POST /api/v1/hopper/packet with {\"card_id\":\"…\",\"text\":\"…\"}.",
        }), 400
    # Lane routing (from the iron-clad feed): a card already knows where it belongs, so the packet
    # lands in the right lane — book → processable Hopper packet; tooling → Tooling/Build (skips the
    # book producer); private-learning → its own lane (no Book-N mis-route). Generic when unknown.
    lane = str(body.get("lane") or "").strip()
    series_ref = str(body.get("series_ref") or "").strip()
    lgp_hint = str(body.get("lgp_hint") or "").strip()
    src_ref = str(body.get("ref") or "").strip() or ("b51:" + card_id if card_id else None)
    preview = _preview(text)[:90] or card_id or "captured delta"
    intent = text[:_TEXT_CAP]
    if series_ref:
        intent += "\nTarget: " + series_ref
        m = re.search(r"\bB(?:ook )?(\d+)\b", series_ref)
        if m:
            intent += "\nPage: Book " + m.group(1)   # so the producer grounds against the right manuscript
    if lgp_hint:
        intent += "\nLGP hint: " + lgp_hint
    if lane == "tooling":
        title, ref = "Tooling/Build · " + preview, "tooling:" + (series_ref or card_id or "hopper")
    elif lane == "private-learning":
        title, ref = "Private learning — " + preview, "private:" + (series_ref or card_id or "")
    elif lane == "coordination":
        title, ref = "Coordination — " + preview, src_ref
    else:  # book:* or unknown → processable Hopper packet
        title, ref = "Hopper packet — " + preview, src_ref
    entry = get_obligation_ledger().open(
        title=title,
        owner=current_principal(),
        classification="C2",
        intent=intent,
        ref=ref,
        material=False,
        next_gate="Human disposition (Atrium Review)",
    )
    return jsonify({"status": "opened", "obligation": entry,
                    "next_step": "It is now a DRAFT obligation on your node — disposition it in the loop."}), 201
