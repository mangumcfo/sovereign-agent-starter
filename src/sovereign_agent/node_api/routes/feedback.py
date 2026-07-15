"""
Section — Feedback & Awaiting-the operator (Atrium Loop-Closure R2, Wave 1 — the B12 Pilot Kit).

Per the loop-closure audit (2026-06-10). The backend loops were real; the cockpit was a mock.
This is the ONE intake primitive that lets EVERY Atrium surface turn an observation into a packet, plus
the the operator-framed "waiting on me" projection with inline accept/reject — all on the hash-chained
ObligationLedger. Clones the hopper_to_packet / obligations.open|approve|close patterns; invents nothing.

    POST /feedback                  → mint a Human-disposition obligation from any surface  (G-3, G-6, G-2)
    GET  /awaiting_owner            → projection of obligations awaiting the operator disposition       (G-4)
    POST /feedback/<id>/disposition → {action: accept|reject, note} → approve | close         (G-4 inline)

Read-only projections (/series, /coherence) stay read-only per the fence — they call POST /feedback to
emit a packet; they never gain write access. DRIFT button and viewer feedback are typed /feedback calls.

∞Δ∞ Wire the glass to the machine and the human never leaves the chair. ∞Δ∞
"""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request

from ...obligations import AlreadyClosedError
from .._jsonstore import read_json_cached, sidecar_store
from ..auth import current_principal, require_principal, require_owner
from ..errors import route_error
from ..deps import get_obligation_ledger

bp = Blueprint("feedback", __name__, url_prefix="/api/v1")

HUMAN_GATE = "Human disposition"
IMPLEMENT_GATE = "the operator confirm → the node implement"
BATCH_GATE = "batch:mechanical"

# Typed sources → a readable title prefix. Any surface can emit; the type just frames the packet.
_KINDS = {
    "drift": "DRIFT",
    "viewer": "Viewer feedback",
    "series": "Pipeline feedback",
    "coherence": "Coherence/DRIFT",
    "general": "Feedback",
}

# A2 (the peer meta-review #2) — capture-time classification. The one-tap category routes the lane
# AUTOMATICALLY so triage never lands downstream on the node or on the operator's attention:
#   mechanical (typo/wording/structure) → BATCH lane, born-approved (material=False, no the operator gate)
#   technical                           → DISCRETE, the operator confirm → the node implements (a build/tooling fix)
#   judgment                            → DISCRETE, gated on the operator's Human disposition (he decides)
# Smart default = 'wording': the dominant class (~90 PDF-edit packets are page-level wording/typo/
# structure). Defaulting kills the 36% "other" — capture is always classified, never unclassified.
_CATEGORIES = {
    "typo":      {"lane": "batch",    "material": False, "gate": BATCH_GATE},
    "wording":   {"lane": "batch",    "material": False, "gate": BATCH_GATE},
    "structure": {"lane": "batch",    "material": False, "gate": BATCH_GATE},
    "technical": {"lane": "discrete", "material": False, "gate": IMPLEMENT_GATE},
    "judgment":  {"lane": "discrete", "material": True,  "gate": HUMAN_GATE},
}
_DEFAULT_CATEGORY = "wording"


def _classify(body: dict) -> tuple[str, dict, bool]:
    """Resolve the capture category → (category, routing, defaulted?). Unknown/absent → smart default."""
    raw = (body.get("category") or "").strip().lower()
    if raw in _CATEGORIES:
        return raw, _CATEGORIES[raw], False
    return _DEFAULT_CATEGORY, _CATEGORIES[_DEFAULT_CATEGORY], True


def _source_ref(body: dict) -> str:
    """Build a resolving source ref. Viewer feedback packs {book, chapter, page} (manual now; pdf.js later)."""
    if body.get("book"):
        loc = body.get("book")
        if body.get("chapter"):
            loc += f" ch{body['chapter']}"
        if body.get("page"):
            loc += f" p{body['page']}"
        return f"viewer:{loc}"
    return (body.get("source") or "atrium:feedback").strip()


def _reply_to(body: dict) -> str:
    """The obligation id this feedback REPLIES TO (a value/input typed ON an open gate card)."""
    return (body.get("reply_to") or body.get("on_card") or body.get("replies_to") or "").strip()


