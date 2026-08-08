# -*- coding: utf-8 -*-
"""Proof-first tests for material.provision_shelter (S9 Vol 4, Shelter & Manufacturing).

Kill-targets pinned: no-central-housing-authority · human-primacy · verify-by-receipt-not-a-registry ·
honest-condition (known condition, non-negative capacity) · composes-V01-rolls-no-crypto · weakest-party.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.material.provision_shelter import (
    provision_shelter,
    verify_shelter,
    ProvisionRefused,
    ProvisionStatus,
)

DWELL, LOC, CAP, COND = "north-cabin", "ridge-parcel-3", 4, "habitable"
MANDATE, SRC, AT, AUTHOR = "ridgeline-homestead", "provision:ridgeline-cabin", "2026-08-08T14:00:00Z", "Kenneth Mangum"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def test_provisions_shelter_as_receipted_object(tmp_path):
    r = provision_shelter(DWELL, location=LOC, capacity=CAP, condition=COND, mandate=MANDATE, author=AUTHOR,
                          source_ref=SRC, at=AT, registry=_reg(tmp_path))
    assert r["kind"] == "provision" and r["mandate"] == MANDATE
    assert r["object_id"] == "MaterialGood:shelter:north-cabin@ridge-parcel-3"
    assert r["payload"]["condition"] == "habitable" and r["payload"]["capacity"] == 4.0
    assert r["version_hash"]


def test_verify_shelter_by_receipt_no_registry(tmp_path):
    r = provision_shelter(DWELL, location=LOC, capacity=CAP, condition=COND, mandate=MANDATE, author=AUTHOR,
                          source_ref=SRC, at=AT, registry=_reg(tmp_path))
    st = verify_shelter(r, DWELL, location=LOC, capacity=CAP, condition=COND)
    assert st.provisioned is True and st.reason == "provisioned"


def test_location_required(tmp_path):
    with pytest.raises(ProvisionRefused):
        provision_shelter(DWELL, location="", capacity=CAP, condition=COND, mandate=MANDATE, author=AUTHOR,
                          source_ref=SRC, at=AT, registry=_reg(tmp_path))


def test_condition_must_be_known(tmp_path):
    with pytest.raises(ProvisionRefused):
        provision_shelter(DWELL, location=LOC, capacity=CAP, condition="palatial", mandate=MANDATE,
                          author=AUTHOR, source_ref=SRC, at=AT, registry=_reg(tmp_path))


def test_negative_capacity_refused(tmp_path):
    with pytest.raises(ProvisionRefused):
        provision_shelter(DWELL, location=LOC, capacity=-2, condition=COND, mandate=MANDATE, author=AUTHOR,
                          source_ref=SRC, at=AT, registry=_reg(tmp_path))


def test_verify_shelter_detects_a_tampered_condition(tmp_path):
    # a structure sold as habitable but really needing repair — the receipt catches the swap
    r = provision_shelter(DWELL, location=LOC, capacity=CAP, condition=COND, mandate=MANDATE, author=AUTHOR,
                          source_ref=SRC, at=AT, registry=_reg(tmp_path))
    st = verify_shelter(r, DWELL, location=LOC, capacity=CAP, condition="needs-repair")
    assert st.provisioned is False


def test_no_central_housing_authority_two_local_registries(tmp_path):
    node_a, node_b = _reg(tmp_path, "node_a"), _reg(tmp_path, "node_b")
    ra = provision_shelter(DWELL, location=LOC, capacity=CAP, condition=COND, mandate=MANDATE, author=AUTHOR,
                           source_ref=SRC, at=AT, registry=node_a)
    rb = provision_shelter("cedar-barn", location="cedar-parcel-1", capacity=0, condition="needs-repair",
                           mandate="cedar-node", author=AUTHOR, source_ref="provision:cedar-barn", at=AT,
                           registry=node_b)
    assert len(node_a.entries()) == 1 and len(node_b.entries()) == 1
    assert verify_shelter(ra, DWELL, location=LOC, capacity=CAP, condition=COND).provisioned is True
    assert verify_shelter(rb, "cedar-barn", location="cedar-parcel-1", capacity=0, condition="needs-repair").provisioned is True


def test_human_primacy_gated_shelter_refused_without_approval(tmp_path):
    gate = HumanApprovalGate()
    role_spec = {"charter_v7_forbidden_classes": ["provision_shelter"]}
    with pytest.raises(ProvisionRefused):
        provision_shelter(DWELL, location=LOC, capacity=CAP, condition=COND, mandate=MANDATE, author=AUTHOR,
                          source_ref=SRC, at=AT, registry=_reg(tmp_path), gate=gate, role_spec=role_spec,
                          mode="corporate_regulated")


def test_composes_v01_rolls_no_crypto():
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "material" / "provision_shelter.py"
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography"):
            assert tok not in ln.lower(), f"provision_shelter must not roll its own {tok} — compose V01"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from .")]
    assert sibling and all(".provision_local" in ln for ln in sibling), "the only sibling import is the Material Primitive (V01)"


def test_weakest_party_verdict_is_a_plain_bool(tmp_path):
    r = provision_shelter(DWELL, location=LOC, capacity=CAP, condition=COND, mandate=MANDATE, author=AUTHOR,
                          source_ref=SRC, at=AT, registry=_reg(tmp_path))
    st = verify_shelter(r, DWELL, location=LOC, capacity=CAP, condition=COND)
    assert isinstance(st, ProvisionStatus) and isinstance(st.provisioned, bool)
