#!/usr/bin/env python3
"""Reference example A — P2P receipted messaging between two sovereign nodes.

Thin client. Builds NO engine, NO message bus, NO hub. It only *composes* sealed floors:
  · peerhood.genesis        establish_self_held_identity   (S14 V01 · D1 keystore)
  · peerhood.recognition    mutual_recognition / verify_recognition / refuse_recognition (S14 V02)
  · messaging.inter_node    send_message / carry_to_peer / receive_from_peer (S6 V01)

What it demonstrates, end to end, on a bare public clone (no network, no account, no telemetry):
  1. two nodes each hold their OWN key on their OWN iron;
  2. they recognize each other — a mutual, signed, public-only receipt; a non-party cannot verify in;
  3. node A sends a message that IS a receipt the moment it is sent (authored, provenance-carrying, integrity-bound);
  4. node B validates the delivered packet INDEPENDENTLY, over the packet's own bytes — no hub, no sender registry;
  5. offline verification binds to a peer-stated root; a wrong stated root is REFUSED;
  6. a TAMPERED message payload is REFUSED (fail-closed);
  7. node A REFUSES the peer with a first-class signed act that leaves NO residual claim — exit is non-hostage.

Kill-targets held (an app built on this MUST NOT violate):
  · no custodian / no hub takes custody of the message (delivery carries nothing in between);
  · no central validator (each node validates for itself);
  · no silent acceptance (a packet that fails its own checks, or a wrong stated root, is refused);
  · refusing a peer leaves no residual claim (hostage-free) — you can always walk.

Run:  python examples/p2p_messaging/run_p2p.py
Exits non-zero on any failed assertion.
"""
from __future__ import annotations

import copy
import tempfile
from pathlib import Path

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.peerhood.genesis import establish_self_held_identity
from sovereign_agent.peerhood.recognition import (
    mutual_recognition, verify_recognition, refuse_recognition,
)
from sovereign_agent.messaging.inter_node import (
    send_message, carry_to_peer, receive_from_peer, MessagingError,
)

AT = "2026-08-11T18:00:00Z"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        ks = str(Path(tmp) / "keystore")           # each node's key lives on its own iron
        reg = ObjectRegistry(str(Path(tmp) / "node-a"))  # node A's own append-only object record

        # 1 · two self-held identities (D1 keystore) — no custodian, no account
        a = establish_self_held_identity(ks, "node-a", at=AT, registry=reg)
        b = establish_self_held_identity(ks, "node-b", at=AT, registry=reg)
        print(f"[1] identities minted on own iron: node-a={a.fingerprint[:16]}… node-b={b.fingerprint[:16]}…")

        # 2 · mutual recognition — signed, public-only receipt; a non-party cannot verify in
        rec = mutual_recognition(ks, "node-a", "node-b", at=AT, registry=reg)
        assert verify_recognition(rec, a, b) is True, "the two parties must verify their own recognition"
        stranger = establish_self_held_identity(ks, "stranger", at=AT, registry=reg)
        assert verify_recognition(rec, a, stranger) is False, "a non-party must NOT verify into a recognition"
        print("[2] mutual recognition verifies for both parties · a stranger is refused (public-only, no registry)")

        # 3 · a message that is a receipt the moment it is sent (authored, provenance, integrity)
        msg = send_message(reg, "m1", {"text": "hello, peer"}, mandate="node-a",
                           author="node-a", source_ref="msg://node-a/m1", at=AT)
        assert msg["version_hash"], "a sent message carries its own integrity identity"
        print(f"[3] message sent as a governed receipt: {msg['object_id']} hash={msg['version_hash'][:16]}…")

        # 4 · node B validates the delivered packet INDEPENDENTLY, over its own bytes — no hub between
        packet = carry_to_peer(reg, at=AT)          # self-verifying packet; travels node-to-node, nothing in between
        got = receive_from_peer(packet)             # node B: pure, offline validation
        assert got["received"] is True and got["validated_by"] == "self", "node B validates for itself"
        print(f"[4] node B accepted the packet by its OWN validation · message_root={str(got['message_root'])[:16]}…")

        # 5 · offline verification binds to a peer-stated root; the right root matches, a wrong one is refused
        stated_root = packet["manifest"]["root"]
        ok = receive_from_peer(packet, expected_root=stated_root)
        assert ok["received"] is True, "the correct peer-stated root must match"
        try:
            receive_from_peer(packet, expected_root="00" * 32)
            raise AssertionError("a WRONG peer-stated root must be refused")
        except MessagingError:
            print("[5] offline root check: correct root matches · a wrong stated root is REFUSED (fail-closed)")

        # 6 · a tampered message payload is refused (integrity fails from the packet's own bytes)
        bad = copy.deepcopy(packet)
        target = next(o for o in bad["objects"] if o["object_id"].startswith("message:"))
        target["payload"]["text"] = "TAMPERED"
        try:
            receive_from_peer(bad)
            raise AssertionError("a tampered message payload must be refused")
        except MessagingError:
            print("[6] tampered message payload REFUSED — validation fails from the packet's own bytes")

        # 7 · refuse the peer — first-class SIGNED act, NO residual claim (exit is non-hostage)
        ref = refuse_recognition(ks, "node-a", "node-b", at=AT, registry=reg, reason="stepping back")
        assert ref["residual_claim"] is None, "refusing a peer must leave no residual claim"
        assert ref["hostage_free"] is True and ref["signature"], "refusal is a signed, hostage-free act"
        print("[7] node A refused the peer: signed act · residual_claim=None · hostage_free=True (you can always walk)")

    print("\nP2P MESSAGING EXAMPLE — all checks passed. "
          "No hub, no custodian, no central validator; refuse/exit leaves no hostage.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
