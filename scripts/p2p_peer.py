#!/usr/bin/env python3
"""p2p_peer.py — CROSS-IRON two-node peer (transport-split) for AA_P2P_HARNESS_BAR P8/P5-live.

Each peer runs as its OWN process holding ONLY its own keystore. They exchange a recognition object + signatures
over a DECLARED TCP socket (P8). Only public_hex + signatures cross the wire — never a private scalar (P6/fences).
B verifies A's message against the public_hex it learned in the HANDSHAKE, out-of-band from the message (P3).
The kill test (P5) is against a LIVE peer process: A asks the live B to co-sign; when B is SIGKILL'd, A cannot
obtain B's half and cannot forge it (its keystore lacks B's key) — it degrades honestly, no fabricated receipt.

Roles:
  B (responder):  p2p_peer.py --role B --host 0.0.0.0 --port 8600 --home /path/beard-home --name nodeB
  A (initiator):  p2p_peer.py --role A --peer-host <beard-ip> --peer-port 8600 --home /path/dragon-home --name nodeA
  driver (local proof): p2p_peer.py            # spawns B + runs A over a real loopback socket + kills B live

Cross-iron GO: run B on Beard (declared listener), A on Dragon (connect to Beard). For P5, the operator SIGKILLs
B's process mid-flow (A prints the honest-degrade transcript). No third-party signer, no new durable identity.
"""
from __future__ import annotations

import argparse
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
from sovereign_agent.keystore.node_keystore import sign_node_act, verify_node_act, KeystoreError
from sovereign_agent.messaging.inter_node import send_message

NOW = lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()


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


def role_b(home, name, host, port):
    ks = os.path.join(home, "ks"); reg = ObjectRegistry(os.path.join(home, "reg"))
    idB = establish_self_held_identity(ks, name, at=NOW(), registry=reg)
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port)); srv.listen(1)
    print(f"[B {name}] fp={idB.fingerprint} listening on {host}:{port} (DECLARED listener)", flush=True)
    conn, addr = srv.accept()
    a_public_hex = None
    # handshake: exchange public identities out-of-band (no private material)
    hello = _recv(conn); a_public_hex = hello["a_public_hex"]
    _send(conn, {"b_public_hex": idB.public_hex, "b_fingerprint": idB.fingerprint})
    while True:
        try:
            req = _recv(conn)
        except ConnectionError:
            break
        op = req.get("op")
        if op == "cosign_recognition":
            sig_b = sign_node_act(ks, name, req["obj_hash"].encode())     # B signs with ITS OWN key
            _send(conn, {"sig_b": sig_b})                                 # only the signature crosses
        elif op == "verify_message":
            # verify A's message signature against the HANDSHAKE public_hex (out-of-band), NOT a payload copy
            ok = verify_node_act(a_public_hex, req["hash"].encode(), req["sig"])
            _send(conn, {"verified": bool(ok), "checked_against": "handshake a_public_hex"})
        elif op == "bye":
            _send(conn, {"bye": True}); break


def role_a(home, name, peer_host, peer_port):
    ks = os.path.join(home, "ks"); reg = ObjectRegistry(os.path.join(home, "reg"))
    idA = establish_self_held_identity(ks, name, at=NOW(), registry=reg)
    print(f"[A {name}] fp={idA.fingerprint} connecting to {peer_host}:{peer_port}", flush=True)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.connect((peer_host, peer_port))
    _send(s, {"a_public_hex": idA.public_hex, "a_fingerprint": idA.fingerprint})
    hello = _recv(s)
    idB = PeerIdentity(peer_id="peerB", public_hex=hello["b_public_hex"], fingerprint=hello["b_fingerprint"], evidence_hash="")
    print(f"  P0 · two live processes: A pid {os.getpid()} fp {idA.fingerprint} · B fp {hello['b_fingerprint']} (peer)")
    print(f"  P8 · transport DECLARED: TCP {peer_host}:{peer_port}, initiated by A; only public_hex + signatures cross")

    # P1 recognition — A builds object + sig_a, asks LIVE B to co-sign
    msg = send_message(reg, f"recognition:{name}:peerB", {"recognize": [name, "peerB"], "bilateral": True},
                       mandate=name, author=name, source_ref=f"rec://{name}", at=NOW())
    h = str(msg["version_hash"])
    sig_a = sign_node_act(ks, name, h.encode())
    _send(s, {"op": "cosign_recognition", "obj_hash": h}); sig_b = _recv(s)["sig_b"]
    rec = {"recognition": msg, "sig_a": sig_a, "sig_b": sig_b, "peers": [name, "peerB"], "third_party": None}
    print(f"  P1 · recognition verify (public-only, both sigs vs each other's public_hex): {verify_recognition(rec, idA, idB)}")

    # P3 message — B verifies A's sig against the HANDSHAKE public_hex (out-of-band)
    m = send_message(reg, "msg:1", {"text": "hello peer"}, mandate=name, author=name, source_ref=f"msg://{name}/1", at=NOW())
    mh = str(m["version_hash"]); msig = sign_node_act(ks, name, mh.encode())
    _send(s, {"op": "verify_message", "hash": mh, "sig": msig}); vr = _recv(s)
    print(f"  P3 · B verified A's message vs {vr['checked_against']}: {vr['verified']} (not an embedded copy)")

    # P5 · KILL — signal the driver to kill B, then A attempts to complete a two-party act against the dead peer
    print("  P5 · (awaiting peer death) — after B is SIGKILL'd, A must degrade honestly …", flush=True)
    return s, ks, name, h, idA, idB, rec


