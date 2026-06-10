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

from flask import Blueprint, jsonify, request

from ..auth import current_principal, require_principal
from ..deps import get_obligation_ledger

bp = Blueprint("feedback", __name__, url_prefix="/api/v1")

HUMAN_GATE = "Human disposition"

# Typed sources → a readable title prefix. Any surface can emit; the type just frames the packet.
_KINDS = {
    "drift": "DRIFT",
    "viewer": "Viewer feedback",
    "series": "Pipeline feedback",
    "coherence": "Coherence/DRIFT",
    "general": "Feedback",
}


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
    title = f"{prefix}: {text[:80]}"
    entry = get_obligation_ledger().open(
        title=title,
        owner=body.get("owner") or current_principal(),
        classification=body.get("classification", "C2"),
        intent=text,
        ref=ref,
        material=bool(body.get("material", False)),
        lgp=body.get("lgp"),
        next_gate=HUMAN_GATE,
    )
    return jsonify({"obligation": entry, "kind": kind, "source": ref}), 201


def _awaiting(led) -> list:
    """Open obligations gated on Human disposition — KM-framed (the cockpit's missing home screen)."""
    out = []
    for o in led.open_obligations():
        # Awaiting KM = gated on a human AND not yet disposed. Once accepted (approved) it leaves this
        # view — it's now awaiting the owning agent's execution, not the human's decision. Rejected
        # items are closed and already drop out of open_obligations().
        if (o.get("next_gate") or "") == HUMAN_GATE and not o.get("approved"):
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


@bp.post("/feedback/<obligation_id>/disposition")
@require_principal
def feedback_disposition(obligation_id: str):
    """disposition — KM acts inline: accept (approve/clear gate) or reject (close, rejected). Clones
    obligations.approve / obligations.close so the packet visibly leaves the Awaiting-KM view."""
    body = request.get_json(silent=True) or {}
    action = (body.get("action") or "").lower()
    note = (body.get("note") or "").strip()
    led = get_obligation_ledger()
    if action == "accept":
        entry = led.approve(obligation_id, approved_by=current_principal())
        return jsonify({"action": "accept", "obligation": entry})
    if action == "reject":
        entry = led.close(
            obligation_id,
            evidence=f"REJECTED by {current_principal()}: {note or 'no reason given'}",
            evidence_tier="E1", require_e1=False, closed_by=current_principal(),
        )
        return jsonify({"action": "reject", "obligation": entry})
    return jsonify({
        "error": "bad_action",
        "what": "Disposition needs an action: accept or reject.",
        "next_step": "POST .../disposition with JSON {\"action\": \"accept|reject\", \"note\": \"...\"}.",
    }), 400
