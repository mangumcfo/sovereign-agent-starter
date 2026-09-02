"""Fingerprint enforcement at /api/open (KM-NO1 GO ATTACH 2026-09-02 15:09Z).

SOL's enumerated cases:
  - match           -> open
  - mismatch        -> refuse, _BINDING unchanged
  - expected set + missing identity -> refuse
  - request cannot override the expected fp (it is process-owned, never browser-supplied)
Plus the enforcement-presence flag on /api/vocab reports THAT enforcement is configured, never the value.
"""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "usn_erp_surface"))
import server as surface  # noqa: E402
from sovereign_agent.keystore.node_keystore import generate_node_key  # noqa: E402


@pytest.fixture
def surface_env(tmp_path, monkeypatch):
    """A hermetic keystore with one generated key, the surface pointed at it, _BINDING reset.
    USN_EXPECTED_FINGERPRINT is cleared by default; each test sets it as its case requires."""
    ks = tmp_path / "keystore"
    ks.mkdir()
    node = generate_node_key(str(ks), "UniversalSovereignNode", at="2026-09-02T00:00:00Z")
    monkeypatch.setenv("NODE_KEYSTORE_DIR", str(ks))
    monkeypatch.setenv("SUBSTRATE_STORAGE_ROOT", str(tmp_path / "substrate"))
    monkeypatch.delenv("USN_EXPECTED_FINGERPRINT", raising=False)
    surface._BINDING = None
    client = surface.app.test_client()
    yield client, node.fingerprint, str(ks)
    surface._BINDING = None


def _open(client, **body):
    return client.post("/api/open", json=body)


def test_match_opens(surface_env, monkeypatch):
    client, fp, _ = surface_env
    monkeypatch.setenv("USN_EXPECTED_FINGERPRINT", fp)
    r = _open(client)                         # blank body -> env keystore
    assert r.status_code == 200, r.get_json()
    assert fp in json.dumps(r.get_json())     # the matched identity is what opened
    assert surface._BINDING is not None       # committed only after the match


def test_mismatch_refuses_and_binding_unchanged(surface_env, monkeypatch):
    client, fp, _ = surface_env
    monkeypatch.setenv("USN_EXPECTED_FINGERPRINT", "deadbeefdead")   # wrong iron
    r = _open(client)
    assert r.status_code == 403, r.get_json()
    assert r.get_json().get("refused") is True
    assert surface._BINDING is None           # the whole point: nothing was bound
    assert client.get("/api/status").status_code == 409   # and nothing is open


def test_expected_set_missing_identity_refuses(surface_env, monkeypatch, tmp_path):
    client, fp, _ = surface_env
    empty = tmp_path / "empty_ks"
    empty.mkdir()
    monkeypatch.setenv("USN_EXPECTED_FINGERPRINT", fp)
    r = _open(client, keystore_dir=str(empty))   # a real dir, but no key in it
    assert r.status_code == 403, r.get_json()
    assert surface._BINDING is None


def test_request_cannot_override_expected(surface_env, monkeypatch, tmp_path):
    """The expected fp comes from the process env only. A request that points at a DIFFERENT
    (wrong-fp) keystore and also tries to smuggle its own expected value is still refused."""
    client, fp, _ = surface_env
    other = tmp_path / "other_ks"
    other.mkdir()
    other_node = generate_node_key(str(other), "Other", at="2026-09-02T00:00:00Z")
    assert other_node.fingerprint != fp
    monkeypatch.setenv("USN_EXPECTED_FINGERPRINT", fp)      # process expects the FIRST key
    r = _open(client, keystore_dir=str(other),
              expected_fingerprint=other_node.fingerprint,      # body override attempt (a)
              USN_EXPECTED_FINGERPRINT=other_node.fingerprint)  # body override attempt (b)
    assert r.status_code == 403, r.get_json()    # env wins; body cannot relax enforcement
    assert surface._BINDING is None


def test_presence_flag_reports_without_leaking_value(surface_env, monkeypatch):
    client, fp, _ = surface_env
    assert client.get("/api/vocab").get_json()["expected_fp_configured"] is False
    monkeypatch.setenv("USN_EXPECTED_FINGERPRINT", fp)
    v = client.get("/api/vocab").get_json()
    assert v["expected_fp_configured"] is True
    assert fp not in json.dumps(v)               # presence only, never the value
