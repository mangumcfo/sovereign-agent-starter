"""R-23 Phase 3 — Node API /obligations endpoints (Flask test client)."""
import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    # dev auth + node-local ledger root in a tmp dir (never the live seal chain)
    monkeypatch.setenv("BREATHLINE_NODE_API_DEV", "1")
    monkeypatch.setenv("OBLIGATION_LEDGER_ROOT", str(tmp_path / "obligations"))
    from sovereign_agent.node_api import deps
    deps.reset_node()
    from sovereign_agent.node_api.server import create_app
    yield create_app().test_client()
    deps.reset_node()


def test_open_list_approve_close(client):
    # open
    r = client.post("/api/v1/obligations", json={"title": "Wire Phase 4 Atrium lens"})
    assert r.status_code == 201
    ob = r.get_json()
    assert ob["type"] == "debit" and ob["draft"] is True
    oid = ob["id"]

    # list shows it open
    r = client.get("/api/v1/obligations")
    assert r.status_code == 200
    body = r.get_json()
    assert any(o["id"] == oid for o in body["open"])
    assert body["status"]["open"] >= 1 and body["chain_ok"] is True

    # approve, then close with E2 evidence
    assert client.post(f"/api/v1/obligations/{oid}/approve", json={}).status_code == 200
    r = client.post(f"/api/v1/obligations/{oid}/close",
                    json={"evidence": "/repo/atrium/index.html hash a1b2c3d4e5f60718"})
    assert r.status_code == 200
    credit = r.get_json()
    assert credit["type"] == "credit"
    assert credit["receipt"]["evidence_tier"] == "E2"
    assert credit["receipt"].get("node_receipt_hash")  # a node receipt was minted


def test_e0_evidence_rejected(client):
    oid = client.post("/api/v1/obligations", json={"title": "x"}).get_json()["id"]
    r = client.post(f"/api/v1/obligations/{oid}/close", json={"evidence": "done"})
    assert r.status_code == 422
    assert r.get_json()["error"] == "insufficient_evidence"


def test_material_requires_approval(client):
    oid = client.post("/api/v1/obligations",
                      json={"title": "Promote ledger", "material": True}).get_json()["id"]
    # close before approval -> 409
    r = client.post(f"/api/v1/obligations/{oid}/close",
                    json={"evidence": "/x hash a1b2c3d4e5f60718"})
    assert r.status_code == 409 and r.get_json()["error"] == "approval_required"
    # approve, then close -> 200
    assert client.post(f"/api/v1/obligations/{oid}/approve", json={}).status_code == 200
    assert client.post(f"/api/v1/obligations/{oid}/close",
                       json={"evidence": "/x hash a1b2c3d4e5f60718"}).status_code == 200


def test_validation_errors(client):
    assert client.post("/api/v1/obligations", json={}).status_code == 400          # no title
    oid = client.post("/api/v1/obligations", json={"title": "y"}).get_json()["id"]
    assert client.post(f"/api/v1/obligations/{oid}/close", json={}).status_code == 400  # no evidence
