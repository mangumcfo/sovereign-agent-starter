# -*- coding: utf-8 -*-
"""Proof-first tests for material.provision_local (S9 Vol 1, The Material Primitive, the S9 opener).

Kill-targets pinned: no-central-provisioner (each node's own local registry) · human-primacy (a gated
material provision refused without approval) · verify-by-receipt-not-a-registry · mandate-scoped ·
provenance-never-false · rolls-no-cryptography · weakest-party verdict is a plain green light.
"""
import copy
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry, MandateViolation
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.material.provision_local import (
    provision_local,
    verify_provision,
    ProvisionRefused,
    ProvisionStatus,
    PROVISION_KIND,
)

GOOD = {"id": "solar-panel-01", "name": "Ridgeline rooftop PV", "unit": "panel", "qty": 12}
MANDATE = "ridgeline-homestead"
SRC = "provision:ridgeline-solar-01"   # symbolic source_ref (no path) — provenance passes as-is
AT = "2026-08-08T02:00:00Z"
AUTHOR = "Kenneth Mangum"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def test_provisions_a_good_as_a_receipted_object(tmp_path):
    receipt = provision_local(GOOD, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                              registry=_reg(tmp_path))
    assert receipt["kind"] == PROVISION_KIND
    assert receipt["mandate"] == MANDATE
    assert receipt["payload"] == GOOD
    assert receipt["object_id"] == "MaterialGood:solar-panel-01"
    assert receipt["version_hash"]            # hash-chained governed object (Object Model V5)


def test_verify_provision_by_receipt_no_registry(tmp_path):
    receipt = provision_local(GOOD, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                              registry=_reg(tmp_path))
    # a receiver holds ONLY the receipt + the good — no registry — and gets a green light
    st = verify_provision(receipt, GOOD)
    assert st.provisioned is True
    assert st.reason == "provisioned"


def test_verify_provision_detects_a_tampered_good(tmp_path):
    receipt = provision_local(GOOD, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                              registry=_reg(tmp_path))
    swapped = dict(GOOD, qty=999)            # someone swaps the good after the fact
    st = verify_provision(receipt, swapped)
    assert st.provisioned is False
    assert "does not match" in st.reason


def test_verify_provision_detects_a_tampered_receipt(tmp_path):
    receipt = provision_local(GOOD, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                              registry=_reg(tmp_path))
    forged = dict(receipt, at="2020-01-01T00:00:00Z")   # backdate the receipt but keep its old hash
    st = verify_provision(forged, GOOD)
    assert st.provisioned is False
    assert "does not verify" in st.reason


def test_human_primacy_gated_provision_refused_without_approval(tmp_path):
    gate = HumanApprovalGate()
    role_spec = {"charter_v7_forbidden_classes": ["provision_material"]}
    with pytest.raises(ProvisionRefused):
        provision_local(GOOD, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                        registry=_reg(tmp_path), gate=gate, role_spec=role_spec,
                        mode="corporate_regulated")   # gate requires approval; none supplied


def test_human_primacy_gated_provision_proceeds_with_approval(tmp_path):
    gate = HumanApprovalGate()
    role_spec = {"charter_v7_forbidden_classes": ["provision_material"]}
    receipt = provision_local(GOOD, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                              registry=_reg(tmp_path), gate=gate, role_spec=role_spec,
                              mode="corporate_regulated",
                              approver="Compliance Officer", approval_ref="approval_1")
    assert receipt["approver"] == "Compliance Officer"
    assert receipt["approval_ref"] == "approval_1"
    assert verify_provision(receipt, GOOD).provisioned is True


def test_mandate_scoped_good_cannot_move_mandate(tmp_path):
    reg = _reg(tmp_path)
    provision_local(GOOD, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT, registry=reg)
    # the same good re-provisioned under a DIFFERENT mandate is refused (S5 Vol 28, via the registry)
    with pytest.raises(MandateViolation):
        provision_local(GOOD, mandate="other-node", author=AUTHOR, source_ref=SRC, at=AT, registry=reg)


def test_provenance_never_false(tmp_path):
    # a path-like source_ref that does not resolve is refused (P5, via the composed Object Model)
    with pytest.raises(ValueError):
        provision_local(GOOD, mandate=MANDATE, author=AUTHOR,
                        source_ref="does/not/exist.yaml", at=AT, registry=_reg(tmp_path))


def test_no_central_provisioner_two_local_registries(tmp_path):
    # two nodes provision independently into their OWN registries; a receipt verifies across nodes by
    # receipt alone — there is no central provisioner either node depends on
    node_a = _reg(tmp_path, "node_a")
    node_b = _reg(tmp_path, "node_b")
    good_b = {"id": "well-pump-07", "name": "Cedar well pump", "unit": "pump", "qty": 1}
    ra = provision_local(GOOD, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT, registry=node_a)
    rb = provision_local(good_b, mandate="cedar-node", author=AUTHOR,
                         source_ref="provision:cedar-well-07", at=AT, registry=node_b)
    # each good lives only in its own node's registry
    assert len(node_a.entries()) == 1 and len(node_b.entries()) == 1
    # yet node B can verify node A's good from node A's receipt alone (no shared/central registry)
    assert verify_provision(ra, GOOD).provisioned is True
    assert verify_provision(rb, good_b).provisioned is True


def test_composes_sealed_floors_rolls_no_crypto():
    # rolls-no-cryptography + composes-not-reinvents: the module imports the sealed floors and no crypto
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "material" / "provision_local.py"
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography"):
            assert tok not in ln.lower(), f"provision_local must not roll its own {tok} — compose the sealed floor"
    # its only sealed-floor code import is the Object Model's identity helpers
    sibling = [ln for ln in import_lines if "from .." in ln]
    assert sibling == ["from ..objects.identity import object_id, make_version   # Object Model (S5 Vol 5) — composed by identity"]


def test_weakest_party_verdict_is_a_plain_bool(tmp_path):
    receipt = provision_local(GOOD, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                              registry=_reg(tmp_path))
    st = verify_provision(receipt, GOOD)
    assert isinstance(st, ProvisionStatus)
    assert isinstance(st.provisioned, bool)   # a green light, not a proof to interpret
