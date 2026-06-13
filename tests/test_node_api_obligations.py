"""R-23 Phase 3 — Node API /obligations endpoints (Flask test client)."""
import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    # loopback OWNER (audit 2026-06-13 W5 #1: approve/close are now owner-gated) + node-local ledger root
    # in a tmp dir (never the live seal chain).
    monkeypatch.delenv("BREATHLINE_NODE_API_DEV", raising=False)
    monkeypatch.setenv("BREATHLINE_NODE_LOOPBACK_OWNER", "KM-1176")
    monkeypatch.setenv("OBLIGATION_LEDGER_ROOT", str(tmp_path / "obligations"))
    from sovereign_agent.node_api import deps
    deps.reset_node()
    from sovereign_agent.node_api.server import create_app
    yield create_app().test_client()
    deps.reset_node()


@pytest.fixture
def dev_client(tmp_path, monkeypatch):
    """Dev/anonymous — authenticates but is NOT the node owner."""
    monkeypatch.setenv("BREATHLINE_NODE_API_DEV", "1")
    monkeypatch.delenv("BREATHLINE_NODE_LOOPBACK_OWNER", raising=False)
    monkeypatch.delenv("BREATHLINE_NODE_OWNER", raising=False)
    monkeypatch.setenv("OBLIGATION_LEDGER_ROOT", str(tmp_path / "obligations"))
    from sovereign_agent.node_api import deps
    deps.reset_node()
    from sovereign_agent.node_api.server import create_app
    yield create_app().test_client()
    deps.reset_node()


def test_close_unknown_obligation_carries_canonical_error_shape(client):
    """audit 2026-06-13d #9: a 404 from /close routes through route_error — code mirrors the friendly
    slug, plus why + next_step + cylinder_ref (Error Voice §4), not a bare ad-hoc dict."""
    r = client.post("/api/v1/obligations/obl_does_not_exist/close",
                    json={"evidence": "/x hash a1b2c3d4e5f60718"})
    assert r.status_code == 404
    b = r.get_json()
    assert b["error"] == "obligation_not_found" and b["code"] == "obligation_not_found"
    assert b["why"] and b["next_step"] and "cylinder_ref" in b


def test_approve_and_close_reject_non_owner(dev_client):
    """W5 #1: approve/close dispose KM's chain — a non-owner (dev) principal is forbidden (403)."""
    oid = dev_client.post("/api/v1/obligations", json={"title": "x"}).get_json()["id"]
    assert dev_client.post(f"/api/v1/obligations/{oid}/approve", json={}).status_code == 403
    assert dev_client.post(f"/api/v1/obligations/{oid}/close",
                           json={"evidence": "/x hash a1b2c3d4e5f60718"}).status_code == 403


def test_open_unresolvable_path_ref_is_422_not_500(client):
    """audit 2026-06-13 W5 #7: a path-like ref that doesn't resolve returns a contextual 422, not 500."""
    r = client.post("/api/v1/obligations",
                    json={"title": "x", "ref": "artifacts/does_not_exist_xyz_qqq.md"})
    assert r.status_code == 422 and r.get_json()["error"] == "unresolvable_ref"


def test_open_compound_feed_ref_succeeds(client):
    """A real GB compound feed ref ('<resolving-path> + B51 delta + THREAD[..]') opens cleanly — the
    ' + …' provenance tail is symbolic; only the leading file token is the claim (W5 #6)."""
    r = client.post("/api/v1/obligations", json={
        "title": "hopper packet",
        "ref": "scripts/gen_outline_digest.py + B51 delta + THREAD[67]"})
    assert r.status_code == 201, r.get_json()


def test_open_symbolic_ref_succeeds(client):
    r = client.post("/api/v1/obligations", json={"title": "veto", "ref": "B11:veto-chapter"})
    assert r.status_code == 201


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
