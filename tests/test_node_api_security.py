"""Node API security gates — audit 2026-06-13 Phase B (every_gate_earns_a_test).

Covers the seam findings that let the hardened HTTP boundary leak:
  1. CSRF — a cross-site browser write cannot ride the token-less loopback-owner shortcut.
  2. CORS — Access-Control-Allow-Origin is echoed ONLY for a node-local allowlisted Origin (no '*').
  3. Bell — the executor spawn carries the AUTHENTICATED principal (no hardcoded 'node').
  4. Dev mode — refuses to start bound to a non-loopback host (self-assigned principals stay loopback).
"""
import os

import pytest


@pytest.fixture
def owner_client(tmp_path, monkeypatch):
    """Loopback-trust owner (the owner)."""
    monkeypatch.delenv("BREATHLINE_NODE_API_DEV", raising=False)
    monkeypatch.setenv("BREATHLINE_NODE_LOOPBACK_OWNER", "the owner")
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
    from sovereign_agent.node_api import deps
    deps.reset_node()
    from sovereign_agent.node_api.server import create_app
    yield create_app().test_client()
    deps.reset_node()


@pytest.fixture
def no_spawn(monkeypatch):
    calls = []

    class _FakePopen:
        def __init__(self, args, *a, **k):
            calls.append({"args": list(args), "env": k.get("env", {})})

    import subprocess
    monkeypatch.setattr(subprocess, "Popen", _FakePopen)
    return calls


