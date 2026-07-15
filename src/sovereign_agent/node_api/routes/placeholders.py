"""
Contract sections B, D, E, F — real thin handlers (Track E1, 2026-05-30).

These wrap the existing Python core with pure translation (no business logic),
the same posture as sections A + C. Where the underlying primitive is genuinely
still a simulation (federation mesh) or has no shipped artifact (signed
manifest.yaml), the handler returns an **honestly-shaped** response with a
`note` field — never a silent fake (TRUTH, Constitution §0).

Sections:
    B. /manifest, /specs, /specs/{spec_id}, POST /specs/validate
    D. /invocations/{id}, /breath_gate/pending,
       POST /breath_gate/{id}/approve, POST /breath_gate/{id}/deny
    E. /audit/cylinders, /audit/cylinders/{seq}, /inference/receipts
    F. /federation/peers, /federation/shards, /federation/propagation

Reuses: PlaybookLoader.discover_roles/load_role/load_constitution,
ComplianceEngine.get_audit_trail/run_policy_compliance_check, the process
HumanApprovalGate singleton, UniversalSovereignNode federation registry.

Embodies (SERIES_1_PRINCIPLES): Principle 3 (Receipts/Audit-Immutability —
audit trail + receipts), Principle 2 (Breath/Witness — breath-gate dispose),
Principle 7 (Thin-Waist — pure translation), and TRUTH (honest stubs, never
silent fakes).
"""

from __future__ import annotations


from flask import Blueprint, jsonify, request

from ..auth import current_principal, require_owner, require_principal
from ..deps import get_approval_gate, get_node
from ..errors import build_error, kernel_exception


bp = Blueprint("sections_bdef", __name__, url_prefix="/api/v1")


# ============================================================================
# Section B — Manifest & Specs
# ============================================================================

@bp.get("/manifest")
@require_principal
def manifest_get():
    """
    manifest.get — the sovereign-agent-starter does not ship a signed
    `manifest.yaml`; we return an honest node-derived manifest with a note,
    rather than fabricating a signed artifact.
    """
    node = get_node()
    try:
        status = node.get_status()
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500
    return jsonify({
        "node_id": status.get("identity_public", "unknown"),
        "name": status.get("name"),
        "manifest_version": status.get("merkle_mode", "unknown"),
        "kernel_version": "0.3.0",
        "governance_mode": status.get("context"),
        "loaded_playbooks": status.get("loaded_playbooks", []),
        "seal_glyph": "∞Δ∞",
        "note": "Derived from node identity. The starter ships no signed "
                "manifest.yaml; a signed manifest is generated at install in a "
                "full federation deployment.",
    })


@bp.get("/specs")
@require_principal
def specs_list():
    """specs.list — discoverable role/constitution specs via PlaybookLoader."""
    node = get_node()
    try:
        roles = node.playbook_loader.discover_roles()
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500
    items = [{"spec_id": r, "kind": "role"} for r in roles]
    return jsonify({"specs": items, "count": len(items)})


@bp.get("/specs/<spec_id>")
@require_principal
def specs_get(spec_id: str):
    """specs.get — return one spec's content + source via PlaybookLoader."""
    node = get_node()
    try:
        discoverable = node.playbook_loader.discover_roles()
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500
    if spec_id not in discoverable:
        return jsonify(build_error(
            code="SPEC_NOT_FOUND",
            what=f"Spec '{spec_id}' is not registered on this node.",
            why="PlaybookLoader.discover_roles() does not list this spec_id.",
            next_step="GET /api/v1/specs to list discoverable specs.",
        )), 404
    try:
        module = node.playbook_loader.load_role(spec_id, node)
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500
    return jsonify({
        "spec_id": spec_id,
        "kind": "role",
        "source": module.get("source"),
        "source_path": module.get("source_path"),
        "module_root": module.get("module_root"),
        "module_hash": module.get("module_hash"),
        "envelope": module.get("envelope", {}),
        "content": module.get("content", {}),
    })


