# -*- coding: utf-8 -*-
"""Proof-first tests for risk.protection_covenant (S11 Vol 5, the CAPSTONE:
Generational Continuity & Full Synthesis).

Kill-targets pinned:
- composes the sealed S11 V1–V4 surfaces ONLY (mutual_protection/advanced_pooling/group_applications/
  governance) — invents no new engine, rolls no cryptography, underwrites/prices nothing;
- a whole protection stack is inherited iff EVERY element verifies as owned + intact — ONE honest indicator
  (weakest-party: a resourceless heir reads one green light, "this is mine now");
- a foreign or tampered element fails the whole inheritance;
- an unknown element kind is refused (deny-by-default);
- THE SUCCESSION-FENCE: any escrow / held-obligation / recovery-engine / second-authority field on an element
  is REFUSED — inheritance is re-attribution of owned records, not an escrowed obligation released by an
  authority;
- an empty stack is not inherited; the element kinds are the sealed S11 V1–V4 surfaces.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.risk.mutual_protection import form_protection_pool, record_premium, record_claim
from sovereign_agent.risk.advanced_pooling import build_attestation_chain
from sovereign_agent.risk.group_applications import form_group_pool, group_premium
from sovereign_agent.risk.protection_covenant import (
    inherit_protection, verify_stack_element, protection_stream_kinds,
    ProtectionStatus, PROTECTION_STREAM_KINDS, PROTECTION_SUCCESSION_BREACH_FIELDS, IncomeRefused,
)

OWNER, B, AUTHOR, AT = "ridgeline-kenn", "cedar-partner", "Kenneth Mangum", "2026-08-10T08:00:00Z"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def _stack(reg):
    """The whole protection stack a family builds — a premium (V1), a claim (V1), a group premium (V3), an
    attestation chain (V2), and a governance skin (V4). Returns the stack the covenant reads."""
    pool = form_protection_pool("ridgeline-aid", (OWNER, B))
    gpool = form_group_pool("welders-guild", (OWNER, B), group_class="professional")
    prem = record_premium(pool, OWNER, "aug-prem", contribution_class="attested", author=AUTHOR, source_ref="s",
                          at=AT, registry=reg, amount=25.0)
    clm = record_claim(OWNER, pool, "storm", claim_class="attested", author=AUTHOR, source_ref="s", at=AT,
                       registry=reg, amount=300.0)
    gprem = group_premium(gpool, OWNER, "guild-dues", group_class="professional", contribution_class="attested",
                          author=AUTHOR, source_ref="s", at=AT, registry=reg, amount=50.0)
    chain = build_attestation_chain(OWNER, pool, "big-storm", claim_class="attested",
                                    attestors=[{"party": B, "work_ref": "b-att"}], registry=reg, at=AT,
                                    author=AUTHOR, source_ref="s", amount=400.0)
    return pool, gpool, [
        {"kind": "premium", "receipt": prem, "pool": pool, "work_ref": "aug-prem",
         "contribution_class": "attested", "amount": 25.0},
        {"kind": "claim", "receipt": clm, "pool": pool, "work_ref": "storm", "claim_class": "attested",
         "amount": 300.0},
        {"kind": "group_premium", "receipt": gprem, "pool": gpool, "work_ref": "guild-dues",
         "group_class": "professional", "contribution_class": "attested", "amount": 50.0},
        {"kind": "attestation_chain", "chain": chain, "pool": pool, "work_ref": "big-storm",
         "claim_class": "attested", "attestors": [{"party": B, "work_ref": "b-att"}], "amount": 400.0},
        {"kind": "governance_skin", "skin_id": "ridgeline-gov", "gated_classes": ["approve_large_claim"],
         "limits": {"approve_large_claim": 500.0}, "version": "v1"},
    ]


def test_a_whole_protection_stack_is_inherited(tmp_path):
    _, _, stack = _stack(_reg(tmp_path))
    st = inherit_protection(OWNER, stack)
    assert isinstance(st, ProtectionStatus)
    assert st.inherited is True and st.verified_count == 5
    assert st.by_kind == {"premium": 1, "claim": 1, "group_premium": 1, "attestation_chain": 1,
                          "governance_skin": 1}
    assert "this is mine now" in st.reason


def test_one_honest_indicator_is_a_plain_bool(tmp_path):
    _, _, stack = _stack(_reg(tmp_path))
    st = inherit_protection(OWNER, stack)
    assert isinstance(st.inherited, bool)
    assert not hasattr(st, "value") and not hasattr(st, "balance")


def test_a_tampered_element_fails_the_whole_inheritance(tmp_path):
    _, _, stack = _stack(_reg(tmp_path))
    stack[1] = {**stack[1], "claim_class": "computed"}     # the claim's grade is tampered
    st = inherit_protection(OWNER, stack)
    assert st.inherited is False and st.verified_count == 4
    assert "claim" in st.reason


def test_a_foreign_heir_does_not_inherit(tmp_path):
    _, _, stack = _stack(_reg(tmp_path))
    assert inherit_protection("some-other-heir", stack).inherited is False


def test_an_unknown_element_kind_is_refused(tmp_path):
    with pytest.raises(IncomeRefused):
        verify_stack_element(OWNER, {"kind": "invented", "receipt": {}})
    with pytest.raises(IncomeRefused):
        inherit_protection(OWNER, [{"kind": "invented"}])


def test_the_succession_fence_refuses_escrow_or_second_authority(tmp_path):
    _, _, stack = _stack(_reg(tmp_path))
    base = stack[0]
    for breach in ("escrow", "standing_escrow", "escrowed_obligation", "held_obligation", "release_authority",
                   "second_authority", "succession_authority", "recovery_engine"):
        with pytest.raises(IncomeRefused):
            verify_stack_element(OWNER, {**base, breach: True})
        with pytest.raises(IncomeRefused):
            inherit_protection(OWNER, [{**base, breach: True}])
    assert {"escrow", "second_authority", "escrowed_obligation"}.issubset(PROTECTION_SUCCESSION_BREACH_FIELDS)


def test_an_empty_protection_stack_is_not_inherited(tmp_path):
    st = inherit_protection(OWNER, [])
    assert st.inherited is False and st.verified_count == 0


def test_stream_kinds_are_the_sealed_s11_surfaces():
    assert protection_stream_kinds() == ["premium", "claim", "group_premium", "attestation_chain",
                                         "governance_skin"]


def test_composes_the_sealed_s11_volumes_only():
    src = (pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "risk"
           / "protection_covenant.py")
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography", "zk_proofs",
                    "objects.registry", "objects.identity", "material.", "provision_"):
            assert tok not in ln, f"the covenant composes the sealed S11 V1–V4 surfaces only, not {tok}"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from .")]
    assert sibling
    allowed = (".mutual_protection", ".advanced_pooling", ".group_applications", ".governance")
    for ln in sibling:
        assert any(m in ln for m in allowed), f"only the sealed S11 V1–V4 surfaces may be composed: {ln}"
