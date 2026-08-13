#!/usr/bin/env python3
"""compute_share_outbox.py — Beard-side compute-share OUTBOX + declared listener (peer-messaging transport).

Closes the inter-iron delivery GAP WITHOUT any operator plumbing on the NAT side. Beard (a reachable iron) signs
job envelopes into a local outbox and LISTENS on its OWN declared bind. Dragon (behind NAT) participates
OUTBOUND-ONLY: it dials this listener (scripts/compute_share_pull.py), pulls pending jobs, runs them under the
existing grant, and pushes back the SIGNED receipts. No SSH key exchange, no router port-forward, no hub — envelope
bytes rest only here (Beard's outbox) and in Dragon's registry.

  enqueue : sign ONE job envelope into the outbox (Beard's signed send-record)
  serve   : on Dragon's connect, hand over pending envelopes; receive results; VERIFY each returned receipt against
            the Dragon public_hex Beard already holds (never a key from the wire); move served jobs to done/.

Integrity-only. Delivery language is receipt-honest: a job is "handed to transport" until Dragon's signed receipt
is held and verified — only then "delivered". No channel-secrecy claim on any surface (integrity-only).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
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


def cmd_enqueue(a) -> int:
    load_node_key(a.keystore, a.requester_name)   # fail-loud if Beard's key is absent
    env = {"job_id": a.job_id, "model": a.model, "prompt": a.prompt, "units": a.units,
           "requester_mandate": a.requester_name}
    env["sig"] = sign_node_act(a.keystore, a.requester_name, cs._canonical(env))
    pend = os.path.join(a.outbox, "pending"); os.makedirs(pend, exist_ok=True)
    path = os.path.join(pend, f"{a.job_id}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"envelope": env}, fh, sort_keys=True)
    os.chmod(path, 0o600)
    print(f"enqueued (signed · handed to transport pending pickup): {a.job_id} model={a.model} units={a.units} -> {path}")
    return 0


def cmd_serve(a) -> int:
    pend = os.path.join(a.outbox, "pending"); done = os.path.join(a.outbox, "done")
    os.makedirs(pend, exist_ok=True); os.makedirs(done, exist_ok=True)
    if a.listen_host not in ("127.0.0.1", "localhost", "::1"):
        print(f"⚠ declared outbox bind on {a.listen_host}:{a.listen_port} — signed job envelopes + receipts only "
              f"(this is BEARD's own iron; Dragon connects OUTBOUND — no inbound step on Dragon).")
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((a.listen_host, a.listen_port)); srv.listen(8)
    print(f"∞Δ∞ compute-share OUTBOX listener up on {a.listen_host}:{a.listen_port} · "
          f"Dragon public_hex (of record) {a.dragon_public_hex[:16]}… · integrity-only, observable in transit")
    while True:
        conn, addr = srv.accept()
        try:
            req = _recv(conn)
            if not req or req.get("kind") != "pull":
                _send(conn, {"error": "expected {kind:'pull'}"}); continue
            jobs, files = [], []
            for fn in sorted(os.listdir(pend)):
                if not fn.endswith(".json"):
                    continue
                rec = json.load(open(os.path.join(pend, fn), encoding="utf-8"))
                jobs.append(rec["envelope"]); files.append(fn)
            _send(conn, {"jobs": jobs})
            print(f"  handed {len(jobs)} pending job(s) to {addr[0]} (transport)")
            if not jobs:
                continue
            results = _recv(conn) or {}
            for r in results.get("results", []):
                jid = r.get("job_id"); outcome = r.get("outcome")
                verified = None
                if outcome == "complete":
                    # verify against the Dragon key BEARD HOLDS — never a key from the wire (T4)
                    verified = cs.verify_receipt(r.get("receipt") or {}, a.dragon_public_hex)
                r["receipt_verified_vs_known_dragon_key"] = verified
                with open(os.path.join(done, f"{jid}.json"), "w", encoding="utf-8") as fh:
                    json.dump(r, fh, sort_keys=True)
                fn = f"{jid}.json"
                if fn in files and os.path.exists(os.path.join(pend, fn)):
                    os.remove(os.path.join(pend, fn))
                tag = ("DELIVERED · receipt verified" if verified else
                       ("REFUSED" if outcome != "complete" else "COMPLETE · receipt UNVERIFIED — hold"))
                print(f"  {jid}: {outcome} · {tag} · remaining={r.get('remaining')} · "
                      f"head={str(r.get('result_head',''))[:48]!r}")
            _send(conn, {"kind": "ack"})
        except Exception as e:
            try: _send(conn, {"error": f"{type(e).__name__}"})
            except Exception: pass
        finally:
            conn.close()
        if a.once:
            break
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Beard outbox + declared listener for compute-share peer delivery.")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("enqueue"); e.add_argument("--keystore", required=True); e.add_argument("--requester-name", required=True)
    e.add_argument("--model", required=True); e.add_argument("--units", type=int, default=1)
    e.add_argument("--prompt", required=True); e.add_argument("--job-id", required=True); e.add_argument("--outbox", required=True)
    e.set_defaults(fn=cmd_enqueue)
    s = sub.add_parser("serve"); s.add_argument("--outbox", required=True); s.add_argument("--dragon-public-hex", required=True)
    s.add_argument("--listen-host", default="0.0.0.0"); s.add_argument("--listen-port", type=int, default=8620)
    s.add_argument("--once", action="store_true"); s.set_defaults(fn=cmd_serve)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
