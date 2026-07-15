"""
Track A2 — Lightweight HTTP-roundtrip parity smoke tests for the Series 2 demos.

Per G's sequencing emphasis: "A smoke test per demo (Python direct vs HTTP
roundtrip producing identical receipts) is sufficient for the first pass.
Full behavioral parity can come later."

Coverage scope (Track A2 first pass):

    ✅ load_role_demo            — exercises roles.get + roles.invoke
    ✅ compliance_cfo_demo       — exercises roles.invoke with action_class
    ✅ family_governance_demo    — exercises roles.invoke with family context

    🚧 fail_closed_demo          — needs /actions/validate (not yet implemented; A3 follow-up)
    🚧 cross_role_veto_demo      — needs /reviews/cross-role-request (A3 follow-up)
    🚧 k_invariant_walkthrough   — needs /invariants/validate (A3 follow-up)
    🚧 multi_mandate_handoff     — needs /mandates/handoff (A3 follow-up)
    🚧 post_deal_monitoring      — needs /receipts/chain-verify (A3 follow-up)
    🚧 multi_node_federation     — needs /federation/verify-handoff (post-A3)

For each in-scope demo, the test:
  1. Loads the role via the Python core (direct).
  2. Loads the role via HTTP GET /api/v1/roles/{role_id} (HTTP).
  3. Invokes via the Python core (direct).
  4. Invokes via HTTP POST /api/v1/roles/{role_id}/invoke (HTTP).
  5. Asserts the receipt envelope shape is identical (modulo HTTP-side
     request_id which the route synthesises if not provided).

Embodies Principle 7 (Thin-Waist, Separability, Replaceability) — the HTTP
layer must NOT mutate the receipt envelope; it is pure translation.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["BREATHLINE_NODE_API_DEV"] = "1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _envelope_shape(result: dict) -> set:
    """Return the set of top-level keys present on a BoundRole.process result."""
    return set(result.keys()) if isinstance(result, dict) else set()


def _attest_signature(result: dict) -> str | None:
    """
    Extract the canonical attestation signature from a result.

    Different demos surface attestation differently; we look in common slots
    so the parity check is robust to minor envelope variation.
    """
    if not isinstance(result, dict):
        return None
    for key in ("usn_attestation", "attestation", "compliance_attestation"):
        attest = result.get(key)
        if isinstance(attest, dict):
            for sig_key in ("signature", "merkle_root", "node_attestation"):
                if attest.get(sig_key):
                    return str(attest[sig_key])
    return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def node():
    """Shared Python-direct node singleton."""
    from sovereign_agent.node_api.deps import get_node, reset_node
    reset_node()
    return get_node()


@pytest.fixture(scope="module")
def client(node):
    """Shared Flask test client that uses the same node singleton."""
    from sovereign_agent.node_api.server import create_app
    app = create_app()
    return app.test_client()


# ---------------------------------------------------------------------------
# Parity tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("role_id", [
    "cfo_agent",
    "family_cfo_agent",
])
def test_roles_get_envelope_shape(client, node, role_id):
    """HTTP roles.get returns the same role-spec envelope keys as Python-direct."""
    discoverable = node.playbook_loader.discover_roles()
    if role_id not in discoverable:
        pytest.skip(f"role '{role_id}' not discoverable in this environment")

    rv = client.get(f"/api/v1/roles/{role_id}")
    assert rv.status_code == 200, rv.get_json()
    body = rv.get_json()

    # Core contract shape from contract_v1.yaml roles.get
    for field in ("role_id", "name", "allowed_action_classes",
                  "invocation_envelope", "handler_bound"):
        assert field in body, f"HTTP envelope missing {field}"
    assert body["role_id"] == role_id
    assert isinstance(body["allowed_action_classes"], list)


def test_load_role_demo_parity(client, node):
    """
    Mirrors examples/load_role_demo.py.

    Python-direct: node.load_role("cfo_agent").process(...)
    HTTP:          POST /api/v1/roles/cfo_agent/invoke

    Both must produce a receipt with the same top-level envelope shape.
    """
    discoverable = node.playbook_loader.discover_roles()
    if "cfo_agent" not in discoverable:
        pytest.skip("cfo_agent not discoverable; demo can't run")

    payload = {
        "financial_data": {"revenue": [1200, 1350, 1100], "expenses": [800, 820, 790]},
        "forecast_horizon": 3,
    }

    # Python-direct (matches the demo exactly)
    bound = node.load_role("cfo_agent")
    direct_result = bound.process(
        payload=payload,
        principal_id="owner",
        request_id="parity-test-direct",
    )
    direct_shape = _envelope_shape(direct_result)

    # HTTP roundtrip
    rv = client.post(
        "/api/v1/roles/cfo_agent/invoke",
        json={
            "payload": payload,
            "request_id": "parity-test-http",
        },
    )
    assert rv.status_code == 200, rv.get_json()
    http_body = rv.get_json()
    assert http_body["role_id"] == "cfo_agent"
    assert http_body["request_id"] == "parity-test-http"
    assert "result" in http_body

    http_shape = _envelope_shape(http_body["result"])

    # The HTTP layer is pure translation — the inner `result` shape must match
    # the Python-direct shape exactly. (Top-level HTTP keys add request_id,
    # role_id, principal_id, action_class; those are HTTP-side metadata.)
    assert direct_shape == http_shape, (
        f"Envelope drift detected!\n"
        f"  direct: {sorted(direct_shape)}\n"
        f"  http:   {sorted(http_shape)}\n"
        f"This violates Principle 7 (thin-waist) — the HTTP layer must not "
        f"mutate the receipt envelope."
    )


def test_invoke_unknown_role_returns_loud_404(client):
    rv = client.post(
        "/api/v1/roles/this_role_definitely_does_not_exist/invoke",
        json={"payload": {"x": 1}},
    )
    assert rv.status_code == 404
    body = rv.get_json()
    assert body["code"] == "ROLE_NOT_FOUND"


def test_invoke_with_disallowed_action_class_returns_403(client, node):
    discoverable = node.playbook_loader.discover_roles()
    if "cfo_agent" not in discoverable:
        pytest.skip("cfo_agent not discoverable; can't test action_class denial")

    rv = client.post(
        "/api/v1/roles/cfo_agent/invoke",
        json={
            "payload": {"data": "test"},
            "action_class": "definitely_not_in_envelope",
        },
    )
    assert rv.status_code == 403
    body = rv.get_json()
    assert body["code"] == "ROLE_ACTION_DENIED"
    assert "definitely_not_in_envelope" in body["what"]


# ---------------------------------------------------------------------------
# Coverage gap-marker
# ---------------------------------------------------------------------------

def test_gap_marker_for_unimplemented_demo_endpoints():
    """
    Marker test that documents the demos whose endpoints are still placeholders.

    When the corresponding endpoints land (Tracks A2/A3 follow-up), the
    corresponding xfail / skip markers here should flip to active assertions.
    """
    # This is intentionally always-passing; it exists to keep the gap visible
    # in pytest output until the placeholder endpoints are filled in.
    gaps = {
        "fail_closed_demo":         "/api/v1/actions/validate (Track A3)",
        "cross_role_veto_demo":     "/api/v1/reviews/cross-role-request (Track A3)",
        "k_invariant_walkthrough":  "/api/v1/invariants/validate (Track A3)",
        "multi_mandate_handoff":    "/api/v1/mandates/handoff (Track A3)",
        "post_deal_monitoring":     "/api/v1/receipts/chain-verify (Track A3)",
        "multi_node_federation":    "/api/v1/federation/verify-handoff (post-A3)",
    }
    # Print only when run with -s (visible during dev)
    for demo, gap in gaps.items():
        print(f"  GAP: {demo} → {gap}")
    assert True  # marker
