# -*- coding: utf-8 -*-
"""Proof-first tests for material.provision_sustenance (S9 Vol 3, Regenerative Food & Water).

Kill-targets pinned: no-central-provisioner · human-primacy · verify-by-receipt-not-a-registry ·
origin-required (regenerative provenance) · honest-quantity · composes-V01-rolls-no-crypto · weakest-party.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.material.provision_sustenance import (
    provision_sustenance,
    verify_sustenance,
    ProvisionRefused,
    ProvisionStatus,
)

ITEM, QTY, KIND, ORIGIN = "heirloom-wheat", 120.0, "food", "north-field-2026"
MANDATE, SRC, AT, AUTHOR = "ridgeline-homestead", "provision:ridgeline-harvest", "2026-08-08T05:00:00Z", "Kenneth Mangum"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def test_provisions_sustenance_as_receipted_object(tmp_path):
    r = provision_sustenance(ITEM, QTY, kind_of=KIND, origin=ORIGIN, mandate=MANDATE, author=AUTHOR,
                             source_ref=SRC, at=AT, registry=_reg(tmp_path))
    assert r["kind"] == "provision" and r["mandate"] == MANDATE
    assert r["object_id"] == "MaterialGood:food:heirloom-wheat:north-field-2026"
    assert r["payload"]["origin"] == ORIGIN and r["payload"]["kind_of"] == "food" and r["payload"]["quantity"] == 120.0
    assert r["version_hash"]


def test_verify_sustenance_by_receipt_no_registry(tmp_path):
    r = provision_sustenance(ITEM, QTY, kind_of=KIND, origin=ORIGIN, mandate=MANDATE, author=AUTHOR,
                             source_ref=SRC, at=AT, registry=_reg(tmp_path))
    st = verify_sustenance(r, ITEM, QTY, kind_of=KIND, origin=ORIGIN)
    assert st.provisioned is True and st.reason == "provisioned"


def test_origin_required(tmp_path):
    with pytest.raises(ProvisionRefused):
        provision_sustenance(ITEM, QTY, kind_of=KIND, origin="", mandate=MANDATE, author=AUTHOR,
                             source_ref=SRC, at=AT, registry=_reg(tmp_path))


def test_kind_must_be_food_or_water(tmp_path):
    with pytest.raises(ProvisionRefused):
        provision_sustenance(ITEM, QTY, kind_of="fuel", origin=ORIGIN, mandate=MANDATE, author=AUTHOR,
                             source_ref=SRC, at=AT, registry=_reg(tmp_path))


def test_negative_quantity_refused(tmp_path):
    with pytest.raises(ProvisionRefused):
        provision_sustenance(ITEM, -3.0, kind_of=KIND, origin=ORIGIN, mandate=MANDATE, author=AUTHOR,
                             source_ref=SRC, at=AT, registry=_reg(tmp_path))


def test_verify_sustenance_detects_a_tampered_origin(tmp_path):
    # a receiver checks the ORIGIN too — swapping where the food came from flips the light
    r = provision_sustenance(ITEM, QTY, kind_of=KIND, origin=ORIGIN, mandate=MANDATE, author=AUTHOR,
                             source_ref=SRC, at=AT, registry=_reg(tmp_path))
    st = verify_sustenance(r, ITEM, QTY, kind_of=KIND, origin="unknown-import")
    assert st.provisioned is False


def test_no_central_provisioner_two_local_registries(tmp_path):
    node_a, node_b = _reg(tmp_path, "node_a"), _reg(tmp_path, "node_b")
    ra = provision_sustenance(ITEM, QTY, kind_of=KIND, origin=ORIGIN, mandate=MANDATE, author=AUTHOR,
                              source_ref=SRC, at=AT, registry=node_a)
    rb = provision_sustenance("spring-water", 200.0, kind_of="water", origin="cedar-spring", mandate="cedar-node",
                              author=AUTHOR, source_ref="provision:cedar-water", at=AT, registry=node_b)
    assert len(node_a.entries()) == 1 and len(node_b.entries()) == 1
    assert verify_sustenance(ra, ITEM, QTY, kind_of=KIND, origin=ORIGIN).provisioned is True
    assert verify_sustenance(rb, "spring-water", 200.0, kind_of="water", origin="cedar-spring").provisioned is True


def test_human_primacy_gated_sustenance_refused_without_approval(tmp_path):
    gate = HumanApprovalGate()
    role_spec = {"charter_v7_forbidden_classes": ["provision_sustenance"]}
    with pytest.raises(ProvisionRefused):
        provision_sustenance(ITEM, QTY, kind_of=KIND, origin=ORIGIN, mandate=MANDATE, author=AUTHOR,
                             source_ref=SRC, at=AT, registry=_reg(tmp_path), gate=gate, role_spec=role_spec,
                             mode="corporate_regulated")


def test_composes_v01_rolls_no_crypto():
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "material" / "provision_sustenance.py"
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography"):
            assert tok not in ln.lower(), f"provision_sustenance must not roll its own {tok} — compose V01"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from .")]
    assert sibling and all(".provision_local" in ln for ln in sibling), "the only sibling import is the Material Primitive (V01)"


def test_weakest_party_verdict_is_a_plain_bool(tmp_path):
    r = provision_sustenance(ITEM, QTY, kind_of=KIND, origin=ORIGIN, mandate=MANDATE, author=AUTHOR,
                             source_ref=SRC, at=AT, registry=_reg(tmp_path))
    st = verify_sustenance(r, ITEM, QTY, kind_of=KIND, origin=ORIGIN)
    assert isinstance(st, ProvisionStatus) and isinstance(st.provisioned, bool)
