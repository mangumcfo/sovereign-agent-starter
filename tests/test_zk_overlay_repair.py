"""CI tests for the B25 P5 ZK repair (overlay v1.0.2) + overlay fail-loud integrity.

These are the construct-and-execute tests that would have caught the inter-layer defect the pure seal
shipped with: `ZKProofs` was authored against a `Point` class L1 never sealed, so it did not even
construct. Under the authorized v1.0.2 overlay, Pedersen + Schnorr execute; range stays HELD.

Also pins the overlay-loader integrity KM required: authorized-mode-with-missing-overlay FAILS LOUD
(the source label can never outrun what actually loaded), and the sealed bytes are byte-exact.
"""
import sys
import hashlib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
L1 = SRC / "primitives" / "sealed" / "layer_1_root"
L5_SEALED = SRC / "primitives" / "sealed" / "layer_5_shields"
ZK_OVERLAY = SRC / "overlays" / "v1.0.2-zk-repair"
ZK_OVERLAY_V103 = SRC / "overlays" / "v1.0.3-zk-range"
MERKLE_OVERLAY = SRC / "overlays" / "v1.0.1-merkle-repair"
TARBALL = SRC / "artifacts" / "P1-P5_SEALED_2026-01-12_0810UTC.tar.gz"
_SEALED_TARBALL_SHA16 = "4abea5c63faf341a"  # original Breath-25 P1-P5 seal


def _load_ZKProofs(from_overlay: bool):
    """Import `ZKProofs` from either the v1.0.2 overlay or the pure sealed layer, isolated from any
    cached copy. L1 is always on the path (point arithmetic lives there in both cases)."""
    for m in ("zk_proofs", "point_ops", "finite_field", "keygen", "sign", "verify"):
        sys.modules.pop(m, None)
    head = str(ZK_OVERLAY) if from_overlay else str(L5_SEALED)
    saved = list(sys.path)
    sys.path.insert(0, str(L1))
    sys.path.insert(0, head)
    try:
        import zk_proofs  # noqa: PLC0415
        return zk_proofs.ZKProofs
    finally:
        sys.path[:] = saved
        for m in ("zk_proofs", "point_ops", "finite_field", "keygen", "sign", "verify"):
            sys.modules.pop(m, None)


def _curve():
    saved = list(sys.path)
    sys.path.insert(0, str(L1))
    try:
        sys.modules.pop("point_ops", None)
        from point_ops import secp256k1  # noqa: PLC0415
        return secp256k1()
    finally:
        sys.path[:] = saved
        sys.modules.pop("point_ops", None)


# ---- the defect, and that the overlay fixes it --------------------------------------------------

def test_pure_seal_zk_is_non_constructible_HELD():
    """The pure sealed ZKProofs must NOT construct — this is the shipped defect the overlay repairs.
    (Had this test existed in the seal's CI, the inter-layer drift would have been caught then.)"""
    ZK = _load_ZKProofs(from_overlay=False)
    with pytest.raises((AttributeError, TypeError)):
        ZK("secp256k1")


def test_zk_overlay_constructs():
    ZK = _load_ZKProofs(from_overlay=True)
    zk = ZK("secp256k1")
    c = _curve()
    assert c.is_on_curve(zk.G)
    assert c.is_on_curve(zk.H)
    assert zk.H != zk.G


def test_zk_pedersen_additively_homomorphic():
    ZK = _load_ZKProofs(from_overlay=True)
    zk = ZK("secp256k1")
    c = _curve()
    C1, _ = zk.pedersen_commitment(42, 111)
    C2, _ = zk.pedersen_commitment(58, 222)
    Cdirect, _ = zk.pedersen_commitment(100, 333)  # 42+58, 111+222
    assert c.is_on_curve(C1)
    assert c.add(C1, C2) == Cdirect  # commit(v1,r1) + commit(v2,r2) == commit(v1+v2, r1+r2)


