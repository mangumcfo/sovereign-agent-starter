# -*- coding: utf-8 -*-
"""Proof-first tests for economy.attribution (S10 Vol 3, Sovereign Value Attribution).

Kill-targets pinned: composes-V01-only (attribute_income) · splits-are-records-not-value-movement
(money-path OFF) · each-contributor-owns-their-share (contributor mandate) · weakest-party (each
contributor verifies their share by receipt).
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.economy.income import MONEY_PATH_BREACH_FIELDS
from sovereign_agent.economy.attribution import attribute_value, verify_attribution, IncomeRefused, IncomeStatus

VALUE, AUTHOR, AT = "welding-qms-buildout", "Kenneth Mangum", "2026-08-09T01:00:00Z"
CONTRIBUTORS = [("ridgeline-kenn", "60"), ("cedar-partner", "40")]


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def test_attributes_value_across_contributors(tmp_path):
    rs = attribute_value(VALUE, CONTRIBUTORS, author=AUTHOR, source_ref="attr:welding", at=AT,
                         registry=_reg(tmp_path))
    assert set(rs) == {"ridgeline-kenn", "cedar-partner"}
    for who, share in CONTRIBUTORS:
        r = rs[who]
        assert r["kind"] == "income"
        assert r["payload"]["share"] == share and r["payload"]["value_ref"] == VALUE
        assert r["object_id"] == f"IncomeEvent:{who}:{VALUE}"


def test_each_contributor_owns_their_share(tmp_path):
    rs = attribute_value(VALUE, CONTRIBUTORS, author=AUTHOR, source_ref="attr:welding", at=AT,
                         registry=_reg(tmp_path))
    # each contributor's share is scoped to their OWN mandate — no central attributor owns the split
    assert rs["ridgeline-kenn"]["mandate"] == "ridgeline-kenn"
    assert rs["cedar-partner"]["mandate"] == "cedar-partner"


def test_verify_attribution_confirms_a_contributors_share(tmp_path):
    rs = attribute_value(VALUE, CONTRIBUTORS, author=AUTHOR, source_ref="attr:welding", at=AT,
                         registry=_reg(tmp_path))
    st = verify_attribution(rs["ridgeline-kenn"], "ridgeline-kenn", VALUE, "60")
    assert st.provisioned is True


def test_verify_attribution_detects_a_tampered_share(tmp_path):
    rs = attribute_value(VALUE, CONTRIBUTORS, author=AUTHOR, source_ref="attr:welding", at=AT,
                         registry=_reg(tmp_path))
    st = verify_attribution(rs["ridgeline-kenn"], "ridgeline-kenn", VALUE, "90")   # claim a bigger share
    assert st.provisioned is False


def test_attribution_records_are_money_path_off(tmp_path):
    rs = attribute_value(VALUE, CONTRIBUTORS, author=AUTHOR, source_ref="attr:welding", at=AT,
                         registry=_reg(tmp_path))
    for r in rs.values():
        assert set(k.lower() for k in r["payload"]).isdisjoint(MONEY_PATH_BREACH_FIELDS)


def test_empty_contributors_refused(tmp_path):
    with pytest.raises(IncomeRefused):
        attribute_value(VALUE, [], author=AUTHOR, source_ref="attr:welding", at=AT, registry=_reg(tmp_path))


def test_composes_v01_only():
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "economy" / "attribution.py"
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "objects.registry", "objects.identity", "provision_"):
            assert tok not in ln, f"attribution must compose V01 (income) only, not {tok}"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from .")]
    assert sibling and all(".income" in ln for ln in sibling), "the only sibling import is the Income Primitive (V01)"


def test_weakest_party_verdict_is_a_plain_bool(tmp_path):
    rs = attribute_value(VALUE, CONTRIBUTORS, author=AUTHOR, source_ref="attr:welding", at=AT,
                         registry=_reg(tmp_path))
    st = verify_attribution(rs["cedar-partner"], "cedar-partner", VALUE, "40")
    assert isinstance(st, IncomeStatus) and isinstance(st.provisioned, bool)
