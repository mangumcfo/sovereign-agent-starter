# -*- coding: utf-8 -*-
"""Proof-first tests for economy.contribution (S10 Vol 1, Sovereign Livelihood — Building Income &
Productivity on Rails You Own).

Kill-targets pinned: composes-income.py-only · proof-grade-honest (unknown class refused; tampered
class/source flips) · money-path-OFF (inherited) · concrete-sources record with their honest default class ·
human-primacy (a gated contribution passes a human) · personal-ledger (Atlas Ch6) tallies by class and holds
iff every contribution is the earner's own · weakest-party verdict is a plain bool.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.economy.income import MONEY_PATH_BREACH_FIELDS
from sovereign_agent.economy.contribution import (
    record_contribution, verify_contribution, contribution_ledger,
    contribute_surplus_energy, contribute_idle_compute, contribute_skill_service,
    CONTRIBUTION_CLASSES, SOURCE_DEFAULT_CLASS, IncomeRefused, IncomeStatus, LedgerStatus,
)

EARNER, MANDATE, AUTHOR, AT = "ridgeline-kenn", "ridgeline-kenn", "Kenneth Mangum", "2026-08-09T01:00:00Z"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def test_records_a_contribution_as_an_owned_proof_graded_income(tmp_path):
    r = record_contribution(EARNER, "surplus_energy", "aug-dispatch", contribution_class="metered",
                            mandate=MANDATE, author=AUTHOR, source_ref="meter:aug", at=AT,
                            registry=_reg(tmp_path), amount=42.0, unit="kWh-credits")
    assert r["kind"] == "income"
    assert r["payload"]["contribution_class"] == "metered"
    assert r["payload"]["source"] == "surplus_energy"
    assert r["payload"]["amount"] == 42.0
    st = verify_contribution(r, EARNER, "aug-dispatch", contribution_class="metered",
                             source="surplus_energy", amount=42.0, unit="kWh-credits")
    assert st.provisioned is True


def test_unknown_contribution_class_is_refused(tmp_path):
    with pytest.raises(IncomeRefused):
        record_contribution(EARNER, "skill_service", "logo-design", contribution_class="guessed",
                            mandate=MANDATE, author=AUTHOR, source_ref="s", at=AT, registry=_reg(tmp_path))


def test_a_contribution_needs_a_concrete_source(tmp_path):
    with pytest.raises(IncomeRefused):
        record_contribution(EARNER, "  ", "work", contribution_class="attested",
                            mandate=MANDATE, author=AUTHOR, source_ref="s", at=AT, registry=_reg(tmp_path))


def test_money_path_off_inherited(tmp_path):
    # the contribution's attribution fields carry no in-node money-path field...
    r = record_contribution(EARNER, "idle_compute", "batch-77", contribution_class="metered",
                            mandate=MANDATE, author=AUTHOR, source_ref="c", at=AT, registry=_reg(tmp_path),
                            amount=10.0, port_ref="port:ext-rail")
    assert set(k.lower() for k in r["payload"]).isdisjoint(MONEY_PATH_BREACH_FIELDS)
    # ...and a breach field in extra is refused by the composed Income Primitive
    with pytest.raises(IncomeRefused):
        record_contribution(EARNER, "idle_compute", "batch-78", contribution_class="metered",
                            mandate=MANDATE, author=AUTHOR, source_ref="c", at=AT, registry=_reg(tmp_path),
                            extra={"balance": 999})


def test_tampered_class_or_source_flips_the_light(tmp_path):
    r = record_contribution(EARNER, "skill_service", "logo-design", contribution_class="attested",
                            mandate=MANDATE, author=AUTHOR, source_ref="s", at=AT, registry=_reg(tmp_path))
    # claim a richer proof grade than recorded
    assert verify_contribution(r, EARNER, "logo-design", contribution_class="computed",
                               source="skill_service").provisioned is False
    # claim a different source than recorded
    assert verify_contribution(r, EARNER, "logo-design", contribution_class="attested",
                               source="surplus_energy").provisioned is False


def test_concrete_sources_record_with_their_honest_default_class(tmp_path):
    reg = _reg(tmp_path)
    e = contribute_surplus_energy(EARNER, "aug-dispatch", mandate=MANDATE, author=AUTHOR,
                                  source_ref="m", at=AT, registry=reg, amount=42.0)
    c = contribute_idle_compute(EARNER, "batch-77", mandate=MANDATE, author=AUTHOR,
                                source_ref="m", at=AT, registry=reg, amount=10.0)
    s = contribute_skill_service(EARNER, "logo-design", mandate=MANDATE, author=AUTHOR,
                                 source_ref="a", at=AT, registry=reg)
    assert e["payload"]["contribution_class"] == SOURCE_DEFAULT_CLASS["surplus_energy"] == "metered"
    assert c["payload"]["contribution_class"] == "metered" and c["payload"]["source"] == "idle_compute"
    assert s["payload"]["contribution_class"] == "attested" and s["payload"]["source"] == "skill_service"


def test_human_primacy_gated_contribution_refused_without_approval(tmp_path):
    gate = HumanApprovalGate()
    role_spec = {"charter_v7_forbidden_classes": ["record_contribution"]}
    with pytest.raises(IncomeRefused):
        record_contribution(EARNER, "skill_service", "big-job", contribution_class="attested",
                            mandate=MANDATE, author=AUTHOR, source_ref="s", at=AT, registry=_reg(tmp_path),
                            gate=gate, role_spec=role_spec, mode="corporate_regulated")


def test_personal_ledger_tallies_by_class_and_holds_only_the_earners_own(tmp_path):
    reg = _reg(tmp_path)
    items = []
    for src, work, cc, amt in [("surplus_energy", "aug-dispatch", "metered", 42.0),
                               ("idle_compute", "batch-77", "metered", 10.0),
                               ("skill_service", "logo-design", "attested", None)]:
        r = record_contribution(EARNER, src, work, contribution_class=cc, mandate=MANDATE, author=AUTHOR,
                                source_ref="x", at=AT, registry=reg, amount=amt)
        items.append({"receipt": r, "work_ref": work, "contribution_class": cc, "source": src,
                      "amount": amt})
    st = contribution_ledger(EARNER, items)
    assert st.provisioned is True and st.verified_count == 3
    assert st.by_class["metered"] == 2 and st.by_class["attested"] == 1
    # a contribution that is not the earner's own fails the whole ledger
    other = record_contribution("cedar-partner", "skill_service", "fence", contribution_class="attested",
                                mandate="cedar-partner", author=AUTHOR, source_ref="x", at=AT, registry=reg)
    items.append({"receipt": other, "work_ref": "fence", "contribution_class": "attested",
                  "source": "skill_service"})
    assert contribution_ledger(EARNER, items).provisioned is False


def test_empty_ledger_not_established(tmp_path):
    st = contribution_ledger(EARNER, [])
    assert st.provisioned is False and st.verified_count == 0


def test_composes_income_only():
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "economy" / "contribution.py"
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography",
                    "objects.registry", "objects.identity", "provision_", "material."):
            assert tok not in ln, f"contribution must compose income.py only, not {tok}"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from .")]
    assert sibling and all(".income" in ln for ln in sibling), "the only sibling import is the Income Primitive"


def test_weakest_party_verdict_is_a_plain_bool(tmp_path):
    r = contribute_surplus_energy(EARNER, "aug-dispatch", mandate=MANDATE, author=AUTHOR,
                                  source_ref="m", at=AT, registry=_reg(tmp_path), amount=42.0)
    st = verify_contribution(r, EARNER, "aug-dispatch", contribution_class="metered", source="surplus_energy",
                             amount=42.0)
    assert isinstance(st, IncomeStatus) and isinstance(st.provisioned, bool)
    lst = contribution_ledger(EARNER, [{"receipt": r, "work_ref": "aug-dispatch",
                                        "contribution_class": "metered", "source": "surplus_energy",
                                        "amount": 42.0}])
    assert isinstance(lst, LedgerStatus) and isinstance(lst.provisioned, bool)
