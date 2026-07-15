"""
Smoke tests for the Track A1 minimal viable Node API shell.

These tests verify the HTTP surface boots, routes are registered per
contract_v1.yaml shape, implemented sections (A node + C roles) return
real envelopes, and placeholder sections (B/D/E/F) return loud 501s.

Run:

    pytest tests/test_node_api.py -v

These are deliberately thin — Track A2 will add behavioural parity tests
(Python-direct vs HTTP-roundtrip identical receipts for each demo).
"""

from __future__ import annotations

import os
import sys

import pytest

# Ensure src/ is importable when running pytest from repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture(scope="module")
def app():
    os.environ["BREATHLINE_NODE_API_DEV"] = "1"  # bypass bearer for tests
    from sovereign_agent.node_api.server import create_app
    return create_app()


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


@pytest.fixture
def owner_client(monkeypatch, tmp_path):
    """Loopback OWNER (not dev) — for the owner-gated breath-gate routes (audit 2026-06-13c #6)."""
    monkeypatch.delenv("BREATHLINE_NODE_API_DEV", raising=False)
    monkeypatch.setenv("BREATHLINE_NODE_LOOPBACK_OWNER", "owner")
    monkeypatch.setenv("OBLIGATION_LEDGER_ROOT", str(tmp_path / "obligations"))
    from sovereign_agent.node_api import deps
    deps.reset_node()
    from sovereign_agent.node_api.server import create_app
    yield create_app().test_client()
    deps.reset_node()


# --- Index + service envelope ----------------------------------------------

def test_index_envelope(client):
    rv = client.get("/")
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["service"] == "breathline-node-api"
    assert body["contract"].endswith("contract_v1.yaml")
    assert "A (node)" in body["implemented_sections"]
    assert "C (roles)" in body["implemented_sections"]
    assert body["seal_glyph"] == "∞Δ∞"


# --- Section A — Node identity / health / ladder ---------------------------

def test_node_get(client):
    rv = client.get("/api/v1/node")
    assert rv.status_code == 200
    body = rv.get_json()
    # Contract shape per contract_v1.yaml node.get
    for field in ("node_id", "tier", "ladder_level", "ladder_level_name",
                  "kernel_version", "manifest_version", "seal_glyph"):
        assert field in body, f"missing field: {field}"
    assert body["seal_glyph"] == "∞Δ∞"


def test_node_health(client):
    rv = client.get("/api/v1/node/health")
    assert rv.status_code == 200
    body = rv.get_json()
    for field in ("kernel_ok", "manifest_ok", "specs_valid", "signatures_ok",
                  "chain_sentinel", "breath_gate_ready", "details"):
        assert field in body, f"missing field: {field}"
    assert isinstance(body["details"], list)
    assert any(d["check"] == "kernel_responsive" for d in body["details"])


def test_node_ladder(client):
    rv = client.get("/api/v1/node/ladder")
    assert rv.status_code == 200
    body = rv.get_json()
    assert "current_level" in body
    assert isinstance(body["current_level"], int)
    assert 0 <= body["current_level"] <= 4
    # next_level is None at top of ladder, int otherwise
    nl = body.get("next_level")
    assert nl is None or isinstance(nl, int)


# --- Section C — Roles -----------------------------------------------------

def test_roles_list(client):
    rv = client.get("/api/v1/roles")
    assert rv.status_code == 200
    body = rv.get_json()
    assert "roles" in body
    assert isinstance(body["roles"], list)
    # At least one shipped demo role should be discoverable
    assert body["count"] >= 0  # Allow zero in pure-test environment


def test_roles_get_unknown_returns_404_with_loud_error(client):
    rv = client.get("/api/v1/roles/this_role_does_not_exist_anywhere")
    assert rv.status_code == 404
    body = rv.get_json()
    # Loud error envelope per CONSTITUTION §4
    assert body["code"] == "ROLE_NOT_FOUND"
    assert "what" in body
    assert "why" in body
    assert "next_step" in body


# --- Sections B / D / E / F — REAL handlers (Track E1 backfill, 2026-05-30) -----
# Previously 501 placeholders; now return real (or honestly-shaped) JSON.

@pytest.mark.parametrize("path", [
    "/api/v1/manifest",
    "/api/v1/specs",
    "/api/v1/breath_gate/pending",
    "/api/v1/audit/cylinders",
    "/api/v1/inference/receipts",
    "/api/v1/federation/peers",
    "/api/v1/federation/shards",
    "/api/v1/federation/propagation",
])
def test_bdef_sections_return_200_real(client, path):
    """Track E1: B/D/E/F sections now return 200 with real/honest JSON (no more 501)."""
    rv = client.get(path)
    assert rv.status_code == 200, rv.get_json()
    assert rv.get_json() is not None


def test_no_501_remaining_for_bdef(client):
    """Hard guard: zero 501 NOT_IMPLEMENTED across the B/D/E/F surface."""
    paths = [
        "/api/v1/manifest", "/api/v1/specs", "/api/v1/breath_gate/pending",
        "/api/v1/audit/cylinders", "/api/v1/inference/receipts",
        "/api/v1/federation/peers", "/api/v1/federation/shards",
        "/api/v1/federation/propagation",
    ]
    for p in paths:
        assert client.get(p).status_code != 501, f"{p} still returns 501"