# ── 1. CSRF ───────────────────────────────────────────────────────────────────────────────────────
def test_cross_site_browser_post_is_csrf_blocked(owner_client, no_spawn):
    """The documented drive-by: a page the operator visits POSTs to /apply. Sec-Fetch-Site=cross-site
    (un-spoofable by JS) → the loopback shortcut refuses → 403, no ignition."""
    r = owner_client.post("/api/v1/proposals/prop_x/apply", json={},
                          headers={"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403 and r.get_json()["error"] == "csrf_blocked"
    assert no_spawn == []


def test_same_origin_browser_write_passes_auth(owner_client, no_spawn):
    """The operator's own cockpit (same-origin) is NOT blocked — it reaches the handler (404 here proves
    it got past the CSRF/owner gate to the decision-existence check)."""
    r = owner_client.post("/api/v1/proposals/prop_nope/apply", json={},
                          headers={"Sec-Fetch-Site": "same-origin"})
    assert r.status_code == 404


def test_non_browser_client_unaffected(owner_client, no_spawn):
    """A CLI/agent caller sends no Sec-Fetch-* → the loopback shortcut still works → 404 (not 403)."""
    r = owner_client.post("/api/v1/proposals/prop_nope/apply", json={})
    assert r.status_code == 404


def test_safe_cross_site_get_not_blocked(owner_client):
    """A cross-site GET is not a state-changing write — must not be blocked."""
    r = owner_client.get("/api/v1/proposals", headers={"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 200


def test_dns_rebinding_host_is_refused(owner_client):
    """audit 2026-06-13d #2: a non-loopback Host header (DNS-rebinding) cannot use the loopback-owner
    shortcut, even with loopback remote_addr + same-origin Sec-Fetch-Site."""
    r = owner_client.post("/api/v1/proposals/prop_x/apply", json={},
                          headers={"Host": "evil.example", "Sec-Fetch-Site": "same-origin"})
    assert r.status_code == 403 and r.get_json()["error"] == "forbidden_host"


def test_loopback_host_still_passes(owner_client):
    """A genuine loopback Host (the test client default) still reaches the handler (404 = past auth)."""
    r = owner_client.post("/api/v1/proposals/prop_nope/apply", json={},
                          headers={"Host": "127.0.0.1:8421"})
    assert r.status_code == 404


# ── 2. CORS ─────────────────────────────────────────────────────────────────────────────────────--
def test_cors_echoes_only_allowlisted_origin(owner_client):
    r = owner_client.get("/api/v1/proposals", headers={"Origin": "http://127.0.0.1:8421"})
    assert r.headers.get("Access-Control-Allow-Origin") == "http://127.0.0.1:8421"


def test_cors_no_wildcard_and_no_header_for_foreign_origin(owner_client):
    r = owner_client.get("/api/v1/proposals", headers={"Origin": "https://evil.example"})
    acao = r.headers.get("Access-Control-Allow-Origin")
    assert acao != "*"
    assert acao is None      # a non-allowlisted origin gets no ACAO at all


# ── 3. Bell principal propagation ──────────────────────────────────────────────────────────────────
def test_bell_carries_authenticated_principal(owner_client, no_spawn):
    """Accept ignites the bell — the spawn env must name the Accept-clicker, not a hardcoded 'node'."""
    oid = owner_client.post("/api/v1/feedback", json={
        "text": "judge this", "category": "judgment"}).get_json()["obligation"]["id"]
    r = owner_client.post(f"/api/v1/feedback/{oid}/disposition", json={"action": "accept"})
    assert r.status_code == 200 and r.get_json()["executor"] == "spawned"
    assert len(no_spawn) == 1
    assert no_spawn[0]["env"].get("BREATHLINE_BELL_PRINCIPAL") == "the owner"


def test_bell_disposition_rejects_non_owner(dev_client):
    """Accept ignites code execution + chain mutation — must be owner-only (night-watch HIGH)."""
    r = dev_client.post("/api/v1/feedback/obl_x/disposition", json={"action": "accept"})
    assert r.status_code == 403 and r.get_json()["error"] == "forbidden"


def test_bell_spawn_failure_does_not_break_the_gate(owner_client, monkeypatch):
    """'The bell must never break the human gate' — a spawn exception is swallowed+logged, disposition 200."""
    import subprocess

    def _boom(*a, **k):
        raise OSError("simulated spawn failure")

    monkeypatch.setattr(subprocess, "Popen", _boom)
    oid = owner_client.post("/api/v1/feedback", json={
        "text": "judge this", "category": "judgment"}).get_json()["obligation"]["id"]
    r = owner_client.post(f"/api/v1/feedback/{oid}/disposition", json={"action": "accept"})
    assert r.status_code == 200 and r.get_json()["action"] == "accept"


# ── 4. Dev-mode host guard ─────────────────────────────────────────────────────────────────────────
def test_dev_mode_refuses_non_loopback_host(monkeypatch):
    import sovereign_agent.node_api.server as srv
    monkeypatch.setattr(srv.sys, "argv", ["breathline-node-api", "--dev", "--host", "0.0.0.0"])
    try:
        with pytest.raises(SystemExit) as ei:
            srv.cli_serve()
        assert ei.value.code == 2
    finally:
        os.environ.pop("BREATHLINE_NODE_API_DEV", None)


def test_group_world_readable_cred_file_is_refused(tmp_path, monkeypatch):
    """audit 2026-06-13d #18: a 0644 credential file silently authenticates anyone who can read it.
    _verify_token_against_file must refuse loudly (mode in the message, chmod-600 next_step) instead of
    trusting 'the OS enforces it'. A 0600 file with the same secret verifies normally."""
    import sovereign_agent.node_api.auth as auth
    monkeypatch.setattr(auth, "CREDENTIALS_DIR", tmp_path)
    cred = tmp_path / "owner.token"
    cred.write_text("s3cr3t", encoding="utf-8")

    cred.chmod(0o644)                                   # group/world-readable
    ok, pid, reason = auth._verify_token_against_file("owner:s3cr3t")
    assert ok is False and pid is None
    assert "group/world-accessible" in reason and "chmod 600" in reason

    cred.chmod(0o600)                                   # operator-only
    ok, pid, _ = auth._verify_token_against_file("owner:s3cr3t")
    assert ok is True and pid == "owner"
