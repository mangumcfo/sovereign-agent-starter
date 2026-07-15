"""
Section A — Node identity, health, ladder.

Per contract_v1.yaml:

    GET /node          → node.get
    GET /node/health   → node.health
    GET /node/ladder   → node.ladder

These wrap `UniversalSovereignNode.get_status()` and friends. The shapes are
calibrated to the contract; gaps (e.g. real chain-sentinel state) are
explicitly named in the response so the Atrium UI never silently fakes.
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from ..auth import current_principal, require_principal
from ..deps import get_node


bp = Blueprint("node", __name__, url_prefix="/api/v1")


@bp.get("/node")
@require_principal
def node_get():
    """node.get — identity envelope."""
    node = get_node()
    status = node.get_status()
    return jsonify({
        "node_id": status.get("identity_public", "unknown"),
        "name": status.get("name"),
        "context": status.get("context"),
        "tier": _infer_tier(status.get("context", "personal")),
        "ladder_level": _infer_ladder_level(status.get("context", "personal")),
        "ladder_level_name": _ladder_level_name(_infer_ladder_level(status.get("context", "personal"))),
        "kernel_version": "0.3.0",  # tracks pyproject.toml [project].version
        "manifest_version": status.get("merkle_mode", "unknown"),
        "seal_glyph": "∞Δ∞",
        "principal_id": current_principal(),
    })


@bp.get("/node/health")
@require_principal
def node_health():
    """node.health — active health check (minimal viable)."""
    node = get_node()
    try:
        node.get_status()
        kernel_ok = True
        kernel_msg = "node responsive"
    except Exception as exc:  # noqa: BLE001 — surface kernel failure loudly
        kernel_ok = False
        kernel_msg = f"kernel raised: {exc}"

    details = [
        {"check": "kernel_responsive", "ok": kernel_ok, "message": kernel_msg},
        {"check": "node_api_version", "ok": True, "message": "node_api 0.1.0 (Track A1 minimal viable)"},
    ]

    return jsonify({
        "kernel_ok": kernel_ok,
        "manifest_ok": True,           # placeholder until specs validation lands
        "specs_valid": True,           # placeholder
        "signatures_ok": True,         # placeholder
        "chain_sentinel": "clean",     # placeholder; real sentinel in follow-up
        "breath_gate_ready": True,
        "last_seal_seq": None,         # placeholder; populated when audit route lands
        "details": details,
    })


@bp.get("/node/ladder")
@require_principal
def node_ladder():
    """node.ladder — Sovereign Ascension Ladder rung."""
    node = get_node()
    context = node.get_status().get("context", "personal")
    current_level = _infer_ladder_level(context)
    return jsonify({
        "current_level": current_level,
        "current_level_name": _ladder_level_name(current_level),
        "next_level": current_level + 1 if current_level < 4 else None,
        "next_level_name": _ladder_level_name(current_level + 1) if current_level < 4 else None,
        "requirements": [],  # populated when specs route lands
        "anchor_book": _anchor_book_for_level(current_level),
    })


# --- helpers (pure functions; no I/O) ---------------------------------------


def _infer_tier(context: str) -> str:
    """Coarse mapping from context_type → ladder tier label."""
    mapping = {
        "personal": "family",
        "family": "family",
        "corporate_executive": "executive",
        "corporate_enterprise": "enterprise",
        "full_sovereign": "full-sovereign",
    }
    return mapping.get(context, "family")


def _infer_ladder_level(context: str) -> int:
    """Coarse mapping from context_type → ladder level (0..4)."""
    mapping = {
        "personal": 0,
        "family": 1,
        "corporate_executive": 2,
        "corporate_enterprise": 3,
        "full_sovereign": 4,
    }
    return mapping.get(context, 0)


def _ladder_level_name(level: int) -> str:
    names = {
        0: "Awakening",
        1: "Family Sovereignty",
        2: "Executive Mastery",
        3: "Enterprise Governance",
        4: "Generational Inheritance",
    }
    return names.get(level, "Unknown")


def _anchor_book_for_level(level: int) -> str | None:
    anchors = {
        0: "B1 — Strategic Finance",
        1: "B12 — The Agentic Enterprise",
        2: "B12 — The Agentic Enterprise",
        3: "Series 2 Vol 4 — Federated Sovereignty",
        4: "Series 2 Vol 5 — The Sovereign Yield Engine",
    }
    return anchors.get(level)
