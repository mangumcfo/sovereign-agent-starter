# -*- coding: utf-8 -*-
"""Proof-first tests for economy.livelihood (S10 Vol 2, Sovereign Livelihood).

Kill-targets pinned: composes-V01-only (verify_income) · a-livelihood-is-the-earner's-own-receipts ·
money-path-OFF (a proof, no held value) · weakest-party (established from receipts the earner holds).
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.economy.income import attribute_income
from sovereign_agent.economy.livelihood import attest_livelihood, LivelihoodStatus, IncomeRefused

EARNER, MANDATE, AUTHOR, AT = "ridgeline-kenn", "ridgeline-kenn", "Kenneth Mangum", "2026-08-09T01:00:00Z"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def _income(reg, earner, work, mandate, amount=None):
    r = attribute_income(earner, work, mandate=mandate, author=AUTHOR, source_ref=f"income:{work}", at=AT,
                         registry=reg, amount=amount)
    item = {"receipt": r, "work_ref": work}
    if amount is not None:
        item["amount"] = amount
    return item


def test_establishes_livelihood_from_owned_incomes(tmp_path):
    reg = _reg(tmp_path)
    incomes = [_income(reg, EARNER, "welding-qms", MANDATE, 1200.0),
               _income(reg, EARNER, "cad-consult", MANDATE, 800.0),
               _income(reg, EARNER, "site-survey", MANDATE)]
    st = attest_livelihood(EARNER, incomes)
    assert st.established is True
    assert st.verified_count == 3
    assert st.earner == EARNER


def test_livelihood_not_established_if_one_income_is_not_the_earners(tmp_path):
    reg = _reg(tmp_path)
    mine = _income(reg, EARNER, "welding-qms", MANDATE, 1200.0)
    someone_elses = _income(reg, "cedar-partner", "landscaping", "cedar-partner", 500.0)
    st = attest_livelihood(EARNER, [mine, someone_elses])   # a livelihood is only the earner's own
    assert st.established is False
    assert "not the earner's" in st.reason


def test_livelihood_detects_a_tampered_income(tmp_path):
    reg = _reg(tmp_path)
    good = _income(reg, EARNER, "welding-qms", MANDATE, 1200.0)
    tampered = dict(good, amount=9999.0)                     # claim a different figure than the receipt
    st = attest_livelihood(EARNER, [tampered])
    assert st.established is False


def test_empty_livelihood_not_established(tmp_path):
    st = attest_livelihood(EARNER, [])
    assert st.established is False and st.verified_count == 0


def test_composes_v01_only():
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "economy" / "livelihood.py"
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "objects.registry", "objects.identity", "provision_"):
            assert tok not in ln, f"livelihood must compose V01 (income) only, not {tok}"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from .")]
    assert sibling and all(".income" in ln for ln in sibling), "the only sibling import is the Income Primitive (V01)"


def test_weakest_party_verdict_is_a_plain_bool(tmp_path):
    reg = _reg(tmp_path)
    st = attest_livelihood(EARNER, [_income(reg, EARNER, "welding-qms", MANDATE, 1200.0)])
    assert isinstance(st, LivelihoodStatus) and isinstance(st.established, bool)
