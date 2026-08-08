# -*- coding: utf-8 -*-
"""Proof-first tests for material.provision_energy (S9 Vol 2, Sovereign Energy).

Kill-targets pinned: no-central-utility (each node's own local registry) · human-primacy (a gated energy
provision refused without approval) · verify-by-receipt-not-a-utility-registry · honest-metering
(negative reading refused) · composes-V01-rolls-no-crypto · weakest-party green light.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry, MandateViolation
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.material.provision_energy import (
    provision_energy,
    verify_energy,
    ProvisionRefused,
    ProvisionStatus,
)

ASSET, KWH, PERIOD = "rooftop-array-01", 42.5, "2026-08"
MANDATE, SRC, AT, AUTHOR = "ridgeline-homestead", "provision:ridgeline-energy", "2026-08-08T05:00:00Z", "Kenneth Mangum"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def test_provisions_metered_energy_as_receipted_object(tmp_path):
    r = provision_energy(ASSET, KWH, period=PERIOD, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                         registry=_reg(tmp_path))
    assert r["kind"] == "provision"
    assert r["mandate"] == MANDATE
    assert r["object_id"] == "MaterialGood:rooftop-array-01@2026-08"
    assert r["payload"]["kwh"] == 42.5 and r["payload"]["unit"] == "kWh" and r["payload"]["period"] == PERIOD
    assert r["version_hash"]


def test_verify_energy_by_receipt_no_registry(tmp_path):
    r = provision_energy(ASSET, KWH, period=PERIOD, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                         registry=_reg(tmp_path))
    st = verify_energy(r, ASSET, KWH, period=PERIOD)
    assert st.provisioned is True and st.reason == "provisioned"


def test_negative_meter_reading_refused(tmp_path):
    with pytest.raises(ProvisionRefused):
        provision_energy(ASSET, -5.0, period=PERIOD, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                         registry=_reg(tmp_path))


def test_verify_energy_detects_a_tampered_reading(tmp_path):
    r = provision_energy(ASSET, KWH, period=PERIOD, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                         registry=_reg(tmp_path))
    st = verify_energy(r, ASSET, 99.0, period=PERIOD)   # a meter inflated after the fact
    assert st.provisioned is False


def test_no_central_utility_two_local_registries(tmp_path):
    node_a, node_b = _reg(tmp_path, "node_a"), _reg(tmp_path, "node_b")
    ra = provision_energy(ASSET, KWH, period=PERIOD, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                          registry=node_a)
    rb = provision_energy("cedar-turbine-02", 17.0, period=PERIOD, mandate="cedar-node", author=AUTHOR,
                          source_ref="provision:cedar-energy", at=AT, registry=node_b)
    assert len(node_a.entries()) == 1 and len(node_b.entries()) == 1
    assert verify_energy(ra, ASSET, KWH, period=PERIOD).provisioned is True
    assert verify_energy(rb, "cedar-turbine-02", 17.0, period=PERIOD).provisioned is True


def test_human_primacy_gated_energy_refused_without_approval(tmp_path):
    gate = HumanApprovalGate()
    role_spec = {"charter_v7_forbidden_classes": ["provision_energy"]}
    with pytest.raises(ProvisionRefused):
        provision_energy(ASSET, KWH, period=PERIOD, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                         registry=_reg(tmp_path), gate=gate, role_spec=role_spec, mode="corporate_regulated")


def test_composes_v01_rolls_no_crypto():
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "material" / "provision_energy.py"
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography"):
            assert tok not in ln.lower(), f"provision_energy must not roll its own {tok} — compose V01"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from .")]
    assert sibling and all(".provision_local" in ln for ln in sibling), "the only sibling import is the Material Primitive (V01)"


def test_weakest_party_verdict_is_a_plain_bool(tmp_path):
    r = provision_energy(ASSET, KWH, period=PERIOD, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                         registry=_reg(tmp_path))
    st = verify_energy(r, ASSET, KWH, period=PERIOD)
    assert isinstance(st, ProvisionStatus) and isinstance(st.provisioned, bool)
