"""
Section — Obligations (R-23 Phase 3).

Exposes the node ObligationLedger over the Node API:

    GET  /obligations                     → list open + status rollup + the view
    POST /obligations                     → open (debit; draft, CYL-006)
    POST /obligations/{id}/approve        → approve (breath-gate; human disposition)
    POST /obligations/{id}/close          → close (credit; evidence-tiered; mints a node receipt)

No business logic in the HTTP layer — it only translates JSON ↔ the ObligationLedger and
re-emits the receipted envelope. The ledger enforces CYL-006 (draft→approve), the evidence
floor (E0 rejected for material closes), and the hard storage boundary.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..auth import current_principal, require_principal
from ..deps import get_obligation_ledger

bp = Blueprint("obligations", __name__, url_prefix="/api/v1")


@bp.get("/obligations")
@require_principal
def obligations_list():
    """obligations.list — open obligations + status rollup + per-owner view."""
    led = get_obligation_ledger()
    return jsonify({
        "open": led.open_obligations(),
        "status": led.by_status(),
        "by_owner": led.by_owner(),
        "chain_ok": led.verify_chain(),
    })


@bp.get("/obligations/log")
@require_principal
def obligations_log():
    """obligations.log — full materialized ledger (open + closed w/ evidence + receipts), read-only.

    Powers the Atrium review / book↔code drilldown: lets the cockpit show a closed obligation
    with the seal evidence it produced — the feedback→edits→seal trace, live.
    """
    led = get_obligation_ledger()
    return jsonify({
        "log": led.full_log(),
        "status": led.by_status(),
        "chain_ok": led.verify_chain(),
    })


@bp.post("/obligations")
@require_principal
def obligations_open():
    """obligations.open — open a debit (draft, CYL-006)."""
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    if not title:
        return jsonify({
            "error": "missing_title",
            "what": "An obligation needs a title.",
            "next_step": "POST /api/v1/obligations with JSON {\"title\": \"...\"}.",
        }), 400
    entry = get_obligation_ledger().open(
        title=title,
        owner=current_principal(),  # bind to authenticated principal, never the request body (audit 2026-06-10)
        classification=body.get("classification", "C2"),
        intent=body.get("intent"),
        ref=body.get("ref"),
        material=bool(body.get("material", False)),
        lgp=body.get("lgp"),            # P0-2: LGP travels through the HTTP layer too
        next_gate=body.get("next_gate"),
    )
    return jsonify(entry), 201


@bp.post("/obligations/<obligation_id>/approve")
@require_principal
def obligations_approve(obligation_id: str):
    """obligations.approve — clear the breath-gate (human disposition)."""
    body = request.get_json(silent=True) or {}
    led = get_obligation_ledger()
    try:
        entry = led.approve(
            obligation_id,
            approved_by=current_principal(),  # the breath-gate actor is the AUTHENTICATED principal — uncloneable (audit 2026-06-10)
            rationale=body.get("rationale", ""),
        )
    except PermissionError as exc:
        return jsonify({
            "error": "breath_gate_denied",
            "what": str(exc),
            "next_step": "The obligation stays open. Re-propose or revise before re-requesting approval.",
        }), 403
    return jsonify(entry)


@bp.post("/obligations/<obligation_id>/close")
@require_principal
def obligations_close(obligation_id: str):
    """obligations.close — credit with evidence; mints a node receipt."""
    body = request.get_json(silent=True) or {}
    evidence = (body.get("evidence") or "").strip()
    if not evidence:
        return jsonify({
            "error": "missing_evidence",
            "what": "Closing an obligation requires evidence (an artifact pointer / hash / receipt).",
            "next_step": "POST .../close with JSON {\"evidence\": \"<path|hash|receipt_id>\"}.",
        }), 400
    led = get_obligation_ledger()
    try:
        entry = led.close(
            obligation_id,
            evidence=evidence,
            evidence_tier=body.get("evidence_tier"),
            require_e1=bool(body.get("require_e1", True)),
            closed_by=current_principal(),  # bind to authenticated principal, never the request body (audit 2026-06-10)
        )
    except ValueError as exc:  # E0 / claim-only insufficient
        return jsonify({
            "error": "insufficient_evidence",
            "what": str(exc),
            "next_step": "Provide an artifact pointer, hash, or receipt id (E1 minimum; E2 preferred).",
        }), 422
    except PermissionError as exc:  # material obligation not yet through the breath-gate
        return jsonify({
            "error": "approval_required",
            "what": str(exc),
            "next_step": "POST .../approve first (human disposition), then close.",
        }), 409
    return jsonify(entry)