@bp.post("/specs/validate")
@require_principal
def specs_validate():
    """
    specs.validate — structural validation of a candidate YAML spec.
    Deep Charter V.7 policy validation requires a loaded policy context; this
    pass confirms the YAML parses and carries the expected role-spec fields,
    and notes the limit honestly.
    """
    body = request.get_json(silent=True) or {}
    raw = body.get("yaml")
    if not raw:
        return jsonify(build_error(
            code="VALIDATE_MISSING_YAML",
            what="No `yaml` field in request body.",
            why="specs.validate validates a candidate YAML spec supplied in the body.",
            next_step='POST {"yaml": "<spec yaml>", "declared_parent": "<id|null>"}.',
        )), 400

    import yaml  # noqa: PLC0415 — lazy (audit 2026-06-13): keep the module's yaml-optional discipline
    issues = []
    parsed = None
    try:
        parsed = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        issues.append({"rule": "yaml_parse", "severity": "critical", "message": str(exc)})

    if parsed is not None and isinstance(parsed, dict):
        if "role" not in parsed and "allowed_action_classes" not in parsed:
            issues.append({
                "rule": "role_spec_shape",
                "severity": "warning",
                "message": "Spec has neither a 'role' block nor 'allowed_action_classes'; "
                           "may not be a role spec.",
            })
    elif parsed is not None:
        issues.append({"rule": "root_type", "severity": "critical",
                       "message": "Top-level YAML is not a mapping."})

    import hashlib
    sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    valid = not any(i["severity"] == "critical" for i in issues)
    return jsonify({
        "valid": valid,
        "issues": issues,
        "sha256": sha,
        "note": "Structural validation only. Deep Charter V.7 policy validation "
                "runs against a loaded policy context via "
                "ComplianceEngine.run_policy_compliance_check at ingestion.",
    })


# ============================================================================
# Section D — Invocations & Breath-Gates
# ============================================================================

@bp.get("/invocations/<invocation_id>")
@require_principal
def invocations_get(invocation_id: str):
    """invocations.get — find an attested invocation by request_id / receipt_hash in the audit trail."""
    node = get_node()
    try:
        trail = node.compliance_engine.get_audit_trail(limit=500)
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500
    for rec in trail:
        meta = getattr(rec, "metadata", {}) or {}
        if invocation_id in (meta.get("request_id"), getattr(rec, "receipt_hash", None)):
            return jsonify({"invocation_id": invocation_id, "record": rec})
    return jsonify(build_error(
        code="INVOCATION_NOT_FOUND",
        what=f"No attested invocation matches '{invocation_id}'.",
        why="No audit record carries this request_id or receipt_hash.",
        next_step="GET /api/v1/audit/cylinders to list attested actions.",
    )), 404


@bp.get("/breath_gate/pending")
@require_principal
def breath_gate_pending():
    """breath_gate.pending — pending human-approval requests (session-scoped store)."""
    gate = get_approval_gate()
    pending = gate.get_pending()
    items = [{"req_id": rid, "request": req, "status": "pending"} for rid, req in pending.items()]
    return jsonify({
        "pending": items,
        "count": len(items),
        "note": "Session-scoped breath-gate store. Empty until a "
                "corporate_regulated action triggers requires_approval. The "
                "empty state is the honest truth, not a stub.",
    })


@bp.post("/breath_gate/<gate_id>/approve")
@require_principal
@require_owner
def breath_gate_approve(gate_id: str):
    """breath_gate.{id}/approve — explicit human approval (the witness act).
    Owner-gated (audit 2026-06-13c #6): a breath-gate disposition is a constitutional human act and must
    carry the same authority as the sibling disposition routes (obligations/feedback/proposals).

    CROSS-REF (audit 2026-06-13c #29): this is the SESSION-SCOPED in-memory HumanApprovalGate surface.
    The LIVE constitutional gate for material *obligations* is POST /obligations/<id>/approve (ledger-
    backed). Use that for obligation dispositions; this surface is the compliance-engine breath-gate."""
    gate = get_approval_gate()
    # Truth-in-naming (audit 2026-06-16 #4b): the LIVE route records a REAL disposition by the
    # authenticated principal — not a simulation. simulate_* stay genuinely test-only.
    result = gate.record_disposition(gate_id, status="approved", approver=current_principal())
    if result.get("status") == "unknown_request":
        return jsonify(build_error(
            code="GATE_NOT_FOUND",
            what=f"No pending breath-gate '{gate_id}'.",
            why="The id is not in the pending-approvals store.",
            next_step="GET /api/v1/breath_gate/pending to list pending gates.",
        )), 404
    return jsonify(result)