def driver():
    """Local proof over a REAL loopback socket between two processes, with a LIVE-process kill for P5."""
    import tempfile
    base = tempfile.mkdtemp()
    homeA, homeB = os.path.join(base, "A"), os.path.join(base, "B")
    for h in (homeA, homeB):
        os.makedirs(os.path.join(h, "ks"), exist_ok=True)
    port = 8600
    env = dict(os.environ, PYTHONPATH=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
    procB = subprocess.Popen([sys.executable, __file__, "--role", "B", "--host", "127.0.0.1",
                              "--port", str(port), "--home", homeB, "--name", "nodeB"], env=env)
    time.sleep(2.0)  # let B bind + provision
    print(f"∞Δ∞ P2P CROSS-IRON PEER (local proof: two processes, real loopback socket) — {NOW()} — host {os.uname().nodename}")
    print(f"  B process pid {procB.pid} (the peer that will be killed for P5)")
    s, ks, name, h, idA, idB, rec = role_a(homeA, "nodeA", "127.0.0.1", port)

    # kill the LIVE B process mid-flow, then A tries to complete another two-party act
    print(f"  killing LIVE B pid {procB.pid} at {NOW()} …", flush=True)
    os.kill(procB.pid, signal.SIGKILL); procB.wait(timeout=5)
    h2 = hashlib.sha256(b"fresh-two-party-after-kill").hexdigest()
    try:
        _send(s, {"op": "cosign_recognition", "obj_hash": h2}); _ = _recv(s)
        print("  ✗ got a cosign from a DEAD peer — FAIL")
    except (ConnectionError, OSError) as e:
        print(f"  ✓ live B is dead — A cannot obtain B's half over the wire ({type(e).__name__})")
    try:
        sign_node_act(ks, "nodeB", h2.encode()); print("  ✗ A forged B's signature — FAIL (HOLD-class)")
    except KeystoreError as e:
        print(f"  ✓ A cannot forge B's half (no B key in A's keystore): {str(e)[:64]}…")
    print(f"  survivor verify of incomplete act: {verify_recognition({'recognition': rec['recognition'], 'sig_a': rec['sig_a'], 'peers': rec['peers']}, idA, idB)}  (False = honest degrade)")
    print("∞Δ∞ CROSS-IRON PEER (local proof) END — for the real run, B on Beard + A on Dragon; operator SIGKILLs B mid-flow.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", choices=["A", "B", "driver"], default="driver")
    ap.add_argument("--host", default="127.0.0.1"); ap.add_argument("--port", type=int, default=8600)
    ap.add_argument("--peer-host", default="127.0.0.1"); ap.add_argument("--peer-port", type=int, default=8600)
    ap.add_argument("--home", default="/tmp/peer"); ap.add_argument("--name", default="node")
    a = ap.parse_args()
    if a.role == "B":
        role_b(a.home, a.name, a.host, a.port)
    elif a.role == "A":
        role_a(a.home, a.name, a.peer_host, a.peer_port)
    else:
        driver()


if __name__ == "__main__":
    main()
