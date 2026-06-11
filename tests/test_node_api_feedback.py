"""Node API /feedback + /awaiting_km + disposition gates (every_gate_earns_a_test, audit 2026-06-11).

The Atrium loop-closure intake (feedback.py) carries three constitutional gates the audit asked be
EARNED by a test, not asserted by a docstring:
  1. principal-binding — owner is the AUTHENTICATED principal, never the request body (no spoofing).
  2. error voice — not-found → 404, already-closed → 409, bad action → 400 (loud + contextual, §4).
  3. the Awaiting-KM projection only lists obligations gated on the human and not yet disposed.
Storage is a node-local ledger in a tmp dir (never the live seal chain).
"""
import pytest


@pytest.fixture
def owner_client(tmp_path, monkeypatch):
    """Loopback-trust owner (KM-1176) — a real authenticated principal, not dev/anonymous."""
    monkeypatch.delenv("BREATHLINE_NODE_API_DEV", raising=False)
    monkeypatch.setenv("BREATHLINE_NODE_LOOPBACK_OWNER", "KM-1176")
    monkeypatch.setenv("OBLIGATION_LEDGER_ROOT", str(tmp_path / "obligations"))
    from sovereign_agent.node_api import deps
    deps.reset_node()
    from sovereign_agent.node_api.server import create_app
    yield create_app().test_client()
    deps.reset_node()


def _mint(client, text="Tighten the ch3 cross-foot", **extra):
    body = {"text": text, "type": "viewer", "book": "B12", "chapter": 3, **extra}
    r = client.post("/api/v1/feedback", json=body)
    return r


def test_feedback_binds_owner_to_authenticated_principal(owner_client):
    # Even if the body tries to set owner, the ledger records the AUTHENTICATED principal (no spoofing).
    r = _mint(owner_client, owner="attacker", produced_by="attacker")
    assert r.status_code == 201
    ob = r.get_json()["obligation"]
    assert ob["owner"] == "KM-1176"           # bound to current_principal, NOT the request body
    assert ob["ref"] == "viewer:B12 ch3"      # resolving source ref built from the typed fields
    assert ob["next_gate"] == "Human disposition"


def test_feedback_missing_text_is_loud_400(owner_client):
    r = owner_client.post("/api/v1/feedback", json={"type": "general"})
    assert r.status_code == 400
    body = r.get_json()
    assert body["error"] == "missing_text"
    assert "next_step" in body and "what" in body   # error voice: what + next step (§4)


def test_awaiting_km_lists_then_drops_on_accept(owner_client):
    oid = _mint(owner_client).get_json()["obligation"]["id"]
    # projection lists it while it awaits the human
    aw = owner_client.get("/api/v1/awaiting_km").get_json()
    assert aw["meta"]["gate"] == "Human disposition" and aw["meta"]["chain_ok"] is True
    assert any(i["id"] == oid and i["owner"] == "KM-1176" for i in aw["awaiting"])
    # accept = approve → it clears the gate and leaves the Awaiting-KM view
    r = owner_client.post(f"/api/v1/feedback/{oid}/disposition", json={"action": "accept"})
    assert r.status_code == 200 and r.get_json()["action"] == "accept"
    aw2 = owner_client.get("/api/v1/awaiting_km").get_json()
    assert all(i["id"] != oid for i in aw2["awaiting"])


def test_reject_closes_and_double_reject_is_409(owner_client):
    oid = _mint(owner_client).get_json()["obligation"]["id"]
    r = owner_client.post(f"/api/v1/feedback/{oid}/disposition",
                          json={"action": "reject", "note": "out of scope"})
    assert r.status_code == 200 and r.get_json()["action"] == "reject"
    # already disposed → loud 409, not a silent re-close
    r2 = owner_client.post(f"/api/v1/feedback/{oid}/disposition", json={"action": "reject"})
    assert r2.status_code == 409 and r2.get_json()["error"] == "already_closed"


def test_disposition_not_found_is_404(owner_client):
    r = owner_client.post("/api/v1/feedback/obl_does_not_exist/disposition", json={"action": "accept"})
    assert r.status_code == 404 and r.get_json()["error"] == "obligation_not_found"


def test_disposition_bad_action_is_400(owner_client):
    oid = _mint(owner_client).get_json()["obligation"]["id"]
    r = owner_client.post(f"/api/v1/feedback/{oid}/disposition", json={"action": "maybe"})
    assert r.status_code == 400 and r.get_json()["error"] == "bad_action"
