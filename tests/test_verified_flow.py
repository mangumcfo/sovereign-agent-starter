"""Acceptance tests for Verified Data Flows Across Nodes (s7_04, S7 Vol 4) — every flow a receipted,
integrity-proven (sealed P5 Merkle), policy-governed (federation authorize_crossing) event, accepted
deny-by-default. Plus the zero-knowledge privacy option (sealed P5 ZK, authorized v1.0.3 overlay):
prove a flow clears a minimum WITHOUT revealing the quantity. No transport, no store, no second trust
authority, no central attestation, no hub that vouches, no standing trust across flows."""
import sys
from pathlib import Path

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.objects.scope import SharingRule
from sovereign_agent.flows.verified_flow import (
    declare_flow, verify_flow, attest_flow_clears, verify_flow_clears, FlowError,
)

_ZK_OVERLAY = Path(__file__).resolve().parents[1] / "src" / "overlays" / "v1.0.3-zk-range"
_L1 = Path(__file__).resolve().parents[1] / "src" / "primitives" / "sealed" / "layer_1_root"


def _zk():
    """Construct ZKProofs from the authorized v1.0.3 overlay (Pedersen+Schnorr+Range PRESENT)."""
    for m in ("zk_proofs", "point_ops", "finite_field", "keygen", "sign", "verify"):
        sys.modules.pop(m, None)
    saved = list(sys.path)
    sys.path.insert(0, str(_L1))
    sys.path.insert(0, str(_ZK_OVERLAY))
    try:
        import zk_proofs  # noqa: PLC0415
        return zk_proofs.ZKProofs("secp256k1")
    finally:
        sys.path[:] = saved
        for m in ("zk_proofs", "point_ops", "finite_field", "keygen", "sign", "verify"):
            sys.modules.pop(m, None)


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path))


def _flow(reg, source="nodeA", target="nodeB", chunks=(b"batch", b"payload")):
    return declare_flow(reg, source, target, list(chunks), mandate=source, author=source,
                        source_ref=f"flow://{source}", at="2026-08-06")


# ---- declare_flow / verify_flow (receipted + integrity + policy) --------------------------------

def test_declare_flow_registers_governed_object_with_root(tmp_path):
    reg = _reg(tmp_path)
    f = _flow(reg)
    assert f["version_hash"] and f["object_id"].startswith("flow:nodeA->nodeB:")
    assert f["payload"]["source"] == "nodeA" and f["payload"]["target"] == "nodeB" and f["payload"]["root"]


def test_declare_flow_refuses_empty(tmp_path):
    reg = _reg(tmp_path)
    for bad in (("", "nodeB", [b"x"]), ("nodeA", "", [b"x"]), ("nodeA", "nodeB", [])):
        with pytest.raises(FlowError):
            declare_flow(reg, bad[0], bad[1], bad[2], mandate="nodeA", author="nodeA", source_ref="f://1", at="t")


def test_verify_flow_own_mandate_integrity_verified(tmp_path):
    reg = _reg(tmp_path)
    f = _flow(reg, "nodeA", "nodeA")  # own-mandate acceptance is whole
    res = verify_flow(reg, f, [], [b"batch", b"payload"], principal_mandate="nodeA")
    assert res["accepted"] is True and res["integrity"] == "verified"


def test_verify_flow_cross_node_needs_declared_policy(tmp_path):
    reg = _reg(tmp_path)
    f = _flow(reg, "nodeA", "nodeB")
    with pytest.raises(FlowError):  # no standing trust across flows
        verify_flow(reg, f, [], [b"batch", b"payload"], principal_mandate="nodeB")
    rule = SharingRule(f["object_id"], "nodeB", "read")
    res = verify_flow(reg, f, [rule], [b"batch", b"payload"], principal_mandate="nodeB")
    assert res["accepted"] is True


def test_verify_flow_denies_tampered_in_transit(tmp_path):
    reg = _reg(tmp_path)
    f = _flow(reg, "nodeA", "nodeA")
    with pytest.raises(FlowError):  # presented bytes differ -> Merkle mismatch
        verify_flow(reg, f, [], [b"batch", b"ALTERED"], principal_mandate="nodeA")


def test_verify_flow_refuses_no_real_flow(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(FlowError):
        verify_flow(reg, {}, [], [b"x"], principal_mandate="nodeA")


# ---- attest_flow_clears / verify_flow_clears (zero-knowledge privacy option) ---------------------

def test_attest_flow_clears_zero_knowledge():
    zk = _zk()
    commitment, proof = attest_flow_clears(zk, quantity=120, minimum=100, bits=8)  # clears, quantity hidden
    assert verify_flow_clears(zk, commitment, proof, minimum=100, bits=8) is True


def test_attest_flow_clears_refuses_below_minimum():
    zk = _zk()
    with pytest.raises(FlowError):  # cannot prove a false clearance
        attest_flow_clears(zk, quantity=90, minimum=100, bits=8)


def test_verify_flow_clears_rejects_wrong_minimum():
    zk = _zk()
    commitment, proof = attest_flow_clears(zk, quantity=120, minimum=100, bits=8)
    # a proof that clears 100 must not verify against a claimed minimum of 130
    assert verify_flow_clears(zk, commitment, proof, minimum=130, bits=8) is False


def test_verify_flow_clears_rejects_tampered_proof():
    import copy
    zk = _zk()
    commitment, proof = attest_flow_clears(zk, quantity=120, minimum=100, bits=8)
    t = copy.deepcopy(proof)
    t["bit_commitments"][0] = zk.curve.mul(2, zk.G)
    assert verify_flow_clears(zk, commitment, t, minimum=100, bits=8) is False
