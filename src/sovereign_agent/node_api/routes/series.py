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

import json
import os
from pathlib import Path

from flask import Blueprint, jsonify, request

from ... import config
from .._filecache import memoize_on
from ..auth import require_principal
from ..errors import route_error

bp = Blueprint("series", __name__, url_prefix="/api/v1")

# Playbooks dir flows from config (BREATHLINE_BOOKS_VAULT) — resolved PER-CALL in _asin_cands/_channel_cands
# (audit 2026-06-13d #34) so a re-pointed vault is honored, not frozen at import. None → overlay no-ops.

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


def _chapter_cands() -> list:
    explicit = os.environ.get("CHAPTER_INDEX")
    if explicit:
        return [Path(explicit)]
    repo = Path(__file__).resolve().parents[4]
    return sorted(repo.glob("artifacts/extracted_chapter_outlines*.json"), reverse=True)


@memoize_on(_chapter_cands)
def _chapter_index() -> dict:
    """Extracted chapter TOCs keyed by book_id (Tiger extracts real '# Chapter N' headers from the
    manuscripts). The lens MERGES these at render time (Path B, KM ratify 2026-06-09) so the roadmap
    projection stays lean and chapters trace to the books by construction — no hand-copy, no drift.
    This is the 1M-book foundation: chapters source from the manuscripts, not a curated YAML.
    CHAPTER_INDEX overrides; else newest artifacts/extracted_chapter_outlines*.json wins. Missing = {}.
    Memoized on the source file's (mtime,size) (audit 2026-06-13 W5 #4/#15)."""
    cands = _chapter_cands()
    for p in cands:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return data.get("books", {}) if isinstance(data, dict) else {}
        except (ValueError, OSError):
            continue
    return {}


def _load_tracker(path: Path) -> dict | None:
    """ONE yaml-optional tracker read (audit 2026-06-13d #22) the three overlay lenses share, instead of
    each re-implementing the import-guard + read + (OSError,ValueError) swallow. Returns the parsed mapping,
    {} for an empty/non-mapping file, or None when yaml is absent or the file can't be read — so a caller
    can `continue` to the next candidate on None and treat {} as 'present but empty'."""
    try:
        import yaml  # noqa: PLC0415 — local import keeps the lenses yaml-optional
    except ImportError:
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else {}


def _asin_cands() -> list:
    explicit = os.environ.get("ASIN_TRACKER")
    pdir = config.get_playbooks_dir()   # per-call (audit 2026-06-13d #34) — honors a re-pointed vault
    return ([Path(explicit)] if explicit else [pdir / "ASIN_TRACKER.yaml"] if pdir else [])


@memoize_on(_asin_cands)
def _publishing_index() -> dict:
    """KDP publishing status keyed by book_id, derived from the ASIN_TRACKER (the canonical KDP record
    Tiger maintains). The lens OVERLAYS publishing_state + asin + release at render time so the Series
    Pipeline reflects real KDP status AUTOMATICALLY — no manual roadmap edits, never stale. Roadmap stays
    lean + GB-sole-writer. Mirrors the _chapter_index() read-only merge (Path B). ASIN_TRACKER env overrides;
    default = the agentic_playbooks tracker. Memoized on the tracker's (mtime,size) (audit W5 #4/#15)."""
    cands = _asin_cands()
    _MAP = {"live": "published", "pre_order_live": "pre_order_live",
            "pre_order_in_review": "pre_order", "pre_order_publishing": "pre_order_live"}
    for p in cands:
        data = _load_tracker(p)
        if data is None:
            continue
        import logging  # noqa: PLC0415
        out = {}
        for section in ("books", "executive_series"):
            for bid, b in (data.get(section) or {}).items():
                if not isinstance(b, dict):
                    continue
                raw = str(b.get("status", "")).strip()
                state = _MAP.get(raw)
                eb = b.get("ebook") if isinstance(b.get("ebook"), dict) else {}
                if not state:
                    # Error Voice §4 (audit 2026-06-13): an UNMAPPED non-empty status must SCREAM, not
                    # vanish — surface it with a loud sentinel + log so a new KDP status is never silently
                    # dropped from the publishing index.
                    if raw:
                        logging.getLogger("breathline.series").warning(
                            "⚠ UNMAPPED KDP status '%s' for %s — add it to _MAP", raw, bid)
                        out[bid] = {"publishing_state": f"⚠ unmapped:{raw}",
                                    "asin": eb.get("asin"), "release": b.get("release")}
                    continue
                out[bid] = {"publishing_state": state, "asin": eb.get("asin"), "release": b.get("release")}
        return out
    return {}


def _channel_cands() -> list:
    explicit = os.environ.get("CHANNEL_TRACKER")
    pdir = config.get_playbooks_dir()   # per-call (audit 2026-06-13d #34)
    return ([Path(explicit)] if explicit else [pdir / "CHANNEL_TRACKER.yaml"] if pdir else [])


