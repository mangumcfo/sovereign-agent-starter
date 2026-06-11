"""Node API /proposals + code-executing route gates (every_gate_earns_a_test, audit 2026-06-11).

proposals.py carries the gates the audit asked be EARNED by a test:
  1. require_owner — /produce, /apply, /recompile execute code or mutate the operator's machine and
     must reject dev/anonymous + non-owner principals (403), allow only the node owner.
  2. principal-binding — produced_by / decided_by are the AUTHENTICATED principal, never the body.
  3. input validation — /produce strict obligation_id shape before any subprocess (no injection).
  4. error voice — missing groups → 400, unknown proposal → 404 (loud + contextual, §4).
"""
import pytest


@pytest.fixture
def owner_client(tmp_path, monkeypatch):
    """Loopback-trust owner (KM-1176) — passes require_owner."""
    monkeypatch.delenv("BREATHLINE_NODE_API_DEV", raising=False)
    monkeypatch.setenv("BREATHLINE_NODE_LOOPBACK_OWNER", "KM-1176")
    monkeypatch.setenv("OBLIGATION_LEDGER_ROOT", str(tmp_path / "obligations"))
    monkeypatch.setenv("PROPOSALS_STORE", str(tmp_path / "proposals.json"))
    from sovereign_agent.node_api import deps
    deps.reset_node()
    from sovereign_agent.node_api.server import create_app
    yield create_app().test_client()
    deps.reset_node()


@pytest.fixture
def dev_client(tmp_path, monkeypatch):
    """Dev/anonymous — authenticates (require_principal) but is NOT the node owner."""
    monkeypatch.setenv("BREATHLINE_NODE_API_DEV", "1")
    monkeypatch.delenv("BREATHLINE_NODE_LOOPBACK_OWNER", raising=False)
    monkeypatch.delenv("BREATHLINE_NODE_OWNER", raising=False)
    monkeypatch.setenv("OBLIGATION_LEDGER_ROOT", str(tmp_path / "obligations"))
    monkeypatch.setenv("PROPOSALS_STORE", str(tmp_path / "proposals.json"))
    from sovereign_agent.node_api import deps
    deps.reset_node()
    from sovereign_agent.node_api.server import create_app
    yield create_app().test_client()
    deps.reset_node()


# ── require_owner: code-executing routes reject non-owners, allow the owner ──────────────────────
@pytest.mark.parametrize("path,payload", [
    ("/api/v1/produce", {"obligation_id": "obl_20260611_abcd"}),
    ("/api/v1/proposals/prop_1/apply", {}),
    ("/api/v1/recompile", {"book": "Book 12"}),
])
def test_code_routes_reject_dev_anonymous(dev_client, path, payload):
    r = dev_client.post(path, json=payload)
    assert r.status_code == 403          # authenticated but not the owner → forbidden
    assert r.get_json()["error"] == "forbidden"


def test_owner_passes_require_owner_then_validates_input(owner_client):
    # Owner clears require_owner and REACHES the handler, which rejects a malformed id BEFORE subprocess.
    r = owner_client.post("/api/v1/produce", json={"obligation_id": "not-a-real-id"})
    assert r.status_code == 400 and r.get_json()["error"] == "bad_obligation_id"
    # missing id is also a loud 400 (not a 403 — proves the owner got past the gate)
    r2 = owner_client.post("/api/v1/produce", json={})
    assert r2.status_code == 400 and r2.get_json()["error"] == "missing_obligation_id"


# ── /proposals: principal-binding + error voice ──────────────────────────────────────────────────
def test_create_binds_produced_by_to_principal(owner_client):
    r = owner_client.post("/api/v1/proposals", json={
        "session_ref": "sess_x", "groups": [{"id": "g1", "diff": "..."}],
        "produced_by": "attacker",   # must be IGNORED
    })
    assert r.status_code == 201
    prop = r.get_json()
    assert prop["produced_by"] == "KM-1176"      # bound to current_principal, not the body
    assert prop["status"] == "proposed"


def test_create_missing_groups_is_400(owner_client):
    r = owner_client.post("/api/v1/proposals", json={"session_ref": "sess_x"})
    assert r.status_code == 400 and r.get_json()["error"] == "missing_groups"


def test_info_card_allowed_without_groups(owner_client):
    r = owner_client.post("/api/v1/proposals", json={"info": True, "note": "no diff; observation only"})
    assert r.status_code == 201 and r.get_json()["info"] is True


def test_decide_binds_decided_by_and_404_on_unknown(owner_client):
    pid = owner_client.post("/api/v1/proposals", json={
        "session_ref": "s", "groups": [{"id": "g1"}]}).get_json()["id"]
    r = owner_client.post(f"/api/v1/proposals/{pid}/decide", json={"decisions": {"g1": "accept"}})
    assert r.status_code == 200
    assert r.get_json()["decided_by"] == "KM-1176" and r.get_json()["status"] == "decided"
    r404 = owner_client.post("/api/v1/proposals/prop_nope/decide", json={"decisions": {}})
    assert r404.status_code == 404 and r404.get_json()["error"] == "not_found"


def test_list_returns_created_proposals(owner_client):
    owner_client.post("/api/v1/proposals", json={"session_ref": "s", "groups": [{"id": "g1"}]})
    r = owner_client.get("/api/v1/proposals")
    assert r.status_code == 200 and len(r.get_json()["proposals"]) >= 1
