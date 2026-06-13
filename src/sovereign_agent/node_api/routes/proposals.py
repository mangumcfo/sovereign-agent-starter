"""
Section — Proposals (Step C: diff-review).

The producer (an agent reading a captured session) writes grouped diffs here; the Atrium
diff-review surface reads them and lets the operator accept/reject BEFORE anything is written.

    GET  /proposals                  → list proposals (newest first)
    POST /proposals                  → producer writes a proposal {session_ref, groups:[...]}
    POST /proposals/{id}/decide      → record the operator's per-group accept/reject decisions

Storage is a node-local append-style JSON file beside the obligation ledger. This is the REVIEW
queue, not the seal chain: acceptance is the disposition; the actual git-apply + seal is performed
by the agent (and traced in the obligation ledger). No hardcoded principals (CONSTITUTION §1).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from flask import Blueprint, jsonify, request

from ... import config
from ...obligations.ledger import get_ledger_root
from .._jsonstore import read_json_cached, sidecar_store, update_json
from ..auth import current_principal, require_owner, require_principal

bp = Blueprint("proposals", __name__, url_prefix="/api/v1")

# Books-vault root flows from config (BREATHLINE_BOOKS_VAULT, legacy path is a resolved candidate) so the
# node runs anywhere; the empty-string fallback keeps the module import-safe on a vault-less host (audit
# runs_anywhere). Endpoints that need a real file already 404 when the artifact is absent.
_VAULT = str(config.get_books_kdp_root() or "")

# Book number → registry book_id (audit 2026-06-13: was duplicated in recompile() + _resolve_book_id();
# adding Book 13 meant two edits). One constant; each caller keeps its OWN fallback (they differ).
_BOOK_NUM_TO_ID = {"10": "10_scaling_enterprise", "11": "11_ma_due_diligence",
                   "12": "12_agentic_enterprise"}


def _store_path() -> Path:
    return sidecar_store("proposals.json", "PROPOSALS_STORE")   # one resolver (audit 2026-06-13c #9)


def _read() -> list:
    return read_json_cached(_store_path())   # GET-only reads memoized (audit 2026-06-13c #17); mutators use _update


def _update(mutate):
    """Fenced read-modify-write on proposals.json (audit 2026-06-13 W5 #2): the lock spans read→mutate→
    write so concurrent create/decide/dismiss (threaded=True + the apply subprocess) can't lose a write."""
    return update_json(_store_path(), mutate)


@bp.get("/proposals")
@require_principal
def proposals_list():
    items = sorted(_read(), key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify({"proposals": items})


@bp.post("/proposals")
@require_principal
def proposals_create():
    body = request.get_json(silent=True) or {}
    groups = body.get("groups") or []
    is_info = bool(body.get("info"))   # info card = a 'no diff produced, here's why' result (no groups)
    if not groups and not is_info:
        return jsonify({
            "error": "missing_groups",
            "what": "A proposal needs at least one grouped diff (or info:true for a no-diff feedback card).",
            "next_step": "POST /api/v1/proposals with {\"session_ref\":\"...\",\"groups\":[…]} or {\"info\":true,\"note\":\"…\"}.",
        }), 400
    prop = {
        "id": "prop_" + str(int(time.time() * 1000)),
        "session_ref": body.get("session_ref", ""),
        "obligation_id": body.get("obligation_id"),
        "book": body.get("book", ""),
        "note": body.get("note", ""),
        "info": is_info,
        "cross_book": body.get("cross_book") or [],
        "produced_by": current_principal(),  # bind to authenticated principal, never the request body (audit 2026-06-10)
        "groups": groups,
        "reflection_mode": body.get("reflection_mode"),   # B3: embodied_principle | direct_mechanics
        "principle": body.get("principle"),               # the behavior/invariant when embodied_principle
        "route": body.get("route"),                       # principle | tooling | observation (for info cards)
        "status": "proposed",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _update(lambda items: (items + [prop], None))   # fenced append (audit 2026-06-13 W5 #2)
    return jsonify(prop), 201


@bp.post("/produce")
@require_principal
@require_owner
def produce():
    """produce — HUMAN-TRIGGERED (the Atrium 'Process' button). Spawns the producer for ONE session:
    it reads the transcript + manuscript and posts grouped diffs to /proposals (proposals only; the
    operator still accepts in the diff-review). Not an autonomous daemon — fires only on this request.
    """
    import subprocess
    import sys
    from pathlib import Path

    body = request.get_json(silent=True) or {}
    oid = (body.get("obligation_id") or "").strip()
    if not oid:
        return jsonify({"error": "missing_obligation_id",
                        "what": "Tell me which session to process.",
                        "next_step": "POST /api/v1/produce with {\"obligation_id\":\"obl_...\"}."}), 400
    import re as _re  # noqa: PLC0415
    if not _re.fullmatch(r"obl_[0-9]{8,}_[0-9a-f]{4,}", oid):  # strict shape before subprocess/fs use (audit)
        return jsonify({"error": "bad_obligation_id",
                        "what": "obligation_id is not a valid obl_ identifier.",
                        "next_step": "Use the exact id from /obligations (obl_<digits>_<hex>)."}), 400
    repo = Path(__file__).resolve().parents[4]
    script = repo / "scripts" / "atrium_producer.py"
    if not script.exists():
        return jsonify({"error": "producer_missing", "what": f"No producer at {script}."}), 500
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo / "src")
    env["PYTHONUNBUFFERED"] = "1"   # so the agent's progress lines stream to the log live
    # Capture the agent's output to a per-run log + write a run-status file so the cockpit can show
    # 'is an agent working, on what, for how long, what is it doing' (KM: not a black box).
    import json as _json
    import time as _time
    runs = Path(os.path.expanduser("~/.breathline/runs"))
    runs.mkdir(parents=True, exist_ok=True)
    logf = runs / f"{oid}.log"
    proc = subprocess.Popen([sys.executable, str(script), "--session", oid], cwd=str(repo), env=env,
                            stdout=open(logf, "w"), stderr=subprocess.STDOUT, start_new_session=True)
    (runs / f"{oid}.json").write_text(_json.dumps(
        {"session_id": oid, "started_at": _time.time(), "pid": proc.pid, "log": str(logf)}), encoding="utf-8")
    return jsonify({"status": "processing", "obligation_id": oid,
                    "next_step": "The diff(s) appear in the diff-review when ready (~1-3 min)."}), 202


@bp.get("/processing")
@require_principal
def processing():
    """processing — what agents are working on RIGHT NOW: session, elapsed time, live log tail.
    Once a run produces a result (a proposal / info card), its entry drops here and shows in the diff-review."""
    import json as _json
    import time as _time
    from pathlib import Path

    runs = Path(os.path.expanduser("~/.breathline/runs"))
    out = []
    if runs.exists():
        have = {p.get("obligation_id") for p in _read()}
        for jf in sorted(runs.glob("*.json")):
            try:
                meta = _json.loads(jf.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            oid = meta.get("session_id")
            elapsed = int(_time.time() - meta.get("started_at", 0))
            pid = meta.get("pid")
            alive = False
            if pid:
                try:
                    os.kill(int(pid), 0)
                    alive = True
                except (OSError, ValueError):
                    alive = False
            has_result = oid in have
            if has_result or (not alive and elapsed > 150):   # result landed, or it died → hand off / clean
                try:
                    jf.unlink()
                except OSError:
                    pass
                continue
            tail = ""
            lf = meta.get("log")
            if lf and os.path.isfile(lf):
                try:
                    tail = "\n".join(open(lf, encoding="utf-8", errors="replace").read().splitlines()[-14:])
                except OSError:
                    pass
            out.append({"session_id": oid, "elapsed_seconds": elapsed,
                        "status": "processing" if alive else "finishing", "alive": alive, "log_tail": tail})
    out.sort(key=lambda x: x["elapsed_seconds"], reverse=True)
    return jsonify({"runs": out})


@bp.post("/recompile")
@require_principal
@require_owner
def recompile():
    """recompile — HUMAN-TRIGGERED. Rebuild a book's PDF from the (just-edited) manuscript so KM can
    re-load it in the viewer and see the applied changes. Spawns the book's build script."""
    import re
    import subprocess
    import sys

    body = request.get_json(silent=True) or {}
    book = (body.get("book") or "").strip()
    m = re.search(r"Book (\d+)", book)
    sub = _BOOK_NUM_TO_ID.get(m.group(1) if m else "")
    if not sub:
        return jsonify({"error": "unknown_book", "what": f"No build mapping for '{book}'."}), 400
    vault = os.path.join(_VAULT, "agentic_playbooks")
    cwd = os.path.join(vault, sub, "v1.0")
    script = os.path.join(cwd, "build_v1.0.py")
    if not os.path.isfile(script):
        return jsonify({"error": "no_build_script", "what": f"No build_v1.0.py for {book}."}), 500
    subprocess.Popen([sys.executable, script], cwd=cwd,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return jsonify({"status": "recompiling", "book": book,
                    "next_step": "~30-90s; then the viewer auto-reloads (GET /book_pdf) or re-Browse."}), 202


def _book_registry() -> dict:
    """Helix increment #1 — the deterministic title→artifacts registry (single source of truth)."""
    p = Path(__file__).resolve().parents[4] / "memory" / "book_artifacts_registry.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("books", {})
    except (OSError, ValueError):
        return {}


def _resolve_book_id(book: str) -> str:
    """A request ("Book 10" / "the_sealing_hand" / "The Sealing Hand") → the registry book_id."""
    import re
    m = re.search(r"Book (\d+)", book)
    if m:
        return _BOOK_NUM_TO_ID.get(m.group(1), "")
    return {"the sealing hand": "the_sealing_hand", "breath & echo": "breath_and_echo"}.get(book.lower(), book)


@bp.get("/book_artifacts")
@require_principal
def book_artifacts():
    """The full title→artifacts registry (receipt + per-title present flags) — the pipeline/coherence read this."""
    p = Path(__file__).resolve().parents[4] / "memory" / "book_artifacts_registry.json"
    try:
        return jsonify(json.loads(p.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return jsonify({"_meta": {"ok": False, "note": "registry not built — run scripts/build_book_registry.py"}, "books": {}})


@bp.get("/book_pdf")
@require_principal
def book_pdf():
    """Serve a book's built interior PDF. Resolution reads the Helix file-management registry first
    (memory/book_artifacts_registry.json); falls back to a vault glob if the registry is stale/absent."""
    import glob
    from flask import send_file

    book = (request.args.get("book") or "").strip()
    vault = _VAULT
    bid = _resolve_book_id(book)
    if not bid or "/" in bid or ".." in bid:
        return jsonify({"error": "unknown_book", "what": f"No id resolvable from '{book}'."}), 400
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
        return jsonify({"error": "no_pdf", "what": f"No built PDF found for '{bid}' under the kdp vault."}), 404
    return send_file(pdfs[0], mimetype="application/pdf", max_age=0)


# ── KDP Dispatch (Atrium ship surface) — artifact serving + KDP-ready metadata ──────────────────
def _artifact_path(book: str, kind: str):
    """Resolve a book's artifact (pdf|epub|cover) → (abs_path|None, bid|None). Registry-first, glob fallback
    (mirrors /book_pdf; the registry is the source of truth, the glob is robustness)."""
    import glob
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


@bp.get("/book_epub")
@require_principal
def book_epub():
    """Serve a book's built EPUB (registry-first + glob fallback)."""
    from flask import send_file
    p, bid = _artifact_path(request.args.get("book") or "", "epub")
    if not bid:
        return jsonify({"error": "unknown_book"}), 400
    if not p:
        return jsonify({"error": "no_epub", "what": f"No EPUB for '{bid}'."}), 404
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
        return jsonify({"error": "unknown_book"}), 400
    if not p:
        return jsonify({"error": "no_cover", "variant": variant,
                        "what": f"No {variant} cover for '{bid}' — needs generation (use the cover-tweak channel)."}), 404
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
        return jsonify({"error": "unknown_book", "what": f"No id resolvable from '{book}'."}), 400
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


@bp.post("/proposals/<proposal_id>/apply")
@require_principal
@require_owner
def proposals_apply(proposal_id: str):
    """apply — HUMAN-TRIGGERED by KM's Accept. Spawns the apply agent: land accepted+tested diffs →
    re-test code (abort on red) → commit (local) + seal + close. Execute-after-Approve; reversible.

    CONSTITUTIONAL GATE (audit 2026-06-13 CRIT-1, CONSTITUTION §2): Propose → Decide → Execute. This
    route VERIFIES a decision exists before it ignites — it LOADS the proposal, requires
    status 'decided'/'partially decided', and requires ≥1 group explicitly accepted. `require_owner`
    gates *who* fires; this gates *whether a decision exists*. The old behaviour spawned the apply
    agent without ever loading the proposal, and atrium_apply defaulted undecided groups to 'accept' —
    reducing Propose→Decide(Accept)→Execute to Propose→Execute. Both holes are now closed."""
    import subprocess
    import sys
    from pathlib import Path

    body = request.get_json(silent=True) or {}
    gids = body.get("group_ids")

    # Decision-existence gate — the gate cannot pass on a proposal it never read.
    prop = next((x for x in _read() if x.get("id") == proposal_id), None)
    if prop is None:
        return jsonify({"error": "not_found",
                        "what": f"No proposal '{proposal_id}'.",
                        "next_step": "Refresh the Diffs-ready view — it may already be applied."}), 404
    if prop.get("status") not in ("decided", "partially decided"):
        return jsonify({"error": "not_decided",
                        "what": "Propose → Decide → Execute: this proposal has not been decided.",
                        "why": f"status is '{prop.get('status') or 'undecided'}', not 'decided'.",
                        "next_step": "POST .../decide with per-group accept/reject first, then apply."}), 409
    decisions = prop.get("decisions") or {}
    accepted = {g.get("id") for g in prop.get("groups", []) if decisions.get(g.get("id")) == "accept"}
    if not accepted:
        return jsonify({"error": "no_accepted_groups",
                        "what": "A decision exists but no group was accepted — nothing to execute.",
                        "next_step": "Accept ≥1 group in /decide, or dismiss the proposal."}), 422
    if gids:
        # a passed group id applies only if it was ALSO explicitly accepted (undecided/rejected never apply)
        gids = [g for g in gids if g in accepted]
        if not gids:
            return jsonify({"error": "no_accepted_in_selection",
                            "what": "None of the passed group_ids were accepted in /decide.",
                            "next_step": "Pass only accepted group ids, or omit group_ids to apply all accepted."}), 422

    repo = Path(__file__).resolve().parents[4]
    script = repo / "scripts" / "atrium_apply.py"
    if not script.exists():
        return jsonify({"error": "apply_agent_missing"}), 500
    args = [sys.executable, str(script), proposal_id]
    if gids:
        args.append(",".join(gids))
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo / "src")
    # Propagate the authenticated apply-clicker so atrium_apply's in-process close names the real
    # operator, not a hardcoded 'tiger' (audit 2026-06-13c H1/#10, CONSTITUTION §1).
    env["BREATHLINE_APPLY_PRINCIPAL"] = current_principal()
    subprocess.Popen(args, cwd=str(repo), env=env,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return jsonify({"status": "applying", "proposal_id": proposal_id,
                    "next_step": "Re-tests, commits (local), seals, closes — then the proposal clears. ~10-30s."}), 202


@bp.post("/proposals/<proposal_id>/dismiss")
@require_principal
@require_owner
def proposals_dismiss(proposal_id: str):
    """dismiss — clear an info / no-diff proposal + close its session obligation (nothing to apply).

    Owner-gated + principal-bound (audit 2026-06-13 W5 #2 fence + #9): it closes KM's session obligation,
    so it carries the same authority as /decide and /apply; the fenced RMW removes the proposal atomically;
    and `closed_by` is the AUTHENTICATED principal, never a hardcoded 'tiger' (CONSTITUTION §1)."""
    prop = _update(lambda items: ([x for x in items if x.get("id") != proposal_id],
                                  next((x for x in items if x.get("id") == proposal_id), None)))
    oid = (prop or {}).get("obligation_id")
    if oid:
        try:
            from ..deps import get_obligation_ledger
            get_obligation_ledger().close(
                oid, evidence="E1: dismissed — " + str((prop or {}).get("note", "no diff produced"))[:120],
                evidence_tier="E1", closed_by=current_principal())
        except Exception as exc:  # noqa: BLE001 — dismissal must never ERROR the UI, but must not fail SILENTLY
            import logging
            logging.getLogger("breathline.obligations").warning(
                "dismiss: close(%s) failed for proposal %s: %s — obligation may remain OPEN (card will resurface)",
                oid, proposal_id, exc)
            return jsonify({"status": "dismissed_proposal_only", "proposal_id": proposal_id,
                            "warning": "proposal dismissed but obligation close failed — see node log",
                            "obligation_id": oid}), 200
    return jsonify({"status": "dismissed", "proposal_id": proposal_id})


@bp.post("/proposals/<proposal_id>/decide")
@require_principal
@require_owner
def proposals_decide(proposal_id: str):
    """decide — record the operator's per-group accept/reject decisions. The accept disposition IS the
    human gate that the owner-gated /apply executes, so it must carry the SAME authority as /apply,
    /produce, /recompile, /feedback-disposition (audit 2026-06-13 HIGH): @require_owner below
    @require_principal. A non-owner federation/dev/loopback peer can no longer set the decisions that
    apply then runs."""
    body = request.get_json(silent=True) or {}
    decisions = body.get("decisions") or {}  # {group_id: "accept"|"reject"}

    def _decide(items):
        for it in items:
            if it.get("id") == proposal_id:
                it.setdefault("decisions", {}).update(decisions)
                it["decided_by"] = current_principal()
                it["status"] = "decided"
                return items, it
        return items, None

    found = _update(_decide)   # fenced RMW (audit 2026-06-13 W5 #2): no lost decision under concurrency
    if not found:
        return jsonify({"error": "not_found", "what": f"No proposal {proposal_id}."}), 404
    return jsonify(found)


@bp.get("/seeit")
@require_principal
def seeit():
    """seeit — derived operator-docs surface (render-not-recreate). Serves artifacts/seeit_content.json:
    core harness mechanics rendered from sealed S2 passages (+ citations/hashes) + the per-chapter
    walkthroughs S1 B10-12 link to. Regenerate with scripts/build_seeit.py (auto-refresh on book updates)."""
    p = Path(__file__).resolve().parents[4] / "artifacts" / "seeit_content.json"
    try:
        return jsonify(json.loads(p.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return jsonify({"_meta": {"surface": "seeit", "ok": False,
                                  "note": "seeit content not built — run scripts/build_seeit.py"},
                        "topics": [], "walkthroughs": []})


@bp.get("/export/packet")
@require_principal
@require_owner
def export_packet_route():
    """R22-1 Evidence-Packet Exports — assemble obligations into ONE self-verifying evidence bundle
    {manifest, receipts[], merkle_proof, chain_range, sha}. Owner-gated; deterministic; the bundle
    self-verifies on a clean machine (`export_packet.py verify <bundle>`). Engine for S5_37 Clean Exit.
    (audit 2026-06-13: @require_principal restored above @require_owner — was unreachable even by owner.)"""
    import sys as _sys  # noqa: PLC0415
    repo = Path(__file__).resolve().parents[4]
    if str(repo / "scripts") not in _sys.path:      # dedup-guard (audit: unbounded sys.path growth)
        _sys.path.insert(0, str(repo / "scripts"))
    import export_packet as _EP  # noqa: PLC0415
    ids = [x.strip() for x in (request.args.get("obl_ids") or "").split(",") if x.strip()]
    if not ids:
        return jsonify({"error": "missing_obl_ids", "what": "pass ?obl_ids=A,B,C (comma-separated)"}), 400
    led_root = get_ledger_root()      # ONE resolver (audit 2026-06-13)
    try:
        bundle = _EP.build_packet(ids, led_root)
    except ValueError as e:
        return jsonify({"error": "no_entries", "what": str(e)}), 404
    return jsonify(bundle)


@bp.get("/actions")
@require_principal
def actions_route():
    """R22-2 Queryable actions projection — verifiable rows over the Merkle leaves (read-only).
    Filters: type/principal/obligation/since/until. Each row cites its leaf + inclusion proof + root."""
    import sys as _sys  # noqa: PLC0415
    repo = Path(__file__).resolve().parents[4]
    if str(repo / "scripts") not in _sys.path:      # dedup-guard (audit: unbounded sys.path growth)
        _sys.path.insert(0, str(repo / "scripts"))
    import actions_projection as _AP  # noqa: PLC0415
    led_root = get_ledger_root()      # ONE resolver (audit 2026-06-13)
    g = request.args.get
    return jsonify(_AP.query_actions(led_root, type=g("type"), principal=g("principal"),
                                     obligation=g("obligation"), since=g("since"), until=g("until")))
