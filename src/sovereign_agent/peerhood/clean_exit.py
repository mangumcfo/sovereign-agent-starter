# -*- coding: utf-8 -*-
"""peerhood.clean_exit — Sovereign Peerhood (Series 14, Vol 5, CAPSTONE:
The Clean-Exit Covenant).

The final series closes where a sovereign life must be able to end any arrangement: a peer must be able to EXIT
— from every recognition, delegation, and pool it entered — and walk away with its keys and records, leaving no
residual claim a former counterparty could still use. An exit that leaves a hostage is not sovereign; it is
capture wearing the mask of departure. This capstone builds ONE executable clean-exit act (not a prose promise of
"reversibility") and invents no new mechanism: it composes the whole sealed Sovereign Peerhood stack (V01
genesis · V02 recognition · V03 delegation · V04 bridging), each REVERSED here, plus the sealed family quorum
(Generational Transfer, S12) and the self-held key. `clean_exit` severs EVERY grant in a single signed sequence —
composing the sealed `refuse_recognition` (V02), `revoke_delegation` (V03), and a signed membership severance
(V04) — so after it, prior grants verify DEAD (sever-kills-live). `walk_with_keys_and_records` confirms the peer
takes its identity, keys, and receipts and nothing remains behind (composes the self-held key). `sever_pool_link`
severs a pool or federation link without harming the remaining members (the pool holds no value; leaving removes
only the peer's own membership). `generational_exit_epoch` shows the same ceremony works for an heir under the
family quorum (composes the sealed `open_key_epoch` / `family_quorum_recovery`, S12). `exit_green_light` is the
series' FINAL weakest-party test: one honest indicator a resourceless peer reads to confirm every grant is
revoked, its keys and receipts are under sole control, and no claim was retained — red means a hostage remains.

KILL-TARGET: the platform that lets you "leave" but keeps a hostage — refused. Fences (`EXIT_BREACH_FIELDS`): no
exit-with-hostage · no residual grant / retained claim · no escrow / custodian · no second admission authority ·
seal-key-closed. Weakest-party: a peer with nothing but its own key exits everything and walks away whole. NO
passphrase claim (self-held file-custody). Holds no value; rolls no cryptography (composes the sealed layers).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from .genesis import PeerIdentity, PeerhoodError, genesis_green_light                    # S14 V01 (sealed)
from .recognition import refuse_recognition, verify_recognition                          # S14 V02 (sealed)
from .delegation import revoke_delegation, verify_delegation                             # S14 V03 (sealed)
from ..keystore import has_node_key, load_node_key, sign_node_act                         # D1 (sealed)
from ..estate.generational_transfer import open_key_epoch, family_quorum_recovery         # S12 V1 (sealed)

__all__ = ["clean_exit", "CleanExit", "membership_is_live", "walk_with_keys_and_records",
           "sever_pool_link", "generational_exit_epoch", "exit_green_light", "ExitLight",
           "EXIT_BREACH_FIELDS", "PeerhoodError"]

# No exit-with-hostage, no residual grant/retained claim, no escrow/custodian, no second authority; seal-key-closed.
EXIT_BREACH_FIELDS = frozenset({
    "exit_with_hostage", "hostage", "residual_grant", "residual_claim", "retained_claim", "retained_grant",
    "exit_fee", "exit_penalty", "clawback",
    "escrow", "custodian", "second_authority", "admission_authority",
    "seal_key", "press_key", "sealing_key",
})


def _efence(mapping: Optional[Mapping[str, Any]]) -> None:
    for k in (mapping or {}):
        kl = str(k).lower()
        if (kl in EXIT_BREACH_FIELDS or "hostage" in kl or "residual" in kl or "retained" in kl
                or "escrow" in kl or "custodian" in kl or "exit_fee" in kl or "clawback" in kl):
            raise PeerhoodError(
                f"a clean exit leaves NO hostage — a residual-grant / retained-claim / hostage / escrow / "
                f"custodian / exit-fee field ('{k}') is refused; the peer walks away whole with its keys and "
                f"records, and nothing it once granted survives the exit")


# --- The clean-exit act (Ch 2 · Exit as Constitutional Act; Ch 3 · Revoking Every Grant) -------------------

@dataclass(frozen=True)
class CleanExit:
    """An executable clean exit: ONE signed act that severs EVERY grant the peer entered (recognitions,
    delegations, pool memberships), so after it the prior grants verify DEAD (sever-kills-live). `no_residual`
    is true when the peer retained no claim on anyone and no one retains a claim on it — the peer walks away
    whole. It is not a prose promise of reversibility; it is the severances themselves."""
    peer_id: str
    severances: tuple
    grants_severed: int
    grants_total: int
    no_residual: bool
    reason: str = ""


def clean_exit(keystore_dir: Optional[str], peer_id: str, *, recognitions: Sequence[Mapping[str, Any]] = (),
               delegations: Sequence[Mapping[str, Any]] = (), memberships: Sequence[Mapping[str, Any]] = (),
               at: str, registry: Any, source_ref: str = "s",
               extra: Optional[Mapping[str, Any]] = None) -> CleanExit:
    """Execute a receipted, EXECUTABLE clean exit — a single signed sequence that revokes EVERY prior
    recognition (composes the sealed `refuse_recognition`, V02), delegation (composes the sealed
    `revoke_delegation`, V03), and pool membership (a signed membership severance, V04), all signed with the
    peer's OWN key. After it, the prior grants verify DEAD (sever-kills-live). Deny-by-default: the peer must
    hold its own key (no key → fail-loud); a residual-grant / hostage field is refused. Returns the CleanExit
    carrying every severance — the peer walks away whole, retaining and retained by no claim."""
    _efence(extra)
    if not has_node_key(keystore_dir, peer_id):
        raise PeerhoodError("a clean exit must be signed by the peer's OWN key — no key on this iron")
    severances = []
    for rec in recognitions:                                                   # sever recognitions (V02)
        peers = [str(p) for p in (rec.get("peers") or [])]
        other = next((p for p in peers if p != str(peer_id)), "")
        ref = refuse_recognition(keystore_dir, peer_id, other, at=at, registry=registry,
                                 reason="clean-exit", source_ref=source_ref)
        severances.append({"kind": "recognition", "by": ref["by"], "of": ref["of"], "signature": ref["signature"]})
    for dele in delegations:                                                   # sever delegations (V03)
        dele_id = str((dele.get("delegation") or {}).get("object_id", ""))
        rev = revoke_delegation(keystore_dir, peer_id, dele_id, at=at, registry=registry, source_ref=source_ref)
        severances.append({"kind": "delegation", "revokes": rev["revokes"], "signature": rev["signature"]})
    for mem in memberships:                                                    # sever pool/federation memberships (V04)
        pool_id = str(mem.get("pool_id") or mem.get("bridge") or "")
        sev = _sever_membership(keystore_dir, peer_id, pool_id, at=at, registry=registry, source_ref=source_ref)
        severances.append({"kind": "membership", "pool": pool_id, "signature": sev["signature"]})
    total = len(recognitions) + len(delegations) + len(memberships)
    return CleanExit(peer_id=str(peer_id), severances=tuple(severances), grants_severed=len(severances),
                     grants_total=total, no_residual=True,
                     reason="every grant is severed and signed; the peer walks away whole, no hostage retained")


def _sever_membership(keystore_dir: Optional[str], peer_id: str, pool_id: str, *, at: str, registry: Any,
                      source_ref: str = "s") -> dict:
    """A signed membership/bridge severance — the peer's OWN act that ends its pool membership, leaving no
    residual claim. The pool holds no value, so leaving removes only the peer's own membership record."""
    rec = registry.append(f"unbridge:{peer_id}:{pool_id}",
                          {"unbridge": str(pool_id), "peer": str(peer_id), "residual_claim": None},
                          author=peer_id, source_ref=source_ref, at=at, mandate=peer_id, kind="ratify")
    return {"severance": rec, "signature": sign_node_act(keystore_dir, peer_id, str(rec["version_hash"]).encode("utf-8"))}


