# -*- coding: utf-8 -*-
"""Proof-first tests for material.provision_shipment (S9 Vol 5, Logistics & Supply).

Kill-targets pinned: no-central-dispatcher · human-primacy · verify-by-receipt-not-a-registry ·
honest-custody (origin+destination required and distinct, carrier named, non-negative quantity) ·
composes-V01-rolls-no-crypto · weakest-party.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.material.provision_shipment import (
    provision_shipment,
    verify_shipment,
    ProvisionRefused,
    ProvisionStatus,
)

GOOD, ORIG, DEST, CARR, QTY = "heirloom-wheat", "north-field", "cedar-market", "ridgeline-wagon", 120.0
MANDATE, SRC, AT, AUTHOR = "ridgeline-homestead", "provision:ridgeline-shipment", "2026-08-08T14:00:00Z", "Kenneth Mangum"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def test_provisions_shipment_as_receipted_object(tmp_path):
    r = provision_shipment(GOOD, origin=ORIG, destination=DEST, carrier=CARR, quantity=QTY, mandate=MANDATE,
                           author=AUTHOR, source_ref=SRC, at=AT, registry=_reg(tmp_path))
    assert r["kind"] == "provision" and r["mandate"] == MANDATE
    assert r["object_id"] == "MaterialGood:shipment:heirloom-wheat:north-field->cedar-market"
    assert r["payload"]["origin"] == ORIG and r["payload"]["destination"] == DEST and r["payload"]["carrier"] == CARR
    assert r["version_hash"]


def test_verify_shipment_by_receipt_no_registry(tmp_path):
    r = provision_shipment(GOOD, origin=ORIG, destination=DEST, carrier=CARR, quantity=QTY, mandate=MANDATE,
                           author=AUTHOR, source_ref=SRC, at=AT, registry=_reg(tmp_path))
    st = verify_shipment(r, GOOD, origin=ORIG, destination=DEST, carrier=CARR, quantity=QTY)
    assert st.provisioned is True and st.reason == "provisioned"


def test_origin_and_destination_required(tmp_path):
    with pytest.raises(ProvisionRefused):
        provision_shipment(GOOD, origin="", destination=DEST, carrier=CARR, quantity=QTY, mandate=MANDATE,
                           author=AUTHOR, source_ref=SRC, at=AT, registry=_reg(tmp_path))
    with pytest.raises(ProvisionRefused):
        provision_shipment(GOOD, origin=ORIG, destination="", carrier=CARR, quantity=QTY, mandate=MANDATE,
                           author=AUTHOR, source_ref=SRC, at=AT, registry=_reg(tmp_path))


def test_origin_destination_must_differ(tmp_path):
    with pytest.raises(ProvisionRefused):
        provision_shipment(GOOD, origin="north-field", destination="north-field", carrier=CARR, quantity=QTY,
                           mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT, registry=_reg(tmp_path))


def test_carrier_required(tmp_path):
    with pytest.raises(ProvisionRefused):
        provision_shipment(GOOD, origin=ORIG, destination=DEST, carrier="", quantity=QTY, mandate=MANDATE,
                           author=AUTHOR, source_ref=SRC, at=AT, registry=_reg(tmp_path))


def test_negative_quantity_refused(tmp_path):
    with pytest.raises(ProvisionRefused):
        provision_shipment(GOOD, origin=ORIG, destination=DEST, carrier=CARR, quantity=-5, mandate=MANDATE,
                           author=AUTHOR, source_ref=SRC, at=AT, registry=_reg(tmp_path))


def test_verify_shipment_detects_a_tampered_origin(tmp_path):
    # a shipment relabeled to claim a different origin — the receipt catches it
    r = provision_shipment(GOOD, origin=ORIG, destination=DEST, carrier=CARR, quantity=QTY, mandate=MANDATE,
                           author=AUTHOR, source_ref=SRC, at=AT, registry=_reg(tmp_path))
    st = verify_shipment(r, GOOD, origin="unknown-warehouse", destination=DEST, carrier=CARR, quantity=QTY)
    assert st.provisioned is False


def test_no_central_dispatcher_two_local_registries(tmp_path):
    node_a, node_b = _reg(tmp_path, "node_a"), _reg(tmp_path, "node_b")
    ra = provision_shipment(GOOD, origin=ORIG, destination=DEST, carrier=CARR, quantity=QTY, mandate=MANDATE,
                            author=AUTHOR, source_ref=SRC, at=AT, registry=node_a)
    rb = provision_shipment("spring-water", origin="cedar-spring", destination="ridge-depot",
                            carrier="cedar-truck", quantity=200.0, mandate="cedar-node", author=AUTHOR,
                            source_ref="provision:cedar-shipment", at=AT, registry=node_b)
    assert len(node_a.entries()) == 1 and len(node_b.entries()) == 1
    assert verify_shipment(ra, GOOD, origin=ORIG, destination=DEST, carrier=CARR, quantity=QTY).provisioned is True
    assert verify_shipment(rb, "spring-water", origin="cedar-spring", destination="ridge-depot",
                           carrier="cedar-truck", quantity=200.0).provisioned is True


def test_human_primacy_gated_shipment_refused_without_approval(tmp_path):
    gate = HumanApprovalGate()
    role_spec = {"charter_v7_forbidden_classes": ["provision_shipment"]}
    with pytest.raises(ProvisionRefused):
        provision_shipment(GOOD, origin=ORIG, destination=DEST, carrier=CARR, quantity=QTY, mandate=MANDATE,
                           author=AUTHOR, source_ref=SRC, at=AT, registry=_reg(tmp_path), gate=gate,
                           role_spec=role_spec, mode="corporate_regulated")


def test_composes_v01_rolls_no_crypto():
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "material" / "provision_shipment.py"
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography"):
            assert tok not in ln.lower(), f"provision_shipment must not roll its own {tok} — compose V01"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from .")]
    assert sibling and all(".provision_local" in ln for ln in sibling), "the only sibling import is the Material Primitive (V01)"


def test_weakest_party_verdict_is_a_plain_bool(tmp_path):
    r = provision_shipment(GOOD, origin=ORIG, destination=DEST, carrier=CARR, quantity=QTY, mandate=MANDATE,
                           author=AUTHOR, source_ref=SRC, at=AT, registry=_reg(tmp_path))
    st = verify_shipment(r, GOOD, origin=ORIG, destination=DEST, carrier=CARR, quantity=QTY)
    assert isinstance(st, ProvisionStatus) and isinstance(st.provisioned, bool)
