"""Peer-messaging transport e2e (AA_COMPUTE_SHARE_PEER_TRANSPORT_BAR T1-T10, loopback stand-in).

Beard enqueues + LISTENS on its own declared bind; Dragon dials OUT (compute_share_pull), runs submit_job, pushes
signed receipts back; Beard verifies each receipt against the Dragon key it already holds. Dragon opens no listener
(outbound-only). Loopback stub stands in for the model; loopback stands in for the declared cross-iron transport —
the protocol is identical. Proves: delivery + verify (T1/T4), wrong-key dies unreceipted (T2), over-units refused
+ receipted + returned (T3).
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("compute_share", ROOT / "scripts" / "compute_share.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.keystore.node_keystore import generate_node_key, load_node_key, sign_node_act
from sovereign_agent.peerhood.delegation import delegate_governed

NODE, REQ = "Dragon", "Beard"


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


class _Stub(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); self.rfile.read(n)
        self.send_response(200); self.end_headers(); self.wfile.write(json.dumps({"response": "sovereign"}).encode())

    def log_message(self, *a):
        pass


def _run(script, *args, env):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args],
                          env=env, capture_output=True, text=True, timeout=60)


@pytest.fixture()
def rig(tmp_path):
    ks = tmp_path / "ks"; ks.mkdir()
    env = dict(os.environ, NODE_KEYSTORE_DIR=str(ks), BREATHLINE_SEALED_ROOT=str(ROOT),
               PYTHONPATH=f"{ROOT}/src:" + os.environ.get("PYTHONPATH", ""))
    node = generate_node_key(str(ks), NODE, at="2026-08-13T00:00:00+00:00")
    beard = generate_node_key(str(ks), REQ, at="2026-08-13T00:00:00+00:00")
    reg_dir = tmp_path / "reg"; reg = ObjectRegistry(str(reg_dir))
    off = cs.open_offer(reg, NODE, 5, at="2026-08-13T00:30:00+00:00")
    grant = delegate_governed(str(ks), NODE, REQ, f"compute:{off['object_id']}",
                              expires_at="2026-08-20T00:00:00+00:00", at="2026-08-13T01:00:00+00:00",
                              registry=reg, approver="KM-1176", approval_ref="km")
    gfile = tmp_path / "grant_Beard.json"
    gfile.write_text(json.dumps({"grant": grant, "requester_public_hex": beard.public_hex,
                                 "models": ["llama3.2:1b"], "node": NODE}))
    mport = _free_port(); httpd = HTTPServer(("127.0.0.1", mport), _Stub)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    outbox = tmp_path / "outbox"
    yield {"ks": str(ks), "env": env, "reg_dir": str(reg_dir), "gfile": str(gfile),
           "node_pub": node.public_hex, "beard_pub": beard.public_hex, "outbox": str(outbox),
           "mport": mport, "reg": reg}
    httpd.shutdown()


def _serve_once(rig, lport):
    """Beard outbox listener, one cycle, in a thread (it blocks on accept)."""
    def run():
        _run("compute_share_outbox.py", "serve", "--outbox", rig["outbox"],
             "--dragon-public-hex", rig["node_pub"], "--listen-host", "127.0.0.1",
             "--listen-port", str(lport), "--once", env=rig["env"])
    t = threading.Thread(target=run, daemon=True); t.start()
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", lport), timeout=0.2).close(); break
        except OSError:
            time.sleep(0.1)
    return t


def _pull(rig, lport):
    return _run("compute_share_pull.py", "--node", NODE, "--registry", rig["reg_dir"],
                "--grant-file", rig["gfile"], "--beard-host", "127.0.0.1", "--beard-port", str(lport),
                "--model-url", f"http://127.0.0.1:{rig['mport']}/api/generate", "--once", env=rig["env"])


def _enqueue(rig, job_id, model="llama3.2:1b", units=1, signer=REQ, mandate=REQ):
    # enqueue writes a signed envelope; for the wrong-key case we hand-write a mis-signed one
    env = {"job_id": job_id, "model": model, "prompt": "hi", "units": units, "requester_mandate": mandate}
    env["sig"] = sign_node_act(rig["ks"], signer, cs._canonical(env))
    pend = pathlib.Path(rig["outbox"]) / "pending"; pend.mkdir(parents=True, exist_ok=True)
    (pend / f"{job_id}.json").write_text(json.dumps({"envelope": env}))


def _done(rig, job_id):
    return json.loads((pathlib.Path(rig["outbox"]) / "done" / f"{job_id}.json").read_text())


def test_t1_t4_delivery_and_receipt_verify(rig):
    _enqueue(rig, "job-ok")
    t = _serve_once(rig, _free_port_for(rig))
    lport = rig["_lport"]
    out = _pull(rig, lport); assert "admit→complete job-ok" in out.stdout, out.stdout + out.stderr
    t.join(timeout=10)
    d = _done(rig, "job-ok")
    assert d["outcome"] == "complete"
    assert d["receipt_verified_vs_known_dragon_key"] is True     # Beard verified vs the Dragon key it holds (T4)
    # re-derive independently: the receipt verifies against Dragon's public_hex
    assert cs.verify_receipt(d["receipt"], rig["node_pub"]) is True


def test_t2_wrong_key_dies_unreceipted(rig):
    before = len([e for e in rig["reg"].entries() if e["object_id"].startswith("share-receipt")])
    _enqueue(rig, "job-forge", signer=NODE, mandate=REQ)          # signed by Dragon's key, claims Beard
    t = _serve_once(rig, _free_port_for(rig)); lport = rig["_lport"]
    _pull(rig, lport); t.join(timeout=10)
    d = _done(rig, "job-forge")
    assert d["outcome"] == "refused" and "does not verify" in d["reason"]
    reg2 = ObjectRegistry(rig["reg_dir"])
    after = len([e for e in reg2.entries() if e["object_id"].startswith("share-receipt")])
    assert after == before                                        # unreceipted — garbage adds nothing (T2)


def test_t3_over_units_refused_receipted_and_returned(rig):
    _enqueue(rig, "job-big", units=99)
    t = _serve_once(rig, _free_port_for(rig)); lport = rig["_lport"]
    _pull(rig, lport); t.join(timeout=10)
    d = _done(rig, "job-big")
    assert d["outcome"] == "refused" and ("over-subscription" in d["reason"] or "exceeds" in d["reason"])
    reg2 = ObjectRegistry(rig["reg_dir"])
    assert any(e["object_id"] == "share-receipt:Dragon:job-big" and e["payload"]["outcome"] == "refused"
               for e in reg2.entries())                           # post-signature refusal IS receipted (T3)


# helper: pick a port and stash it on rig so serve+pull agree
def _free_port_for(rig):
    p = _free_port(); rig["_lport"] = p; return p