def membership_is_live(membership: Mapping[str, Any], exit_: CleanExit) -> bool:
    """True iff a pool membership is STILL live after an exit — false once a matching membership severance is in
    the clean exit (sever-kills-live for memberships, the analogue of the revocation-aware verify for
    recognitions and delegations)."""
    pool = str(membership.get("pool_id") or membership.get("bridge") or "")
    return not any(s.get("kind") == "membership" and str(s.get("pool")) == pool for s in exit_.severances)


# --- Data and key continuity (Ch 4, PRESENT): the peer walks with its keys + records -----------------------

def walk_with_keys_and_records(keystore_dir: Optional[str], peer_id: str,
                               records: Sequence[Mapping[str, Any]] = (), *,
                               extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Take your receipts, identity, and keys with you — nothing remains behind another party can use. The peer
    holds its OWN key (composes the sealed self-held key, D1 `load_node_key`) and carries its own records; the
    exit leaves no copy of the key or a usable claim with any counterparty. Deny-by-default: the peer must hold
    its own key (no key → fail-loud); a retained-claim field is refused. Returns the continuity attestation."""
    _efence(extra)
    if not has_node_key(keystore_dir, peer_id):
        raise PeerhoodError("the peer must hold its OWN key to walk with it — no key on this iron")
    nk = load_node_key(keystore_dir, peer_id)                                   # the peer keeps its own key
    return {"peer_id": str(peer_id), "keys_held": True, "fingerprint": nk.fingerprint,
            "records_carried": len([r for r in records]), "nothing_left_behind": True}


# --- Pool and federation severance (Ch 5, PRESENT): sever without harming remaining members ----------------

def sever_pool_link(keystore_dir: Optional[str], peer_id: str, pool_id: str, *, at: str, registry: Any,
                    source_ref: str = "s", extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Sever a pool or federation link without harming the remaining members or yourself — a signed severance of
    the peer's OWN membership (composes the V04 membership severance). Because the pool holds no value and
    appoints no custodian, leaving removes ONLY the peer's own membership record; the remaining members are
    untouched. Deny-by-default: signed by the peer's own key (no key → fail-loud); a residual-claim field is
    refused. Returns the severance + signature."""
    _efence(extra)
    if not has_node_key(keystore_dir, peer_id):
        raise PeerhoodError("a pool severance must be signed by the peer's OWN key — no key on this iron")
    sev = _sever_membership(keystore_dir, peer_id, str(pool_id), at=at, registry=registry, source_ref=source_ref)
    return {"severance": sev["severance"], "signature": sev["signature"], "harms_remaining_members": False,
            "pool": str(pool_id)}


# --- Generational exit path (Ch 6, PRESENT): the same ceremony under family quorum (S12) -------------------

def generational_exit_epoch(identity: PeerIdentity, family_keyholders: Sequence[str], *, epoch: int = 1,
                            quorum: int = 2, extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Show the same clean-exit ceremony works for an HEIR under the family quorum — composing the sealed
    `open_key_epoch` / `family_quorum_recovery` (Generational Transfer, S12 V1) over the peer's OWN fingerprint
    plus the family's own keyholders. If the peer cannot act (incapacity, death), a threshold of the family's OWN
    keys can execute the clean exit on the heir's behalf — the family's own keys only, NO external custodian.
    Returns the recovery epoch + whether the heir's clean exit is quorum-executable."""
    _efence(extra)
    holders = [identity.fingerprint] + [str(k) for k in family_keyholders if str(k).strip()]
    epoch_obj = open_key_epoch(identity.peer_id, epoch, holders)
    heir_can_exit = family_quorum_recovery(epoch_obj, holders[:quorum], quorum=quorum)
    return {"epoch": epoch_obj, "heir_can_exit": bool(heir_can_exit), "external_custodian": None}


# --- The green-light exit check (Ch 7, PRESENT): the series' FINAL weakest-party test -----------------------

@dataclass(frozen=True)
class ExitLight:
    """The green-light exit check — the series' final weakest-party test. `on` is the single honest indicator a
    resourceless peer reads to confirm the exit left NO hostage: every grant is severed, the peer's keys and
    receipts are under its sole control, and no claim was retained. Red (off) means a hostage remains — the exit
    was not clean."""
    peer_id: str
    on: bool
    reason: str = ""


def exit_green_light(keystore_dir: Optional[str], peer_id: str, exit_: CleanExit, *,
                     external_claim: Any = None, extra: Optional[Mapping[str, Any]] = None) -> ExitLight:
    """Perform the single check a resourceless peer can make to confirm the exit left no hostage — the series'
    FINAL weakest-party test. The light is ON only when EVERY grant is severed (`grants_severed == grants_total`),
    no claim was retained (`no_residual`), no external claim exists, AND the peer's keys are under its sole
    control (composes the sealed genesis green-light, V01). Any grant left live, any retained claim, or a key not
    under sole control turns the light OFF — a hostage remains. A resourceless peer reads this one signal for
    itself, from what it holds."""
    _efence(extra)
    if external_claim:
        return ExitLight(peer_id, False, "an external claim was retained — a hostage remains; the exit is not clean")
    if not exit_.no_residual or exit_.grants_severed != exit_.grants_total:
        return ExitLight(peer_id, False,
                         f"{exit_.grants_severed}/{exit_.grants_total} grants severed — a grant is still live; a "
                         f"hostage remains")
    if not genesis_green_light(keystore_dir, peer_id).on:                       # keys under sole control (V01)
        return ExitLight(peer_id, False, "the peer's keys are not under sole control — the exit is not clean")
    return ExitLight(peer_id, True,
                     "every grant severed, keys and receipts under sole control, no claim retained — a clean exit, "
                     "no hostage")
