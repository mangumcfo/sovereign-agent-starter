#!/usr/bin/env python3
"""p2p_harness.py — two-node p2p harness against AA_P2P_HARNESS_BAR (observables P0–P9), script stdout only.

Two DISTINCT node keystores + two DISTINCT node_api processes (same-iron two-HOME is a legitimate two-node rig for
the protocol rows; it does NOT exercise transport — P8 is cross-iron). Composes sealed kernel verbs ONLY:
  genesis.establish_self_held_identity · keystore.sign_node_act/verify_node_act · messaging.send_message/
  carry_to_peer/receive_from_peer · recognition.verify_recognition/refuse_recognition · clean_exit ·
  port.open_crossing/sanction_crossing.

Fences (HOLD-class if violated): no private key on the wire (only public_hex + signatures cross) · no third-party
signer · no hub/escrow · no simulate_* · no node mints a NEW durable identity during the run (the two identities are
provisioned as the precondition, then fixed). The LOAD-BEARING row is P5 — SIGKILL one node mid-flow; the survivor
must not synthesize the dead peer's half (it cryptographically CANNOT: its keystore lacks the peer's key).

Run:  python3 scripts/p2p_harness.py    (env HOME_A/HOME_B/NAME_A/NAME_B/PORT_A/PORT_B optional)
"""
from __future__ import annotations

import datetime
import hashlib
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.objects.scope import SharingRule
from sovereign_agent.peerhood.genesis import establish_self_held_identity
from sovereign_agent.peerhood.recognition import verify_recognition, refuse_recognition
from sovereign_agent.peerhood.clean_exit import clean_exit
from sovereign_agent.keystore.node_keystore import (
    has_node_key, sign_node_act, verify_node_act, load_node_keypair, KeystoreError,
)
from sovereign_agent.messaging.inter_node import send_message, carry_to_peer, receive_from_peer, MessagingError
from sovereign_agent.port.crossing import open_crossing, sanction_crossing, CrossingError

NOW = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
HOME_A = os.environ.get("HOME_A", "/tmp/p2p_A")
HOME_B = os.environ.get("HOME_B", "/tmp/p2p_B")
NAME_A = os.environ.get("NAME_A", "nodeA")
NAME_B = os.environ.get("NAME_B", "nodeB")
PORT_A = int(os.environ.get("PORT_A", "8531"))
PORT_B = int(os.environ.get("PORT_B", "8532"))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def digest(ks, name):
    p = Path(ks) / f"{name}.nodekey.json"
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "(absent)"