@bp.post("/breath_gate/<gate_id>/deny")
@require_principal
@require_owner
def breath_gate_deny(gate_id: str):
    """breath_gate.{id}/deny — explicit human denial (the refusal is the constitutional act).
    Owner-gated (audit 2026-06-13c #6): the refusal is a constitutional human act, owner-only."""
    body = request.get_json(silent=True) or {}
    gate = get_approval_gate()
    # Truth-in-naming (audit 2026-06-16 #4b): real disposition, not a simulation.
    result = gate.record_disposition(gate_id, status="denied", approver=current_principal(),
                                     reason=body.get("reason", ""))
    if result.get("status") == "unknown_request":
        return jsonify(build_error(
            code="GATE_NOT_FOUND",
            what=f"No pending breath-gate '{gate_id}'.",
            why="The id is not in the pending-approvals store.",
            next_step="GET /api/v1/breath_gate/pending to list pending gates.",
        )), 404
    return jsonify(result)


# ============================================================================
# Section E — Audit Chain & Receipts
# ============================================================================

@bp.get("/audit/cylinders")
@require_principal
def audit_cylinders_list():
    """audit.cylinders — the node's attested audit trail (Merkle-chained AuditRecords)."""
    node = get_node()
    try:
        limit = int(request.args.get("limit", "50"))
    except ValueError:
        limit = 50
    try:
        trail = node.compliance_engine.get_audit_trail(limit=limit)
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500
    cylinders = [{"seq": i, "record": rec} for i, rec in enumerate(trail)]
    return jsonify({"cylinders": cylinders, "count": len(cylinders)})


@bp.get("/audit/cylinders/<int:seq>")
@require_principal
def audit_cylinders_get(seq: int):
    """audit.cylinders.{seq} — one record by index into the audit trail."""
    node = get_node()
    try:
        trail = node.compliance_engine.get_audit_trail(limit=10000)
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500
    if seq < 0 or seq >= len(trail):
        return jsonify(build_error(
            code="CYLINDER_NOT_FOUND",
            what=f"No audit cylinder at seq {seq}.",
            why=f"The audit trail has {len(trail)} record(s).",
            next_step="GET /api/v1/audit/cylinders to list available seqs.",
        )), 404
    return jsonify({"seq": seq, "record": trail[seq]})


@bp.get("/inference/receipts")
@require_principal
def inference_receipts():
    """inference.receipts — the receipt view (6-key summary) projected from the audit trail."""
    node = get_node()
    try:
        limit = int(request.args.get("limit", "50"))
    except ValueError:
        limit = 50
    try:
        trail = node.compliance_engine.get_audit_trail(limit=limit)
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500
    receipts = [{
        "action_class": getattr(r, "action_class", None),
        "risk_level": getattr(r, "risk_level", None),
        "receipt_hash": getattr(r, "receipt_hash", None),
        "prev_receipt_hash": getattr(r, "prev_receipt_hash", None),
        "timestamp": getattr(r, "timestamp", None),
        "compliance_block": getattr(r, "compliance_block", {}),
    } for r in trail]
    return jsonify({"receipts": receipts, "count": len(receipts)})


# ============================================================================
# Section E+ — Evidence Bundle & Invariants (contract_v1.1 EXTENSION, Track E2)
# Not in the sealed 21-route contract_v1.yaml — flagged for the operator/spec ratification.
# ============================================================================

