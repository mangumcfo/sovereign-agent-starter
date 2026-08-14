"""S7 V02 confidentiality shield — the sealed P5 Paillier composed through `_lazy_bp`, verify/combine
WITHOUT reveal (KM Seal 1176-INFINITY-RHO · Option A).

CS-bar (KM's three + the fences): round-trip owner-side · wrong-key refuse · unknown-kind still refuses ·
integrity behaviour byte-unchanged · no private key in any governed object · no node decrypt on this path
(the kernel never calls decrypt — see the grep in the deposit) · empty key / empty ciphertexts / empty
stack deny-by-default. No sealed-tree edit — the primitive stays in sealed P5; the kernel only composes it.
"""
import json

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.shields.protective import declare_shield, pass_shield_stack, ShieldError
from sovereign_agent._lazy_bp import generate_paillier_keys, encrypt, decrypt, add

_BITS = 128  # small keys keep the test fast; the shield's math is bit-length independent


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path))


def _encrypt_values(pub, values):
    return [encrypt(pub, v) for v in values]


def _fold(pub, cts):
    combined = cts[0]
    for c in cts[1:]:
        combined = add(pub, combined, c)
    return combined


def test_cs1_confidentiality_roundtrip_owner_side(tmp_path):
    """Declare binds the PUBLIC key + an encrypted total; the node clears from public material + the presented
    ciphertexts alone (no key, no reveal); the OWNER — only — decrypts the combined total to the plaintext sum."""
    reg = _reg(tmp_path)
    priv, pub = generate_paillier_keys(bit_length=_BITS)
    values = [10, 25, 7]
    cts = _encrypt_values(pub, values)
    total = _fold(pub, cts)
    shield = declare_shield(reg, "doc:conf1", "confidentiality", [], mandate="ownerA", author="ownerA",
                            source_ref="shield://doc:conf1", at="2026-08-14",
                            public_n=pub.n, encrypted_total=total)
    res = pass_shield_stack([shield], [], ciphertexts=cts)   # node verifies/combines WITHOUT decrypting
    assert res["cleared"] is True and res["kinds"] == ["confidentiality"]
    # owner-side ONLY (never the node): the declared total decrypts to the plaintext sum — combine-without-reveal is real
    assert decrypt(priv, total) == sum(values)


def test_cs2_wrong_key_refuses(tmp_path):
    """A shield bound to key A refuses ciphertexts produced under key B — verified without reveal, deny-by-default."""
    reg = _reg(tmp_path)
    _privA, pubA = generate_paillier_keys(bit_length=_BITS)
    _privB, pubB = generate_paillier_keys(bit_length=_BITS)
    a_cts = _encrypt_values(pubA, [3, 4])
    shield = declare_shield(reg, "doc:conf2", "confidentiality", [], mandate="ownerA", author="ownerA",
                            source_ref="shield://doc:conf2", at="t", public_n=pubA.n,
                            encrypted_total=_fold(pubA, a_cts))
    b_cts = _encrypt_values(pubB, [3, 4])   # right plaintexts, WRONG key
    with pytest.raises(ShieldError):
        pass_shield_stack([shield], [], ciphertexts=b_cts)


def test_cs3_unknown_kind_still_refuses(tmp_path):
    """Adding the confidentiality kind must NOT open the default — a truly unknown kind still refuses (deny-by-default)."""
    reg = _reg(tmp_path)
    bogus = reg.append("shield:doc:q:quantum", {"kind": "quantum", "resource": "doc:q"},
                       author="ownerA", source_ref="shield://doc:q", at="t", mandate="ownerA", kind="ratify")
    with pytest.raises(ShieldError):
        pass_shield_stack([bogus], [b"x"])


def test_cs6_empty_key_refuses(tmp_path):
    """Deny-by-default: a confidentiality shield with no bound public key is refused at declare."""
    reg = _reg(tmp_path)
    with pytest.raises(ShieldError):
        declare_shield(reg, "doc:c", "confidentiality", [], mandate="ownerA", author="ownerA",
                       source_ref="shield://doc:c", at="t", public_n=None)


def test_cs6_empty_ciphertexts_refuses(tmp_path):
    """Deny-by-default: nothing clears that presents no ciphertexts."""
    reg = _reg(tmp_path)
    _priv, pub = generate_paillier_keys(bit_length=_BITS)
    shield = declare_shield(reg, "doc:c2", "confidentiality", [], mandate="ownerA", author="ownerA",
                            source_ref="shield://doc:c2", at="t", public_n=pub.n)
    with pytest.raises(ShieldError):
        pass_shield_stack([shield], [], ciphertexts=None)


def test_cs5_no_private_key_in_governed_object(tmp_path):
    """No custody: the declared shield object carries only PUBLIC material — no private key field anywhere."""
    reg = _reg(tmp_path)
    priv, pub = generate_paillier_keys(bit_length=_BITS)
    shield = declare_shield(reg, "doc:c3", "confidentiality", [], mandate="ownerA", author="ownerA",
                            source_ref="shield://doc:c3", at="t", public_n=pub.n,
                            encrypted_total=_fold(pub, _encrypt_values(pub, [1, 2])))
    blob = json.dumps(shield)
    for secret in ('"private"', '"p":', '"q":', '"lam"', '"mu"', str(priv.p), str(priv.q), str(priv.lam)):
        assert secret not in blob, f"private material leaked: {secret}"
    # only the public modulus (+ optional total) are stored
    assert shield["payload"]["public_n"] == pub.n
    assert set(shield["payload"].keys()) <= {"kind", "resource", "public_n", "encrypted_total"}


def test_cs4_integrity_unchanged(tmp_path):
    """Regression: the integrity shield behaves byte-identically (declare + pass + tamper-refuse) after the add."""
    reg = _reg(tmp_path)
    s = declare_shield(reg, "doc:i", "integrity", [b"a", b"b"], mandate="ownerA", author="ownerA",
                       source_ref="shield://doc:i", at="t")
    assert pass_shield_stack([s], [b"a", b"b"])["layers"] == 1
    with pytest.raises(ShieldError):
        pass_shield_stack([s], [b"a", b"CHANGED"])
