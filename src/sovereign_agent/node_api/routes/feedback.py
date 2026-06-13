"""
Section — Feedback & Awaiting-KM (Atrium Loop-Closure R2, Wave 1 — the B12 Pilot Kit).

Per GB_Atrium_LoopClosure_Audit_2026-06-10.md. The backend loops were real; the cockpit was a mock.
This is the ONE intake primitive that lets EVERY Atrium surface turn an observation into a packet, plus
the KM-framed "waiting on me" projection with inline accept/reject — all on the hash-chained
ObligationLedger. Clones the hopper_to_packet / obligations.open|approve|close patterns; invents nothing.

    POST /feedback                  → mint a Human-disposition obligation from any surface  (G-3, G-6, G-2)
    GET  /awaiting_km               → projection of obligations awaiting KM disposition       (G-4)
    POST /feedback/<id>/disposition → {action: accept|reject, note} → approve | close         (G-4 inline)

Read-only projections (/series, /coherence) stay read-only per the fence — they call POST /feedback to
emit a packet; they never gain write access. DRIFT button and viewer feedback are typed /feedback calls.

∞Δ∞ Wire the glass to the machine and the human never leaves the chair. ∞Δ∞
"""
from __future__ import annotations

import json
import os

from flask import Blueprint, jsonify, request

from ...obligations import AlreadyClosedError
from ..auth import current_principal, require_principal, require_owner
from ..deps import get_obligation_ledger

bp = Blueprint("feedback", __name__, url_prefix="/api/v1")

HUMAN_GATE = "Human disposition"
TIGER_GATE = "KM confirm → Tiger implement"
BATCH_GATE = "batch:mechanical"

# Typed sources → a readable title prefix. Any surface can emit; the type just frames the packet.
_KINDS = {
    "drift": "DRIFT",
    "viewer": "Viewer feedback",
    "series": "Pipeline feedback",
    "coherence": "Coherence/DRIFT",
    "general": "Feedback",
}

