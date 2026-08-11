# -*- coding: utf-8 -*-
"""keystore.node_keystore — D1: the self-held node key (the missing key-custody primitive).

A sovereign peer must hold its OWN cryptographic identity on its OWN iron: generate a keypair locally, keep it
durable across process and reboot in a keystore file the operator controls, sign the node's acts with it, and
verify any node's acts against its public identity — with **no custodian, no recovery authority, no cloud KMS,
and no confusion with the press/seal key**. This is the substrate the sealed generational-recovery layer
(Generational Transfer, S12 — `open_key_epoch` / `family_quorum_recovery`) consumes later: a node's stable
`fingerprint` is exactly the keyholder identity an epoch records. D1 itself holds no recovery authority; recovery
composes the sealed S12 quorum on top, never inside this primitive.

Kill-targets, refused in code (`KEYSTORE_BREACH_FIELDS`): a custodian / escrow / recovery-authority that holds
the key for you; a cloud KMS or key-backup service off your iron; a second admission authority; and any
press/seal-key field (the node key is NOT the operator's seal key — separate key, separate purpose, separate
env). Fail-loud law: a key that is ABSENT is refused loudly — `load`/`sign` never invent or stub a key. Bare-
clone / pure-seal posture: if the sealed crypto substrate is unavailable, generation and signing FAIL LOUD with
a named error — an honest skip/fail, never a silent stub success.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from typing import Any, Mapping, Optional

__all__ = ["NodeKey", "generate_node_key", "load_node_key", "has_node_key",
           "sign_node_act", "verify_node_act", "node_fingerprint",
           "KEYSTORE_BREACH_FIELDS", "KeystoreError"]

SIG_SCHEME = "ecdsa-secp256k1"

# No custodian, no recovery authority, no cloud KMS, no second admission authority, no seal-key confusion.
KEYSTORE_BREACH_FIELDS = frozenset({
    "custodian", "escrow", "recovery_authority", "recovery_agent", "recovery_engine",
    "cloud_kms", "kms", "key_backup_service", "backup_service", "hsm_service",
    "admission_authority", "second_authority", "attestation_authority",
    "seal_key", "press_key", "sealing_key",
})


class KeystoreError(ValueError):
    """A node-keystore act was refused (absent key, fenced field, or absent crypto substrate) — fail-loud."""


@dataclass(frozen=True)
class NodeKey:
    """A node's self-held cryptographic identity — its PUBLIC face only. The private scalar never leaves the
    keystore file on the operator's iron; this record carries the public key and a stable fingerprint that
    other layers (e.g. the sealed S12 key epoch) record as the node's keyholder identity."""
    node_id: str
    public_hex: str          # 128-hex uncompressed public point (x||y)
    fingerprint: str         # stable short identity = sha256(public bytes)[:16]
    created_at: str
    sig_scheme: str = SIG_SCHEME


# --- crypto substrate (sealed breathline_primitives) — resolved fail-loud, never stubbed -------------------

def _curve():
    try:
        from .._lazy_bp import secp256k1_curve
        return secp256k1_curve() if callable(secp256k1_curve) else secp256k1_curve
    except Exception as e:                                                              # bare-clone / pure-seal
        raise KeystoreError(
            "sealed crypto substrate (breathline_primitives secp256k1) is unavailable — cannot generate or use "
            "a node key on a bare clone; this is an honest fail, not a stubbed key") from e


def _keygen():
    try:
        from .._lazy_bp import generate_keypair
        kp = generate_keypair()
        return int(kp.private_key), (int(kp.public_key[0]), int(kp.public_key[1]))
    except KeystoreError:
        raise
    except Exception as e:
        raise KeystoreError(
            "sealed crypto keygen (breathline_primitives generate_keypair) is unavailable — cannot mint a node "
            "key on a bare clone; honest fail, not a stub") from e


def _pub_hex(pub) -> str:
    return f"{pub[0]:064x}{pub[1]:064x}"


def _pub_from_priv(priv: int) -> tuple:
    c = _curve()
    p = priv % c.n
    if p == 0:
        raise KeystoreError("node key reduces to 0 mod n (degenerate scalar) — refused; regenerate the key")
    return c.mul(p)


def node_fingerprint(public_hex: str) -> str:
    """A node's stable short identity — sha256 of its public key, first 16 hex. This is the keyholder string the
    sealed S12 key epoch records; the same node key always yields the same fingerprint."""
    if not str(public_hex).strip():
        raise KeystoreError("a fingerprint needs a public key")
    return hashlib.sha256(bytes.fromhex(public_hex)).hexdigest()[:16]


def _kfence(mapping: Optional[Mapping[str, Any]]) -> None:
    for k in (mapping or {}):
        kl = str(k).lower()
        if kl in KEYSTORE_BREACH_FIELDS or "custodian" in kl or "escrow" in kl or "kms" in kl:
            raise KeystoreError(
                f"a node key is self-held on the peer's own iron — a custodian / escrow / cloud-KMS / recovery-"
                f"authority / seal-key field ('{k}') is refused; no one holds this key for you, and it is not "
                f"the press/seal key")


# --- keystore paths (on the operator's own iron) ----------------------------------------------------------

def _resolve_dir(keystore_dir: Optional[str]) -> str:
    d = keystore_dir or os.environ.get("NODE_KEYSTORE_DIR")
    if not d:
        raise KeystoreError(
            "no keystore directory — pass keystore_dir or set NODE_KEYSTORE_DIR; the node key lives on disk "
            "under the operator's control, never a silent default")
    return d


