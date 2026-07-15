"""
Section C — Roles.

Per contract_v1.yaml:

    GET  /roles                    → roles.list
    GET  /roles/{role_id}          → roles.get
    POST /roles/{role_id}/invoke   → roles.invoke

Wraps PlaybookLoader.discover_roles + UniversalSovereignNode.load_role +
BoundRole.process. No business logic added; the HTTP layer only translates
JSON ↔ Python and re-emits the existing receipt envelope.
"""

from __future__ import annotations

import uuid
from typing import Any

from flask import Blueprint, jsonify, request

from ..auth import current_principal, require_principal
from ..deps import get_node
from ..errors import kernel_exception, role_action_denied, unknown_role


bp = Blueprint("roles", __name__, url_prefix="/api/v1")


@bp.get("/roles")
@require_principal
def roles_list():
    """roles.list — enumerate discoverable role specs."""
    node = get_node()
    try:
        discoverable = node.playbook_loader.discover_roles()
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500

    items = []
    for role_id in discoverable:
        items.append({
            "role_id": role_id,
            "loaded": role_id in node.loaded_roles,
            # Lazy details — full spec returned only on GET /roles/{role_id}
        })
    return jsonify({"roles": items, "count": len(items)})


@bp.get("/roles/<role_id>")
@require_principal
def roles_get(role_id: str):
    """roles.get — return a single role's spec envelope."""
    node = get_node()

    # Default-deny: only load roles the loader can discover. PlaybookLoader
    # returns a placeholder for unknown role_keys; we want a loud 404 instead.
    try:
        discoverable = node.playbook_loader.discover_roles()
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500

    if role_id not in discoverable:
        return jsonify(unknown_role(role_id)), 404

    try:
        bound = node.load_role(role_id)
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500

    spec = getattr(bound, "spec", {}) or {}
    if not isinstance(spec, dict):
        spec = {}

    # The role spec schema varies between sources:
    #   - Federation pattern: top-level `role:` is a string (the role_id);
    #     other fields (name/framework/etc.) live as siblings of `role:`.
    #   - Demo pattern:       top-level `role:` is a dict (with id/name/etc.).
    # Normalise both so the HTTP envelope is consistent.
    role_field = spec.get("role")
    if isinstance(role_field, dict):
        role_block = role_field
    else:
        role_block = {}

    def _coalesce(*candidates):
        for c in candidates:
            if c not in (None, "", {}, []):
                return c
        return None

    return jsonify({
        "role_id": role_id,
        "name": _coalesce(role_block.get("name"), spec.get("name"), role_id),
        "description": _coalesce(role_block.get("description"), spec.get("description")),
        "framework": _coalesce(role_block.get("framework"), spec.get("framework")),
        "mandate": _coalesce(role_block.get("mandate"), spec.get("mandate")),
        "identity_key_fingerprint": _coalesce(
            role_block.get("identity_key_fingerprint"),
            spec.get("identity_key_fingerprint"),
        ),
        "allowed_action_classes": bound.get_allowed_action_classes(),
        "invocation_envelope": spec.get("invocation_envelope", {}),
        "handler_bound": bound.handler is not None if hasattr(bound, "handler") else False,
        # Surface the source spec schema flavour so consumers know which
        # shape they're looking at (helps Atrium render variant role-spec forms).
        "spec_schema": "demo" if isinstance(role_field, dict) else "federation",
    })


@bp.post("/roles/<role_id>/invoke")
@require_principal
def roles_invoke(role_id: str):
    """
    roles.invoke — execute a role action through the existing BoundRole.process
    path. The receipt envelope (`usn_attestation` + `compliance_attestation` +
    signature + memory_root) is returned unchanged.
    """
    node = get_node()
    body: dict[str, Any] = request.get_json(silent=True) or {}
    payload = body.get("payload", {})
    action_class = body.get("action_class")
    request_id = body.get("request_id") or f"req_{uuid.uuid4().hex[:12]}"

    # Default-deny: discoverable roles only (PlaybookLoader otherwise returns
    # placeholder modules for unknown role_keys).
    try:
        discoverable = node.playbook_loader.discover_roles()
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500

    if role_id not in discoverable:
        return jsonify(unknown_role(role_id)), 404

    try:
        bound = node.load_role(role_id)
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500

    # Default-deny K2: if action_class missing and the role allows none,
    # surface the structural reason rather than guessing.
    allowed = bound.get_allowed_action_classes()
    if action_class is None and allowed:
        # Use the role's hint logic for a sensible suggestion
        action_class = bound.suggest_action_class(body.get("hint", "")) or allowed[0]

    if action_class is not None and action_class not in allowed:
        return jsonify(role_action_denied(
            role_id,
            action_class,
            f"action_class not in role's allowed envelope {allowed}",
        )), 403

    try:
        result = bound.process(
            payload=payload,
            principal_id=current_principal(),
            request_id=request_id,
            action_class=action_class,
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500

    # The BoundRole already emits the canonical receipt envelope. Wrap with
    # the HTTP-side request_id for traceability; do not mutate the receipt.
    return jsonify({
        "request_id": request_id,
        "role_id": role_id,
        "action_class": action_class,
        "principal_id": current_principal(),
        "result": result,
    })