# A2 (GB meta-review #2) — capture-time classification. The one-tap category routes the lane
# AUTOMATICALLY so triage never lands downstream on Tiger or on KM's attention:
#   mechanical (typo/wording/structure) → BATCH lane, born-approved (material=False, no KM gate)
#   technical                           → DISCRETE, KM confirm → Tiger implements (a build/tooling fix)
#   judgment                            → DISCRETE, gated on KM's Human disposition (he decides)
# Smart default = 'wording': the dominant class (~90 PDF-edit packets are page-level wording/typo/
# structure). Defaulting kills the 36% "other" — capture is always classified, never unclassified.
_CATEGORIES = {
    "typo":      {"lane": "batch",    "material": False, "gate": BATCH_GATE},
    "wording":   {"lane": "batch",    "material": False, "gate": BATCH_GATE},
    "structure": {"lane": "batch",    "material": False, "gate": BATCH_GATE},
    "technical": {"lane": "discrete", "material": False, "gate": TIGER_GATE},
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


@bp.post("/feedback")
@require_principal
def feedback_intake():
    """feedback.intake — any surface → a C2 obligation gated on Human disposition (G-3/G-6/G-2)."""
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({
            "error": "missing_text",
            "what": "Feedback needs text — what should change?",
            "next_step": "POST /api/v1/feedback with JSON {\"text\": \"...\", \"type\": \"drift|viewer|general\", \"source\": \"...\"}.",
        }), 400
    kind = (body.get("type") or "general").lower()
    prefix = _KINDS.get(kind, _KINDS["general"])
    ref = _source_ref(body)
    # A2 capture classification → automatic lane routing (mechanical batch / technical / judgment).
    category, route, defaulted = _classify(body)
    title = f"[{category}] {prefix}: {text[:72]}"
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
    return jsonify({"obligation": entry, "kind": kind, "source": ref,
                    "category": category, "lane": route["lane"],
                    "category_defaulted": defaulted}), 201


def _awaiting(led) -> list:
    """Open obligations gated on Human disposition — KM-framed (the cockpit's missing home screen)."""
    out = []
    for o in led.open_obligations():
        # Awaiting KM = gated on a human AND not yet disposed. Once accepted (approved) it leaves this
        # view — it's now awaiting the owning agent's execution, not the human's decision. Rejected
        # items are closed and already drop out of open_obligations().
        # Prefix match, not exact: a human gate may carry a context suffix (e.g.
        # "Human disposition (Atrium Review)"). Exact-== silently hid those, leaving real
        # human-gated feedback stale + invisible to KM. Any "Human disposition…" gate is KM's.
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


@bp.get("/awaiting_km")
@require_principal
def awaiting_km():
    """awaiting_km — the 'waiting on me' home view: every packet gated on KM, accept/reject inline (G-4)."""
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
    Awaiting-KM card (pilot finding #2, GB [171]: 'is the brief attached to the card?' — yes)."""
    from pathlib import Path as _P  # noqa: PLC0415
    tok = (request.args.get("book") or "").strip()
    if not tok:
        return jsonify({"error": "missing_book", "what": "Pass ?book=<id-or-token> (e.g. B12)."}), 400
    art = _P(__file__).resolve().parents[4] / "artifacts"
    for p in sorted(art.glob("*[Rr]eview_[Bb]rief*")):
        if tok.lower() in p.name.lower():
            return jsonify({"book": tok, "file": p.name, "markdown": p.read_text(encoding="utf-8")})
    return jsonify({"error": "not_found", "what": f"No Review Brief found for '{tok}'.",
                    "next_step": "GB seals it in artifacts/<TOKEN>_*Review_Brief*.md."}), 404


# Allowed document roots — a card may HAND any readable doc under these (GB A4: artifacts handed, not listed).
def _doc_roots():
    from pathlib import Path as _P  # noqa: PLC0415
    repo = _P(__file__).resolve().parents[4]
    vault = _P("/home/kmangum/work-repos/mangumcfo/breathline-books-vault")
    return [repo / "artifacts", repo / "scripts", vault / "kdp"]


@bp.get("/doc")
@require_principal
def doc():
    """doc — serve a whitelisted document (board review, Review Brief, proposal, dispatch sheet) as markdown
    so EVERY Awaiting-Me card can hand its artifact for the operator to read before disposing, in-cockpit
    (GB A4). Safe: resolves ONLY under the allowed doc roots; .md/.txt/.yaml/.yml only; resolve() collapses
    any '..' and the result must still start with an allowed root (no traversal escape)."""
    from pathlib import Path as _P  # noqa: PLC0415
    rel = (request.args.get("path") or "").strip()
    if not rel:
        return jsonify({"error": "missing_path",
                        "what": "Pass ?path=<doc path> (the path the card references)."}), 400
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
            return jsonify({"error": "ambiguous", "what": f"'{rel}' matches {len(uniq)} files.",
                            "next_step": "Pass the full vault-relative path (the card's path field)."}), 409

    return jsonify({"error": "not_found", "what": f"No readable document for '{rel}'.",
                    "next_step": "Cards may hand .md/.yaml docs under artifacts/, scripts/, or the books vault kdp/."}), 404


def _ring_the_bell(obligation_id: str, principal: str = "system:bell") -> None:
    """THE BELL — on KM's Accept, spawn the executor for this packet (detached; clone of /produce's spawn).
    Turns approval into automatic execution + receipt back in the cockpit, so 'processing' means working,
    never waiting. Best-effort: a spawn failure is logged, never blocks the disposition (the --drain
    backstop catches anything missed).

    PRINCIPAL PROPAGATION (audit 2026-06-13 HIGH, CONSTITUTION §1): the executor mutates the hash-chained
    ledger; its write must attribute to the OPERATOR who clicked Accept, not a hardcoded 'tiger'. We pass
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
    """A3 — the handshakes row: agent-to-agent residue (executor pending / awaiting GB / awaiting Tiger) so
    any not-yet-closed work is ALWAYS visible to KM, never silently stuck. Reads the executor's store."""
    from pathlib import Path as _P  # noqa: PLC0415
    led_root = os.environ.get("OBLIGATION_LEDGER_ROOT")
    base = _P(led_root).parent if led_root else _P(os.path.expanduser("~/.breathline"))
    store = _P(os.environ.get("HANDSHAKES_STORE") or (base / "handshakes.json"))
    items = []
    if store.exists():
        try:
            items = [h for h in (json.loads(store.read_text(encoding="utf-8")) or [])
                     if h.get("status") != "done"]
        except (OSError, ValueError):
            items = []
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify({"meta": {"count": len(items), "doctrine": "every approved packet is working or visible — never stuck"},
                    "handshakes": items})


@bp.post("/feedback/<obligation_id>/disposition")
@require_principal
@require_owner
def feedback_disposition(obligation_id: str):
    """disposition — KM acts inline: accept (approve/clear gate) or reject (close, rejected). Clones
    obligations.approve / obligations.close so the packet visibly leaves the Awaiting-KM view.

    SECURITY (night-watch HIGH 2026-06-12): @require_owner — Accept ignites the executor (_ring_the_bell)
    which mutates the hash-chained ledger and can spawn BREATHLINE_EXECUTOR_AGENT, so it is owner-only,
    mirroring the code-executing /produce, /apply, /recompile routes. KM-1176 (loopback owner) still acts;
    federation peers / non-owner principals are barred from triggering execution + chain mutation."""
    body = request.get_json(silent=True) or {}
    action = (body.get("action") or "").lower()
    note = (body.get("note") or "").strip()
    led = get_obligation_ledger()
    if action not in ("accept", "reject"):
        return jsonify({
            "error": "bad_action",
            "what": "Disposition needs an action: accept or reject.",
            "next_step": "POST .../disposition with JSON {\"action\": \"accept|reject\", \"note\": \"...\"}.",
        }), 400
    # Mirror obligations.py error voice (audit fix): not-found → 404, already-closed → 409, denied → 403.
    try:
        if action == "accept":
            entry = led.approve(obligation_id, approved_by=current_principal())
            # Accept IS the ignition — spawn the registered executor, carrying the authenticated
            # principal so the bell's chain write names the Accept-clicker (audit 2026-06-13 HIGH).
            _ring_the_bell(obligation_id, current_principal())
            return jsonify({"action": "accept", "obligation": entry, "executor": "spawned"})
        entry = led.close(
            obligation_id,
            evidence=f"REJECTED by {current_principal()}: {note or 'no reason given'}",
            evidence_tier="E1", require_e1=False, closed_by=current_principal(),
            rejected=True,  # a refusal is a valid human disposition — no prior approve() needed (even if material)
        )
        return jsonify({"action": "reject", "obligation": entry})
    except KeyError:
        return jsonify({"error": "obligation_not_found", "what": f"No obligation '{obligation_id}'.",
                        "next_step": "Refresh the Awaiting-Me view — it may already be disposed."}), 404
    except AlreadyClosedError as exc:
        return jsonify({"error": "already_closed", "what": str(exc),
                        "next_step": "It already left the queue — no further action."}), 409
    except PermissionError as exc:
        return jsonify({"error": "breath_gate_denied", "what": str(exc)}), 403