def _open_obligation(led, oid: str) -> dict | None:
    """Resolve an OPEN obligation by id (None if absent/closed). No getter on the ledger — scan opens."""
    if not oid:
        return None
    for o in led.open_obligations():
        if o.get("id") == oid:
            return o
    return None


@bp.post("/feedback")
@require_principal
def feedback_intake():
    """feedback.intake — any surface → a C2 obligation gated on Human disposition (G-3/G-6/G-2)."""
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify(route_error(
            error="missing_text",
            what="Feedback needs text — what should change?",
            why="The request body had no non-empty 'text' to open a C2 obligation from.",
            next_step="POST /api/v1/feedback with JSON {\"text\": \"...\", \"type\": \"drift|viewer|general\", \"source\": \"...\"}.")), 400
    kind = (body.get("type") or "general").lower()
    prefix = _KINDS.get(kind, _KINDS["general"])
    ref = _source_ref(body)
    # A2 capture classification → automatic lane routing (mechanical batch / technical / judgment).
    category, route, defaulted = _classify(body)
    title = f"[{category}] {prefix}: {text[:72]}"

    # FIX finding:feedback_misroute_2026-06-13 (52acd023, the peer→the node [390]): a reply typed ON an open
    # human-gated card is INPUT (the operator answering a 'provide value' card), NOT a mechanical edit. It must
    # (1) ATTACH to that card — carry its obligation_id in the ref — and (2) NEVER be auto-batched into
    # invisibility. Root cause of "my feedback gets missed": the operator's ISBNs were born-approved into
    # batch:mechanical and never linked to the card. Same view-out-truthing-the-ledger disease the
    # parity harness guards — generalized to feedback↔card linkage.
    parent = _open_obligation(get_obligation_ledger(), _reply_to(body))
    if parent is not None:
        ref = f"card:{parent['id']}"                       # (1) attach: carry the parent obligation id
        if route["lane"] == "batch":                       # (2) a reply to an open gate is never mechanical
            category, route, defaulted = "technical", _CATEGORIES["technical"], False
        title = f"[input→{parent['id'][-8:]}] {prefix}: {text[:60]}"
    try:
        entry = get_obligation_ledger().open(
            title=title,
            owner=current_principal(),  # bind to authenticated principal, never the request body (audit 2026-06-10)
            classification=body.get("classification", "C2"),
            intent=text,
            ref=ref,
            material=route["material"],   # category drives the gate, not the caller (judgment=gated, mechanical=born-approved)
            lgp=body.get("lgp"),
            next_gate=route["gate"],
            category=category,
            lane=route["lane"],
        )
    except ValueError as exc:  # resolve-at-entry on a path-like source ref (audit 2026-06-13 W5 #7)
        return jsonify(route_error(
            error="unresolvable_ref",
            what=str(exc),
            why="The feedback `source` is path-like but does not resolve — a pointer is never written false.",
            next_step="Point `source` at a real file, or omit it / use a symbolic tag.")), 422
    return jsonify({"obligation": entry, "kind": kind, "source": ref,
                    "category": category, "lane": route["lane"],
                    "category_defaulted": defaulted,
                    "replies_to": parent["id"] if parent else None}), 201


def _awaiting(led) -> list:
    """Open obligations gated on Human disposition — the operator-framed (the cockpit's missing home screen)."""
    out = []
    for o in led.open_obligations():
        # Awaiting the operator = gated on a human AND not yet disposed. Once accepted (approved) it leaves this
        # view — it's now awaiting the owning agent's execution, not the human's decision. Rejected
        # items are closed and already drop out of open_obligations().
        # Prefix match, not exact: a human gate may carry a context suffix (e.g.
        # "Human disposition (Atrium Review)"). Exact-== silently hid those, leaving real
        # human-gated feedback stale + invisible to the operator. Any "Human disposition…" gate is the operator's.
        if (o.get("next_gate") or "").startswith(HUMAN_GATE) and not o.get("approved"):
            out.append({
                "id": o.get("id"),
                "title": o.get("title"),
                "source": o.get("ref"),
                "detail": o.get("intent"),
                "material": o.get("material"),
                "classification": o.get("classification"),
                "owner": o.get("owner"),
                "opened": o.get("timestamp"),
            })
    return out


