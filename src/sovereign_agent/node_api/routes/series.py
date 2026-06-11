"""
Section — Series Pipeline (ATR-7 lens, read-only).

The Atrium "Series Pipeline" lens reads this to witness the whole hopper: every series →
its titles → stage / visibility / LGP through-line / next gate. It is a *read-only
projection* — GB is the sole writer of `series_roadmap.yaml` (two-writers fence §6); this
endpoint only renders it. No writes, no mutation; honest labels (degraded-parse + private
visibility surfaced loudly). No hardcoded principals (CONSTITUTION §1).

    GET /series   → { meta, series:[ { number, slug, name, visibility, status, titles:[…] } ] }

Robust-read: `series_roadmap.yaml`'s tail meta blocks (gb_notes / references) are GB working
notes that occasionally carry YAML the strict parser rejects. The lens never needs them, so on
a full-parse failure we fall back to the safe prefix (everything up to the first gb_notes/
references key) and flag `meta.degraded=true` so the surface tells the truth about it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from flask import Blueprint, jsonify, request

from ... import config
from ..auth import require_principal

bp = Blueprint("series", __name__, url_prefix="/api/v1")

# Playbooks dir flows from config (BREATHLINE_BOOKS_VAULT, legacy path is a resolved candidate) so the
# trackers resolve on any host; None when no vault is present (the overlay simply no-ops) — runs_anywhere.
_PLAYBOOKS_DIR = config.get_playbooks_dir()

# Title fields the read-only card needs (everything else in the projection is GB working detail).
_TITLE_FIELDS = (
    "book_id", "vol_id", "title", "subtitle", "stage", "phase",
    "reader_order", "lgp_alignment_score", "next_gate", "drill_down",
    # Publishing lifecycle (GB authors these in the projection; the lens renders a state badge +
    # drill-through). published_date / revision / asin feed the title-card history pane.
    "publishing_state", "published_date", "revision", "asin",
    # Chapter outline cards (GB folds G's outlines: {n,title,promise,beats[],keywords[],stage,coherence_pin}).
    # The Series Pipeline drill renders these as read-only chapter cards (ATR-7d).
    "chapters",
)


def _roadmap_path() -> Path:
    explicit = os.environ.get("SERIES_ROADMAP")
    if explicit:
        return Path(explicit)
    repo = Path(__file__).resolve().parents[4]
    return repo / "artifacts" / "series_roadmap.yaml"


def _chapter_index() -> dict:
    """Extracted chapter TOCs keyed by book_id (Tiger extracts real '# Chapter N' headers from the
    manuscripts). The lens MERGES these at render time (Path B, KM ratify 2026-06-09) so the roadmap
    projection stays lean and chapters trace to the books by construction — no hand-copy, no drift.
    This is the 1M-book foundation: chapters source from the manuscripts, not a curated YAML.
    CHAPTER_INDEX overrides; else newest artifacts/extracted_chapter_outlines*.json wins. Missing = {}."""
    explicit = os.environ.get("CHAPTER_INDEX")
    if explicit:
        cands = [Path(explicit)]
    else:
        repo = Path(__file__).resolve().parents[4]
        cands = sorted(repo.glob("artifacts/extracted_chapter_outlines*.json"), reverse=True)
    for p in cands:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return data.get("books", {}) if isinstance(data, dict) else {}
        except (ValueError, OSError):
            continue
    return {}


def _publishing_index() -> dict:
    """KDP publishing status keyed by book_id, derived from the ASIN_TRACKER (the canonical KDP record
    Tiger maintains). The lens OVERLAYS publishing_state + asin + release at render time so the Series
    Pipeline reflects real KDP status AUTOMATICALLY — no manual roadmap edits, never stale. Roadmap stays
    lean + GB-sole-writer. Mirrors the _chapter_index() read-only merge (Path B). ASIN_TRACKER env overrides;
    default = the agentic_playbooks tracker. yaml is imported locally so absence just no-ops the overlay."""
    try:
        import yaml  # noqa: PLC0415 — local import keeps the lens yaml-optional
    except ImportError:
        return {}
    explicit = os.environ.get("ASIN_TRACKER")
    cands = ([Path(explicit)] if explicit
             else [_PLAYBOOKS_DIR / "ASIN_TRACKER.yaml"] if _PLAYBOOKS_DIR else [])
    _MAP = {"live": "published", "pre_order_live": "pre_order_live",
            "pre_order_in_review": "pre_order", "pre_order_publishing": "pre_order_live"}
    for p in cands:
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except (OSError, ValueError):
            continue
        out = {}
        for section in ("books", "executive_series"):
            for bid, b in (data.get(section) or {}).items():
                if not isinstance(b, dict):
                    continue
                state = _MAP.get(str(b.get("status", "")).strip())
                if not state:
                    continue
                eb = b.get("ebook") if isinstance(b.get("ebook"), dict) else {}
                out[bid] = {"publishing_state": state, "asin": eb.get("asin"), "release": b.get("release")}
        return out
    return {}


def _channel_index() -> dict:
    """Distribution-federation state keyed by book_id, derived from CHANNEL_TRACKER.yaml (Tiger-owned,
    sibling of ASIN_TRACKER). The lens OVERLAYS per-channel state (beyond kdp_core, which _publishing_index
    already carries) so the Series Pipeline shows the WHOLE federation's truth automatically — never stale,
    never hand-edited. Mirrors _publishing_index. CHANNEL_TRACKER env overrides; absence no-ops the overlay."""
    try:
        import yaml  # noqa: PLC0415 — local import keeps the lens yaml-optional
    except ImportError:
        return {}
    explicit = os.environ.get("CHANNEL_TRACKER")
    cands = ([Path(explicit)] if explicit
             else [_PLAYBOOKS_DIR / "CHANNEL_TRACKER.yaml"] if _PLAYBOOKS_DIR else [])
    for p in cands:
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except (OSError, ValueError):
            continue
        out = {}
        for section in ("books", "executive_series"):
            for bid, b in (data.get(section) or {}).items():
                if isinstance(b, dict):
                    out[bid] = {k: v for k, v in b.items() if isinstance(v, dict)}
        return out
    return {}


def _dispatch_gate_summary(channel_index: dict) -> dict:
    """The batched G1 Dispatch Gate (Distribution Spec §2): ONE recurring card listing all staged dispatches
    across channels — KM looks once, accepts once. Counts staged rows so the surface never pings per-item."""
    staged = []
    for bid, chans in channel_index.items():
        for ch, st in chans.items():
            if isinstance(st, dict) and st.get("state") == "staged":
                staged.append({"book_id": bid, "channel": ch, "note": st.get("note", "")})
    return {"staged_count": len(staged), "staged": staged,
            "gate": "G1 — Dispatch Gate (batched)", "doctrine": "one look, one Accept, all channels"}


def _stage_labels() -> dict:
    """Canonical stage vocabulary (GB sole-write artifacts/pipeline_stage_labels.yaml). Renderers LABEL from
    this — never the raw slug (pilot #3); an unknown slug must render LOUD, never blank (pilot #4 / Error Voice §4)."""
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        return {}
    p = Path(__file__).resolve().parents[4] / "artifacts" / "pipeline_stage_labels.yaml"
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return {}
    return data.get("stages", {}) if isinstance(data, dict) else {}


def _review_index() -> dict:
    """Review-Ready contract truth per book (artifacts/review_ready/<book_id>.json) — the per-step overlay so
    the /series checklist renders the live contract, never a hand-kept stage (pilot finding #1). Auto, never stale."""
    out = {}
    base = Path(__file__).resolve().parents[4] / "artifacts" / "review_ready"
    if not base.is_dir():
        return out
    for p in base.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out[p.stem] = {"review_ready": bool(d.get("review_ready")),
                       "checks": {c.get("check"): c.get("pass") for c in d.get("checks", []) if isinstance(c, dict)}}
    return out


# --- In-memory read-repair (GB owns the file; we NEVER write it). A common GB gotcha is an unquoted
# scalar value carrying an inner ": " (e.g.  drill_down: Published; KDP evidence: Live $19.99 ...) which
# breaks strict YAML and can blank the whole lens. We quote ONLY such values, and ONLY when not inside a
# multi-line quoted/block scalar (so a valid multi-line value is never corrupted). Verified to touch only
# the offending lines on the live roadmap. ---
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


def _repair_unquoted_colons(text: str):
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


def _load(text: str):
    """Parse the roadmap. On failure, attempt an in-memory quote-repair of unquoted ':'-bearing values
    (GB's file is never modified); else fall back to the safe prefix. Returns (data, degraded, detail)."""
    import yaml  # system python ships PyYAML 6.x; lazy so an import gap degrades, never 500s
    try:
        return yaml.safe_load(text) or {}, False, ""
    except yaml.YAMLError:
        pass
    repaired, n = _repair_unquoted_colons(text)
    if n:
        try:
            data = yaml.safe_load(repaired) or {}
            if data.get("series"):
                return data, True, (
                    f"Auto-repaired {n} unquoted value(s) carrying an inner ': ' (e.g. 'KDP evidence: …') "
                    "so the lens renders. GB's file is unchanged in place — flag GB to quote them at source.")
        except yaml.YAMLError:
            pass
    m = re.search(r"^(gb_notes|references):", text, re.M)
    if m:
        try:
            return (yaml.safe_load(text[: m.start()]) or {}, True,
                    "Rendered from the safe prefix — GB's gb_notes/references tail is unparseable YAML "
                    "(data above intact). Flag GB to fix the tail.")
        except yaml.YAMLError:
            pass
    return {}, True, "Roadmap unparseable — even the safe prefix failed; GB must fix the YAML."


def _title_card(t: dict, chapter_index: dict | None = None, publishing_index: dict | None = None,
                channel_index: dict | None = None, stage_labels: dict | None = None,
                review_index: dict | None = None) -> dict:
    card = {k: t.get(k) for k in _TITLE_FIELDS if t.get(k) is not None}
    # Path B (lens-sourced chapters): a title's own chapters always win (rich G-outlines / outline_locked).
    # If it carries none, merge the extracted TOC from the index by book_id — so chapters trace to the
    # manuscript by construction, the roadmap YAML stays lean, and there is nothing to drift out of sync.
    if not card.get("chapters") and chapter_index:
        idx = chapter_index.get(t.get("book_id"))
        if isinstance(idx, dict) and idx.get("chapters"):
            card["chapters"] = idx["chapters"]
            card["chapters_source"] = "extracted-index"
    # Publishing-state overlay (KDP truth from the ASIN_TRACKER): a title's OWN publishing_state wins
    # (GB can pin it); else derive from the tracker by book_id so the pipeline auto-reflects KDP — never stale.
    if not card.get("publishing_state") and publishing_index:
        pub = publishing_index.get(t.get("book_id"))
        if isinstance(pub, dict) and pub.get("publishing_state"):
            card["publishing_state"] = pub["publishing_state"]
            if pub.get("asin") and not card.get("asin"):
                card["asin"] = pub["asin"]
            if pub.get("release") and not card.get("published_date"):
                card["published_date"] = str(pub["release"])
            card["publishing_source"] = "asin-tracker"
    # Distribution-federation overlay (CHANNEL_TRACKER truth): per-channel state beyond kdp_core, auto-derived.
    if channel_index:
        chans = channel_index.get(t.get("book_id"))
        if isinstance(chans, dict) and chans:
            card["channels"] = chans
            card["channel_source"] = "channel-tracker"
    # Stage-vocabulary contract: label from pipeline_stage_labels.yaml, NEVER the raw slug; an unknown slug
    # screams (Error Voice) instead of rendering blank (pilot findings #3 raw-slug + #4 silent-blank).
    stage = t.get("stage")
    if stage is not None and stage_labels is not None:
        info = stage_labels.get(stage)
        if isinstance(info, dict):
            card["stage_label"] = info.get("label", stage)
            card["stage_step"] = info.get("step")
            card["stage_state"] = info.get("state")
        else:
            card["stage_label"] = f"⚠ UNMAPPED STAGE: {stage}"
            card["stage_unmapped"] = True
    # Review-Ready contract overlay (pilot finding #1): per-step truth from review_ready/<book>.json.
    if review_index:
        rv = review_index.get(t.get("book_id"))
        if isinstance(rv, dict):
            card["review_contract"] = rv
    return card


def _series_card(s: dict, chapter_index: dict | None = None, publishing_index: dict | None = None,
                 channel_index: dict | None = None, stage_labels: dict | None = None,
                 review_index: dict | None = None) -> dict:
    titles = s.get("titles") or s.get("volumes") or []
    return {
        "number": s.get("series_number"),
        "slug": s.get("slug", ""),
        "name": s.get("name", ""),
        # absent visibility = public KDP ladder (S1/S2); private must be explicit.
        "visibility": s.get("visibility") or "public",
        "status": s.get("status", ""),
        "title_count": len(titles),
        "titles": [_title_card(t, chapter_index, publishing_index, channel_index, stage_labels, review_index)
                   for t in titles if isinstance(t, dict)],
    }


@bp.get("/series")
@require_principal
def series_list():
    path = _roadmap_path()
    if not path.exists():
        return jsonify({
            "meta": {"source": str(path), "ok": False, "degraded": True,
                     "note": "series_roadmap.yaml not found — GB has not produced the projection yet."},
            "series": [],
        })
    text = path.read_text(encoding="utf-8")
    data, degraded, detail = _load(text)
    msr = data.get("multi_series_roadmap", {}) if isinstance(data, dict) else {}
    chapter_index = _chapter_index()  # Path B: chapters merged from the manuscripts' extracted TOCs
    publishing_index = _publishing_index()  # KDP status overlaid from the ASIN_TRACKER — auto, never stale
    channel_index = _channel_index()  # distribution-federation state overlaid from CHANNEL_TRACKER — auto
    stage_labels = _stage_labels()  # canonical stage vocabulary — label, never raw slug; unknown screams
    review_index = _review_index()  # Review-Ready contract truth per book — per-step overlay, never stale
    all_cards = [_series_card(s, chapter_index, publishing_index, channel_index, stage_labels, review_index)
                 for s in (data.get("series") or []) if isinstance(s, dict)]
    # One-source-of-truth visibility gate (KM ratify 2026-06-09): the public Series Pipeline view
    # shows only the public ladder. Private series (series_number: null, visibility: private) are
    # hidden unless KM explicitly surfaces them via ?include_private=1. Honest labels: we never drop
    # them silently — meta.private_hidden tells the surface exactly how many are withheld and how to see them.
    include_private = request.args.get("include_private", "").strip().lower() in ("1", "true", "yes")
    if include_private:
        series = all_cards
        private_hidden = 0
    else:
        series = [c for c in all_cards if c.get("visibility") != "private"]
        private_hidden = len(all_cards) - len(series)
    return jsonify({
        "meta": {
            "source": str(path),
            "ok": bool(series),
            "degraded": degraded,
            "note": detail if degraded else "",
            "version": data.get("version", "") if isinstance(data, dict) else "",
            "current_arc": msr.get("current_arc", ""),
            "active_series_count": msr.get("active_series_count"),
            "include_private": include_private,
            "private_hidden": private_hidden,
            "private_note": (
                "" if include_private or not private_hidden
                else f"{private_hidden} private series hidden from public view — "
                     "append ?include_private=1 (KM only) to surface them."),
            "dispatch_gate": _dispatch_gate_summary(channel_index),
        },
        "series": series,
    })


def _thread_entries():
    """The hash-chained Tiger↔GB THREAD as dialogue cards. Returns (entries, chain_ok). Read-only."""
    p = Path(__file__).resolve().parents[4] / "memory" / "coordination" / "THREAD_Tiger_GB.ndjson"
    entries, ok = [], True
    if p.is_file():
        prev_hash = None
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if prev_hash is not None and e.get("prev") and e.get("prev") != prev_hash:
                ok = False
            prev_hash = e.get("hash")
            entries.append({
                "n": e.get("n"), "ts": e.get("ts"), "from": e.get("from"), "to": e.get("to"),
                "ref": e.get("ref", ""), "msg": e.get("msg", ""),
                "receipt": (e.get("hash") or "")[:16], "prev": (e.get("prev") or "")[:12],
                "source": "thread",
            })
    entries.reverse()  # newest first
    return entries, ok


# B51 = the human's live Memory Cylinder (KM's own raw capture stream). It is anchored by a single Merkle
# root_hash over the whole cylinder, NOT a per-entry prev/hash chain like the THREAD. So we render each entry
# honestly: receipt = sha256(content)[:16] (deterministic, verifiable per-entry), and the cylinder's
# merkle_root is the chain anchor surfaced in meta. Read-only; we never write the cylinder.
# B51 live capture dir flows from B51_LIVE_DIR (default: XDG data home) so it resolves per-operator
# rather than for one host (runs_anywhere); read-only — we never write the cylinder.
_B51_LIVE_DIR = Path(os.environ.get(
    "B51_LIVE_DIR",
    os.path.join(os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
                 "human-memory-cylinder", "sessions"),
))


def _b51_cylinder_path() -> Path | None:
    scan = Path(__file__).resolve().parents[4] / "artifacts" / ".b51_last_scan.json"
    if scan.is_file():
        try:
            p = Path(json.loads(scan.read_text(encoding="utf-8")).get("path", ""))
            if p.is_file():
                return p
        except (ValueError, OSError):
            pass
    if _B51_LIVE_DIR.is_dir():  # fallback: newest live cyl_*.json
        cyls = sorted(_B51_LIVE_DIR.glob("cyl_*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
        if cyls:
            return cyls[0]
    return None


def _b51_entries(limit: int = 12):
    """The latest `limit` entries of KM's live B51 Memory Cylinder, as dialogue cards. Returns
    (entries_newest_first, merkle_root, cyl_id). Honest: per-entry receipt = content hash; merkle_root anchors."""
    path = _b51_cylinder_path()
    if not path:
        return [], "", ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return [], "", ""
    raw = data.get("entries", []) or []
    merkle = data.get("root_hash") or ""
    cyl_id = data.get("id") or ""
    total = len(raw)
    out = []
    for i, e in enumerate(raw[-limit:]):
        content = (e.get("content") or e.get("preview") or "").strip()
        idx = total - len(raw[-limit:]) + i  # absolute index in the cylinder
        out.append({
            "n": "b51-%d" % idx, "ts": e.get("timestamp", ""),
            "from": "KM-1176", "to": "field", "ref": "B51 capture · %s" % (cyl_id[:12] or "live"),
            "msg": content,
            "receipt": hashlib.sha256(content.encode("utf-8")).hexdigest()[:16],
            "prev": (merkle or "")[:12], "source": "b51",
        })
    out.reverse()  # newest first
    return out, merkle, cyl_id


@bp.get("/dialogue")
@require_principal
def dialogue():
    """Helix Comm Protocol — the unified, receipted coordination graph as dialogue cards. Two slices today:
    the hash-chained Tiger↔GB THREAD (source=thread) + KM's live B51 Memory Cylinder captures (source=b51).
    Each entry is a per-card-receipted Helix card; one cockpit-native graph. G responses extend the same lens
    next. Read-only; thin wrapper over what already exists (THREAD chain + B51 cylinder)."""
    thread, ok = _thread_entries()
    b51, merkle, cyl_id = _b51_entries()
    # Unified, newest-first by ISO timestamp (both sources emit ISO ts; string sort is correct + stable).
    entries = sorted(thread + b51, key=lambda e: str(e.get("ts") or ""), reverse=True)
    return jsonify({
        "meta": {"source": "THREAD_Tiger_GB + B51", "count": len(entries), "chain_ok": ok,
                 "sources": {"thread": len(thread), "b51": len(b51)},
                 "b51_merkle": (merkle or "")[:16], "b51_cyl": cyl_id[:12],
                 "note": "Helix Comm Protocol — the coordination THREAD + KM's live B51 captures as one "
                         "receipted graph. THREAD is per-entry hash-chained; B51 is content-hashed + "
                         "Merkle-anchored. Hopper / G responses extend the same lens next."},
        "entries": entries,
    })


@bp.get("/book_docs")
@require_principal
def book_docs():
    """List a title's board / review documents (Editorial R1/R2/R3, Book-to-UX, Tech/Arch, Review Brief)
    so the Series Pipeline card can HAND them — each opens via GET /doc (GB A4). Resolves the book dir
    across the S1 agentic_playbooks vault AND each Series-N folder; paths are returned vault-relative."""
    book = (request.args.get("book") or "").strip()
    if not book or "/" in book or ".." in book:
        return jsonify({"error": "bad_book", "what": "Pass ?book=<book_id>."}), 400
    kdp = config.get_books_kdp_root()
    if not kdp:
        return jsonify({"book": book, "docs": []})
    roots = [kdp / "agentic_playbooks"] + sorted(kdp.glob("series_*"))
    bdir = None
    for r in roots:
        vs = sorted((r / book).glob("v*"), reverse=True)
        if vs and vs[0].is_dir():
            bdir = vs[0]
            break
    docs = []
    if bdir:
        labelmap = [("round1", "Editorial R1 — stylistic / structural"),
                    ("round2", "Editorial R2 — disciplinary / functional"),
                    ("round3", "Editorial R3 — scholarly / research"),
                    ("virality_to_ux", "Book-to-UX Translation"),
                    ("tech_arch", "Tech / Architectural Review (5 gates)"),
                    ("review_brief", "Review Brief")]
        seen = set()
        for pat in ("*editorial_board_review*.md", "*virality_to_ux*.md", "*tech_arch_review*.md",
                    "*[Rr]eview_[Bb]rief*.md"):
            for p in sorted(bdir.glob(pat)):
                if p.name in seen:
                    continue
                seen.add(p.name)
                rel = str(p).split("/breathline-books-vault/")[-1]  # vault-relative → servable by /doc
                lab = next((l for k, l in labelmap if k in p.name.lower()), p.name)
                docs.append({"label": lab, "file": p.name, "path": rel})
    return jsonify({"book": book, "docs": docs})
