# -*- coding: utf-8 -*-
"""Proof-first tests for keystore.node_keystore (D1: the self-held node key).

Kill-targets pinned:
- generate_node_key mints a secp256k1 keypair on THIS iron and persists it durably (0600); the private scalar
  never leaves the file (NodeKey carries only the public face);
- DURABLE across a REAL process restart — a separate process loads the persisted key, signs an act, and the act
  verifies against the same public identity (same fingerprint);
- sign_node_act signs with the self-held key; verify_node_act is PUBLIC-ONLY;
- FAIL-LOUD if absent — load/sign on a keystore with no key raise, never invent or stub a key;
- no custodian / escrow / cloud-KMS / recovery-authority / second-admission / seal-key field (KEYSTORE_BREACH_
  FIELDS) — no one holds the key for you, and it is NOT the press/seal key;
- bare-clone posture is honest (fail-loud on absent substrate — asserted by construction, not stubbed);
- the node fingerprint is exactly the keyholder identity the sealed S12 key epoch (open_key_epoch) consumes —
  D1 is the substrate, recovery composes S12 quorum on top (never inside D1).
"""
import json
import os
import subprocess
import sys

import pytest

from sovereign_agent.keystore import (
    NodeKey, generate_node_key, load_node_key, has_node_key,
    sign_node_act, verify_node_act, node_fingerprint,
    KEYSTORE_BREACH_FIELDS, KeystoreError,
)

AT = "2026-08-11T14:00:00Z"


def test_generate_holds_a_keypair_locally_and_persists_it(tmp_path):
    ks = str(tmp_path)
    assert has_node_key(ks, "node-a") is False
    nk = generate_node_key(ks, "node-a", at=AT)
    assert isinstance(nk, NodeKey) and nk.node_id == "node-a"
    assert len(nk.public_hex) == 128 and nk.sig_scheme == "ecdsa-secp256k1"
    assert has_node_key(ks, "node-a") is True                               # durable on disk
    path = os.path.join(ks, "node-a.nodekey.json")
    assert oct(os.stat(path).st_mode)[-3:] == "600"                         # operator-only file
    # the private scalar is NOT on the returned record (public face only)
    assert not hasattr(nk, "private_hex") and "private" not in vars(nk)


def test_sign_and_public_only_verify(tmp_path):
    ks = str(tmp_path)
    nk = generate_node_key(ks, "node-a", at=AT)
    sig = sign_node_act(ks, "node-a", b"node-act-1")
    assert verify_node_act(nk.public_hex, b"node-act-1", sig) is True       # public-only verify
    assert verify_node_act(nk.public_hex, b"tampered-act", sig) is False    # wrong payload fails
    other = generate_node_key(ks, "node-b", at=AT)
    assert verify_node_act(other.public_hex, b"node-act-1", sig) is False   # wrong identity fails


def test_durable_across_a_real_process_restart(tmp_path):
    ks = str(tmp_path)
    nk = generate_node_key(ks, "node-a", at=AT)
    # a genuinely SEPARATE process loads the persisted key and signs an act — proves cross-process/reboot durability
    code = (
        "import json;"
        "from sovereign_agent.keystore import load_node_key, sign_node_act;"
        f"nk=load_node_key({ks!r},'node-a');"
        f"sig=sign_node_act({ks!r},'node-a',b'act-after-restart');"
        "print(json.dumps({'pub':nk.public_hex,'fp':nk.fingerprint,'sig':sig}))"
    )
    env = dict(os.environ); env["PYTHONPATH"] = os.pathsep.join(sys.path)
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert out.returncode == 0, out.stderr
    res = json.loads(out.stdout.strip().splitlines()[-1])
    assert res["pub"] == nk.public_hex and res["fp"] == nk.fingerprint      # same identity after restart
    assert verify_node_act(nk.public_hex, b"act-after-restart", res["sig"]) is True  # post-restart act verifies


def test_fail_loud_when_absent(tmp_path):
    ks = str(tmp_path)
    with pytest.raises(KeystoreError):                                      # load a key that was never generated
        load_node_key(ks, "ghost")
    with pytest.raises(KeystoreError):                                      # sign with no key — never a stub
        sign_node_act(ks, "ghost", b"act")


def test_no_silent_overwrite(tmp_path):
    ks = str(tmp_path)
    a = generate_node_key(ks, "node-a", at=AT)
    with pytest.raises(KeystoreError):                                      # re-mint would orphan the identity
        generate_node_key(ks, "node-a", at=AT)
    b = generate_node_key(ks, "node-a", at=AT, overwrite=True)             # deliberate only
    assert b.public_hex != a.public_hex


def test_the_fence_refuses_custodian_kms_and_seal_key(tmp_path):
    ks = str(tmp_path)
    for bad in ("custodian", "escrow", "cloud_kms", "kms", "recovery_authority", "admission_authority"):
        with pytest.raises(KeystoreError):
            generate_node_key(ks, f"n-{bad}", at=AT, extra={bad: "acme"})
    for bad in ("seal_key", "press_key", "sealing_key"):                    # NOT the operator's seal key
        with pytest.raises(KeystoreError):
            generate_node_key(ks, f"n-{bad}", at=AT, extra={bad: "x"})
    nk = generate_node_key(ks, "node-a", at=AT)
    with pytest.raises(KeystoreError):
        sign_node_act(ks, "node-a", b"act", extra={"custodian": "acme"})
    assert {"custodian", "cloud_kms", "seal_key", "recovery_authority"} <= KEYSTORE_BREACH_FIELDS


def test_tamper_is_detected(tmp_path):
    ks = str(tmp_path)
    generate_node_key(ks, "node-a", at=AT)
    path = os.path.join(ks, "node-a.nodekey.json")
    rec = json.load(open(path))
    rec["private_hex"] = f"{(int(rec['private_hex'], 16) + 1):064x}"       # priv no longer derives stored pub
    json.dump(rec, open(path, "w"))
    with pytest.raises(KeystoreError):
        load_node_key(ks, "node-a")


def test_fingerprint_is_the_sealed_s12_keyholder_identity(tmp_path):
    # D1 is the substrate the sealed S12 recovery layer consumes: a node's fingerprint IS a keyholder identity.
    from sovereign_agent.estate.generational_transfer import open_key_epoch, family_quorum_recovery
    ks = str(tmp_path)
    a = generate_node_key(ks, "node-a", at=AT)
    b = generate_node_key(ks, "node-b", at=AT)
    assert node_fingerprint(a.public_hex) == a.fingerprint                  # stable, deterministic
    epoch = open_key_epoch("fam-1", 1, [a.fingerprint, b.fingerprint])      # S12 records D1 identities
    assert a.fingerprint in epoch.keyholders and b.fingerprint in epoch.keyholders
    # recovery composes the sealed S12 quorum ON TOP of D1 — D1 itself holds no recovery authority
    assert family_quorum_recovery(epoch, [a.fingerprint, b.fingerprint], quorum=2) is True