def _key_path(keystore_dir: Optional[str], node_id: str) -> str:
    nid = str(node_id).strip()
    if not nid or "/" in nid or nid in (".", ".."):
        raise KeystoreError("a node key needs a simple node_id (no path separators)")
    return os.path.join(_resolve_dir(keystore_dir), nid + ".nodekey.json")


def has_node_key(keystore_dir: Optional[str], node_id: str) -> bool:
    """True iff a durable node key is present on this iron for node_id (survives process/reboot)."""
    try:
        return os.path.exists(_key_path(keystore_dir, node_id))
    except KeystoreError:
        return False


# --- generate / load / sign / verify ----------------------------------------------------------------------

def generate_node_key(keystore_dir: Optional[str], node_id: str, *, at: str,
                      overwrite: bool = False, extra: Optional[Mapping[str, Any]] = None) -> NodeKey:
    """Generate a fresh secp256k1 keypair on THIS iron and persist it durably to the keystore (0600), under the
    operator's control. Returns the node's public identity (`NodeKey`); the private scalar is written only to the
    keystore file and never returned. Deny-by-default: refuses to overwrite an existing key unless overwrite=True
    (a silent re-mint would orphan the node's identity); a custodian/escrow/KMS/seal-key field is refused; fails
    loud if the sealed crypto substrate is absent (bare clone) rather than stubbing a key."""
    _kfence(extra)
    path = _key_path(keystore_dir, node_id)
    if os.path.exists(path) and not overwrite:
        raise KeystoreError(
            f"a node key already exists for '{node_id}' — refusing to overwrite (a re-mint would orphan the "
            f"node's identity); pass overwrite=True only deliberately")
    priv, pub = _keygen()                                                              # fail-loud on bare clone
    c = _curve()
    if priv % c.n == 0:
        raise KeystoreError("generated a degenerate key (0 mod n) — refused; regenerate")
    pub_hex = _pub_hex(pub)
    rec = {"node_id": str(node_id), "sig_scheme": SIG_SCHEME, "created_at": str(at),
           "private_hex": f"{priv:064x}", "public_hex": pub_hex}
    os.makedirs(_resolve_dir(keystore_dir), exist_ok=True)
    # atomic write with 0600 — the operator's own file on the operator's own iron
    fd, tmp = tempfile.mkstemp(dir=_resolve_dir(keystore_dir), suffix=".tmp")
    try:
        os.write(fd, json.dumps(rec, sort_keys=True).encode("utf-8"))
        os.close(fd)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    os.chmod(path, 0o600)
    return NodeKey(node_id=str(node_id), public_hex=pub_hex, fingerprint=node_fingerprint(pub_hex),
                   created_at=str(at))


def _read_priv(keystore_dir: Optional[str], node_id: str) -> tuple:
    """Load (priv:int, public_hex:str) from the keystore, fail-loud if ABSENT or tampered."""
    path = _key_path(keystore_dir, node_id)
    if not os.path.exists(path):
        raise KeystoreError(
            f"no node key on this iron for '{node_id}' — the key is ABSENT; a sovereign act requires a self-held "
            f"key (generate one first). This is a fail-loud refusal, never a stubbed identity")
    with open(path, "r", encoding="utf-8") as f:
        rec = json.load(f)
    priv = int(str(rec["private_hex"]), 16)
    stored_pub = str(rec["public_hex"])
    if _pub_hex(_pub_from_priv(priv)) != stored_pub:                                    # integrity: priv derives pub
        raise KeystoreError(f"node key for '{node_id}' is tampered — its private scalar does not derive its "
                            f"stored public key; refused")
    return priv, stored_pub


def load_node_key(keystore_dir: Optional[str], node_id: str) -> NodeKey:
    """Load the node's PUBLIC identity from the durable keystore — the same public key and fingerprint across
    process restarts and reboots. Fail-loud if the key is absent (never invents one)."""
    _, pub_hex = _read_priv(keystore_dir, node_id)
    path = _key_path(keystore_dir, node_id)
    with open(path, "r", encoding="utf-8") as f:
        created = str(json.load(f).get("created_at", ""))
    return NodeKey(node_id=str(node_id), public_hex=pub_hex, fingerprint=node_fingerprint(pub_hex),
                   created_at=created)


def sign_node_act(keystore_dir: Optional[str], node_id: str, payload: bytes, *,
                  extra: Optional[Mapping[str, Any]] = None) -> str:
    """Sign a node act with the node's OWN self-held key, returning the signature as hex. Fail-loud if the key is
    absent; refuses a custodian/escrow/KMS/seal-key field; fails loud if the crypto substrate is absent."""
    _kfence(extra)
    if not isinstance(payload, (bytes, bytearray)):
        raise KeystoreError("a node act must be signed over bytes")
    priv, _ = _read_priv(keystore_dir, node_id)
    try:
        from .._lazy_bp import sign as _p1_sign
        return _p1_sign(priv, bytes(payload)).to_hex()
    except KeystoreError:
        raise
    except Exception as e:
        raise KeystoreError("sealed crypto signer is unavailable — cannot sign a node act on a bare clone; "
                            "honest fail, not a stub signature") from e


def verify_node_act(public_hex: str, payload: bytes, sig_hex: str) -> bool:
    """Verify a node act PUBLIC-ONLY — against the node's public identity, no secret needed. Returns bool; any
    substrate/parse failure verifies as False (never raises a truthy stub)."""
    try:
        from .._lazy_bp import verify as _p1_verify
        from breathline_primitives.layer1 import ECDSASignature
        pub = (int(public_hex[:64], 16), int(public_hex[64:128], 16))
        return bool(_p1_verify(pub, bytes(payload), ECDSASignature.from_hex(sig_hex)))
    except Exception:
        return False
