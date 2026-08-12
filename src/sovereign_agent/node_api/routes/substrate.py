"""Substrate thin routes — gate-enqueue, storage, and Port, as PURE TRANSLATION over existing kernel verbs.

KM GO (Substrate Thin Routes for Node Home e2e, 2026-08-12). Option B posture, same as `placeholders.py`:
these handlers wrap kernel primitives with no business logic, no new governance engine, and no second authority.

Why this file exists: at the base pin, `HumanApprovalGate.request_approval` was only ever called *in-process*
(onboard / obligations), so nothing over HTTP could put an item in `/breath_gate/pending` — Node Home's Gate Inbox
had nothing to show. These routes close that: they call the SAME process `HumanApprovalGate` singleton the existing
`/breath_gate/*` routes read and dispose. There is one gate authority, not two.

Boundaries (enforced here, not promised):
  * thin translation only — every route wraps an existing kernel verb (`request_approval`, `store_datum`,
    `retrieve_datum`, `open_crossing`, `sanction_crossing`);
  * NEVER `simulate_approval` / `simulate_denial` over HTTP — dispositions are the real `record_disposition`
    behind the existing owner-gated `/breath_gate/<id>/approve|deny` routes;
  * no key material in any response; no custody of bytes (storage keeps the integrity root, not the file);
  * the Port receipt carries no value field (money-path OFF — `sanction_crossing` returns the receipt, never value);
  * the gate store is **process-local** (the API process's `HumanApprovalGate`) — a gate enqueued here is visible
    to the SAME process's `/breath_gate/pending`, not to a separate CLI process. Stated in every response `note`.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict

from flask import Blueprint, jsonify, request

from ..auth import current_principal, require_owner, require_principal
from ..deps import get_approval_gate, get_node
from ..errors import build_error, kernel_exception

from ...compliance.human_approval_gate import ApprovalRequest
from ...objects.registry import ObjectRegistry
from ...objects.scope import SharingRule
from ...storage.sovereign_store import store_datum, retrieve_datum, StorageError
from ...port.crossing import open_crossing, sanction_crossing, CrossingError
from ...onboarding.onboard import run_onboard, verify_onboard_receipt, OnboardReceipt
from ...peerhood.recognition import refuse_recognition
from ...peerhood.clean_exit import clean_exit
from ...keystore.node_keystore import has_node_key


bp = Blueprint("substrate", __name__, url_prefix="/api/v1")

# The default set of acts a fresh operator chooses to gate (onboard turn 3). Kept in sync with the kernel's
# onboarding.DEFAULT_GATED_ACTS by import, so this route never invents an action class the kernel doesn't know.
from ...onboarding.onboard import DEFAULT_GATED_ACTS  # noqa: E402

_PROCESS_NOTE = ("Process-local gate store: this item lives in THIS API process's HumanApprovalGate and is "
                 "visible to GET /api/v1/breath_gate/pending in the same process. A separate CLI process has "
                 "its own store.")

# ── process-local object registry for the storage + Port surfaces (the kernel primitive, one per process) ──
_REG: ObjectRegistry | None = None
_DATUM: Dict[str, dict] = {}     # object_id -> governed datum object (metadata only; NEVER the raw bytes)
_CROSSING: Dict[str, dict] = {}  # crossing object_id -> {crossing, gate_req_id, boundary_mandate}
# provenance side-map (NOT on the sealed ApprovalRequest dataclass): req_id -> {source, boundary}. Lets the
# breath-gate inbox serializer tell an HTTP-raised gate from a kernel-raised one, and surface a Port boundary.
_GATE_META: Dict[str, dict] = {}


def gate_meta() -> Dict[str, dict]:
    """Provenance for gates this process raised over HTTP (read by the /breath_gate/pending serializer)."""
    return dict(_GATE_META)


def _reg() -> ObjectRegistry:
    global _REG
    if _REG is None:
        root = os.environ.get("SUBSTRATE_STORAGE_ROOT",
                              os.path.join(os.getcwd(), ".substrate_storage"))
        _REG = ObjectRegistry(root)
    return _REG


def reset_substrate() -> None:
    """Drop the process-local substrate singletons (tests)."""
    global _REG, _DATUM, _CROSSING, _GATE_META
    _REG = None
    _DATUM = {}
    _CROSSING = {}
    _GATE_META = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_chunks(body) -> list[bytes] | None:
    """Accept {chunks: [str|str]} or {content: str}; return a list of bytes, or None if empty/absent."""
    if isinstance(body.get("chunks"), list) and body["chunks"]:
        return [c.encode("utf-8") if isinstance(c, str) else bytes(c) for c in body["chunks"]]
    if isinstance(body.get("content"), str) and body["content"]:
        return [body["content"].encode("utf-8")]
    return None


# ============================================================================
# Priority 1 — the gate-enqueue path (make /breath_gate/pending fillable over HTTP)
# ============================================================================

@bp.post("/onboard/run")
@require_principal
def onboard_run():
    """onboard.run — enqueue the ceremony's first GATED act into the process breath-gate.

    Pure translation: builds an ApprovalRequest and calls the process HumanApprovalGate's `request_approval`
    (the SAME singleton the /breath_gate/* routes read). After this call, GET /breath_gate/pending returns >=1
    item that Node Home can approve/deny via the existing owner-gated routes (which call the real
    record_disposition — never simulate_*). No key is minted or exported here; the node already boots on its
    durable self-held key. The disposition is the operator's, at the existing gate routes."""
    body = request.get_json(silent=True) or {}
    action_class = body.get("action_class") or (DEFAULT_GATED_ACTS[0] if DEFAULT_GATED_ACTS else "send_value")
    # fail-loud: only a real gated-act class may be proposed — never an invented action class
    if action_class not in DEFAULT_GATED_ACTS:
        return jsonify(build_error(
            code="UNKNOWN_ACTION_CLASS",
            what=f"action_class '{action_class}' is not a gated act.",
            why="onboard.run only enqueues one of the node's declared gated acts (DEFAULT_GATED_ACTS).",
            next_step=f"Use one of: {', '.join(DEFAULT_GATED_ACTS)}.",
        )), 400
    principal = current_principal()
    req = ApprovalRequest(
        action_class=str(action_class),
        role_id=str(body.get("role_id", "onboard")),
        principal_id=principal,
        risk_level=str(body.get("risk_level", "high")),
        rationale=str(body.get("rationale", "Onboard ceremony: the operator's first gated act (turn 4).")),
        required_approvers=[principal],
    )
    gate = get_approval_gate()
    req_id = gate.request_approval(req)
    _GATE_META[req_id] = {"source": "http:onboard.run", "boundary": None, "action_class": req.action_class}
    return jsonify({
        "status": "pending_gate",
        "req_id": req_id,
        "action_class": req.action_class,
        "pending_url": "/api/v1/breath_gate/pending",
        "approve_url": f"/api/v1/breath_gate/{req_id}/approve",
        "deny_url": f"/api/v1/breath_gate/{req_id}/deny",
        "note": "A gated act is now pending. Approve or deny it from Node Home (the Gate Inbox). " + _PROCESS_NOTE,
    }), 201


@bp.get("/onboard/status")
@require_principal
def onboard_status():
    """onboard.status — report the process breath-gate state for the ceremony.

    Honest limit: the compliance breath-gate does not persist disposed receipts (record_disposition returns the
    receipt to the approver at /approve time). So status reports PENDING vs NOT-PENDING for a given ?req_id, plus
    the pending count. A disposed req_id simply no longer appears."""
    gate = get_approval_gate()
    pending = gate.get_pending()
    req_id = request.args.get("req_id")
    out = {
        "pending_count": len(pending),
        "pending_ids": list(pending.keys()),
        "note": "The disposition receipt is returned to the approver at /breath_gate/<id>/approve|deny time; "
                "this surface reports pending vs disposed only. " + _PROCESS_NOTE,
    }
    if req_id is not None:
        out["req_id"] = req_id
        out["state"] = "pending" if req_id in pending else "disposed_or_unknown"
    return jsonify(out)


# ============================================================================
# Priority 2 / A5 — storage thin routes (store_datum / retrieve_datum, integrity unchanged)
# ============================================================================

@bp.post("/storage/datum")
@require_principal
def storage_store():
    """storage.datum.store — wrap store_datum. Stores the datum as the owner's governed object carrying its
    Merkle integrity root; the node keeps the ROOT, never the raw bytes (no custody). Returns object_id + root
    + visibility. No key material."""
    body = request.get_json(silent=True) or {}
    chunks = _as_chunks(body)
    if chunks is None:
        return jsonify(build_error(
            code="STORAGE_MISSING_CONTENT",
            what="No `chunks` (list) or `content` (string) in the request body.",
            why="store_datum needs the datum's content to compute its integrity root.",
            next_step='POST {"chunks": ["...", "..."], "visibility": "private"} or {"content": "..."}.',
        )), 400
    owner = current_principal()
    visibility = str(body.get("visibility", "private"))
    mandate = str(body.get("mandate", owner))
    try:
        datum = store_datum(_reg(), owner, chunks, visibility=visibility, mandate=mandate,
                            author=owner, source_ref=f"storage://{owner}", at=_now())
    except StorageError as exc:
        return jsonify(build_error(
            code="STORAGE_REFUSED", what=str(exc),
            why="store_datum refused (empty owner/chunks or invalid visibility).",
            next_step="Provide non-empty content and visibility of 'private' or 'shared'.",
        )), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500
    _DATUM[datum["object_id"]] = datum
    payload = datum.get("payload", {})
    return jsonify({
        "object_id": datum["object_id"],
        "version_hash": datum["version_hash"],
        "visibility": payload.get("visibility"),
        "root": payload.get("root"),
        "note": "The node holds the integrity root, not your bytes (no custody). To verify/retrieve, "
                "POST /api/v1/storage/datum/<id>/verify with the presented content.",
    }), 201


@bp.get("/storage/datum/<path:datum_id>")
@require_principal
def storage_get(datum_id: str):
    """storage.datum.get — return the governed datum's metadata (object_id, visibility, root, mandate). The node
    never returns the bytes: it holds only the integrity root. Retrieval-with-integrity is the verify POST."""
    datum = _DATUM.get(datum_id)
    if datum is None:
        return jsonify(build_error(
            code="DATUM_NOT_FOUND", what=f"No datum '{datum_id}' on this node.",
            why="The id is not in the process object registry.",
            next_step="POST /api/v1/storage/datum to store one; the response carries its object_id.",
        )), 404
    payload = datum.get("payload", {})
    return jsonify({
        "object_id": datum["object_id"],
        "version_hash": datum["version_hash"],
        "visibility": payload.get("visibility"),
        "root": payload.get("root"),
        "mandate": datum.get("mandate"),
        "note": "Metadata only — the node holds the integrity root, not your bytes. "
                "POST /api/v1/storage/datum/<id>/verify with the presented content to verify + retrieve.",
    })


@bp.post("/storage/datum/<path:datum_id>/verify")
@require_principal
def storage_verify(datum_id: str):
    """storage.datum.verify — wrap retrieve_datum: deny-by-default, scoped, integrity-checked. The caller presents
    the bytes; the node verifies them against the stored Merkle root. Integrity/scope refusals are UNCHANGED."""
    datum = _DATUM.get(datum_id)
    if datum is None:
        return jsonify(build_error(
            code="DATUM_NOT_FOUND", what=f"No datum '{datum_id}' on this node.",
            why="The id is not in the process object registry.",
            next_step="POST /api/v1/storage/datum to store one first.",
        )), 404
    body = request.get_json(silent=True) or {}
    chunks = _as_chunks(body)
    if chunks is None:
        return jsonify(build_error(
            code="VERIFY_MISSING_CONTENT",
            what="No `chunks` or `content` to verify against the stored root.",
            why="retrieve_datum verifies the presented bytes against the datum's Merkle root.",
            next_step='POST {"chunks": ["...", "..."]} (the original content).',
        )), 400
    principal_mandate = str(body.get("mandate", current_principal()))
    rules = []
    # an owner may declare a read scope for another mandate, honestly translated (no wider grant invented)
    if body.get("share_to"):
        rules = [SharingRule(datum_id, str(body["share_to"]), "read")]
        principal_mandate = str(body["share_to"])
    try:
        res = retrieve_datum(_reg(), datum, rules, chunks, principal_mandate=principal_mandate)
    except StorageError as exc:
        # integrity or scope refusal — surfaced unchanged, deny-by-default
        return jsonify(build_error(
            code="RETRIEVAL_REFUSED", what=str(exc),
            why="retrieve_datum refused: undeclared scope or the presented bytes failed the integrity check.",
            next_step="Present the exact stored content, or declare a read scope via 'share_to'.",
        )), 403
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500
    return jsonify(res)


# ============================================================================
# Priority 5 — Port path (open_crossing → sanction; the pending sanction lands in the same gate inbox)
# ============================================================================

@bp.post("/port/crossing")
@require_principal
def port_open():
    """port.crossing.open — wrap open_crossing (a governed object; the instruction is a directive/reference,
    never value). Because reaching outside the sovereign boundary needs a named-human sanction, this ALSO enqueues
    a pending item into the process breath-gate so Node Home shows the crossing awaiting sanction. The breath-gate
    item is the inbox SURFACE; the constitutional authority is sanction_crossing (owner-gated route below) — one
    authority, not two."""
    body = request.get_json(silent=True) or {}
    target = body.get("target")
    instruction = body.get("instruction")
    if not target or not isinstance(instruction, dict) or not instruction:
        return jsonify(build_error(
            code="CROSSING_MISSING_FIELDS",
            what="A crossing needs a `target` (string) and a non-empty `instruction` (object).",
            why="open_crossing refuses an empty target or instruction; the instruction is a directive, never value.",
            next_step='POST {"target": "external-relay", "instruction": {"send": "ref://..."}}.',
        )), 400
    principal = current_principal()
    node_id = None
    try:
        node_id = get_node().get_status().get("name")
    except Exception:  # noqa: BLE001 — node status optional for id; fall back to principal
        pass
    node_id = node_id or principal
    boundary_mandate = str(body.get("boundary_mandate", f"external:{target}"))
    try:
        # source_ref is a COLON-symbolic ref (no path separator) so R22-3 never reads a dotted hostname
        # (example.com / api.example.test) as an unresolvable file path — it accepts symbolic refs as-is.
        crossing = open_crossing(_reg(), node_id, str(target), dict(instruction),
                                 mandate=principal, author=principal,
                                 source_ref=f"crossing:{node_id}:{target}", at=_now())
    except CrossingError as exc:
        return jsonify(build_error(
            code="CROSSING_REFUSED", what=str(exc), why="open_crossing refused.",
            next_step="Provide a non-empty target and instruction.",
        )), 400
    except ValueError as exc:
        # fail-loud structured refusal — never a generic 500 (e.g. a provenance/validation rule)
        return jsonify(build_error(
            code="CROSSING_INVALID", what=str(exc),
            why="The crossing could not be registered as a governed object.",
            next_step="Check the target/instruction; the target may be a plain hostname.",
        )), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500
    # surface a pending sanction in the same breath-gate inbox, carrying the boundary in the rationale
    gate = get_approval_gate()
    req = ApprovalRequest(action_class="boundary_crossing", role_id="port", principal_id=principal,
                          risk_level="high",
                          rationale=f"Port crossing to '{target}' (boundary {boundary_mandate}) "
                                    f"awaiting the operator's sanction.",
                          required_approvers=[principal])
    gate_req_id = gate.request_approval(req)
    _GATE_META[gate_req_id] = {"source": "http:port.crossing", "boundary": boundary_mandate,
                               "crossing_id": crossing["object_id"]}
    _CROSSING[crossing["object_id"]] = {
        "crossing": crossing, "gate_req_id": gate_req_id, "boundary_mandate": boundary_mandate,
    }
    return jsonify({
        "status": "pending_sanction",
        "crossing_id": crossing["object_id"],
        "gate_req_id": gate_req_id,
        "sanction_url": f"/api/v1/port/crossing/{crossing['object_id']}/sanction",
        "note": "The crossing is a governed object; a sanction is pending in the Gate Inbox. The owner sanctions "
                "via the sanction route (a named-human act). The Port carries a directive, never value. "
                + _PROCESS_NOTE,
    }), 201


@bp.post("/port/crossing/<path:crossing_id>/sanction")
@require_principal
@require_owner
def port_sanction(crossing_id: str):
    """port.crossing.sanction — wrap sanction_crossing (DENY-BY-DEFAULT: a node-declared boundary rule + a NAMED
    human). Owner-gated: the authenticated owner IS the named human. Returns the crossing RECEIPT — boundary,
    root, approver — and NEVER a value field (money-path OFF). Also clears the linked breath-gate inbox item via
    the real record_disposition (not a simulation)."""
    entry = _CROSSING.get(crossing_id)
    if entry is None:
        return jsonify(build_error(
            code="CROSSING_NOT_FOUND", what=f"No open crossing '{crossing_id}'.",
            why="The id is not in the process crossing registry.",
            next_step="POST /api/v1/port/crossing to open one first.",
        )), 404
    body = request.get_json(silent=True) or {}
    crossing = entry["crossing"]
    boundary_mandate = entry["boundary_mandate"]
    approver = current_principal()
    approval_ref = str(body.get("approval_ref") or f"node-home sanction {crossing_id}")
    # the node declares the boundary rule for exactly this crossing (its own consent), then a named human sanctions
    rules = [SharingRule(crossing_id, boundary_mandate, "write")]
    try:
        receipt = sanction_crossing(_reg(), crossing, rules=rules, boundary_mandate=boundary_mandate,
                                    approver=approver, approval_ref=approval_ref)
    except CrossingError as exc:
        return jsonify(build_error(
            code="SANCTION_REFUSED", what=str(exc),
            why="sanction_crossing refused (undeclared boundary or no named human).",
            next_step="Retry as the owner with an approval_ref.",
        )), 403
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500
    # clear the linked inbox item with a REAL disposition (never simulate_*)
    get_approval_gate().record_disposition(entry["gate_req_id"], status="approved", approver=approver,
                                           reason="Port crossing sanctioned by the owner.")
    _CROSSING.pop(crossing_id, None)
    _GATE_META.pop(entry["gate_req_id"], None)
    # defense-in-depth: the kernel receipt already carries no value; assert the money-path fence at the surface
    for k in ("value", "amount", "funds", "balance", "held"):
        receipt.pop(k, None)
    receipt["note"] = "Sanctioned crossing receipt — the Port records THAT it happened, never the value."
    return jsonify(receipt)


# ============================================================================
# A1 — the 5-turn onboard CEREMONY, drivable over HTTP (sandbox / UAT), no kernel import in the console
# ============================================================================

@bp.post("/onboard/ceremony")
@require_principal
def onboard_ceremony():
    """onboard.ceremony — run the real 5-turn `run_onboard` in an ISOLATED sandbox keystore (uat=True), driven by
    body dispositions, so a console can prove the two A1 properties WITHOUT importing the kernel and WITHOUT
    touching the node's durable boot key:
      * `disposition: "decline"` → declines at turn 1 → **NO key written, 0 files** (OnboardOutcome).
      * `disposition: "accept"`  → mints a sandbox key, runs turns 2–5, returns the signed receipt AND the result
        of `verify_onboard_receipt` (server-side, real — never a simulation).
    The node's DURABLE identity is provisioned once via the CLI (`keystore.generate_node_key`); the API boots
    load-only. This route is the ceremony demonstration, not the durable-key act. No private key is ever returned."""
    import tempfile  # noqa: PLC0415
    body = request.get_json(silent=True) or {}
    disposition = str(body.get("disposition", "accept")).strip().lower()
    accept = disposition.startswith("a")
    name = str(body.get("name", "ceremony-node"))
    gated = body.get("gated_acts")
    first_gate = "approved" if str(body.get("first_gate", "approve")).lower().startswith("a") else "denied"

    def _prompter(turn):
        if turn.kind == "accept":
            return accept
        if turn.kind == "name":
            return name
        if turn.kind == "edit_set":
            return list(gated) if gated else turn.payload
        if turn.kind == "gate":
            return first_gate
        return None

    with tempfile.TemporaryDirectory() as sandbox:
        try:
            result = run_onboard(sandbox, prompter=_prompter, at=_now(), node_id="ceremony-node", uat=True)
        except Exception as exc:  # noqa: BLE001
            return jsonify(kernel_exception(str(exc))), 500
        if not isinstance(result, OnboardReceipt):
            # declined at turn 1 — prove 0 files were written
            files = []
            for base, _dirs, fs in os.walk(sandbox):
                files += fs
            return jsonify({
                "status": result.status,
                "key_written": result.key_written,
                "files_written": len(files),
                "message": result.message,
                "note": "Declining costs nothing and leaves nothing behind (sandbox ceremony, uat).",
            })
        verified = bool(verify_onboard_receipt(result, sandbox))
        return jsonify({
            "status": "onboarded",
            "node_name": result.node_name,
            "fingerprint": result.fingerprint,
            "gated_acts": list(result.gated_acts),
            "first_gate": {"status": result.first_gate.get("status"), "approver": result.first_gate.get("approver")},
            "signature": result.signature,
            "verified": verified,
            "verify_instructions": result.verify_instructions,
            "note": "Sandbox UAT ceremony: the receipt verified offline against the sandbox key (no private key "
                    "returned). Your DURABLE node identity is provisioned once via the CLI; the API boots load-only.",
        }), 201


# ============================================================================
# A4 — peers: MINIMAL PRESENT (single-node-safe verbs only). mutual_recognition / messaging stay OUT (two-node).
# ============================================================================

def _node_peer_id() -> str:
    return os.environ.get("BREATHLINE_NODE_NAME", "UniversalSovereignNode")


def _keystore_dir() -> str | None:
    return os.environ.get("NODE_KEYSTORE_DIR")


@bp.post("/peers/refuse")
@require_principal
@require_owner
def peers_refuse():
    """peers.refuse — wrap refuse_recognition: THIS node refuses (or revokes) recognition of a NAMED other, a
    first-class signed act that leaves NO residual claim. Single-node-safe: it needs only this node's OWN key and
    the other's name (no second node, no pretend mutual recognition). Owner-gated (a constitutional refusal)."""
    body = request.get_json(silent=True) or {}
    other = body.get("other")
    if not other:
        return jsonify(build_error(
            code="REFUSE_MISSING_OTHER", what="No `other` to refuse.",
            why="refuse_recognition names the peer this node refuses.",
            next_step='POST {"other": "<peer-name>", "reason": "..."}.',
        )), 400
    peer_id = _node_peer_id()
    ks = _keystore_dir()
    if not has_node_key(ks, peer_id):
        return jsonify(build_error(
            code="NODE_KEY_ABSENT", what="This node has no durable self-held key.",
            why="A refusal must be signed by the node's OWN key; provision it via the CLI onboard.",
            next_step="Run keystore.generate_node_key for this node, then retry.",
        )), 409
    try:
        ref = refuse_recognition(ks, peer_id, str(other), at=_now(), registry=_reg(),
                                 reason=str(body.get("reason", "")))
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500
    return jsonify({
        "refused": str(other),
        "residual_claim": ref.get("residual_claim"),   # None — no hostage
        "hostage_free": ref.get("hostage_free"),
        "signature": ref.get("signature"),
        "note": "This node refused a named peer with its own key — no residual claim, no leverage. "
                "mutual_recognition (a two-node act) is OUT of the single-process API; see examples/p2p_messaging.",
    }), 201


@bp.post("/peers/clean_exit")
@require_principal
@require_owner
def peers_clean_exit():
    """peers.clean_exit — wrap clean_exit: THIS node severs its OWN grants (the recognitions / delegations /
    memberships it passes in), an executable act signed with its own key, walking with no residual claim.
    Single-node-safe (it acts only on this node's own records). Owner-gated."""
    body = request.get_json(silent=True) or {}
    peer_id = _node_peer_id()
    ks = _keystore_dir()
    if not has_node_key(ks, peer_id):
        return jsonify(build_error(
            code="NODE_KEY_ABSENT", what="This node has no durable self-held key.",
            why="A clean exit must be signed by the node's OWN key.",
            next_step="Provision the node key via the CLI onboard, then retry.",
        )), 409
    try:
        ex = clean_exit(ks, peer_id,
                        recognitions=list(body.get("recognitions", [])),
                        delegations=list(body.get("delegations", [])),
                        memberships=list(body.get("memberships", [])),
                        at=_now(), registry=_reg())
    except Exception as exc:  # noqa: BLE001
        return jsonify(kernel_exception(str(exc))), 500
    return jsonify({
        "peer_id": ex.peer_id,
        "grants_severed": ex.grants_severed,
        "grants_total": ex.grants_total,
        "no_residual": ex.no_residual,
        "note": "This node severed its own grants and walks with no residual claim (single-node act).",
    }), 201