@bp.get("/awaiting_owner")
@require_principal
def awaiting_owner():
    """awaiting_owner — the 'waiting on me' home view: every packet gated on the operator, accept/reject inline (G-4)."""
    led = get_obligation_ledger()
    items = _awaiting(led)
    return jsonify({
        "meta": {"gate": HUMAN_GATE, "count": len(items),
                 "doctrine": "one human gate; accept → approve, reject → close (rejected)",
                 "chain_ok": led.verify_chain()},
        "awaiting": items,
    })


@bp.get("/review_brief")
@require_principal
def review_brief():
    """review_brief — serve the sealed Review Brief markdown for a book so it is one click from the
    Awaiting-the operator card (pilot finding #2, peer review [171]: 'is the brief attached to the card?' — yes)."""
    from pathlib import Path as _P  # noqa: PLC0415
    tok = (request.args.get("book") or "").strip()
    if not tok:
        return jsonify(route_error(
            error="missing_book",
            what="Pass ?book=<id-or-token> (e.g. B12).",
            why="The request had no 'book' query parameter to resolve a Review Brief for.",
            next_step="Add ?book=<id-or-token> to the request.")), 400
    art = _P(__file__).resolve().parents[4] / "artifacts"
    for p in sorted(art.glob("*[Rr]eview_[Bb]rief*")):
        if tok.lower() in p.name.lower():
            return jsonify({"book": tok, "file": p.name, "markdown": p.read_text(encoding="utf-8")})
    return jsonify(route_error(
        error="not_found",
        what=f"No Review Brief found for '{tok}'.",
        why="No artifacts/<token>_*Review_Brief*.md matched the requested book token.",
        next_step="the peer seals it in artifacts/<TOKEN>_*Review_Brief*.md.")), 404


# Allowed document roots — a card may HAND any readable doc under these (the peer A4: artifacts handed, not listed).
def _doc_roots():
    # Runs-anywhere (audit 2026-06-13d #3, §1 SOURCE): the vault root flows through config (honors
    # BREATHLINE_BOOKS_VAULT) like every other vault consumer — not a hardcoded operator literal that
    # made /doc serve nothing on any other host / when the vault is repointed. get_books_kdp_root()
    # already returns the kdp root (no `/ "kdp"` suffix).
    from pathlib import Path as _P  # noqa: PLC0415
    from ... import config  # noqa: PLC0415
    repo = _P(__file__).resolve().parents[4]
    roots = [repo / "artifacts", repo / "scripts"]
    kdp = config.get_books_kdp_root()
    if kdp:
        roots.append(_P(kdp))
    return roots


