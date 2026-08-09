# -*- coding: utf-8 -*-
"""Proof-first tests for economy.livelihood_covenant (S10 Vol 5, the CAPSTONE:
Designing Income Systems That Outlive You).

Kill-targets pinned:
- composes the sealed S10 V01–V04 verify functions ONLY (contribution/pool/productivity/compliance) — invents
  no new recovery/succession/escrow engine, rolls no cryptography;
- a whole livelihood is inherited iff EVERY stream verifies as the owner's own — ONE honest indicator
  (weakest-party: a resourceless heir reads one green light, "this is mine now");
- a foreign or tampered stream fails the whole inheritance;
- an unknown stream kind is refused (deny-by-default; a covenant composes only the four sealed streams);
- THE SUCCESSION-FENCE: any in-node escrow / standing-held value / recovery-succession-engine / second
  authority field on a stream is REFUSED — inheritance is re-attribution of ownership RECORDS, not a held
  value released by an authority (kill-target: the fund-custodian your heirs must beg to release);
- an empty livelihood is not inherited.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.economy.contribution import record_contribution
from sovereign_agent.economy.pool import form_pool, contribute_to_pool
from sovereign_agent.economy.productivity import record_intent
from sovereign_agent.economy.compliance import record_tax_event
from sovereign_agent.economy.livelihood_covenant import (
    inherit_livelihood, verify_stream, livelihood_stream_kinds,
    LivelihoodStatus, SUCCESSION_BREACH_FIELDS, IncomeRefused, IncomeStatus,
)

OWNER, MANDATE, AUTHOR, AT = "ridgeline-kenn", "ridgeline-kenn", "Kenneth Mangum", "2026-08-09T02:00:00Z"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def _whole_livelihood(reg):
    """The four sealed S10 streams a person builds — a contribution (V1), a pooled contribution (V2), a
    productivity intent (V3), a tax record (V4). Returns the streams list the covenant reads."""
    contrib = record_contribution(OWNER, "surplus_energy", "aug-solar-surplus", contribution_class="metered",
                                  mandate=MANDATE, author=AUTHOR, source_ref="c:1", at=AT, registry=reg,
                                  amount=40.0)
    pool = form_pool("ridgeline-mutual", (OWNER, "cedar-partner"))
    pooled = contribute_to_pool(pool, OWNER, "verification_work", "aug-pool-verify",
                                contribution_class="computed", author=AUTHOR, source_ref="p:1", at=AT,
                                registry=reg, amount=12.0)
    intent = record_intent(OWNER, "close-the-august-books", "aug-books", contribution_class="attested",
                           mandate=MANDATE, author=AUTHOR, source_ref="i:1", at=AT, registry=reg)
    tax = record_tax_event(OWNER, "aug-self-employment", category="self_employment", mandate=MANDATE,
                           author=AUTHOR, source_ref="t:1", at=AT, registry=reg, amount=1200.0)
    return pool, [
        {"kind": "contribution", "receipt": contrib, "work_ref": "aug-solar-surplus",
         "contribution_class": "metered", "source": "surplus_energy", "amount": 40.0},
        {"kind": "pool", "receipt": pooled, "pool": pool, "work_ref": "aug-pool-verify",
         "contribution_class": "computed", "source": "verification_work", "amount": 12.0},
        {"kind": "productivity", "receipt": intent, "work_ref": "aug-books",
         "contribution_class": "attested", "intent": "close-the-august-books"},
        {"kind": "tax", "receipt": tax, "work_ref": "aug-self-employment", "category": "self_employment",
         "amount": 1200.0},
    ]


def test_a_whole_livelihood_of_all_four_streams_is_inherited(tmp_path):
    _, streams = _whole_livelihood(_reg(tmp_path))
    st = inherit_livelihood(OWNER, streams)
    assert isinstance(st, LivelihoodStatus)
    assert st.inherited is True and st.verified_count == 4
    assert st.by_kind == {"contribution": 1, "pool": 1, "productivity": 1, "tax": 1}
    assert "this is mine now" in st.reason


def test_one_honest_indicator_is_a_plain_bool(tmp_path):
    # weakest-party: the resourceless heir reads ONE green light — not a score, not a value
    _, streams = _whole_livelihood(_reg(tmp_path))
    st = inherit_livelihood(OWNER, streams)
    assert isinstance(st.inherited, bool)
    assert not hasattr(st, "value") and not hasattr(st, "balance")


def test_a_tampered_stream_fails_the_whole_inheritance(tmp_path):
    _, streams = _whole_livelihood(_reg(tmp_path))
    streams[3] = {**streams[3], "category": "capital"}   # the tax record's category is tampered
    st = inherit_livelihood(OWNER, streams)
    assert st.inherited is False and st.verified_count == 3
    assert "tax" in st.reason


def test_a_foreign_stream_is_not_inherited_by_this_owner(tmp_path):
    _, streams = _whole_livelihood(_reg(tmp_path))
    assert inherit_livelihood("some-other-heir", streams).inherited is False


def test_an_unknown_stream_kind_is_refused(tmp_path):
    with pytest.raises(IncomeRefused):
        verify_stream(OWNER, {"kind": "invented", "receipt": {}, "work_ref": "x"})
    with pytest.raises(IncomeRefused):
        inherit_livelihood(OWNER, [{"kind": "invented", "receipt": {}}])


def test_the_succession_fence_refuses_any_escrow_or_second_authority(tmp_path):
    reg = _reg(tmp_path)
    _, streams = _whole_livelihood(reg)
    base = streams[0]
    for breach in ("escrow", "standing_escrow", "release_authority", "second_authority",
                   "succession_authority", "recovery_engine", "fund_custodian", "held_value"):
        with pytest.raises(IncomeRefused):
            verify_stream(OWNER, {**base, breach: True})
        with pytest.raises(IncomeRefused):
            inherit_livelihood(OWNER, [{**base, breach: True}])
    assert {"escrow", "second_authority", "fund_custodian", "held_value"}.issubset(SUCCESSION_BREACH_FIELDS)


def test_an_empty_livelihood_is_not_inherited(tmp_path):
    st = inherit_livelihood(OWNER, [])
    assert st.inherited is False and st.verified_count == 0


def test_stream_kinds_are_the_four_sealed_s10_volumes():
    assert livelihood_stream_kinds() == ["contribution", "pool", "productivity", "tax"]


def test_composes_the_sealed_s10_volumes_only():
    src = (pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "economy"
           / "livelihood_covenant.py")
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography",
                    "objects.registry", "objects.identity", "material.", "provision_"):
            assert tok not in ln, f"the covenant composes the sealed S10 verify fns only, not {tok}"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from .")]
    assert sibling, "the covenant must compose sibling economy modules"
    allowed = (".contribution", ".pool", ".productivity", ".compliance")
    for ln in sibling:
        assert any(mod in ln for mod in allowed), f"only the sealed S10 V01–V04 siblings may be composed: {ln}"