@memoize_on(_channel_cands)
def _channel_index() -> dict:
    """Distribution-federation state keyed by book_id, derived from CHANNEL_TRACKER.yaml (Tiger-owned,
    sibling of ASIN_TRACKER). The lens OVERLAYS per-channel state (beyond kdp_core, which _publishing_index
    already carries) so the Series Pipeline shows the WHOLE federation's truth automatically — never stale,
    never hand-edited. Mirrors _publishing_index. CHANNEL_TRACKER env overrides; absence no-ops the overlay.
    Memoized on the tracker's (mtime,size) (audit 2026-06-13 W5 #4/#15)."""
    cands = _channel_cands()
    for p in cands:
        data = _load_tracker(p)
        if data is None:
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
    staged, other = [], []
    for bid, chans in channel_index.items():
        for ch, st in chans.items():
            if not isinstance(st, dict):
                continue
            s = st.get("state")
            row = {"book_id": bid, "channel": ch, "state": s, "note": st.get("note", "")}
            (staged if s == "staged" else other).append(row)
    # Error Voice §4 (audit 2026-06-13): non-staged channel states are surfaced in `other` instead of
    # silently dropped — a new/unknown channel state can never vanish from the dispatch summary.
    return {"staged_count": len(staged), "staged": staged,
            "other_count": len(other), "other": other,
            "gate": "G1 — Dispatch Gate (batched)", "doctrine": "one look, one Accept, all channels"}


def _stage_labels_path() -> Path:
    return Path(__file__).resolve().parents[4] / "artifacts" / "pipeline_stage_labels.yaml"


@memoize_on(lambda: [_stage_labels_path()])
def _stage_labels() -> dict:
    """Canonical stage vocabulary (GB sole-write artifacts/pipeline_stage_labels.yaml). Renderers LABEL from
    this — never the raw slug (pilot #3); an unknown slug must render LOUD, never blank (pilot #4 / Error Voice §4).
    Memoized on the file's (mtime,size) (audit 2026-06-13 W5 #4/#15)."""
    data = _load_tracker(_stage_labels_path())
    if not data:
        return {}
    return data.get("stages", {}) if isinstance(data, dict) else {}


def _review_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "artifacts" / "review_ready"


@memoize_on(lambda: ([_review_dir()] + sorted(_review_dir().glob("*.json")) if _review_dir().is_dir() else []))
def _review_index() -> dict:
    """Review-Ready contract truth per book (artifacts/review_ready/<book_id>.json) — the per-step overlay so
    the /series checklist renders the live contract, never a hand-kept stage (pilot finding #1). Auto, never
    stale. Memoized on the dir + each json's (mtime,size) (audit 2026-06-13 W5 #4/#15)."""
    out = {}
    base = _review_dir()
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


# In-memory read-repair extracted to node_api/yaml_repair.py (audit 2026-06-13): one shared resilient
# loader the lens AND the roadmap derivers use, dropping series.py under the 500-line ceiling. `_load`
# is kept as a thin alias so this module's call sites are unchanged.
from ..yaml_repair import load_roadmap as _load  # noqa: E402


@memoize_on(lambda path: [path])
def _read_roadmap(path: Path):
    """Read + parse the 112KB roadmap, memoized on its (mtime,size) — the dominant /series cost (audit
    2026-06-13 W5 #4). Sole-write + rarely-changing → ~100% hit rate. Returns (data, degraded, detail)."""
    return _load(path.read_text(encoding="utf-8"))


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
    data, degraded, detail = _read_roadmap(path)   # mtime-memoized parse (audit 2026-06-13 W5 #4)
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


@bp.get("/book_docs")
@require_principal
def book_docs():
    """List a title's board / review documents (Editorial R1/R2/R3, Book-to-UX, Tech/Arch, Review Brief)
    so the Series Pipeline card can HAND them — each opens via GET /doc (GB A4). Resolves the book dir
    across the S1 agentic_playbooks vault AND each Series-N folder; paths are returned vault-relative."""
    book = (request.args.get("book") or "").strip()
    if not book or "/" in book or ".." in book:
        return jsonify(route_error(
            error="bad_book",
            what="Pass ?book=<book_id>.",
            why="The book param was empty or contained path-traversal chars.",
            next_step="Pass a clean ?book=<book_id> (no '/' or '..').")), 400
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
                    ("renderability_audit", "Renderability Audit (Gate 6)"),
                    ("changelog", "Manuscript Changelog"),
                    ("review_brief", "Review Brief")]
        seen = set()
        for pat in ("*editorial_board_review*.md", "*virality_to_ux*.md", "*tech_arch_review*.md",
                    "*renderability_audit*.md", "*manuscript_v*_changelog.md", "*[Rr]eview_[Bb]rief*.md"):
            for p in sorted(bdir.glob(pat)):
                if p.name in seen:
                    continue
                seen.add(p.name)
                rel = str(p).split("/breathline-books-vault/")[-1]  # vault-relative → servable by /doc
                lab = next((l for k, l in labelmap if k in p.name.lower()), p.name)
                docs.append({"label": lab, "file": p.name, "path": rel})
        # newest manuscript only (so KM can read the updated book from the card; older versions stay out)
        mss = sorted(p for p in bdir.glob("manuscript_v*.md") if "changelog" not in p.name.lower())
        if mss:
            p = mss[-1]
            docs.append({"label": f"📖 Manuscript ({p.stem.split('_')[-1]})", "file": p.name,
                         "path": str(p).split("/breathline-books-vault/")[-1]})
    return jsonify({"book": book, "docs": docs})