@bp.get("/doc")
@require_principal
def doc():
    """doc — serve a whitelisted document (board review, Review Brief, proposal, dispatch sheet) as markdown
    so EVERY Awaiting-Me card can hand its artifact for the operator to read before disposing, in-cockpit
    (the peer A4). Safe: resolves ONLY under the allowed doc roots; .md/.txt/.yaml/.yml only; resolve() collapses
    any '..' and the result must still start with an allowed root (no traversal escape)."""
    from pathlib import Path as _P  # noqa: PLC0415
    rel = (request.args.get("path") or "").strip()
    if not rel:
        return jsonify(route_error(
            error="missing_path",
            what="Pass ?path=<doc path> (the path the card references).",
            why="The request had no 'path' query parameter to resolve a document for.",
            next_step="Add ?path=<doc path> (the card's path field).")), 400
    # Tolerate a leading vault-name prefix (cards sometimes hand 'breathline-books-vault/kdp/…' instead of the
    # vault-relative 'kdp/…'). Normalize so either format resolves (still traversal-safe — checked below).
    if rel.startswith("breathline-books-vault/"):
        rel = rel[len("breathline-books-vault/"):]
    roots = [r.resolve() for r in _doc_roots()]
    raw = _P(rel)
    cands = [raw] if raw.is_absolute() else [r / rel for r in roots]
    # also tolerate a path that begins with a root's last segment (e.g. 'artifacts/x.md', 'kdp/...md')
    for r in _doc_roots():
        cands.append(r.parent / rel)
    for c in cands:
        try:
            rp = c.resolve()
        except (OSError, ValueError):
            continue
        if rp.suffix.lower() not in (".md", ".txt", ".yaml", ".yml"):
            continue
        if not any(str(rp) == str(root) or str(rp).startswith(str(root) + "/") for root in roots):
            continue   # outside every allowed root → refuse (traversal-safe after resolve())
        if rp.is_file():
            return jsonify({"path": rel, "file": rp.name,
                            "markdown": rp.read_text(encoding="utf-8", errors="replace")})

    # Bare-filename fallback: a card may hand just a filename (e.g. 'manuscript_v1.4.md' named in card text).
    # Search the doc roots for an exact, unique filename match; serve it if found (safe: still under a root,
    # allowed suffix; ambiguous matches refuse loudly so we never serve the wrong book's doc).
    if "/" not in rel and _P(rel).suffix.lower() in (".md", ".txt", ".yaml", ".yml"):
        hits = []
        for root in roots:
            hits += [p for p in root.rglob(rel) if p.is_file()]
        uniq = sorted({str(p.resolve()) for p in hits})
        if len(uniq) == 1:
            rp = _P(uniq[0])
            return jsonify({"path": rel, "file": rp.name,
                            "markdown": rp.read_text(encoding="utf-8", errors="replace")})
        if len(uniq) > 1:
            return jsonify(route_error(
                error="ambiguous",
                what=f"'{rel}' matches {len(uniq)} files.",
                why="A bare filename resolved to multiple documents across the doc roots.",
                next_step="Pass the full vault-relative path (the card's path field).")), 409

    return jsonify(route_error(
        error="not_found",
        what=f"No readable document for '{rel}'.",
        why="The path did not resolve to a readable file under any allowed doc root.",
        next_step="Cards may hand .md/.yaml docs under artifacts/, scripts/, or the books vault kdp/.")), 404


@bp.get("/pdf")
@require_principal
def pdf():
    """pdf — serve a whitelisted built PDF (manuscript / outline / cover) as application/pdf so a card can open
    the operator's PREFERRED review format in-cockpit (the operator 2026-06-23: 'my human review is pdf'). Same safety as
    /doc: resolves ONLY under the allowed roots, .pdf only, resolve() collapses '..' and the result must still
    start with an allowed root. Tolerates a leading 'breathline-books-vault/' prefix like /doc."""
    from pathlib import Path as _P  # noqa: PLC0415
    from flask import send_file  # noqa: PLC0415
    rel = (request.args.get("path") or "").strip()
    if not rel:
        return jsonify(route_error(error="missing_path", what="Pass ?path=<pdf path>.",
                                   why="No 'path' query parameter.", next_step="Add ?path=<built pdf path>.")), 400
    if rel.startswith("breathline-books-vault/"):
        rel = rel[len("breathline-books-vault/"):]
    roots = [r.resolve() for r in _doc_roots()]
    raw = _P(rel)
    cands = [raw] if raw.is_absolute() else [r / rel for r in roots]
    for r in _doc_roots():
        cands.append(r.parent / rel)
    for c in cands:
        try:
            rp = c.resolve()
        except (OSError, ValueError):
            continue
        if rp.suffix.lower() != ".pdf":
            continue
        if not any(str(rp) == str(root) or str(rp).startswith(str(root) + "/") for root in roots):
            continue   # traversal-safe
        if rp.is_file():
            return send_file(str(rp), mimetype="application/pdf", as_attachment=False, download_name=rp.name)
    return jsonify(route_error(
        error="not_found", what=f"No readable PDF for '{rel}'.",
        why="The path did not resolve to a .pdf under any allowed doc root.",
        next_step="Pass the vault-relative path to a built PDF (e.g. kdp/.../final/Immutable_Core.pdf).")), 404


