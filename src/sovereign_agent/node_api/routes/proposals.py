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

from ..auth import current_principal, require_principal

bp = Blueprint("proposals", __name__, url_prefix="/api/v1")


def _store_path() -> Path:
    explicit = os.environ.get("PROPOSALS_STORE")
    if explicit:
        return Path(explicit)
    led = os.environ.get("OBLIGATION_LEDGER_ROOT")
    base = Path(led).parent if led else Path(os.path.expanduser("~/.breathline"))
    return base / "proposals.json"


def _read() -> list:
    p = _store_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8")) or []
    except (OSError, ValueError):
        return []


def _write(items: list) -> None:
    p = _store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(items, indent=2), encoding="utf-8")


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
    if not groups:
        return jsonify({
            "error": "missing_groups",
            "what": "A proposal needs at least one grouped diff.",
            "next_step": "POST /api/v1/proposals with {\"session_ref\":\"...\",\"groups\":[{title,kind,scope,rationale,file,before,after}]}.",
        }), 400
    items = _read()
    prop = {
        "id": "prop_" + str(int(time.time() * 1000)),
        "session_ref": body.get("session_ref", ""),
        "obligation_id": body.get("obligation_id"),
        "book": body.get("book", ""),
        "note": body.get("note", ""),
        "produced_by": body.get("produced_by") or current_principal(),
        "groups": groups,
        "status": "proposed",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    items.append(prop)
    _write(items)
    return jsonify(prop), 201


@bp.post("/proposals/<proposal_id>/decide")
@require_principal
def proposals_decide(proposal_id: str):
    body = request.get_json(silent=True) or {}
    decisions = body.get("decisions") or {}  # {group_id: "accept"|"reject"}
    items = _read()
    found = None
    for it in items:
        if it.get("id") == proposal_id:
            it.setdefault("decisions", {}).update(decisions)
            it["decided_by"] = current_principal()
            it["status"] = "decided"
            found = it
            break
    if not found:
        return jsonify({"error": "not_found", "what": f"No proposal {proposal_id}."}), 404
    _write(items)
    return jsonify(found)
