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

from ...obligations import AlreadyClosedError
from ..auth import current_principal, require_owner, require_principal
from ..deps import get_obligation_ledger
from ..errors import route_error


def _not_found(obligation_id: str):
    return jsonify(route_error(
        error="obligation_not_found",
        what=f"No obligation '{obligation_id}' exists.",
        why="The id did not resolve to any debit on the ledger chain.",
        next_step="Open it first (POST /api/v1/obligations) or check the id.")), 404


def _already_closed(exc):
    return jsonify(route_error(
        error="already_closed",
        what=str(exc),
        why="The obligation already carries a credit entry; closing again would double-credit the chain.",
        next_step="This obligation is already credited/closed — no further action.")), 409

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
        return jsonify(route_error(
            error="missing_title",
            what="An obligation needs a title.",
            why="The request body had no non-empty 'title' to open a debit for.",
            next_step="POST /api/v1/obligations with JSON {\"title\": \"...\"}.")), 400
    try:
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
    except ValueError as exc:  # resolve-at-entry: a path-like ref that doesn't resolve (audit 2026-06-13 W5 #7)
        return jsonify(route_error(
            error="unresolvable_ref",
            what=str(exc),
            why="A path-like `ref` is validated at entry — a pointer is never written false.",
            next_step="Pass a ref that resolves to a real file, or a symbolic ref (e.g. 'B11:veto-chapter').")), 422
    return jsonify(entry), 201


@bp.post("/obligations/<obligation_id>/approve")
@require_principal
@require_owner
def obligations_approve(obligation_id: str):
    """obligations.approve — clear the breath-gate (human disposition).

    Owner-gated (audit 2026-06-13 W5 #1): approve() clears KM's constitutional breath-gate and records
    `approved_by`, so it must carry the SAME authority as /feedback/disposition, /proposals/decide,
    /apply. A non-owner (dev/loopback/federation peer) can no longer dispose KM's material obligations.

    CROSS-REF (audit 2026-06-13c #29): this ledger-backed route is the LIVE constitutional gate. The
    separate /breath_gate/<id>/approve surface is the session-scoped in-memory ComplianceEngine gate."""
    body = request.get_json(silent=True) or {}
    led = get_obligation_ledger()
    try:
        entry = led.approve(
            obligation_id,
            approved_by=current_principal(),  # the breath-gate actor is the AUTHENTICATED principal — uncloneable (audit 2026-06-10)
            rationale=body.get("rationale", ""),
        )
    except KeyError:
        return _not_found(obligation_id)
    except AlreadyClosedError as exc:
        return _already_closed(exc)
    except PermissionError as exc:
        return jsonify(route_error(
            error="breath_gate_denied",
            what=str(exc),
            why="The configured breath-gate denied the approval (human disposition not granted).",
            next_step="The obligation stays open. Re-propose or revise before re-requesting approval.")), 403
    return jsonify(entry)


@bp.post("/obligations/<obligation_id>/close")
@require_principal
@require_owner
def obligations_close(obligation_id: str):
    """obligations.close — credit with evidence; mints a node receipt.

    Owner-gated (audit 2026-06-13 W5 #1): close() mints a receipt + credit on the immutable chain and
    records `closed_by`; owner-only, mirroring the sibling disposition routes.

    NOTE (audit 2026-06-13c #23): a body `closed_by`/`owner` is INTENTIONALLY IGNORED — the principal is
    always bound to the authenticated caller (current_principal()), never the request body (§1, no
    spoofing). HTTP callers that still send the field have it silently dropped; this is by design."""
    body = request.get_json(silent=True) or {}
    evidence = (body.get("evidence") or "").strip()
    if not evidence:
        return jsonify(route_error(
            error="missing_evidence",
            what="Closing an obligation requires evidence (an artifact pointer / hash / receipt).",
            why="The close request had no 'evidence' — an E0 claim-only close is rejected.",
            next_step="POST .../close with JSON {\"evidence\": \"<path|hash|receipt_id>\"}.")), 400
    led = get_obligation_ledger()
    try:
        entry = led.close(
            obligation_id,
            evidence=evidence,
            evidence_tier=body.get("evidence_tier"),
            require_e1=bool(body.get("require_e1", True)),
            closed_by=current_principal(),  # bind to authenticated principal, never the request body (audit 2026-06-10)
        )
    except KeyError:
        return _not_found(obligation_id)
    except AlreadyClosedError as exc:
        return _already_closed(exc)
    except ValueError as exc:  # E0 / claim-only insufficient
        return jsonify(route_error(
            error="insufficient_evidence",
            what=str(exc),
            why="The evidence was E0 (claim-only); the ledger requires E1 (pointer) minimum to credit.",
            next_step="Provide an artifact pointer, hash, or receipt id (E1 minimum; E2 preferred).")), 422
    except PermissionError as exc:  # material obligation not yet through the breath-gate
        return jsonify(route_error(
            error="approval_required",
            what=str(exc),
            why="A material obligation cannot credit without a recorded human approval (breath-gate).",
            next_step="POST .../approve first (human disposition), then close.")), 409
    return jsonify(entry)
