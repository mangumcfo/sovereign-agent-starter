# -*- coding: utf-8 -*-
"""Proof-first tests for estate.generational_transfer (S12 Vol 1, the OPENER:
The Sovereign Estate That Executes Itself).

Kill-targets pinned:
- composes the sealed design layers ONLY — S10 V5 (inherit_livelihood), S11 V05 (inherit_protection), S9
  material (verify_under_covenant), S10 V1 (governed record); re-implements none; rolls no cryptography;
- execute_transfer RE-ATTRIBUTES a whole estate (livelihood + protection + material) to the heir by composing
  the sealed inheritance checks — transferred iff every present sub-stack is intact and genuine; a tampered or
  empty estate does not transfer; the heir verifies the estate passed to them from a receipt (weakest-party);
- an unknown estate sub-stack is refused (deny-by-default);
- THE SUCCESSION-FENCE: any escrow / custodian / recovery-authority / second-authority field is refused —
  inheritance is re-attribution of ownership records, not an escrowed estate;
- SEAL-KEY-CLOSED: key succession is the family's own sovereign keys (family-quorum, breath-gated) — a
  press/seal key field is refused; a quorum below two (a single custodian) is refused.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.economy.contribution import record_contribution, IncomeRefused
from sovereign_agent.risk.mutual_protection import form_protection_pool, record_premium
from sovereign_agent.material.provision_covenant import provision_under_covenant
from sovereign_agent.estate.generational_transfer import (
    execute_transfer, verify_transfer, inheritance_package, open_key_epoch, family_quorum_recovery,
    breath_gated_key_transfer, TransferStatus, InheritancePackage, KeyEpoch, ESTATE_STACK_KINDS,
    ESTATE_BREACH_FIELDS, EstateRefused,
)

DECEDENT, HEIR, B, AUTHOR, AT = "ridgeline-kenn", "ridgeline-heir", "cedar-partner", "Kenneth Mangum", "2026-08-10T09:00:00Z"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def _estate(reg):
    """The decedent's whole sovereign estate — a livelihood stream (S10 V5), a protection element (S11 V05),
    and a material good (S9). Returns the estate the transfer executes over."""
    contrib = record_contribution(DECEDENT, "surplus_energy", "aug-solar", contribution_class="metered",
                                  mandate=DECEDENT, author=AUTHOR, source_ref="c", at=AT, registry=reg,
                                  amount=40.0)
    pool = form_protection_pool("ridgeline-aid", (DECEDENT, B))
    prem = record_premium(pool, DECEDENT, "aug-prem", contribution_class="attested", author=AUTHOR,
                          source_ref="p", at=AT, registry=reg, amount=25.0)
    g = provision_under_covenant("good", {"id": "hand-tool-1", "name": "adze"}, mandate=DECEDENT, author=AUTHOR,
                                 source_ref="m", at=AT, registry=reg)
    return {
        "livelihood": [{"kind": "contribution", "receipt": contrib, "work_ref": "aug-solar",
                        "contribution_class": "metered", "source": "surplus_energy", "amount": 40.0}],
        "protection": [{"kind": "premium", "receipt": prem, "pool": pool, "work_ref": "aug-prem",
                        "contribution_class": "attested", "amount": 25.0}],
        "material": [{"receipt": g, "good": g["payload"]}],
    }


def test_execute_transfer_reattributes_a_whole_estate(tmp_path):
    reg = _reg(tmp_path)
    st = execute_transfer(DECEDENT, HEIR, _estate(reg), "estate-2026", at=AT, author=AUTHOR, source_ref="t",
                          registry=reg)
    assert isinstance(st, TransferStatus)
    assert st.transferred is True and st.by_stack == {"livelihood": True, "protection": True, "material": True}
    assert st.receipt is not None and st.receipt["mandate"] == HEIR
    assert "this estate is mine now" in st.reason
    # weakest-party: the heir verifies the estate passed to them from the receipt
    assert verify_transfer(st.receipt, HEIR, DECEDENT, "estate-2026") is True


def test_a_tampered_or_empty_estate_does_not_transfer(tmp_path):
    reg = _reg(tmp_path)
    estate = _estate(reg)
    estate["livelihood"][0] = {**estate["livelihood"][0], "contribution_class": "attested"}  # tampered grade
    st = execute_transfer(DECEDENT, HEIR, estate, "estate-2026", at=AT, author=AUTHOR, source_ref="t",
                          registry=reg)
    assert st.transferred is False and st.receipt is None and st.by_stack["livelihood"] is False
    assert execute_transfer(DECEDENT, HEIR, {}, "e", at=AT, author=AUTHOR, source_ref="t",
                            registry=reg).transferred is False


def test_inheritance_package_complete_only_from_an_intact_estate(tmp_path):
    reg = _reg(tmp_path)
    pkg = inheritance_package(DECEDENT, _estate(reg))
    assert isinstance(pkg, InheritancePackage) and pkg.complete is True
    assert pkg.verified == {"livelihood": True, "protection": True, "material": True}
    assert inheritance_package(DECEDENT, {}).complete is False          # empty estate
    assert inheritance_package("stranger", _estate(reg)).complete is False   # foreign decedent


def test_an_unknown_estate_substack_is_refused(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(EstateRefused):
        inheritance_package(DECEDENT, {"crypto_wallet": []})
    assert set(ESTATE_STACK_KINDS) == {"livelihood", "protection", "material"}


def test_key_succession_is_family_quorum_and_breath_gated_not_custodial(tmp_path):
    reg = _reg(tmp_path)
    epoch = open_key_epoch("ridgeline-family", 1, [DECEDENT, HEIR, B])
    assert isinstance(epoch, KeyEpoch) and epoch.epoch == 1
    assert family_quorum_recovery(epoch, [DECEDENT, HEIR], quorum=2) is True
    assert family_quorum_recovery(epoch, [DECEDENT], quorum=2) is False
    with pytest.raises(EstateRefused):        # a single approver is a custodian, not a family quorum
        family_quorum_recovery(epoch, [DECEDENT], quorum=1)
    # a breath-gated key transfer is refused without a named human's approval
    with pytest.raises(IncomeRefused):
        breath_gated_key_transfer(DECEDENT, HEIR, "ridgeline-family", "key-handoff", gate=HumanApprovalGate(),
                                  at=AT, author=AUTHOR, source_ref="k", registry=reg)
    # with a named human's approval it records as the heir's own governed act
    r = breath_gated_key_transfer(DECEDENT, HEIR, "ridgeline-family", "key-handoff", gate=HumanApprovalGate(),
                                  at=AT, author=AUTHOR, source_ref="k", registry=reg, approver="km-1176",
                                  approval_ref="breath:1")
    assert r["mandate"] == HEIR


def test_seal_key_closed_a_press_or_seal_key_field_is_refused(tmp_path):
    for breach in ("seal_key", "press_key", "sealing_key"):
        with pytest.raises(EstateRefused):
            open_key_epoch("fam", 1, ["a", "b"], extra={breach: "x"})


def test_the_succession_fence_refuses_escrow_custodian_second_authority(tmp_path):
    reg = _reg(tmp_path)
    estate = _estate(reg)
    for breach in ("escrow", "standing_escrow", "custodian", "key_custodian", "second_authority",
                   "succession_authority", "recovery_authority", "recovery_engine"):
        with pytest.raises(EstateRefused):
            execute_transfer(DECEDENT, HEIR, estate, "e", at=AT, author=AUTHOR, source_ref="t", registry=reg,
                             extra={breach: True})
    assert {"escrow", "custodian", "second_authority", "seal_key"}.issubset(ESTATE_BREACH_FIELDS)


def test_composes_the_sealed_design_layers_only():
    src = (pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "estate"
           / "generational_transfer.py")
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography", "zk_proofs",
                    "objects.registry", "objects.identity"):
            assert tok not in ln, f"S12 executes by composing the sealed design layers, not {tok}"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from ..")]
    assert sibling
    allowed = (".economy.livelihood_covenant", ".risk.protection_covenant", ".material.provision_covenant",
               ".economy.contribution")
    for ln in sibling:
        assert any(m in ln for m in allowed), f"only the sealed design layers (S10 V5 / S11 V05 / S9 / S10 V1) may be composed: {ln}"
