#!/usr/bin/env python3
"""compute_share_client.py — DEV TCP HARNESS client (not the federation path).

⚠ Pairs with compute_share_serve.py (the dev harness) and requires Dragon reachable inbound. For the
operator-burden-free product path (no router forward / SSH on the NAT iron), use compute_share_outbox.py enqueue
on Beard + compute_share_pull.py on Dragon.

Beard's one-command compute-share client.

Loads Beard's OWN key, signs a job envelope, sends it to Dragon's declared admit listener over TCP, and prints
the outcome (admit/refuse), the model result head, the receipt, and an offline verify of that receipt against
Dragon's public_hex. The private key never leaves this iron — only the signed envelope (model/prompt/units/
mandate/signature) crosses the wire.

  scripts/compute_share_client.py --keystore ~/.beard-sovereign-keystore --requester-name Beard \
    --dragon-host 192.74.128.96 --dragon-port 8620 --model llama3.2:1b --units 1 \
    --prompt "Reply with one word: sovereign." --job-id beard-test-1
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import socket
import struct

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("compute_share", ROOT / "scripts" / "compute_share.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)

from sovereign_agent.keystore.node_keystore import load_node_key, sign_node_act


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


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Sign one job and submit it to Dragon's compute-admit listener.")
    p.add_argument("--keystore", required=True, help="Beard's keystore dir (holds Beard's OWN key)")
    p.add_argument("--requester-name", required=True, help="Beard's node id (its key name = its mandate)")
    p.add_argument("--dragon-host", required=True)
    p.add_argument("--dragon-port", type=int, required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--units", type=int, default=1)
    p.add_argument("--prompt", required=True)
    p.add_argument("--job-id", required=True)
    a = p.parse_args(argv)

    my = load_node_key(a.keystore, a.requester_name)   # private scalar stays here; only public + sig go out
    env = {"job_id": a.job_id, "model": a.model, "prompt": a.prompt, "units": a.units,
           "requester_mandate": a.requester_name}
    env["sig"] = sign_node_act(a.keystore, a.requester_name, cs._canonical(env))
    print(f"== signing job {a.job_id!r} for model {a.model} ({a.units} unit) as {a.requester_name} "
          f"[{my.public_hex[:16]}…] ==")

    with socket.create_connection((a.dragon_host, a.dragon_port), timeout=120) as s:
        _send(s, {"kind": "compute_job", "envelope": env})
        reply = _recv(s)
    if reply is None:
        print("✗ no reply from Dragon (connection closed)"); return 3

    out = reply.get("outcome")
    if out == "complete":
        rc = reply.get("receipt") or {}
        print(f"== ADMITTED → COMPLETE · remaining {reply.get('remaining')} ==")
        print(f"  result head : {reply.get('result_head','')[:120]}")
        print(f"  receipt     : {rc.get('payload',{}).get('job_id')} "
              f"{rc.get('payload',{}).get('outcome')} · completer_fp {rc.get('payload',{}).get('completer_fingerprint')}")
        node_pub = reply.get("node_public_hex", "")
        ok = cs.verify_receipt(rc, node_pub) if node_pub else None
        print(f"  verify receipt offline vs Dragon public_hex: {ok}")
        return 0
    print(f"== REFUSED (terminal — no fallback) ==\n  reason: {reply.get('reason')}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
