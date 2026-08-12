#!/usr/bin/env python3
"""Reference example B — sovereign file/datum storage: owner-scoped, integrity-bound, governed sharing only.

Thin client. Builds NO store, NO bucket, NO cloud host. It only *composes* sealed floors:
  · objects.registry        ObjectRegistry            (S5 V05 append-only object record)
  · objects.scope           SharingRule               (S7 V05 declared cross-mandate scope)
  · storage.sovereign_store store_datum / retrieve_datum (S7 V03 · P5 Merkle integrity)

What it demonstrates, end to end, on a bare public clone (no network, no account, no telemetry):
  1. a datum is stored as the OWNER's governed object, integrity-bound by a Merkle root over its own bytes;
  2. the owner retrieves their own datum whole — own-mandate access needs no grant;
  3. a DIFFERENT party with no declared rule is REFUSED (deny-by-default — no silent public bucket);
  4. sharing happens ONLY through a governed path — the owner declares a SharingRule naming exactly this datum
     and exactly one other party; then, and only then, that party may read it;
  5. a CORRUPTED datum is REFUSED on retrieval (at-rest integrity fails from its own bytes);
  6. retrieving a datum that is not on the record is REFUSED.

Kill-targets held (an app built on this MUST NOT violate):
  · no central store owns or vouches for the data — the owner does;
  · no standing trust across data — every cross-party read needs a declared, named scope;
  · no silent public bucket — absence of a rule is a refusal, not open access;
  · no altered data served — integrity is checked from the datum's own bytes on every read.

Exit & non-hostage: the datum is the owner's own object; the owner walks with it and reads it with no third
party in the loop. A share is exactly its declared scope and nothing wider — revoking is simply not presenting
the rule again; no grant stands on its own. Nothing holds your data hostage.

Run:  python examples/file_storage/run_storage.py
Exits non-zero on any failed assertion.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.objects.scope import SharingRule
from sovereign_agent.storage.sovereign_store import store_datum, retrieve_datum, StorageError

AT = "2026-08-11T18:30:00Z"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        reg = ObjectRegistry(str(Path(tmp) / "node"))
        chunks = [b"the owner's", b" private", b" file bytes"]

        # 1 · store a datum as the owner's governed object, integrity-bound by a Merkle root over its own bytes
        d = store_datum(reg, "owner-node", chunks, visibility="private", mandate="owner-node",
                        author="owner-node", source_ref="store://owner-node/f1", at=AT)
        assert d["version_hash"] and d["payload"]["root"], "a stored datum carries its own integrity root"
        print(f"[1] datum stored as owner's object: {d['object_id']} root={d['payload']['root'][:16]}…")

        # 2 · the owner retrieves their own datum whole — own-mandate access needs no grant
        got = retrieve_datum(reg, d, [], chunks, principal_mandate="owner-node")
        assert got["retrieved"] is True and got["integrity"] == "verified", "owner reads own datum, integrity verified"
        print("[2] owner retrieved own datum · integrity=verified (own-mandate access is whole)")

        # 3 · a different party with no declared rule is REFUSED — deny-by-default, no silent public bucket
        try:
            retrieve_datum(reg, d, [], chunks, principal_mandate="other-node")
            raise AssertionError("a party with no declared scope must be refused")
        except StorageError:
            print("[3] other-node with NO rule REFUSED — deny-by-default (no silent public bucket)")

        # 4 · sharing ONLY through a governed path: the owner declares a SharingRule naming exactly this datum + party
        rule = SharingRule(d["object_id"], "other-node", "read")
        shared = retrieve_datum(reg, d, [rule], chunks, principal_mandate="other-node")
        assert shared["retrieved"] is True, "a declared read scope lets exactly that party read exactly this datum"
        print("[4] owner declared a read SharingRule → other-node may now read exactly this datum (governed share)")

        # 5 · a corrupted datum is REFUSED on retrieval — at-rest integrity fails from its own bytes
        corrupted = [b"the owner's", b" private", b" file bytes -- ALTERED"]
        try:
            retrieve_datum(reg, d, [], corrupted, principal_mandate="owner-node")
            raise AssertionError("corrupted bytes must be refused")
        except StorageError:
            print("[5] CORRUPTED datum REFUSED on retrieval — Merkle integrity fails from its own bytes")

        # 6 · retrieving a datum not on the record is REFUSED
        try:
            retrieve_datum(reg, {}, [], chunks, principal_mandate="owner-node")
            raise AssertionError("a non-existent datum must be refused")
        except StorageError:
            print("[6] retrieval of a datum NOT on the record REFUSED (no phantom reads)")

    print("\nFILE STORAGE EXAMPLE — all checks passed. "
          "Owner-scoped, integrity-bound; governed share only; no central store, no standing trust, no hostage.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
