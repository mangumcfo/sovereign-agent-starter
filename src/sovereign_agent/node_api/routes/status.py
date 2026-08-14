"""status.py — the ONE canonical node status document (CH3). GET /api/v1/status returns exactly
sovereign_agent.agent.local_mind.facts() — the same function the CLI (node_agent status) and the console chat
panel read. No divergent fact sources. Read-only; composes package verbs; no mutation."""
from __future__ import annotations

from flask import Blueprint, jsonify

from ..auth import require_principal
from ...agent import local_mind

bp = Blueprint("status", __name__, url_prefix="/api/v1")


@bp.route("/status", methods=["GET"])
@require_principal
def status():
    return jsonify(local_mind.facts())
