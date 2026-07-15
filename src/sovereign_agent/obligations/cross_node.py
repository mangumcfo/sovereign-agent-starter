"""Federation-portable cross-NODE review — S2 closure wave slice W2.

DOCTRINE (composed entirely from SEALED sources — no new beats, per the operator 2026-07-08 re-assessment):
  S2-V3 Ch 5 receipt names "the multi-role quorum + federation-portable cross_role_review" as the
  build; S2-V4 Ch 2 supplies the transport (the 3-receipt witness, slice W1); slice 2.2 supplies the
  counting engine (N DISTINCT gate-valid approvers). Cross-node review = a quorum whose reviewers
  sit on DIFFERENT sovereign nodes: a remote principal's approval, anchored by a witness record,
  is imported onto the obligation's home chain and counts as one distinct quorum voice.

FAIL-CLOSED rules:
  - The remote approval entry must be internally hash-consistent (its own recorded hash re-derives).
  - The witness record must validate structurally against the LOCAL chain (W1's validate_witness_ref)
    — i.e. the ceremony actually ran here, not just a claimed dict.
  - An import that fails either check RAISES and appends nothing (importing is a local constitutional
    act; a refused import leaves no approval residue).
  - The imported approval then passes the SAME guards as any local approval inside is_approved
    (AH-1, 2.1 mandate guard, W1 witness validation, 2.2 distinctness) — no privileged path.

CRYPTO SEAM (honest): remote-entry SIGNATURE verification is sealed-host (the seam's verify);
what runs here is hash/structure verification. The import records `remote_assurance` with the
honest sentinel — never a fake verified.
"""
from __future__ import annotations

from . import witness as _witness
from ._util import _hash


def import_remote_approval(local_ledger, remote_approval_entry: dict, witness_ref: dict) -> dict:
    """Fold a remote node's approval into the obligation's home chain as one quorum voice.

    `remote_approval_entry`: the approval entry as sealed on the REMOTE chain (dict incl. its hash).
    `witness_ref`: the W1 witness record anchoring the cross-node act (must exist on the local chain).
    """
    # 1. remote entry internal integrity (hash re-derives over its own fields) — fail-closed
    claimed = remote_approval_entry.get("hash")
    rederived = _hash({k: v for k, v in remote_approval_entry.items() if k != "hash"})
    if not claimed or claimed != rederived:
        raise ValueError("cross-node import refused: remote approval entry hash does not re-derive — fail-closed")
    if remote_approval_entry.get("type") != "approval" or not remote_approval_entry.get("approves"):
        raise ValueError("cross-node import refused: not an approval entry — fail-closed")
    # 2. the witness ceremony must have actually run on THIS chain (structure-verifiable locally;
    #    read through the public gateway per G3 — never the private _entries())
    if not _witness.validate_witness_ref(list(local_ledger.iter_entries()), witness_ref):
        raise ValueError("cross-node import refused: witness record absent/mismatched on the local chain — fail-closed")
    # 3. fold: an ordinary approval entry, marked imported, carrying its anchors + honest assurance.
    #    It earns quorum voice ONLY by passing the same is_approved guards as any local approval.
    from ..yield_organism import _sealed_host_seam as _seam  # lazy: package-cycle guard (witness.py idiom)
    entry = {
        "type": "approval",
        "id": f"imp_{remote_approval_entry['id']}",
        "approves": remote_approval_entry["approves"],
        "approved_by": remote_approval_entry.get("approved_by"),
        "disposition": remote_approval_entry.get("disposition", "approved"),
        "gate": remote_approval_entry.get("gate"),
        "imported": True,
        "remote_node": remote_approval_entry.get("principal_id"),
        "remote_entry_hash": claimed,
        "remote_assurance": _seam.UNVERIFIED,  # signature verify is sealed-host; never faked here
        "cross_mandate_auth": remote_approval_entry.get("cross_mandate_auth")
                              or {"authorized": True, "mandate": witness_ref.get("mandate"),
                                  "witness_ref": witness_ref},
        "held_mandates": remote_approval_entry.get("held_mandates"),
        "principal_id": local_ledger.principal_id,
    }
    entry = {k: v for k, v in entry.items() if v is not None}
    return local_ledger._append(entry)
