"""Tests for the USN compute-share wrapper (scripts/compute_share.py) — AA_COMPUTE_SHARE_WRAPPER_BAR W1-W12.

Composition-only: exercises the wrapper over a real ObjectRegistry + real self-held keys, a fake loopback
model_caller, and explicit clock strings. No kernel module is modified. Deny-by-default is the resting state.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("compute_share", _ROOT / "scripts" / "compute_share.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.keystore.node_keystore import generate_node_key, sign_node_act
from sovereign_agent.peerhood.delegation import delegate_governed

NODE = "Dragon"
REQ = "Beard"
FAKE_MODEL = lambda url, body: json.dumps({"ok": True, "echo": body.get("prompt", "")})  # noqa: E731


@pytest.fixture()
def env(tmp_path, monkeypatch):
    ks = tmp_path / "ks"; ks.mkdir()
    monkeypatch.setenv("NODE_KEYSTORE_DIR", str(ks))
    node_k = generate_node_key(str(ks), NODE, at="2026-08-13T00:00:00+00:00")
    req_k = generate_node_key(str(ks), REQ, at="2026-08-13T00:00:00+00:00")
    reg = ObjectRegistry(str(tmp_path / "reg"))
    return {"ks": str(ks), "reg": reg, "node_pub": node_k.public_hex, "node_fp": node_k.fingerprint,
            "req_pub": req_k.public_hex}


def _signed_envelope(ks, job_id="j1", units=2, prompt="hello", signer=REQ, mandate=REQ, extra=None):
    env = {"job_id": job_id, "model": "tiny", "prompt": prompt, "units": units, "requester_mandate": mandate}
    if extra:
        env.update(extra)
    env["sig"] = sign_node_act(ks, signer, cs._canonical(env))
    return env


def _grant(env, *, expires_at, now="2026-08-13T01:00:00+00:00", to=REQ):
    offer = cs.latest_offer(env["reg"], NODE)
    return delegate_governed(env["ks"], NODE, to, f"compute:{offer['object_id']}",
                             expires_at=expires_at, at=now, registry=env["reg"],
                             approver="KM-1176", approval_ref="km-share-1")


def _submit(env, envelope, delegation, now="2026-08-13T02:00:00+00:00", **kw):
    return cs.submit_job(env["reg"], NODE, envelope, recognized_public_hex=env["req_pub"],
                         node_public_hex=env["node_pub"], delegation=delegation, now=now,
                         model_caller=FAKE_MODEL, **kw)


# ── W1 · offer is the node's own governed object; no offer → refusal ──
def test_w1_offer_and_no_offer(env):
    with pytest.raises(cs.ShareRefusal, match="no governed capacity offer"):
        _submit(env, _signed_envelope(env["ks"]), None)
    off = cs.open_offer(env["reg"], NODE, 10, at="2026-08-13T00:30:00+00:00")
    assert off["version_hash"] and off["payload"]["units"] == "10"


# ── W2 · deny-by-default: offer present, no rule → refused ──
def test_w2_deny_by_default(env):
    cs.open_offer(env["reg"], NODE, 10, at="2026-08-13T00:30:00+00:00")
    with pytest.raises(cs.ShareRefusal, match="admission refused|not consented|declared crossing"):
        _submit(env, _signed_envelope(env["ks"]), delegation=None)  # no grant → no SharingRule


# ── W3 · key-scoped, never secret-scoped ──
def test_w3_wrong_key_refused(env):
    cs.open_offer(env["reg"], NODE, 10, at="2026-08-13T00:30:00+00:00")
    g = _grant(env, expires_at="2026-08-13T23:00:00+00:00")
    bad = _signed_envelope(env["ks"], signer=NODE)  # signed by the WRONG key (node, not requester)
    with pytest.raises(cs.ShareRefusal, match="does not verify against this requester"):
        _submit(env, bad, g)


def test_w3_no_signature_refused(env):
    cs.open_offer(env["reg"], NODE, 10, at="2026-08-13T00:30:00+00:00")
    g = _grant(env, expires_at="2026-08-13T23:00:00+00:00")
    env_nosig = {"job_id": "j1", "model": "tiny", "prompt": "hi", "units": 2, "requester_mandate": REQ}
    with pytest.raises(cs.ShareRefusal, match="key-scoped"):
        _submit(env, env_nosig, g)


def test_w3_self_as_requester_refused(env):
    cs.open_offer(env["reg"], NODE, 10, at="2026-08-13T00:30:00+00:00")
    g = _grant(env, expires_at="2026-08-13T23:00:00+00:00")
    ev = _signed_envelope(env["ks"], signer=NODE, mandate=NODE)
    with pytest.raises(cs.ShareRefusal, match="self-as-requester"):
        cs.submit_job(env["reg"], NODE, ev, recognized_public_hex=env["node_pub"],  # recognized == node
                      node_public_hex=env["node_pub"], delegation=g, now="2026-08-13T02:00:00+00:00",
                      model_caller=FAKE_MODEL)


# ── W4 · grant expires by default ──
def test_w4_live_admits_expired_refuses(env):
    cs.open_offer(env["reg"], NODE, 10, at="2026-08-13T00:30:00+00:00")
    g = _grant(env, expires_at="2026-08-13T12:00:00+00:00")
    ok = _submit(env, _signed_envelope(env["ks"], job_id="live"), g, now="2026-08-13T06:00:00+00:00")
    assert ok["outcome"] == "complete"
    # same grant, now PAST expiry → refused (deny-by-default; nothing auto-renews)
    with pytest.raises(cs.ShareRefusal):
        _submit(env, _signed_envelope(env["ks"], job_id="dead"), g, now="2026-08-13T20:00:00+00:00")


def test_w4_revoked_grant_refuses(env):
    cs.open_offer(env["reg"], NODE, 10, at="2026-08-13T00:30:00+00:00")
    g = _grant(env, expires_at="2026-08-13T23:00:00+00:00")
    dele_id = g["delegation"]["object_id"]
    revs = [{"revokes": dele_id}]
    with pytest.raises(cs.ShareRefusal):
        _submit(env, _signed_envelope(env["ks"], job_id="rev"), g, revocations=revs)


# ── W5 · metering re-derivable from receipts; over-subscription refused ──
def test_w5_metering_and_oversubscription(env):
    cs.open_offer(env["reg"], NODE, 5, at="2026-08-13T00:30:00+00:00")
    g = _grant(env, expires_at="2026-08-13T23:00:00+00:00")
    _submit(env, _signed_envelope(env["ks"], job_id="a", units=2), g)
    assert cs.remaining_units(env["reg"], NODE) == 3
    _submit(env, _signed_envelope(env["ks"], job_id="b", units=1), g)
    assert cs.remaining_units(env["reg"], NODE) == 2
    # re-derive from receipts: 5 - (2+1 completed) == 2
    completed = sum(int(r["payload"]["units"]) for r in cs.receipts(env["reg"], NODE)
                    if r["payload"]["outcome"] == "complete")
    assert 5 - completed == 2
    # one unit more than remains → over-subscription refusal from admit_job
    with pytest.raises(cs.ShareRefusal, match="over-subscription|exceeds"):
        _submit(env, _signed_envelope(env["ks"], job_id="c", units=3), g)


# ── W6 · receipts are offline-verifiable ──
def test_w6_receipt_verifies_offline(env):
    cs.open_offer(env["reg"], NODE, 10, at="2026-08-13T00:30:00+00:00")
    g = _grant(env, expires_at="2026-08-13T23:00:00+00:00")
    r = _submit(env, _signed_envelope(env["ks"], job_id="r1"), g)
    rc = r["receipt"]
    assert rc["payload"]["completer_fingerprint"] == env["node_fp"]
    assert cs.verify_receipt(rc, env["node_pub"]) is True
    # tamper: a different node's public → False
    assert cs.verify_receipt(rc, "ab" * 64) is False


# ── W8 · the job cannot escape the allowlisted inference API ──
@pytest.mark.parametrize("bad", [
    {"prompt": "run; rm -rf /"},
    {"prompt": "cat /etc/passwd"},
    {"prompt": "read ../../keystore/Dragon.nodekey.json"},
    {"prompt": "docker run --privileged x"},
    {"prompt": "crossing:bypass port"},
])
def test_w8_escape_shapes_refused(env, bad):
    cs.open_offer(env["reg"], NODE, 10, at="2026-08-13T00:30:00+00:00")
    g = _grant(env, expires_at="2026-08-13T23:00:00+00:00")
    ev = _signed_envelope(env["ks"], job_id="esc", prompt=bad["prompt"])
    with pytest.raises(cs.ShareRefusal, match="escape shape"):
        _submit(env, ev, g)


def test_w8_unknown_key_refused(env):
    cs.open_offer(env["reg"], NODE, 10, at="2026-08-13T00:30:00+00:00")
    g = _grant(env, expires_at="2026-08-13T23:00:00+00:00")
    ev = _signed_envelope(env["ks"], job_id="uk", extra={"shell": "yes"})
    with pytest.raises(cs.ShareRefusal, match="outside the inference allowlist"):
        _submit(env, ev, g)


# ── W7 · the execution bridge is loopback-only ──
def test_w7_non_loopback_model_refused(env):
    cs.open_offer(env["reg"], NODE, 10, at="2026-08-13T00:30:00+00:00")
    g = _grant(env, expires_at="2026-08-13T23:00:00+00:00")
    ev = _signed_envelope(env["ks"], job_id="net")
    # use the REAL loopback-checking caller against a non-loopback URL → refusal, no fallback
    with pytest.raises(cs.ShareRefusal, match="loopback-only"):
        cs.submit_job(env["reg"], NODE, ev, recognized_public_hex=env["req_pub"],
                      node_public_hex=env["node_pub"], delegation=g, now="2026-08-13T02:00:00+00:00",
                      model_url="http://10.0.0.9:11434/api/generate",
                      model_caller=cs._loopback_model_call)


# ── W9 · a refusal is terminal — no non-USN backend anywhere in the module ──
def test_w9_no_backend_endpoint_in_source():
    src = (_ROOT / "scripts" / "compute_share.py").read_text()
    import re
    urls = re.findall(r"https?://[^\s\"')]+", src)
    non_loopback = [u for u in urls if not re.search(r"127\.0\.0\.1|localhost|::1", u)]
    assert non_loopback == [], f"a non-loopback backend URL is present: {non_loopback}"


# ── W10 · integrity-only labels; no channel-secrecy claim anywhere ──
def test_w10_labels_clean():
    src = (_ROOT / "scripts" / "compute_share.py").read_text().lower()
    assert "private" not in src and "confidential" not in src
    assert cs.LABEL == "governed, receipted, integrity-verified — observable in transit"