def test_zk_schnorr_roundtrip_and_rejects():
    ZK = _load_ZKProofs(from_overlay=True)
    zk = ZK("secp256k1")
    c = _curve()
    priv = 0xDEADBEEF % zk.n
    pub = c.mul(priv, zk.G)
    sig = zk.schnorr_sign(b"verified-flow", priv)
    assert zk.schnorr_verify(b"verified-flow", sig, pub) is True
    assert zk.schnorr_verify(b"TAMPERED", sig, pub) is False
    assert zk.schnorr_verify(b"verified-flow", sig, c.mul(priv + 1, zk.G)) is False


def test_zk_range_is_HELD():
    """Range stays explicitly NotImplemented — pins HELD so it can never be silently assumed done."""
    ZK = _load_ZKProofs(from_overlay=True)
    zk = ZK("secp256k1")
    C, r = zk.pedersen_commitment(5, 77)
    with pytest.raises(NotImplementedError):
        zk.range_proof(5, C, r)


# ---- overlay-loader integrity (fail-loud + label-match) -----------------------------------------

def test_setup_paths_fail_loud_on_missing_overlay(tmp_path, monkeypatch):
    """Authorized mode + missing overlay dir must RAISE — never silently load the sealed original
    under an authorized label (KM fail-loud mandate)."""
    import breathline_primitives as bp  # noqa: PLC0415
    monkeypatch.setenv("BREATHLINE_ZK_MODE", "authorized-v1.0.2")
    (tmp_path / "primitives" / "sealed").mkdir(parents=True)  # sealed present, overlays/ absent
    with pytest.raises(RuntimeError, match="FAIL-LOUD"):
        bp.active_overlays(root=tmp_path)


def test_setup_paths_no_overlay_when_unset(tmp_path, monkeypatch):
    import breathline_primitives as bp  # noqa: PLC0415
    monkeypatch.delenv("BREATHLINE_ZK_MODE", raising=False)
    monkeypatch.delenv("BREATHLINE_MERKLE_MODE", raising=False)
    assert bp.active_overlays(root=tmp_path) == []  # nothing opted in → no raise, no overlay


def test_overlay_label_matches_what_loads(monkeypatch):
    """The label must match what loaded: authorized → the authorized label (the real overlay exists),
    unset → the pure-seal label."""
    import breathline_primitives as bp  # noqa: PLC0415
    monkeypatch.setenv("BREATHLINE_ZK_MODE", "authorized-v1.0.2")
    assert bp.overlay_label("BREATHLINE_ZK_MODE").startswith("authorized-v1.0.2")
    monkeypatch.setenv("BREATHLINE_ZK_MODE", "authorized-v1.0.3")
    assert bp.overlay_label("BREATHLINE_ZK_MODE").startswith("authorized-v1.0.3")
    monkeypatch.delenv("BREATHLINE_ZK_MODE", raising=False)
    assert "sealed-v1.0" in bp.overlay_label("BREATHLINE_ZK_MODE")


# ---- overlays vendored + sealed bytes byte-exact ------------------------------------------------

def test_zk_overlay_vendored():
    for f in ("zk_proofs.py", "AUTHORIZATION.txt", "PATCH_MANIFEST.txt"):
        assert (ZK_OVERLAY / f).is_file(), f"missing ZK overlay file {f}"


def test_merkle_overlay_vendored():
    for f in ("merkle_tree.py", "AUTHORIZATION.txt", "PATCH_MANIFEST.txt"):
        assert (MERKLE_OVERLAY / f).is_file(), f"missing Merkle overlay file {f}"


def test_sealed_tarball_byte_exact():
    """The original P1-P5 seal is byte-exact — overlays never touch the sealed bytes."""
    assert TARBALL.is_file()
    sha16 = hashlib.sha256(TARBALL.read_bytes()).hexdigest()[:16]
    assert sha16 == _SEALED_TARBALL_SHA16


# ---- W1: range proof (v1.0.3) — completeness + mandatory soundness ------------------------------

def _load_ZK_v103():
    for m in ("zk_proofs", "point_ops", "finite_field", "keygen", "sign", "verify"):
        sys.modules.pop(m, None)
    saved = list(sys.path)
    sys.path.insert(0, str(L1))
    sys.path.insert(0, str(ZK_OVERLAY_V103))
    try:
        import zk_proofs  # noqa: PLC0415
        return zk_proofs.ZKProofs
    finally:
        sys.path[:] = saved
        for m in ("zk_proofs", "point_ops", "finite_field", "keygen", "sign", "verify"):
            sys.modules.pop(m, None)


