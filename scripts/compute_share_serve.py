#!/usr/bin/env python3
"""compute_share_serve.py — Dragon's DECLARED compute-admit listener (the network admit surface).

Closes the transport GAP: it accepts a SIGNED job envelope over a declared TCP socket and runs it through the
GREEN wrapper's `submit_job` locally — which calls the LOOPBACK model server. Only signed job envelopes and
governed receipts cross the wire; the GPU/model API never faces the network. Auth is the requester's signature
alone (verified against the recognized public_hex in the grant) — no shared secret, no token, no IP allowlist.

Composition only: no new admission logic, no new series. The grant is the human-gated one you already published
(scripts/compute_share_offer.py --emit-grant). A refused job returns the refusal — never routed anywhere else.

  scripts/compute_share_serve.py --node UniversalSovereignNode \
    --registry ~/.sovereign_share/registry --grant-file ~/.sovereign_share/grant_Beard.json \
    --listen-host 0.0.0.0 --listen-port 8620 --model-url http://127.0.0.1:11434/api/generate --min-gpu-free-mib 20000

--listen-host is a DECLARED bind (the operator names it; 0.0.0.0 means "I intentionally expose this admit port").
The model server stays loopback regardless — the listener refuses a non-loopback --model-url.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import socket
import struct
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("compute_share", ROOT / "scripts" / "compute_share.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.keystore.node_keystore import load_node_key


def _recv(conn) -> dict | None:
    hdr = _read_n(conn, 4)
    if not hdr:
        return None
    (n,) = struct.unpack(">I", hdr)
    if n > 1_000_000:                       # a job envelope is small; cap to refuse oversized frames
        raise ValueError("frame too large")
    return json.loads(_read_n(conn, n).decode("utf-8"))


def _read_n(conn, n) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            return buf if not buf else buf  # short read -> caller handles
        buf += chunk
    return buf


def _send(conn, obj: dict):
    b = json.dumps(obj).encode("utf-8")
    conn.sendall(struct.pack(">I", len(b)) + b)


def _gpu_free_mib():
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                                      text=True, timeout=10)
        return int(out.strip().splitlines()[0])
    except Exception:
        return None


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Declared compute-admit listener composing submit_job over TCP.")
    p.add_argument("--node", required=True)
    p.add_argument("--registry", required=True)
    p.add_argument("--grant-file", required=True)
    p.add_argument("--listen-host", default="127.0.0.1", help="DECLARED bind (0.0.0.0 = intentionally exposed)")
    p.add_argument("--listen-port", type=int, default=8620)
    p.add_argument("--model-url", default="http://127.0.0.1:11434/api/generate")
    p.add_argument("--min-gpu-free-mib", type=int, default=0)
    p.add_argument("--once", action="store_true", help="serve exactly one job then exit (for tests)")
    a = p.parse_args(argv)

    if "127.0.0.1" not in a.model_url and "localhost" not in a.model_url:
        print("✗ --model-url must be loopback — the GPU never faces the network."); return 2
    ks = os.environ.get("NODE_KEYSTORE_DIR")
    node_pub = load_node_key(ks, a.node).public_hex
    g = json.load(open(a.grant_file, encoding="utf-8"))
    grant, rpub, models = g["grant"], g["requester_public_hex"], g.get("models")
    reg = ObjectRegistry(a.registry)

    if a.listen_host not in ("127.0.0.1", "localhost", "::1"):
        print(f"⚠ declared admit bind on {a.listen_host}:{a.listen_port} — signed job envelopes + receipts only; "
              f"the model API stays loopback ({a.model_url}).")
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((a.listen_host, a.listen_port)); srv.listen(8)
    print(f"∞Δ∞ compute-admit listener up on {a.listen_host}:{a.listen_port} · model {a.model_url} (loopback) · "
          f"node {a.node} fp {load_node_key(ks, a.node).fingerprint} · integrity-only, observable in transit")
    import datetime as _dt

    while True:
        conn, addr = srv.accept()
        try:
            msg = _recv(conn)
            if not msg or msg.get("kind") != "compute_job":
                _send(conn, {"outcome": "refused", "reason": "expected {kind:'compute_job', envelope:{…}}"}); continue
            # GPU fence per job — yield to a Vast.ai rental that started after boot
            if a.min_gpu_free_mib > 0:
                free = _gpu_free_mib()
                if free is None or free < a.min_gpu_free_mib:
                    _send(conn, {"outcome": "refused", "reason": f"GPU busy (free={free}) — yielding to rental"}); continue
            now = _dt.datetime.now(_dt.timezone.utc).isoformat()
            env = msg["envelope"]
            try:
                r = cs.submit_job(reg, a.node, env, recognized_public_hex=rpub, node_public_hex=node_pub,
                                  delegation=grant, now=now, model_url=a.model_url, models=models)
                _send(conn, {"outcome": "complete", "remaining": r["remaining"], "receipt": r["receipt"],
                             "result_head": (r["result"] or "")[:200], "node_public_hex": node_pub})
                print(f"  admit→complete job={env.get('job_id')} from {addr[0]} · remaining {r['remaining']}")
            except cs.ShareRefusal as e:
                _send(conn, {"outcome": "refused", "reason": str(e), "node_public_hex": node_pub})
                print(f"  refused job={env.get('job_id')} from {addr[0]} · {str(e)[:60]}")
        except Exception as e:                # a malformed frame is a refusal, never a crash
            try: _send(conn, {"outcome": "refused", "reason": f"bad request: {type(e).__name__}"})
            except Exception: pass
        finally:
            conn.close()
        if a.once:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
