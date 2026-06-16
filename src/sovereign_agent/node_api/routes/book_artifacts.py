"""
Section — Book Artifacts + KDP Dispatch (extracted from proposals.py, audit 2026-06-13d #7).

The book-artifact serving cluster — recompile + book_artifacts/book_pdf/book_epub/book_cover/book_kdp —
plus its helpers (_book_registry, _resolve_book_id, _artifact_path) and the _VAULT / _BOOK_NUM_TO_ID
constants. Carved out of proposals.py so each route module stays under the 500-line breath ceiling
(CONSTITUTION §5): proposals.py keeps the proposal LIFECYCLE (produce → decide → apply → dismiss);
this module keeps artifact SERVING (the KDP Dispatch surface). Same url_prefix, same auth gates — only
the file boundary moved.
"""
from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
from pathlib import Path

from flask import Blueprint, jsonify, request

from ... import config
from .._jsonstore import read_json_cached
from ..auth import require_owner, require_principal
from ..errors import route_error

bp = Blueprint("book_artifacts", __name__, url_prefix="/api/v1")

# Books-vault root flows from config (BREATHLINE_BOOKS_VAULT, legacy path is a resolved candidate) so the
# node runs anywhere; the empty-string fallback keeps the module import-safe on a vault-less host (audit
# runs_anywhere). Endpoints that need a real file already 404 when the artifact is absent.
_VAULT = str(config.get_books_kdp_root() or "")

# Book number → registry book_id (audit 2026-06-13: was duplicated in recompile() + _resolve_book_id();
# adding Book 13 meant two edits). One constant; each caller keeps its OWN fallback (they differ).
_BOOK_NUM_TO_ID = {"10": "10_scaling_enterprise", "11": "11_ma_due_diligence",
                   "12": "12_agentic_enterprise"}


def _book_registry() -> dict:
    """Helix increment #1 — the deterministic title→artifacts registry (single source of truth).
    Memoized (audit 2026-06-13d #20): /book_kdp called this 6×/request via _artifact_path; now cached."""
    p = Path(__file__).resolve().parents[4] / "memory" / "book_artifacts_registry.json"
    data = read_json_cached(p, {})
    return data.get("books", {}) if isinstance(data, dict) else {}


def _resolve_book_id(book: str) -> str:
    """A request ("Book 10" / "the_sealing_hand" / "The Sealing Hand") → the registry book_id."""
    m = re.search(r"Book (\d+)", book)
    if m:
        return _BOOK_NUM_TO_ID.get(m.group(1), "")
    return {"the sealing hand": "the_sealing_hand", "breath & echo": "breath_and_echo"}.get(book.lower(), book)


# ── KDP Dispatch (Atrium ship surface) — artifact serving + KDP-ready metadata ──────────────────
def _artifact_path(book: str, kind: str):
    """Resolve a book's artifact (pdf|epub|cover) → (abs_path|None, bid|None). Registry-first, glob fallback
    (mirrors /book_pdf; the registry is the source of truth, the glob is robustness)."""
    bid = _resolve_book_id(book)
    if not bid or "/" in bid or ".." in bid:
        return None, None
    e = _book_registry().get(bid) or {}
    rel = e.get(kind)
    if rel:
        p = os.path.join(_VAULT, rel)
        if os.path.isfile(p):
            return p, bid
    # Cover VARIANTS (KDP needs 3): ebook = front-only JPG/PNG; paperback/hardcover = full wraps (front+spine+back).
    # Only the ebook cover exists today; paperback/hardcover wraps are generated on request (cover-tweak channel).
    cover_variants = {
        "cover_ebook": ["**/{b}/v*/final/cover_KDP.jpg", "{b}/v*/final/cover_KDP.jpg",
                        "**/{b}/v*/final/cover_KDP.png", "{b}/v*/final/cover_kdp*.jpg", "{b}/v*/final/cover_ebook*.*"],
        "cover_paperback": ["**/{b}/v*/final/*paperback*.pdf", "{b}/v*/final/*paperback*.pdf",
                            "**/{b}/v*/final/*paperback*.png", "**/{b}/v*/final/cover*wrap*pb*.*"],
        "cover_hardcover": ["**/{b}/v*/final/*hardcover*.pdf", "{b}/v*/final/*hardcover*.pdf",
                            "**/{b}/v*/final/*hardback*.pdf", "**/{b}/v*/final/*hardcover*.png"],
    }
    pats = {
        "pdf": ["**/{b}/v*/final/*.pdf", "{b}/v*/final/*.pdf"],
        "epub": ["**/{b}/v*/final/*.epub", "{b}/v*/final/*.epub"],
        "cover": ["**/{b}/v*/final/cover*.jpg", "{b}/v*/final/cover*.jpeg",
                  "**/{b}/v*/final/cover*.png", "{b}/v*/final/cover*.png"],
    }
    pats = cover_variants.get(kind, pats.get(kind, []))
    found = []
    for pat in pats:
        found += glob.glob(os.path.join(_VAULT, pat.format(b=bid)), recursive=True)
    if kind == "pdf":
        found = [p for p in found if "cover" not in os.path.basename(p).lower()]
    found = sorted([p for p in found if os.path.isfile(p)], key=os.path.getmtime, reverse=True)
    return (found[0] if found else None), bid


