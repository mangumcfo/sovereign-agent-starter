# -*- coding: utf-8 -*-
"""Proof-first tests for material.provision_covenant (S9 Vol 6, The Provision Covenant, the CAPSTONE).

Kill-targets pinned: composes-never-reimplements (imports the five sealed provisioners) · one-covenant-
over-all-kinds (declared set; unknown kind refused) · verify-uniform-across-kinds (one weakest-party
check for any good) · human-primacy-inherited · rolls-no-crypto · weakest-party green light.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.material.provision_covenant import (
    provision_kinds,
    provision_under_covenant,
    verify_under_covenant,
    PROVISION_COVENANT,
    ProvisionRefused,
    ProvisionStatus,
)

MANDATE, AUTHOR, AT = "ridgeline-homestead", "Kenneth Mangum", "2026-08-08T23:00:00Z"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def _provision_each_kind(tmp_path):
    """Provision one good of each of the five kinds under the covenant; return {kind: (receipt, good)}."""
    reg = _reg(tmp_path)
    out = {}
    r = provision_under_covenant("good", {"id": "hand-tool-1", "name": "adze"}, mandate=MANDATE,
                                 author=AUTHOR, source_ref="provision:good", at=AT, registry=reg)
    out["good"] = (r, r["payload"])
    r = provision_under_covenant("energy", "array-1", 40.0, period="2026-08", mandate=MANDATE,
                                 author=AUTHOR, source_ref="provision:energy", at=AT, registry=reg)
    out["energy"] = (r, r["payload"])
    r = provision_under_covenant("sustenance", "wheat", 100.0, kind_of="food", origin="north-field",
                                 mandate=MANDATE, author=AUTHOR, source_ref="provision:food", at=AT, registry=reg)
    out["sustenance"] = (r, r["payload"])
    r = provision_under_covenant("shelter", "cabin", location="parcel-3", capacity=4, condition="habitable",
                                 mandate=MANDATE, author=AUTHOR, source_ref="provision:shelter", at=AT, registry=reg)
    out["shelter"] = (r, r["payload"])
    r = provision_under_covenant("shipment", "wheat", origin="north-field", destination="market",
                                 carrier="wagon", quantity=100.0, mandate=MANDATE, author=AUTHOR,
                                 source_ref="provision:shipment", at=AT, registry=reg)
    out["shipment"] = (r, r["payload"])
    return out


def test_covenant_declares_the_five_kinds():
    assert provision_kinds() == ("energy", "good", "shelter", "shipment", "sustenance")
    assert len(PROVISION_COVENANT) == 5


def test_provision_under_covenant_dispatches_each_kind(tmp_path):
    provisioned = _provision_each_kind(tmp_path)
    assert set(provisioned) == {"good", "energy", "sustenance", "shelter", "shipment"}
    for kind, (receipt, good) in provisioned.items():
        assert receipt["kind"] == "provision"
        assert receipt["mandate"] == MANDATE
        assert receipt["version_hash"]


def test_unknown_kind_refused(tmp_path):
    # deny-by-default: a kind not in the covenant is refused, never dispatched
    with pytest.raises(ProvisionRefused):
        provision_under_covenant("weaponry", {"id": "x"}, mandate=MANDATE, author=AUTHOR,
                                 source_ref="provision:x", at=AT, registry=_reg(tmp_path))


def test_verify_under_covenant_is_uniform_across_kinds(tmp_path):
    # ONE uniform check confirms a good of ANY kind — the whole series shares verify_provision
    provisioned = _provision_each_kind(tmp_path)
    for kind, (receipt, good) in provisioned.items():
        st = verify_under_covenant(receipt, good)
        assert st.provisioned is True, f"{kind} should verify under the covenant"
        assert st.reason == "provisioned"


def test_verify_under_covenant_detects_tamper(tmp_path):
    provisioned = _provision_each_kind(tmp_path)
    receipt, good = provisioned["energy"]
    tampered = dict(good, kwh=999.0)     # inflate the metered energy after the fact
    st = verify_under_covenant(receipt, tampered)
    assert st.provisioned is False


def test_human_primacy_inherited_through_the_covenant(tmp_path):
    # a gated provision dispatched under the covenant is refused without a human approval (inherited from V04)
    gate = HumanApprovalGate()
    role_spec = {"charter_v7_forbidden_classes": ["provision_shelter"]}
    with pytest.raises(ProvisionRefused):
        provision_under_covenant("shelter", "manor", location="parcel-9", capacity=8, condition="habitable",
                                 mandate=MANDATE, author=AUTHOR, source_ref="provision:shelter", at=AT,
                                 registry=_reg(tmp_path), gate=gate, role_spec=role_spec,
                                 mode="corporate_regulated")


def test_composes_the_five_never_reimplements():
    # the covenant imports the five sealed provisioners + the shared verify; it rolls no crypto and
    # writes to no registry of its own (re-implements nothing).
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "material" / "provision_covenant.py"
    text = src.read_text(encoding="utf-8")
    import_lines = [ln for ln in text.splitlines() if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography", "objects.registry", "ObjectRegistry"):
            assert tok not in ln, f"provision_covenant must not roll/import {tok} — compose the sealed floors"
    siblings = " ".join(ln for ln in import_lines if ln.lstrip().startswith("from ."))
    for mod in ("provision_local", "provision_energy", "provision_sustenance", "provision_shelter", "provision_shipment"):
        assert mod in siblings, f"the covenant must compose {mod}"


def test_weakest_party_verdict_is_a_plain_bool(tmp_path):
    provisioned = _provision_each_kind(tmp_path)
    receipt, good = provisioned["shipment"]
    st = verify_under_covenant(receipt, good)
    assert isinstance(st, ProvisionStatus) and isinstance(st.provisioned, bool)
