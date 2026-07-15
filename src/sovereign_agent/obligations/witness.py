"""3-Receipt Cross-Mandate Witness Ceremony — S2 closure wave slice W1.

DOCTRINE (S2-V4 *Federated Sovereignty* Ch 2 §221-227; spec artifacts/specs/cross_mandate_witness_v0.1.yaml):
  "A cross-mandate operation is a distinct constitutional act producing THREE receipts: the
   originating receipt (mandate A's chain), the receiving receipt (mandate B's chain), and the
   cross-mandate witness sealed at BOTH chains."

This module is the ceremony. Slice 2.1's guard enforced the authorization GATE with a bare declared
`cross_mandate_auth`; the ceremony upgrades that authorization to a REPLAY-VERIFIABLE witness record:
projection.is_approved now structurally validates a witness-backed auth against the local chain
(the xm_witness entry must exist and its hashes must match) — fail-closed. A bare declared auth
(no witness_ref) remains accepted as the 2.1 floor, unchanged and backward-compatible.

CRYPTO SEAM (honest): witness SEALING routes through the one sealed-host adapter
(yield_organism/_sealed_host_seam.py) — `seal_status` is SEALED_HOST_PENDING in every dev env,
never a fake signature. What is verifiable HERE is STRUCTURE (entries exist, hashes chain, both
sides reference each other); what is verifiable only on the sealed host is the SEAL. The two
verdicts are kept separate (economic_export.verify_bundle idiom).
"""
from __future__ import annotations

from ._util import _hash

# NOTE: the sealed-host seam (yield_organism/_sealed_host_seam.py — the ONE crypto adapter, the node's
# lane) is imported LAZILY inside witness_seal(): a module-level import would cycle
# (obligations.projection → witness → yield_organism.__init__ → value_flow → obligations.ledger).


def originate(ledger, obligation_id: str, target_mandate: str, initiated_by: str) -> dict:
    """Receipt 1 — the originating entry on mandate A's chain (the obligation's home chain)."""
    ob = ledger._get(obligation_id)
    if not ob:
        raise KeyError(f"unknown obligation '{obligation_id}' — cannot originate a cross-mandate act")
    return ledger._append({
        "type": "xm_originate", "id": f"xmo_{obligation_id}", "obligation": obligation_id,
        "obligation_hash": ob.get("hash"), "source_mandate": ob.get("mandate"),
        "target_mandate": target_mandate, "initiated_by": initiated_by,
        "principal_id": ledger.principal_id,
    })


def receive(ledger, originating_entry: dict) -> dict:
    """Receipt 2 — the receiving entry on mandate B's chain, anchored to the originating hash."""
    if originating_entry.get("type") != "xm_originate" or not originating_entry.get("hash"):
        raise ValueError("receive() requires a hashed xm_originate entry — fail-closed")
    return ledger._append({
        "type": "xm_receive", "id": f"xmr_{originating_entry['obligation']}",
        "originating_hash": originating_entry["hash"], "obligation": originating_entry["obligation"],
        "accepted_by": ledger.principal_id, "principal_id": ledger.principal_id,
    })


def witness_seal(ledger_a, ledger_b, originating_entry: dict, receiving_entry: dict) -> dict:
    """Receipt 3 — the witness record, sealed (sealed-host seam) and appended to BOTH chains.

    Returns the witness record (carrying both anchor hashes + the honest seal status) for use as
    `cross_mandate_auth={"authorized": True, "mandate": M, "witness_ref": record}` at approve().
    """
    if receiving_entry.get("originating_hash") != originating_entry.get("hash"):
        raise ValueError("witness refused: receiving entry does not anchor the originating entry — fail-closed")
    record = {
        "obligation": originating_entry["obligation"],
        "mandate": originating_entry["target_mandate"],
        "originating_hash": originating_entry["hash"],
        "receiving_hash": receiving_entry["hash"],
        "witness_id": _hash({"o": originating_entry["hash"], "r": receiving_entry["hash"]})[:16],
    }
    # SEALED-HOST-SEAM: witness sealing — sentinel in dev (never a fake signature); the node wires real sign().
    from ..yield_organism import _sealed_host_seam as _seam  # lazy: avoids the package import cycle
    sealed = _seam.sign_value_flow(record)
    record["seal_status"] = sealed["signature_status"]
    for led in (ledger_a, ledger_b):
        led._append({"type": "xm_witness", "id": f"xmw_{record['witness_id']}", **record,
                     "principal_id": led.principal_id})
    return record


def validate_witness_ref(entries: list[dict], witness_ref: dict) -> bool:
    """PURE structural validation of a witness-backed authorization against ONE chain's entries.

    True iff an xm_witness entry exists whose witness_id + both anchor hashes match the ref.
    This is the replay-verifiable STRUCTURE check (runs anywhere); the SEAL check is sealed-host
    (seal_status carries the honest sentinel until then). Fail-closed on any mismatch/absence.
    """
    if not isinstance(witness_ref, dict):
        return False
    for e in entries:
        if (e.get("type") == "xm_witness"
                and e.get("witness_id") == witness_ref.get("witness_id")
                and e.get("originating_hash") == witness_ref.get("originating_hash")
                and e.get("receiving_hash") == witness_ref.get("receiving_hash")):
            return True
    return False
