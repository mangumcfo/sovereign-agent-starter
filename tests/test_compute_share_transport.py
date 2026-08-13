"""End-to-end: Beard client -> Dragon declared listener over TCP (loopback), composing submit_job.

Proves the network admit surface: a signed job crosses the wire, Dragon runs it through the GREEN wrapper
against a loopback stub model, returns a receipt Beard verifies offline. A wrong-key job is refused; the private
key never crosses (only the envelope + signature). Same-iron loopback stands in for the declared cross-iron
transport — the protocol is identical.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import socket
import struct
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
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps({"response": "sovereign"}).encode())

    def log_message(self, *a):
        pass


def _framed_send(sock, obj):
    b = json.dumps(obj).encode(); sock.sendall(struct.pack(">I", len(b)) + b)


def _framed_recv(sock):
    hdr = b""
    while len(hdr) < 4:
        c = sock.recv(4 - len(hdr))
        if not c:
            return None
        hdr += c
    (n,) = struct.unpack(">I", hdr); buf = b""
    while len(buf) < n:
        buf += sock.recv(n - len(buf))
    return json.loads(buf.decode())


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    ks = tmp_path / "ks"; ks.mkdir()
    monkeypatch.setenv("NODE_KEYSTORE_DIR", str(ks))
    monkeypatch.setenv("BREATHLINE_SEALED_ROOT", str(ROOT))
    node = generate_node_key(str(ks), NODE, at="2026-08-13T00:00:00+00:00")
    beard = generate_node_key(str(ks), REQ, at="2026-08-13T00:00:00+00:00")
    reg_dir = tmp_path / "reg"
    reg = ObjectRegistry(str(reg_dir))
    # publish offer + grant, emit the grant file (what the listener loads)
    off = cs.open_offer(reg, NODE, 5, at="2026-08-13T00:30:00+00:00")
    grant = delegate_governed(str(ks), NODE, REQ, f"compute:{off['object_id']}",
                              expires_at="2026-08-20T00:00:00+00:00", at="2026-08-13T01:00:00+00:00",
                              registry=reg, approver="KM-1176", approval_ref="km-test")
    gfile = tmp_path / "grant_Beard.json"
    gfile.write_text(json.dumps({"grant": grant, "requester_public_hex": beard.public_hex,
                                 "models": ["llama3.2:1b"], "node": NODE}))
    # loopback stub model
    mport = _free_port()
    httpd = HTTPServer(("127.0.0.1", mport), _Stub)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    # the declared listener (serve --once), in a subprocess so it's the real script
    lport = _free_port()
    env = dict(os.environ, NODE_KEYSTORE_DIR=str(ks), BREATHLINE_SEALED_ROOT=str(ROOT),
               PYTHONPATH=f"{ROOT}/src:" + os.environ.get("PYTHONPATH", ""))
    srv = subprocess.Popen(
        [sys.executable, str(ROOT / "scripts" / "compute_share_serve.py"),
         "--node", NODE, "--registry", str(reg_dir), "--grant-file", str(gfile),
         "--listen-host", "127.0.0.1", "--listen-port", str(lport),
         "--model-url", f"http://127.0.0.1:{mport}/api/generate", "--once"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", lport), timeout=0.2).close(); break
        except OSError:
            time.sleep(0.1)
    yield {"ks": str(ks), "node_pub": node.public_hex, "beard_pub": beard.public_hex,
           "lport": lport, "srv": srv}
    srv.terminate(); httpd.shutdown()


def _signed(ks, name, job_id, model="llama3.2:1b", units=1, prompt="hi"):
    e = {"job_id": job_id, "model": model, "prompt": prompt, "units": units, "requester_mandate": name}
    e["sig"] = sign_node_act(ks, name, cs._canonical(e)); return e


def test_beard_job_admits_and_receipt_verifies(rig):
    env = _signed(rig["ks"], REQ, "beard-1")
    with socket.create_connection(("127.0.0.1", rig["lport"]), timeout=10) as s:
        _framed_send(s, {"kind": "compute_job", "envelope": env})
        reply = _framed_recv(s)
    assert reply["outcome"] == "complete"
    assert reply["remaining"] == "4"
    rc = reply["receipt"]
    assert rc["payload"]["outcome"] == "complete"
    assert cs.verify_receipt(rc, reply["node_public_hex"]) is True
    # the private scalar never crossed: the reply carries only public_hex + governed objects
    assert "d" not in json.dumps(reply) or '"d":' not in json.dumps(reply)


def test_wrong_key_job_refused_over_wire(rig):
    # sign with Dragon's key but claim to be Beard -> verify vs Beard's recognized key fails
    env = _signed(rig["ks"], NODE, "forge-1")
    env["requester_mandate"] = REQ
    env["sig"] = sign_node_act(rig["ks"], NODE, cs._canonical(env))
    with socket.create_connection(("127.0.0.1", rig["lport"]), timeout=10) as s:
        _framed_send(s, {"kind": "compute_job", "envelope": env})
        reply = _framed_recv(s)
    assert reply["outcome"] == "refused"
    assert "does not verify" in reply["reason"]