def _ring_the_bell(obligation_id: str, principal: str = "system:bell") -> None:
    """THE BELL — on the operator's Accept, spawn the executor for this packet (detached; clone of /produce's spawn).
    Turns approval into automatic execution + receipt back in the cockpit, so 'processing' means working,
    never waiting. Best-effort: a spawn failure is logged, never blocks the disposition (the --drain
    backstop catches anything missed).

    PRINCIPAL PROPAGATION (audit 2026-06-13 HIGH, CONSTITUTION §1): the executor mutates the hash-chained
    ledger; its write must attribute to the OPERATOR who clicked Accept, not a hardcoded 'node'. We pass
    `principal` (current_principal()) through BREATHLINE_BELL_PRINCIPAL so the credit, its receipt, and the
    actions projection all name the real authorizer."""
    import logging  # noqa: PLC0415
    import subprocess  # noqa: PLC0415
    import sys  # noqa: PLC0415
    from pathlib import Path as _P  # noqa: PLC0415
    try:
        repo = _P(__file__).resolve().parents[4]
        script = repo / "scripts" / "atrium_executor.py"
        if not script.exists():
            return
        env = dict(os.environ)
        env["PYTHONPATH"] = str(repo / "src")
        env["BREATHLINE_BELL_PRINCIPAL"] = principal or "system:bell"
        subprocess.Popen([sys.executable, str(script), obligation_id], cwd=str(repo), env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except Exception as exc:  # noqa: BLE001 — the bell must never break the human gate
        logging.getLogger("breathline.executor").warning("bell spawn failed for %s: %s", obligation_id, exc)


@bp.get("/handshakes")
@require_principal
def handshakes():
    """A3 — the handshakes row: agent-to-agent residue (executor pending / awaiting the peer / awaiting the node) so
    any not-yet-closed work is ALWAYS visible to the operator, never silently stuck. Reads the executor's store.

    One resolver + cached (audit 2026-06-13d #10/#13/#21/#24/#35): the path comes from the SAME
    `sidecar_store` the writer (atrium_executor) uses — no inline reimplementation that could drift — and
    the GET read is memoized like the sibling stores."""
    store = sidecar_store("handshakes.json", "HANDSHAKES_STORE")
    items = [h for h in read_json_cached(store, []) if h.get("status") != "done"]
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify({"meta": {"count": len(items), "doctrine": "every approved packet is working or visible — never stuck"},
                    "handshakes": items})


def _owner_agent(card: dict) -> str:
    """Which AGENT must act on the operator's rejection note (NOT the human card owner). Derived from the card's
    ref/intent — book + distribution work is the node's; the peer plans/reviews. Default the node (the implementer)."""
    blob = ((card.get("ref") or "") + " " + (card.get("intent") or "") + " " + (card.get("title") or "")).lower()
    if blob.startswith("relay") or "peer_" in blob or "re-read" in blob or "board re-stamp" in blob:
        return "peer"
    return os.environ.get("BREATHLINE_FEEDBACK_AGENT", "node")


def _route_note(led, card: dict, obligation_id: str, note: str, tag_as_standard: bool):
    """Forward Feedback Loop — Capture step 1 (the forward-feedback spec). Route a disposition NOTE so it is
    never lost: a comment the operator TAGS AS A STANDARD mints a `feedback_standard:<id>` obligation owned the peer (classify →
    encode into the YAML the gates load → inherit by construction); a plain note mints a `feedback:<id>` follow-on
    owned the card's owner-AGENT (local fix). Either way it lands as tracked, agent-gated work — not the operator again."""
    if not note:
        return None
    label = (card.get("title") or card.get("ref") or obligation_id)
    if tag_as_standard:
        return led.open(
            title=f"📐 the operator standard (encode): {label}"[:118],
            owner="peer", classification="C1", material=False,
            next_gate="peer action", ref=f"feedback_standard:{obligation_id}",
            intent=(f'the operator TAGGED this feedback AS A STANDARD (verbatim): "{note}". Classify (tighten an existing '
                    f"gate vs a new criterion — bloat-guard, the operator-visible), then ENCODE into book_standard.yaml / "
                    f"distribution_standard.yaml (the machine source the gates LOAD from); version-bump + the operator-ratified "
                    f"note; close with the commit ref as the receipt. Every volume after inherits it by construction "
                    f"(Phase-0 re-seed). Source card: {obligation_id} ({label})."),
            lgp={"objective": "the operator judgment propagates forward as a rail standard — quality same-or-tighter (FFL)"},
        )
    agent = _owner_agent(card)
    return led.open(
        title=f"📨 the operator feedback — address: {label}"[:118],
        owner=agent, classification="C2", material=False,
        next_gate=f"{agent} action", ref=f"feedback:{obligation_id}",
        intent=(f'the operator dispositioned "{label}" with feedback (verbatim): "{note}". Address it, then close. '
                f"Linked card: {obligation_id}."),
        lgp={"objective": "the operator feedback reliably captured as tracked agent work (capture-reliability)"},
    )


@bp.post("/feedback/<obligation_id>/disposition")
@require_principal
@require_owner
def feedback_disposition(obligation_id: str):
    """disposition — the operator acts inline: accept (approve/clear gate) or reject (close, rejected). Clones
    obligations.approve / obligations.close so the packet visibly leaves the Awaiting-the operator view.

    SECURITY (night-watch HIGH 2026-06-12): @require_owner — Accept ignites the executor (_ring_the_bell)
    which mutates the hash-chained ledger and can spawn BREATHLINE_EXECUTOR_AGENT, so it is owner-only,
    mirroring the code-executing /produce, /apply, /recompile routes. the owner (loopback owner) still acts;
    federation peers / non-owner principals are barred from triggering execution + chain mutation."""
    body = request.get_json(silent=True) or {}
    action = (body.get("action") or "").lower()
    note = (body.get("note") or "").strip()
    led = get_obligation_ledger()
    if action not in ("accept", "reject"):
        return jsonify(route_error(
            error="bad_action",
            what="Disposition needs an action: accept or reject.",
            why=f"The 'action' was '{action or 'empty'}', not one of accept|reject.",
            next_step="POST .../disposition with JSON {\"action\": \"accept|reject\", \"note\": \"...\"}.")), 400
    # Mirror obligations.py error voice (audit fix): not-found → 404, already-closed → 409, denied → 403.
    try:
        # resolve the card BEFORE acting so a NOTE routes (FFL Capture step 1) regardless of accept/reject
        card = _open_obligation(led, obligation_id) or {}
        tag_std = bool(body.get("tag_as_standard"))
        if action == "accept":
            entry = led.approve(obligation_id, approved_by=current_principal())
            # Accept IS the ignition — spawn the registered executor, carrying the authenticated principal.
            _ring_the_bell(obligation_id, current_principal())
            fu = _route_note(led, card, obligation_id, note, tag_std)   # accept-with-comment is captured too
            return jsonify({"action": "accept", "obligation": entry, "executor": "spawned",
                            "feedback_obligation": (fu or {}).get("id"),
                            "routed_to": (fu or {}).get("owner") if fu else None,
                            "tagged_standard": bool(fu and tag_std)})
        entry = led.close(
            obligation_id,
            evidence=f"REJECTED by {current_principal()}: {note or 'no reason given'}",
            evidence_tier="E1", require_e1=False, closed_by=current_principal(),
            rejected=True,  # a refusal is a valid human disposition — no prior approve() needed (even if material)
        )
        # Capture (Item 1 + FFL): a note routes to tracked agent/the peer work — never lost in the close-evidence string.
        fu = _route_note(led, card, obligation_id, note, tag_std)
        return jsonify({"action": "reject", "obligation": entry,
                        "feedback_obligation": (fu or {}).get("id"),
                        "routed_to": (fu or {}).get("owner") if fu else None,
                        "tagged_standard": bool(fu and tag_std)})
    except KeyError:
        return jsonify(route_error(
            error="obligation_not_found",
            what=f"No obligation '{obligation_id}'.",
            why="The id did not resolve to any obligation on the ledger chain.",
            next_step="Refresh the Awaiting-Me view — it may already be disposed.")), 404
    except AlreadyClosedError as exc:
        return jsonify(route_error(
            error="already_closed",
            what=str(exc),
            why="The obligation already carries a credit; it has left the awaiting-me queue.",
            next_step="It already left the queue — no further action.")), 409
    except PermissionError as exc:
        return jsonify(route_error(
            error="breath_gate_denied",
            what=str(exc),
            why="A material obligation cannot close without a recorded human approval (breath-gate).",
            next_step="Approve it first (the human disposition), then close.")), 403
