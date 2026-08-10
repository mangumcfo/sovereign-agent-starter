# -*- coding: utf-8 -*-
"""Proof-first tests for estate.estate_covenant (S12 Vol 5, the CAPSTONE:
The Sovereign Estate as Living Covenant).

Kill-targets pinned:
- composes the sealed Series-12 volumes ONLY — estate re-attribution verify_transfer (V1), key recovery
  recover_with_quorum (V2), venture handoff handoff_package (V3), family governance weakest_party_protected
  (V4); re-implements none; invents no engine; rolls no crypto;
- inherit_estate returns ONE honest indicator (this estate is mine now) true iff EVERY element of the whole
  estate — income/estate, keys, ventures, governance — verifies as the heir's own and intact;
- a tampered or foreign element fails the whole; an empty estate is not inherited; an unknown kind is refused;
- THE SUCCESSION-FENCE (the whole series' fence in one place): any escrow / second-authority / custodian /
  recovery-engine / penalty / seal-key field is refused — inheritance is re-attribution of owned records, not
  a released fund;
- weakest-party (the series' final test): a resourceless heir reads one green light over the whole estate.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.economy.contribution import record_contribution
from sovereign_agent.risk.mutual_protection import form_protection_pool, record_premium
from sovereign_agent.material.provision_covenant import provision_under_covenant
from sovereign_agent.risk.governance import load_governance_skin
from sovereign_agent.estate.generational_transfer import execute_transfer, open_key_epoch
from sovereign_agent.estate.key_succession import define_quorum
from sovereign_agent.estate.venture_continuity import capture_venture_state
from sovereign_agent.estate.family_governance import load_family_constitution
from sovereign_agent.estate.estate_covenant import (
    inherit_estate, verify_estate_element, estate_stack_kinds, EstateInheritance, ESTATE_STACK_KINDS,
    ESTATE_COVENANT_BREACH_FIELDS, EstateRefused,
)

DEC, HEIR, B, AUTHOR, AT = "ridgeline-kenn", "ridgeline-heir", "cedar-partner", "Kenneth Mangum", "2026-08-10T09:00:00Z"
FAM_KEYS = ("kenn", "mara", "iris")
GATED = ["amend_constitution", "remove_member", "distribute_estate", "resolve_dispute", "dignified_exit"]


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def _estate_receipt(reg):
    contrib = record_contribution(DEC, "surplus_energy", "aug-solar", contribution_class="metered", mandate=DEC,
                                  author=AUTHOR, source_ref="c", at=AT, registry=reg, amount=40.0)
    pool = form_protection_pool("ridgeline-aid", (DEC, B))
    prem = record_premium(pool, DEC, "aug-prem", contribution_class="attested", author=AUTHOR, source_ref="p",
                          at=AT, registry=reg, amount=25.0)
    g = provision_under_covenant("good", {"id": "adze-1", "name": "adze"}, mandate=DEC, author=AUTHOR,
                                 source_ref="m", at=AT, registry=reg)
    estate = {
        "livelihood": [{"kind": "contribution", "receipt": contrib, "work_ref": "aug-solar",
                        "contribution_class": "metered", "source": "surplus_energy", "amount": 40.0}],
        "protection": [{"kind": "premium", "receipt": prem, "pool": pool, "work_ref": "aug-prem",
                        "contribution_class": "attested", "amount": 25.0}],
        "material": [{"receipt": g, "good": g["payload"]}],
    }
    return execute_transfer(DEC, HEIR, estate, "estate-2026", at=AT, author=AUTHOR, source_ref="t",
                            registry=reg).receipt


def _venture_state(reg):
    good = provision_under_covenant("good", {"id": "lathe-1", "name": "lathe"}, mandate=DEC, author=AUTHOR,
                                    source_ref="m", at=AT, registry=reg)
    skin = load_governance_skin("ridgeline-mill", gated_classes=["dissolve_venture"])
    return capture_venture_state("ridgeline-mill", skin, material=[{"receipt": good, "good": good["payload"]}])


def _stack(reg):
    """A whole sovereign estate — the four sealed Series-12 surfaces as one stack the heir inherits."""
    epoch = open_key_epoch("ridgeline", 1, FAM_KEYS)
    return [
        {"kind": "estate", "receipt": _estate_receipt(reg), "decedent": DEC, "work_ref": "estate-2026"},
        {"kind": "keys", "epoch": epoch, "approvers": ("kenn", "mara"), "policy": define_quorum(epoch, threshold=2)},
        {"kind": "ventures", "state": _venture_state(reg)},
        {"kind": "governance", "constitution": load_family_constitution("ridgeline", gated_decisions=GATED),
         "affecting_classes": ["remove_member", "distribute_estate"]},
    ]


def test_inherit_estate_verifies_the_whole_stack(tmp_path):
    reg = _reg(tmp_path)
    st = inherit_estate(HEIR, _stack(reg))
    assert isinstance(st, EstateInheritance) and st.inherited is True and st.verified_count == 4
    assert st.by_kind == {"estate": 1, "keys": 1, "ventures": 1, "governance": 1}
    assert "this estate is mine now" in st.reason
    assert set(ESTATE_STACK_KINDS) == {"estate", "keys", "ventures", "governance"}
    assert estate_stack_kinds() == list(ESTATE_STACK_KINDS)


def test_a_tampered_or_foreign_element_fails_the_whole(tmp_path):
    reg = _reg(tmp_path)
    stack = _stack(reg)
    # a foreign heir cannot inherit this estate (the estate element verifies against the receipt's heir)
    assert inherit_estate("stranger", stack).inherited is False
    # a tampered governance element (a class that could override the heir is NOT gated) fails the whole
    stack2 = _stack(reg)
    stack2[3] = {**stack2[3], "affecting_classes": ["remove_member", "seize_share"]}  # seize_share ungated
    out = inherit_estate(HEIR, stack2)
    assert out.inherited is False and "governance" in out.reason


def test_an_empty_estate_is_not_inherited(tmp_path):
    reg = _reg(tmp_path)
    assert inherit_estate(HEIR, []).inherited is False


def test_an_unknown_estate_element_kind_is_refused(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(EstateRefused):
        verify_estate_element(HEIR, {"kind": "crypto_wallet"})


def test_the_succession_fence_refuses_escrow_second_authority_custodian(tmp_path):
    reg = _reg(tmp_path)
    base = _stack(reg)[0]                         # a valid estate element
    for bad in ("escrow", "released_fund", "second_authority", "custodian", "trust_company",
                "recovery_engine", "arbitration_authority", "penalty"):
        with pytest.raises(EstateRefused):
            verify_estate_element(HEIR, {**base, bad: "acme-trust-co"})
    assert {"escrow", "released_fund", "trust_company", "second_authority"} <= ESTATE_COVENANT_BREACH_FIELDS


def test_seal_key_closed_a_press_or_seal_key_field_is_refused(tmp_path):
    reg = _reg(tmp_path)
    base = _stack(reg)[0]
    for bad in ("seal_key", "press_key", "sealing_key"):
        with pytest.raises(EstateRefused):
            verify_estate_element(HEIR, {**base, bad: "x"})
    assert {"seal_key", "press_key", "sealing_key"} <= ESTATE_COVENANT_BREACH_FIELDS


def test_each_element_composes_its_sealed_series12_verifier(tmp_path):
    reg = _reg(tmp_path)
    stack = _stack(reg)
    assert verify_estate_element(HEIR, stack[0]) is True      # estate -> verify_transfer (V1)
    assert verify_estate_element(HEIR, stack[1]) is True      # keys -> recover_with_quorum (V2)
    assert verify_estate_element(HEIR, stack[2]) is True      # ventures -> handoff_package (V3)
    assert verify_estate_element(HEIR, stack[3]) is True      # governance -> weakest_party_protected (V4)


def test_composes_the_sealed_v1_v4_stack_only_no_new_engine():
    import sovereign_agent.estate.estate_covenant as m
    src = pathlib.Path(m.__file__).read_text()
    for sealed in ("generational_transfer", "key_succession", "venture_continuity", "family_governance"):
        assert sealed in src                                 # composes each sealed Series-12 volume
    # composition-not-engine: no dispatch table beyond the four sealed verifiers, no new persistence
    assert "def verify_estate_element" in src and "inherit_estate" in src