@bp.get("/audit/evidence-bundle")
@require_principal
def audit_evidence_bundle():
    """
    [contract_v1.1 extension] Export a portable SOX-style evidence bundle —
    full audit chain + node identity + policies + bundle self-attestation.
    Wraps ComplianceEngine.export_evidence_bundle (already exists).
    """
    node = get_node()
    case_id = request.args.get("case_id")
    try:
        bundle = node.compliance_engine.export_evidence_bundle(case_id=case_id)
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500
    bundle["_contract_note"] = ("contract_v1.1 extension (not in sealed v1.0 21-route "
                                "contract); flagged for the operator/spec ratification.")
    return jsonify(bundle)


@bp.get("/invariants/status")
@require_principal
def invariants_status():
    """
    [contract_v1.1 extension] K1–K4 constitutional invariants — the structural
    definitions (always true of a sovereign node) + the latest walkthrough
    receipt from memory/ if the operator has run examples/k_invariant_walkthrough.py.
    """
    invariants = [
        {"id": "K1", "name": "Human Primacy",
         "claim": "Interpretive decisions require a documented human authorization; "
                  "the runtime refuses to act on them otherwise."},
        {"id": "K2", "name": "Default-Deny",
         "claim": "Ambiguous or undeclared authorization defaults to denial; "
                  "no constitutional act seals without explicit operator breath."},
        {"id": "K3", "name": "Audit-Immutable (Receipted-Evidence)",
         "claim": "Every constitutional act produces an audit-chainable receipt "
                  "linked via prev_receipt_hash; no act seals without a receipt."},
        {"id": "K4", "name": "Constitutional-Validated Extension",
         "claim": "Amendments to the constitutional surface pass Charter V.7 review; "
                  "GREEN auto-flow cannot weaken K1–K4."},
    ]
    # Honest: surface the live walkthrough receipt if present; else say so.
    walkthrough = None
    note = ("Run examples/k_invariant_walkthrough.py to produce a live "
            "memory/KInvariantWalk-01_k_invariant_receipt.json proving all four "
            "invariants held on your node.")
    try:
        import json as _json
        from pathlib import Path
        for cand in Path("memory").glob("*k_invariant*receipt*.json"):
            walkthrough = _json.loads(cand.read_text(encoding="utf-8"))
            note = f"Live walkthrough receipt loaded from {cand}."
            break
    except Exception:  # noqa: BLE001 — receipt is optional; never fail the status call
        pass
    return jsonify({
        "invariants": invariants,
        "invariants_total": 4,
        "latest_walkthrough": walkthrough,
        "note": note,
        "_contract_note": "contract_v1.1 extension; flagged for the operator/spec ratification.",
    })


# ============================================================================
# Section F — Federation
# ============================================================================

@bp.get("/federation/peers")
@require_principal
def federation_peers():
    """federation.peers — locally known peer nodes (in-memory registry)."""
    node = get_node()
    try:
        names = type(node).list_known_nodes()
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500
    peers = [{"node_name": n, "reachable": True, "source": "local_registry"} for n in names]
    return jsonify({
        "peers": peers,
        "count": len(peers),
        "note": "Local in-memory node registry (development/simulation). The "
                "production peer-to-peer mesh is deferred to SIX federation "
                "(see Series 2 Vol 4). Empty is the honest state on a single node.",
    })


@bp.get("/federation/shards")
@require_principal
def federation_shards():
    """federation.shards — honest stub (real receipted-shard mesh deferred to SIX / Vol 4)."""
    return jsonify({
        "shards": [],
        "count": 0,
        "note": "Receipted-shard propagation is light-simulation in the current "
                "starter; the real mesh (RSPP) is deferred to SIX federation "
                "(Series 2 Vol 4). This is an honest empty shape, not a stub fake.",
    })


@bp.get("/federation/propagation")
@require_principal
def federation_propagation():
    """federation.propagation — honest stub (real propagation deferred to SIX / Vol 4)."""
    return jsonify({
        "propagation": [],
        "count": 0,
        "note": "Cross-node propagation events are deferred to SIX federation "
                "(Series 2 Vol 4). This is an honest empty shape, not a stub fake.",
    })