@bp.post("/recompile")
@require_principal
@require_owner
def recompile():
    """recompile — HUMAN-TRIGGERED. Rebuild a book's PDF from the (just-edited) manuscript so KM can
    re-load it in the viewer and see the applied changes. Spawns the book's build script."""

    body = request.get_json(silent=True) or {}
    book = (body.get("book") or "").strip()
    m = re.search(r"Book (\d+)", book)
    sub = _BOOK_NUM_TO_ID.get(m.group(1) if m else "")
    if not sub:
        return jsonify(route_error(
            error="unknown_book",
            what=f"No build mapping for '{book}'.",
            why="The book label did not match a 'Book <N>' entry in _BOOK_NUM_TO_ID.",
            next_step="Pass a known book label (e.g. 'Book 12').")), 400
    vault = os.path.join(_VAULT, "agentic_playbooks")
    cwd = os.path.join(vault, sub, "v1.0")
    script = os.path.join(cwd, "build_v1.0.py")
    if not os.path.isfile(script):
        return jsonify(route_error(
            error="no_build_script",
            what=f"No build_v1.0.py for {book}.",
            why="The resolved book dir has no build_v1.0.py to rebuild the PDF from.",
            next_step="Ensure the book's v1.0/build_v1.0.py exists in the vault.")), 500
    subprocess.Popen([sys.executable, script], cwd=cwd,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return jsonify({"status": "recompiling", "book": book,
                    "next_step": "~30-90s; then the viewer auto-reloads (GET /book_pdf) or re-Browse."}), 202


@bp.get("/book_artifacts")
@require_principal
def book_artifacts():
    """The full title→artifacts registry (receipt + per-title present flags) — the pipeline/coherence read this."""
    # Memoized on (mtime,size) (Universalize Wave §3): the pipeline + coherence lenses poll this registry;
    # re-parsing it per request was the same waste the sibling _book_registry() already fixed with the cache.
    p = Path(__file__).resolve().parents[4] / "memory" / "book_artifacts_registry.json"
    fallback = {"_meta": {"ok": False, "note": "registry not built — run scripts/build_book_registry.py"}, "books": {}}
    return jsonify(read_json_cached(p, fallback))


@bp.get("/book_pdf")
@require_principal
def book_pdf():
    """Serve a book's built interior PDF. Resolution reads the Helix file-management registry first
    (memory/book_artifacts_registry.json); falls back to a vault glob if the registry is stale/absent."""
    from flask import send_file

    book = (request.args.get("book") or "").strip()
    vault = _VAULT
    bid = _resolve_book_id(book)
    if not bid or "/" in bid or ".." in bid:
        return jsonify(route_error(
            error="unknown_book",
            what=f"No id resolvable from '{book}'.",
            why="The book token did not resolve to a safe book id (empty or path-traversal chars).",
            next_step="Pass a known book id/token (e.g. B12).")), 400
    # 1) REGISTRY (source of truth)
    e = _book_registry().get(bid)
    if e and e.get("pdf"):
        p = os.path.join(vault, e["pdf"])
        if os.path.isfile(p):
            return send_file(p, mimetype="application/pdf", max_age=0)
    # 2) fallback glob (robustness)
    found = (glob.glob(os.path.join(vault, "**", bid, "v*", "final", "*.pdf"), recursive=True)
             + glob.glob(os.path.join(vault, bid, "v*", "final", "*.pdf")))
    interiors = [p for p in found if "cover" not in os.path.basename(p).lower()]
    pdfs = sorted(interiors or found, key=os.path.getmtime, reverse=True)
    if not pdfs:
        return jsonify(route_error(
            error="no_pdf",
            what=f"No built PDF found for '{bid}' under the kdp vault.",
            why="Neither the registry entry nor the vault glob located a built interior PDF.",
            next_step="Build the book (POST /api/v1/recompile) so the final PDF exists.")), 404
    return send_file(pdfs[0], mimetype="application/pdf", max_age=0)


@bp.get("/book_epub")
@require_principal
def book_epub():
    """Serve a book's built EPUB (registry-first + glob fallback)."""
    from flask import send_file
    p, bid = _artifact_path(request.args.get("book") or "", "epub")
    if not bid:
        return jsonify(route_error(
            error="unknown_book",
            what="No book id resolvable from the ?book param.",
            why="The book token was empty or did not resolve to a safe book id.",
            next_step="Pass a known book id/token (e.g. B12).")), 400
    if not p:
        return jsonify(route_error(
            error="no_epub",
            what=f"No EPUB for '{bid}'.",
            why="Neither the registry nor the vault glob located a built EPUB for this book.",
            next_step="Build the book's EPUB so the artifact exists.")), 404
    return send_file(p, mimetype="application/epub+zip", max_age=0)


@bp.get("/book_cover")
@require_principal
def book_cover():
    """Serve a book's cover. ?variant=ebook|paperback|hardcover (default ebook). Paperback/hardcover are
    full wraps (PDF) generated on request; ebook is the front-cover image."""
    from flask import send_file
    variant = (request.args.get("variant") or "ebook").lower()
    kind = {"ebook": "cover_ebook", "paperback": "cover_paperback", "hardcover": "cover_hardcover"}.get(variant, "cover_ebook")
    p, bid = _artifact_path(request.args.get("book") or "", kind)
    if not bid:
        return jsonify(route_error(
            error="unknown_book",
            what="No book id resolvable from the ?book param.",
            why="The book token was empty or did not resolve to a safe book id.",
            next_step="Pass a known book id/token (e.g. B12).")), 400
    if not p:
        body = route_error(
            error="no_cover",
            what=f"No {variant} cover for '{bid}' — needs generation (use the cover-tweak channel).",
            why=f"No {variant} cover artifact exists yet for this book in the vault.",
            next_step="Generate it via the cover-tweak channel, then retry.")
        body["variant"] = variant
        return jsonify(body), 404
    ext = p.lower().rsplit(".", 1)[-1]
    mt = {"pdf": "application/pdf", "png": "image/png"}.get(ext, "image/jpeg")
    return send_file(p, mimetype=mt, max_age=0)


@bp.get("/book_kdp")
@require_principal
def book_kdp():
    """KDP Dispatch payload — artifact presence + URLs + parsed KDP-ready metadata for one book.
    The Atrium KDP Dispatch surface renders this; each metadata field is copy-to-clipboard for the
    manual KDP web upload (KDP has no API — this stages everything up to the one manual click)."""
    from urllib.parse import quote
    from ...kdp_metadata import parse_kdp_metadata
    book = (request.args.get("book") or "").strip()
    bid = _resolve_book_id(book)
    if not bid or "/" in bid or ".." in bid:
        return jsonify(route_error(
            error="unknown_book",
            what=f"No id resolvable from '{book}'.",
            why="The book token did not resolve to a safe book id (empty or path-traversal chars).",
            next_step="Pass a known book id/token (e.g. B12).")), 400
    e = _book_registry().get(bid) or {}
    pdf_p, _ = _artifact_path(book, "pdf")
    epub_p, _ = _artifact_path(book, "epub")
    cov_ebook, _ = _artifact_path(book, "cover_ebook")
    cov_pb, _ = _artifact_path(book, "cover_paperback")
    cov_hc, _ = _artifact_path(book, "cover_hardcover")
    meta = {}
    d = e.get("dir")
    if d:
        mp = os.path.join(_VAULT, d, "metadata_v1.0.md")
        if os.path.isfile(mp):
            try:
                meta = parse_kdp_metadata(Path(mp).read_text(encoding="utf-8"))
            except Exception as ex:  # tolerant — a parse error still yields a usable card
                meta = {"_error": f"metadata parse failed: {ex}"}
    bq = quote(book)
    return jsonify({
        "book": book, "book_id": bid, "version": e.get("version"),
        "artifacts": {
            "pdf": {"present": bool(pdf_p), "url": f"/api/v1/book_pdf?book={bq}"},
            "epub": {"present": bool(epub_p), "url": f"/api/v1/book_epub?book={bq}"},
            # KDP needs 3 covers: ebook (front JPG) · paperback (wrap) · hardcover (wrap).
            "covers": {
                "ebook": {"present": bool(cov_ebook), "url": f"/api/v1/book_cover?book={bq}&variant=ebook"},
                "paperback": {"present": bool(cov_pb), "url": f"/api/v1/book_cover?book={bq}&variant=paperback"},
                "hardcover": {"present": bool(cov_hc), "url": f"/api/v1/book_cover?book={bq}&variant=hardcover"},
            },
        },
        "metadata": meta,
    })
