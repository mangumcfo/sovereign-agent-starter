#!/usr/bin/env python3
"""p2p_peer.py — CROSS-IRON two-node peer (transport-split) for AA_P2P_HARNESS_BAR P8/P5-live.

Each peer runs as its OWN process holding ONLY its own keystore. They exchange a recognition object + signatures
over a DECLARED TCP socket (P8). Only public_hex + signatures cross the wire — never a private scalar (P6/fences).
B verifies A's message against the public_hex it learned in the HANDSHAKE, out-of-band from the message (P3).
The kill test (P5) is against a LIVE peer process: A asks the live B to co-sign; when B is SIGKILL'd, A cannot
obtain B's half over the wire AND cannot forge it — A's own signature does NOT verify against B's public_hex.

Durable identity (no re-mint): pass --keystore-dir at the node's DURABLE keystore + --name at its durable node
id. establish_self_held_identity LOADS the existing key (never re-mints); the keystore file is only READ, so its
digest is unchanged (P9). The registry/work goes under --home, separate from the durable keystore.

Roles:
  B (responder):  p2p_peer.py --role B --host 0.0.0.0 --port 8600 \
                     --keystore-dir ~/.sovereign_keystore --name UniversalSovereignNode --home /tmp/beard-p2p
  A (initiator):  p2p_peer.py --role A --peer-host <beard-ip> --peer-port 8600 --kill-wait 25 \
                     --keystore-dir ~/.sovereign_keystore --name UniversalSovereignNode --home /tmp/dragon-p2p
                  (during the kill-wait window, the operator SIGKILLs B's process on the other iron)
  driver (local proof): p2p_peer.py     # spawns A + B subprocesses over a real loopback socket; kills B live
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.peerhood.genesis import establish_self_held_identity, PeerIdentity
from sovereign_agent.peerhood.recognition import verify_recognition
from sovereign_agent.keystore.node_keystore import sign_node_act, verify_node_act, load_node_keypair
from sovereign_agent.messaging.inter_node import send_message

NOW = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ks(keystore_dir, home):
    return keystore_dir if keystore_dir else os.path.join(home, "ks")


def _digest(ks, name):
    from pathlib import Path
    p = Path(ks) / f"{name}.nodekey.json"
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "(absent)"


def _send(sock, obj):
    sock.sendall((json.dumps(obj) + "\n").encode())


def _recv(sock):
    buf = b""
    while not buf.endswith(b"\n"):
        chunk = sock.recv(65536)
        if not chunk:
            raise ConnectionError("peer closed / died")
        buf += chunk
    return json.loads(buf.decode())


def role_b(keystore_dir, home, name, host, port):
    ks = _ks(keystore_dir, home); os.makedirs(ks, exist_ok=True)
    reg = ObjectRegistry(os.path.join(home, "reg"))
    idB = establish_self_held_identity(ks, name, at=NOW(), registry=reg)  # LOAD if present (no re-mint)
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port)); srv.listen(1)
    print(f"[B {name}] fp={idB.fingerprint} DECLARED listener {host}:{port}", flush=True)
    conn, _ = srv.accept()
    hello = _recv(conn); a_public_hex = hello["a_public_hex"]         # A's identity, out-of-band
    _send(conn, {"b_public_hex": idB.public_hex, "b_fingerprint": idB.fingerprint})
    while True:
        try:
            req = _recv(conn)
        except ConnectionError:
            break
        op = req.get("op")
        if op == "cosign_recognition":
            _send(conn, {"sig_b": sign_node_act(ks, name, req["obj_hash"].encode())})   # only the sig crosses
        elif op == "verify_message":
            ok = verify_node_act(a_public_hex, req["hash"].encode(), req["sig"])          # vs HANDSHAKE public_hex
            _send(conn, {"verified": bool(ok), "checked_against": "handshake a_public_hex"})
        else:
            break


def role_a(keystore_dir, home, name, peer_host, peer_port, kill_wait):
    ks = _ks(keystore_dir, home)
    reg = ObjectRegistry(os.path.join(home, "reg"))
    idA = establish_self_held_identity(ks, name, at=NOW(), registry=reg)  # LOAD durable key (no re-mint)
    dg0 = _digest(ks, name)
    print(f"∞Δ∞ P2P CROSS-IRON A — {NOW()} — host {os.uname().nodename}")
    print(f"  A {name}: fp={idA.fingerprint}  keystore_digest={dg0[:32]}…  (durable; loaded, not re-minted)")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.connect((peer_host, peer_port))
    _send(s, {"a_public_hex": idA.public_hex, "a_fingerprint": idA.fingerprint})
    hello = _recv(s)
    idB = PeerIdentity(peer_id="peerB", public_hex=hello["b_public_hex"], fingerprint=hello["b_fingerprint"], evidence_hash="")
    print(f"  P0 · two live processes: A fp {idA.fingerprint} · B fp {hello['b_fingerprint']} (peer, over the wire)")
    print(f"  P8 · transport DECLARED: TCP {peer_host}:{peer_port}, initiated by A; only public_hex + signatures cross")

    msg = send_message(reg, f"recognition:{name}:peerB", {"recognize": [name, "peerB"], "bilateral": True},
                       mandate=name, author=name, source_ref=f"rec://{name}", at=NOW())
    h = str(msg["version_hash"]); sig_a = sign_node_act(ks, name, h.encode())
    _send(s, {"op": "cosign_recognition", "obj_hash": h}); sig_b = _recv(s)["sig_b"]
    rec = {"recognition": msg, "sig_a": sig_a, "sig_b": sig_b, "peers": [name, "peerB"], "third_party": None}
    print(f"  P1 · recognition verify (public-only, both sigs vs each other's public_hex): {verify_recognition(rec, idA, idB)}")

    m = send_message(reg, "msg:1", {"text": "hello peer"}, mandate=name, author=name, source_ref=f"msg://{name}/1", at=NOW())
    mh = str(m["version_hash"]); msig = sign_node_act(ks, name, mh.encode())
    _send(s, {"op": "verify_message", "hash": mh, "sig": msig}); vr = _recv(s)
    print(f"  P3 · B verified A's message vs {vr['checked_against']}: {vr['verified']} (not an embedded copy)")

    print(f"\n  == P5 · ⛔ SIGKILL the peer process NOW — window {kill_wait}s ==", flush=True)
    time.sleep(kill_wait)
    h2 = hashlib.sha256(("fresh-two-party-after-kill:" + NOW()).encode()).hexdigest()
    try:
        _send(s, {"op": "cosign_recognition", "obj_hash": h2}); _recv(s)
        print("  ✗ got a cosign from a DEAD peer — FAIL (peer may still be alive; re-run and kill in-window)")
    except (ConnectionError, OSError) as e:
        print(f"  ✓ cannot obtain B's half over the wire — peer is dead ({type(e).__name__})")
    # forge test (name-independent): A can only sign with ITS OWN key; that signature does NOT verify as B
    forged = sign_node_act(ks, name, h2.encode())
    print(f"  ✓ A's own signature does NOT verify as B (cannot forge B's half): verifies_as_B={verify_node_act(idB.public_hex, h2, forged)}")
    print(f"  survivor verify of incomplete act (sig_a only): {verify_recognition({'recognition': msg, 'sig_a': sig_a, 'peers': [name, 'peerB']}, idA, idB)}  (False = honest degrade)")

    dg1 = _digest(ks, name); fp1 = load_node_keypair(ks, name).fingerprint
    print(f"\n  P9 (A side) · fp unchanged: {idA.fingerprint == fp1}  keystore digest unchanged: {dg0 == dg1}")
    print("∞Δ∞ CROSS-IRON A END — paste with `ss -ltnp` (sockets+pids) and a fresh scripts/node_d6_report.sh.")


def driver():
    """Local proof: spawn A + B as REAL subprocesses over a loopback socket; kill B live during A's window."""
    import tempfile
    base = tempfile.mkdtemp(); homeA, homeB = os.path.join(base, "A"), os.path.join(base, "B")
    port = 8600
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "src"))
    procB = subprocess.Popen([sys.executable, __file__, "--role", "B", "--host", "127.0.0.1", "--port", str(port),
                              "--home", homeB, "--name", "nodeB"], env=env)
    time.sleep(2.0)
    procA = subprocess.Popen([sys.executable, __file__, "--role", "A", "--peer-host", "127.0.0.1",
                              "--peer-port", str(port), "--home", homeA, "--name", "nodeA", "--kill-wait", "6"], env=env)
    time.sleep(4.0)
    print(f"  [driver] SIGKILL live B pid {procB.pid} at {NOW()}", flush=True)
    os.kill(procB.pid, signal.SIGKILL)
    procA.wait(timeout=30); procB.wait(timeout=5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", choices=["A", "B", "driver"], default="driver")
    ap.add_argument("--host", default="127.0.0.1"); ap.add_argument("--port", type=int, default=8600)
    ap.add_argument("--peer-host", default="127.0.0.1"); ap.add_argument("--peer-port", type=int, default=8600)
    ap.add_argument("--home", default="/tmp/peer"); ap.add_argument("--name", default="node")
    ap.add_argument("--keystore-dir", default=None, help="durable keystore dir (LOAD, no re-mint); else <home>/ks")
    ap.add_argument("--kill-wait", type=int, default=6, help="seconds A waits for the operator to SIGKILL B")
    a = ap.parse_args()
    os.makedirs(a.home, exist_ok=True)
    if a.role == "B":
        role_b(a.keystore_dir, a.home, a.name, a.host, a.port)
    elif a.role == "A":
        role_a(a.keystore_dir, a.home, a.name, a.peer_host, a.peer_port, a.kill_wait)
    else:
        driver()


if __name__ == "__main__":
    main()