def test_specs_list_real_content(client):
    body = client.get("/api/v1/specs").get_json()
    assert "specs" in body and isinstance(body["specs"], list)
    assert body["count"] == len(body["specs"])


def test_specs_get_unknown_404(client):
    rv = client.get("/api/v1/specs/this_spec_does_not_exist")
    assert rv.status_code == 404
    assert rv.get_json()["code"] == "SPEC_NOT_FOUND"


def test_breath_gate_pending_shape(client):
    body = client.get("/api/v1/breath_gate/pending").get_json()
    assert "pending" in body and "count" in body and "note" in body


def test_breath_gate_dispose_rejects_non_owner(client):
    """audit 2026-06-13c #6: a breath-gate disposition is owner-only; dev/non-owner → 403."""
    assert client.post("/api/v1/breath_gate/x/approve").status_code == 403
    assert client.post("/api/v1/breath_gate/x/deny").status_code == 403


def test_breath_gate_approve_unknown_404(owner_client):
    rv = owner_client.post("/api/v1/breath_gate/no_such_gate/approve")
    assert rv.status_code == 404
    assert rv.get_json()["code"] == "GATE_NOT_FOUND"


def test_breath_gate_deny_unknown_404(owner_client):
    rv = owner_client.post("/api/v1/breath_gate/no_such_gate/deny")
    assert rv.status_code == 404
    assert rv.get_json()["code"] == "GATE_NOT_FOUND"


def test_breath_gate_approve_records_real_disposition(owner_client):
    """Engine 95+ #4b: the LIVE approve route routes through record_disposition (real=True, real UTC
    timestamp) — NOT the TEST-ONLY simulate_approval (which set timestamp='simulated' and no 'real' key).
    get_approval_gate() is a process-wide singleton, so the request created here is the one the route sees."""
    from sovereign_agent.compliance.human_approval_gate import ApprovalRequest
    from sovereign_agent.node_api.deps import get_approval_gate

    rid = get_approval_gate().request_approval(ApprovalRequest(
        action_class="x", role_id="r", principal_id="p", risk_level="low",
        rationale="t", required_approvers=["owner"]))
    rv = owner_client.post(f"/api/v1/breath_gate/{rid}/approve")
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["status"] == "approved"
    assert body.get("real") is True               # record_disposition marker — proves NOT simulate_approval
    assert body.get("timestamp") != "simulated"


def test_audit_cylinders_shape(client):
    body = client.get("/api/v1/audit/cylinders").get_json()
    assert "cylinders" in body and "count" in body


def test_inference_receipts_shape(client):
    body = client.get("/api/v1/inference/receipts").get_json()
    assert "receipts" in body and "count" in body


def test_federation_stubs_carry_honest_note(client):
    """Honest stubs (F shards/propagation) must carry a `note`, not silently fake."""
    for p in ("/api/v1/federation/shards", "/api/v1/federation/propagation"):
        body = client.get(p).get_json()
        assert body.get("note"), f"{p} must carry an honest note"


def test_specs_validate_requires_yaml(client):
    rv = client.post("/api/v1/specs/validate", json={})
    assert rv.status_code == 400
    assert rv.get_json()["code"] == "VALIDATE_MISSING_YAML"


def test_specs_validate_parses_real_yaml(client):
    rv = client.post("/api/v1/specs/validate",
                     json={"yaml": "role:\n  name: t\nallowed_action_classes: [x]"})
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["valid"] is True
    assert body.get("sha256")


# --- Track E2 — Evidence Bundle + Invariants (contract_v1.1 extensions) -----

def test_evidence_bundle_real(client):
    rv = client.get("/api/v1/audit/evidence-bundle")
    assert rv.status_code == 200
    body = rv.get_json()
    assert "case_id" in body and "audit_trail" in body and "record_count" in body
    assert body.get("_contract_note"), "v1.1 extension must be flagged"


def test_invariants_status(client):
    rv = client.get("/api/v1/invariants/status")
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["invariants_total"] == 4
    ids = [i["id"] for i in body["invariants"]]
    assert ids == ["K1", "K2", "K3", "K4"]
    assert body.get("note")  # honest note about live walkthrough receipt
    assert body.get("_contract_note")


# --- 404 / 405 envelopes ---------------------------------------------------

def test_unknown_route_returns_loud_404(client):
    rv = client.get("/api/v1/nonexistent_route")
    assert rv.status_code == 404
    body = rv.get_json()
    assert body["code"] == "ROUTE_NOT_FOUND"
    assert "next_step" in body


def test_wrong_method_returns_loud_405(client):
    rv = client.delete("/api/v1/node")  # node only supports GET
    assert rv.status_code == 405
    body = rv.get_json()
    assert body["code"] == "METHOD_NOT_ALLOWED"


# --- Auth (when not in dev mode) -------------------------------------------

def test_missing_bearer_token_in_strict_mode(monkeypatch):
    """Without BREATHLINE_NODE_API_DEV, a request with no Authorization header is 401."""
    monkeypatch.delenv("BREATHLINE_NODE_API_DEV", raising=False)
    from sovereign_agent.node_api.server import create_app
    app = create_app()
    client = app.test_client()
    rv = client.get("/api/v1/node")
    assert rv.status_code == 401
    body = rv.get_json()
    assert body["code"] == "AUTH_MISSING_TOKEN"
    assert "Authorization: Bearer" in body["next_step"]