def start_node(ks, name, port):
    env = dict(os.environ, NODE_KEYSTORE_DIR=ks, BREATHLINE_NODE_NAME=name,
               BREATHLINE_NODE_LOOPBACK_OWNER="owner", BREATHLINE_NODE_API_HOST="127.0.0.1",
               BREATHLINE_NODE_API_PORT=str(port), PYTHONPATH=os.path.join(REPO, "src"),
               SUBSTRATE_STORAGE_ROOT=os.path.join(ks, "storage"),
               OBLIGATION_LEDGER_ROOT=os.path.join(ks, "obl"))
    proc = subprocess.Popen([sys.executable, "-m", "sovereign_agent.node_api.server",
                             "--host", "127.0.0.1", "--port", str(port)],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/manifest", timeout=1); break
        except Exception:
            time.sleep(0.5)
    return proc


def served_fp(port):
    try:
        import json
        d = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/node", timeout=2).read())
        return d.get("fingerprint")
    except Exception:
        return "(node down)"


def main():
    print(f"∞Δ∞ P2P HARNESS — {NOW()} — host {os.uname().nodename} — rig: SAME-IRON two-HOME (protocol rows; P8=cross-iron)")
    try:  # don't die outside a checkout (same pattern as the D6 wrapper)
        head = subprocess.check_output(["git", "-C", REPO, "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        head = "(not a git checkout)"
    print(f"git HEAD: {head}")
    for h in (HOME_A, HOME_B):
        os.makedirs(os.path.join(h, "ks"), exist_ok=True)
    ksA, ksB = os.path.join(HOME_A, "ks"), os.path.join(HOME_B, "ks")
    regA, regB = ObjectRegistry(os.path.join(HOME_A, "reg")), ObjectRegistry(os.path.join(HOME_B, "reg"))

    # ── precondition: two distinct durable identities (provisioned BEFORE the run; not minted during it) ──
    idA = establish_self_held_identity(ksA, NAME_A, at=NOW(), registry=regA)
    idB = establish_self_held_identity(ksB, NAME_B, at=NOW(), registry=regB)

    print("\n== P0 · two nodes ==")
    procA, procB = start_node(ksA, NAME_A, PORT_A), start_node(ksB, NAME_B, PORT_B)
    print(f"  A {NAME_A}: fp={idA.fingerprint}  digest={digest(ksA,NAME_A)[:32]}…  pid={procA.pid}  /node={served_fp(PORT_A)}")
    print(f"  B {NAME_B}: fp={idB.fingerprint}  digest={digest(ksB,NAME_B)[:32]}…  pid={procB.pid}  /node={served_fp(PORT_B)}")
    print(f"  P0.1 distinct fingerprints: {idA.fingerprint != idB.fingerprint}")
    print(f"  P0.2 distinct keystores: {digest(ksA,NAME_A) != digest(ksB,NAME_B)} (paths {ksA} | {ksB})")
    print(f"  P0.3 distinct pids: {procA.pid != procB.pid}")
    A_fp0, B_fp0 = idA.fingerprint, idB.fingerprint
    A_dg0, B_dg0 = digest(ksA, NAME_A), digest(ksB, NAME_B)

    # ── P1 recognition — two-sided: each node signs its OWN half over the shared hash; verify public-only ──
    print("\n== P1 · recognition (two receipts, one per node, verify offline vs the OTHER's public_hex) ==")
    msg = send_message(regA, f"recognition:{NAME_A}:{NAME_B}", {"recognize": [NAME_A, NAME_B], "bilateral": True},
                       mandate=NAME_A, author=NAME_A, source_ref=f"rec://{NAME_A}", at=NOW())
    h = str(msg["version_hash"]).encode("utf-8")
    sig_a = sign_node_act(ksA, NAME_A, h)          # A's process signs with A's key
    sig_b = sign_node_act(ksB, NAME_B, h)          # B's process signs with B's key (separate keystore)
    # rec carries the kernel's mutual_recognition shape (incl. "peers" so clean_exit can target the severance)
    rec = {"recognition": msg, "sig_a": sig_a, "sig_b": sig_b, "peers": [NAME_A, NAME_B], "third_party": None}
    print(f"  recognition object hash: {msg['version_hash'][:32]}…")
    print(f"  A receipt sig_a: {sig_a[:24]}…   B receipt sig_b: {sig_b[:24]}…")
    print(f"  verify_recognition (public-only, offline): {verify_recognition(rec, idA, idB)}")
    # neither node may produce the other's receipt: A's keystore cannot sign as B
    try:
        sign_node_act(ksA, NAME_B, h); print("  ✗ A forged B's signature — FAIL")
    except KeystoreError as e:
        print(f"  ✓ A CANNOT produce B's receipt (kernel refuses): {str(e)[:60]}…")

    # ── P2 refuse — costs the refused nothing; refused node byte-identical before/after ──
    print("\n== P2 · refusal costs the refused party nothing ==")
    B_before = digest(ksB, NAME_B)
    ref = refuse_recognition(ksA, NAME_A, NAME_B, at=NOW(), registry=regA, reason="stepping back")
    B_after = digest(ksB, NAME_B)
    print(f"  refuse receipt: residual_claim={ref['residual_claim']}  hostage_free={ref['hostage_free']}  by={ref['by']} of={ref['of']}  sig={ref['signature'][:20]}…")
    print(f"  refused node (B) keystore byte-identical before/after: {B_before == B_after}")

    # ── P3 message — carries sender's signature; receiver verifies vs sender's public_hex (not an embedded copy) ──
    print("\n== P3 · message carries sender's signature, verified vs sender's public_hex ==")
    m = send_message(regA, "msg:1", {"text": "hello, peer"}, mandate=NAME_A, author=NAME_A, source_ref=f"msg://{NAME_A}/1", at=NOW())
    mh = str(m["version_hash"]).encode("utf-8")
    msig = sign_node_act(ksA, NAME_A, mh)
    # receiver B verifies against ITS OWN copy of A's public_hex (idA.public_hex), not a copy inside the payload
    print(f"  message hash {m['version_hash'][:24]}…  sender sig {msig[:24]}…")
    print(f"  B verifies vs A.public_hex (out-of-band): {verify_node_act(idA.public_hex, mh, msig)}")
    packet = carry_to_peer(regA, at=NOW())
    got = receive_from_peer(packet)               # anti-hub: B validates the packet over its own bytes
    print(f"  B independent packet validation: received={got['received']} validated_by={got['validated_by']}")

    # ── P4 clean exit — executable; prior grants verify DEAD; both sides no residual ──
    print("\n== P4 · clean exit is executable (prior grants verify DEAD) ==")
    ex = clean_exit(ksA, NAME_A, recognitions=[rec], at=NOW(), registry=regA)
    dead = verify_recognition(rec, idA, idB, revocations=ex.severances)
    print(f"  clean_exit: grants_severed={ex.grants_severed}/{ex.grants_total} no_residual={ex.no_residual}")
    print(f"  prior recognition now verifies: {dead}  (must be False — sever-kills-live)")

    # ── P5 · THE KILL TEST — SIGKILL B mid-flow; survivor A must not synthesize B's half ──
    # NOTE (cross-iron upgrade): this same-iron row proves KEY SEPARATION — A's keystore cryptographically cannot
    # sign as B. The CROSS-IRON run must go further: A asks the LIVE node-B process to complete a two-party act,
    # then B is SIGKILL'd mid-request, and A must degrade honestly against a real dead peer (not a hand-built dict).
    print("\n== P5 · ⛔ KILL TEST ==")
    print(f"  killing B pid {procB.pid} at {NOW()} …")
    os.kill(procB.pid, signal.SIGKILL); procB.wait(timeout=5)
    print(f"  B /node after kill: {served_fp(PORT_B)}  (dead)")
    h2 = hashlib.sha256(b"fresh-two-party-act").hexdigest().encode()
    try:
        forged = sign_node_act(ksA, NAME_B, h2)
        print(f"  ✗ SURVIVOR FORGED DEAD PEER'S SIGNATURE: {forged[:20]}… — FAIL (HOLD-class)")
    except KeystoreError as e:
        print(f"  ✓ survivor cannot synthesize B's half (no B key in A's keystore): {str(e)[:70]}…")
    rec_incomplete = {"recognition": msg, "sig_a": sig_a}   # no real sig_b from the dead peer
    print(f"  survivor verify of incomplete act: {verify_recognition(rec_incomplete, idA, idB)}  (False = honest degrade, no fabricated receipt)")

    # ── P6 · no third party — read the field (not a literal), and prove both sigs verify ONLY under A/B keys ──
    print("\n== P6 · no third party holds anything ==")
    tp = rec.get("third_party")                                   # a REAL read of the recognition's field
    both_ab = verify_node_act(idA.public_hex, h, sig_a) and verify_node_act(idB.public_hex, h, sig_b)
    print(f"  recognition.get('third_party') (read from the object): {tp!r}")
    print(f"  both signatures verify under A's and B's OWN public keys (no third key present): {both_ab}")
    print("  no hub / broker / relay-of-record / escrow in any path (harness holds only ksA and ksB)")

    # ── P7 · Port crossing between nodes — named-human sanction, value-free receipt ──
    print("\n== P7 · Port crossing still gates (named human · value-free receipt) ==")
    crossing = open_crossing(regA, NAME_A, f"peer:{NAME_B}", {"reach": NAME_B},
                             mandate=NAME_A, author=NAME_A, source_ref=f"crossing:{NAME_A}:{NAME_B}", at=NOW())
    rule = [SharingRule(crossing["object_id"], f"peer:{NAME_B}", "write")]
    receipt = sanction_crossing(regA, crossing, rules=rule, boundary_mandate=f"peer:{NAME_B}",
                                approver="owner", approval_ref="p2p port sanction #1")
    novalue = all(k not in receipt for k in ("value", "amount", "funds", "balance", "held"))
    print(f"  crossing receipt: crossed={receipt['crossed']} approver={receipt['approver']} boundary={receipt['boundary']}  value-free={novalue}")

    # ── P8 · transport surface (cross-iron required for a transport claim) ──
    print("\n== P8 · transport surface (CROSS-IRON required for any transport claim) ==")
    print(f"  this rig is SAME-IRON two-HOME — listeners were loopback only (A:127.0.0.1:{PORT_A}, B:127.0.0.1:{PORT_B}).")
    print("  NO transport property is claimed from this run. Cross-iron Dragon↔Beard exercises P8; declare the exact")
    print("  listening surface there. (harness opened no non-loopback listener.)")

    # ── P9 · identity survives the harness ──
    print("\n== P9 · identity survives the harness (fingerprints + keystore digests unchanged) ==")
    A_fp1 = load_node_keypair(ksA, NAME_A).fingerprint; A_dg1 = digest(ksA, NAME_A)
    B_fp1 = load_node_keypair(ksB, NAME_B).fingerprint; B_dg1 = digest(ksB, NAME_B)
    print(f"  A fp {A_fp0}=={A_fp1}: {A_fp0==A_fp1}   digest unchanged: {A_dg0==A_dg1}")
    print(f"  B fp {B_fp0}=={B_fp1}: {B_fp0==B_fp1}   digest unchanged: {B_dg0==B_dg1}")
    print("  (P9 full deposit = a fresh scripts/node_d6_report.sh per node — run separately with the durable HOMEs.)")

    try:
        procA.kill()
    except Exception:
        pass
    print("\n∞Δ∞ P2P HARNESS END — paste this whole block. Load-bearing: P5 kill test above.")


if __name__ == "__main__":
    main()
