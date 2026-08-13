#!/usr/bin/env python3
"""compute_share_pull.py — Dragon-side OUTBOUND puller (NAT-friendly compute-share transport).

Dragon participates OUTBOUND-ONLY: it dials Beard's declared outbox listener (scripts/compute_share_outbox.py
serve), pulls pending SIGNED job envelopes, runs each through the GREEN wrapper's `submit_job` (admission
unchanged — recognized public_hex · units · models · loopback model), and pushes back the SIGNED receipts. Dragon
opens NO listener; there is NO inbound step on the NAT iron — the operator-burden fence made real.

Composition of admit_job + the existing grant. Loopback model only. No hub, no fallback wire. A refused job's
receipt travels back as-is; nothing retries elsewhere.

  scripts/compute_share_pull.py --node UniversalSovereignNode --registry ~/.sovereign_share/registry \
    --grant-file ~/.sovereign_share/grant_Beard.json --beard-host 207.244.248.211 --beard-port 8620 \
    --model-url http://127.0.0.1:11434/api/generate --min-gpu-free-mib 20000 [--once]
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import pathlib
import socket
import struct
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("compute_share", ROOT / "scripts" / "compute_share.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.keystore.node_keystore import load_node_key


def _send(sock, obj):
    b = json.dumps(obj).encode("utf-8")
    sock.sendall(struct.pack(">I", len(b)) + b)


def _recv(sock):
    hdr = b""
    while len(hdr) < 4:
        c = sock.recv(4 - len(hdr))
        if not c:
            return None
        hdr += c
    (n,) = struct.unpack(">I", hdr)
    buf = b""
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c:
            break
        buf += c
    return json.loads(buf.decode("utf-8"))


def _gpu_free_mib():
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                                      text=True, timeout=10)
        return int(out.strip().splitlines()[0])
    except Exception:
        return None


def _load_grant(path):
    """Reload the grant on every poll. Absent/unreadable → (None, None, None): no recognized key, no rule →
    deny-by-default on the next job. This is the operator's LIVE revocation: delete the file, jobs refuse; restore
    it, jobs admit again — the daemon never falls over either way."""
    try:
        g = json.load(open(path, encoding="utf-8"))
        return g["grant"], g["requester_public_hex"], g.get("models")
    except (FileNotFoundError, OSError, ValueError, KeyError, TypeError):
        return None, None, None


def _one_pull(a, reg, node_pub) -> int:
    grant, rpub, models = _load_grant(a.grant_file)     # RELOADED each poll (KM 2026-08-13)
    with socket.create_connection((a.beard_host, a.beard_port), timeout=60) as s:
        _send(s, {"kind": "pull"})
        reply = _recv(s) or {}
        jobs = reply.get("jobs", [])
        if not jobs:
            return 0
        results = []
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for env in jobs:
            jid = env.get("job_id")
            if grant is None or not rpub:
                # no grant loaded → cannot authenticate a requester, no rule to admit under → deny-by-default,
                # unreceipted (an unauthenticated node cannot be made to spend a governed object)
                results.append({"job_id": jid, "outcome": "refused", "node_public_hex": node_pub,
                                "reason": "job refused: no grant loaded on this node (grant file absent/unreadable) "
                                          "— deny-by-default until the operator restores/re-issues the grant"})
                print(f"  refused {jid} · no grant loaded (deny-by-default)")
                continue
            if a.min_gpu_free_mib > 0:
                free = _gpu_free_mib()
                if free is None or free < a.min_gpu_free_mib:
                    results.append({"job_id": jid, "outcome": "refused",
                                    "reason": f"GPU busy (free={free}) — yielding to rental", "node_public_hex": node_pub})
                    continue
            try:
                r = cs.submit_job(reg, a.node, env, recognized_public_hex=rpub, node_public_hex=node_pub,
                                  delegation=grant, now=now, model_url=a.model_url, models=models)
                results.append({"job_id": jid, "outcome": "complete", "remaining": r["remaining"],
                                "receipt": r["receipt"], "result_head": (r["result"] or "")[:200],
                                "node_public_hex": node_pub})
                print(f"  admit→complete {jid} · remaining {r['remaining']}")
            except cs.ShareRefusal as e:
                results.append({"job_id": jid, "outcome": "refused", "reason": str(e), "node_public_hex": node_pub})
                print(f"  refused {jid} · {str(e)[:60]}")
        _send(s, {"kind": "results", "results": results})
        _recv(s)   # Beard's ack
        return len(results)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Dragon outbound puller for compute-share peer delivery.")
    p.add_argument("--node", required=True); p.add_argument("--registry", required=True)
    p.add_argument("--grant-file", required=True)
    p.add_argument("--beard-host", required=True); p.add_argument("--beard-port", type=int, required=True)
    p.add_argument("--model-url", default="http://127.0.0.1:11434/api/generate")
    p.add_argument("--min-gpu-free-mib", type=int, default=0)
    p.add_argument("--poll-seconds", type=int, default=5)
    p.add_argument("--once", action="store_true")
    a = p.parse_args(argv)

    if "127.0.0.1" not in a.model_url and "localhost" not in a.model_url:
        print("✗ --model-url must be loopback — the GPU never faces the network."); return 2
    ks = os.environ.get("NODE_KEYSTORE_DIR")
    node_pub = load_node_key(ks, a.node).public_hex
    reg = ObjectRegistry(a.registry)
    _g0, _r0, _m0 = _load_grant(a.grant_file)
    print(f"∞Δ∞ compute-share puller — Dragon {a.node} fp {load_node_key(ks, a.node).fingerprint} dials "
          f"Beard {a.beard_host}:{a.beard_port} OUTBOUND · model {a.model_url} (loopback) · no inbound bind here")
    print(f"  grant file {a.grant_file}: {'loaded' if _g0 else 'ABSENT/UNREADABLE — jobs deny-by-default until restored'} "
          f"(RELOADED every poll — delete the file to revoke live)")
    if a.once:
        n = _one_pull(a, reg, node_pub)
        print(f"  pulled/processed {n} job(s)"); return 0
    while True:
        try:
            _one_pull(a, reg, node_pub)          # grant is reloaded inside, every cycle
        except OSError as e:
            print(f"  (beard unreachable: {type(e).__name__} — will retry)")
        time.sleep(a.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