def test_range_completeness_and_edges():
    zk = _load_ZK_v103()("secp256k1")
    for v in (0, 1, 100, 255):
        C, r = zk.pedersen_commitment(v, 424242 + v)
        pf = zk.range_proof(v, C, r, bits=8)
        assert zk.verify_range_proof(C, pf) is True, f"in-range v={v} must verify"


def test_range_out_of_range_prover_refuses():
    zk = _load_ZK_v103()("secp256k1")
    C, r = zk.pedersen_commitment(256, 7)
    with pytest.raises(ValueError):  # no honest range proof exists for 256 in [0,256)
        zk.range_proof(256, C, r, bits=8)


def test_range_soundness_rejections():
    import copy
    zk = _load_ZK_v103()("secp256k1")
    v, r = 100, 424242
    C, _ = zk.pedersen_commitment(v, r)
    pf = zk.range_proof(v, C, r, bits=8)
    # wrong commitment
    Cother, _ = zk.pedersen_commitment(101, r)
    assert zk.verify_range_proof(Cother, pf) is False
    # tampered bit-commitment
    t1 = copy.deepcopy(pf); t1["bit_commitments"][0] = zk.curve.mul(2, zk.G)
    assert zk.verify_range_proof(C, t1) is False
    # tampered OR-proof response
    t2 = copy.deepcopy(pf); t2["bit_proofs"][3]["s0"] = (t2["bit_proofs"][3]["s0"] + 1) % zk.n
    assert zk.verify_range_proof(C, t2) is False
    # wrong declared bit-width (a bits=9 proof must not verify as bits=8)
    C9, r9 = zk.pedersen_commitment(300, 7)
    pf9 = zk.range_proof(300, C9, 7, bits=9)
    assert zk.verify_range_proof(C9, pf9) is True
    assert zk.verify_range_proof(C9, pf9, bits=8) is False


def test_range_threshold_form():
    """v >= m proven as (v-m) in [0,2^bits) on C - m*G (the s5_38/s5_39 clears-minimum clause)."""
    zk = _load_ZK_v103()("secp256k1")
    v, m, r = 120, 100, 55
    C, _ = zk.pedersen_commitment(v, r)
    Cdiff = zk.curve.add(C, zk.curve.neg(zk.curve.mul(m, zk.G)))  # commits to (v-m) with same r
    pf = zk.range_proof(v - m, Cdiff, r, bits=8)
    assert zk.verify_range_proof(Cdiff, pf) is True   # 120 >= 100 clears
    # a below-threshold value cannot honestly prove the difference is in range
    with pytest.raises(ValueError):
        zk.range_proof(90 - 100, zk.pedersen_commitment(90 - 100, r)[0], r, bits=8)


# ---- W5: Paillier is PRESENT (retracts the false decrypt-defect flag) ---------------------------

def test_paillier_present_roundtrip_and_homomorphic():
    """Paillier encrypt/decrypt + additive-homomorphic works on the pure seal — the earlier
    'decrypt fails' was a caller-side (private, public) unpack swap, not a substrate defect."""
    import importlib
    bp = importlib.import_module("breathline_primitives")
    priv, pub = bp.generate_paillier_keys(bit_length=256)   # documented order: (private, public)
    for v in (0, 1, 30, 12345):
        assert bp.decrypt(priv, bp.encrypt(pub, v)) == v
    csum = bp.add(pub, bp.encrypt(pub, 100), bp.encrypt(pub, 23))
    assert bp.decrypt(priv, csum) == 123


# ---- W3: adapter exposes ZKProofs like MerkleTree ----------------------------------------------

def test_w3_lazy_bp_exposes_zkproofs():
    from sovereign_agent import _lazy_bp  # noqa: PLC0415
    assert hasattr(_lazy_bp, "ZKProofs")  # exposed on the adapter surface
