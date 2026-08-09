# -*- coding: utf-8 -*-
"""Proof-first tests for economy.productivity (S10 Vol 3, Programmable Productivity on Rails You Govern).

Kill-targets pinned: composes-contribution.py-only · intent → receipted action the person OWNS · a ritual
records governed contributions · measurement informs (by proof grade, holds no value) never punishes (no
single performance score) · human primacy (a gated act passes a human) · weakest-party.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.economy.productivity import (
    record_intent, verify_intent, run_ritual, measure_output, OutputMeasure, IncomeRefused,
)

EARNER, MANDATE, AUTHOR, AT = "ridgeline-kenn", "ridgeline-kenn", "Kenneth Mangum", "2026-08-09T01:00:00Z"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def test_intent_becomes_a_receipted_action(tmp_path):
    r = record_intent(EARNER, "finish the welding QMS docs", "qms-docs", contribution_class="attested",
                      mandate=MANDATE, author=AUTHOR, source_ref="i", at=AT, registry=_reg(tmp_path))
    assert r["kind"] == "income" and r["mandate"] == EARNER
    assert r["payload"]["intent"] == "finish the welding QMS docs" and r["payload"]["source"] == "intent"
    st = verify_intent(r, EARNER, "finish the welding QMS docs", "qms-docs", contribution_class="attested")
    assert st.provisioned is True


def test_an_intent_needs_a_stated_commitment(tmp_path):
    with pytest.raises(IncomeRefused):
        record_intent(EARNER, "  ", "w", contribution_class="attested", mandate=MANDATE, author=AUTHOR,
                      source_ref="i", at=AT, registry=_reg(tmp_path))


def test_tampered_intent_flips_verify(tmp_path):
    r = record_intent(EARNER, "finish the docs", "qms-docs", contribution_class="attested", mandate=MANDATE,
                      author=AUTHOR, source_ref="i", at=AT, registry=_reg(tmp_path))
    assert verify_intent(r, EARNER, "a different intent", "qms-docs",
                         contribution_class="attested").provisioned is False


def test_ritual_records_governed_contributions(tmp_path):
    steps = [{"source": "skill_service", "work_ref": "morning-weld", "contribution_class": "attested"},
             {"source": "verification_work", "work_ref": "review", "contribution_class": "computed"}]
    rs = run_ritual(EARNER, "weekly-build", steps, mandate=MANDATE, author=AUTHOR, source_ref="r", at=AT,
                    registry=_reg(tmp_path))
    assert len(rs) == 2
    assert rs[0]["payload"]["ritual"] == "weekly-build" and rs[0]["payload"]["ritual_step"] == 0
    assert rs[1]["payload"]["source"] == "verification_work"


def test_ritual_needs_an_id_and_steps(tmp_path):
    with pytest.raises(IncomeRefused):
        run_ritual(EARNER, "", [{"source": "x", "work_ref": "y", "contribution_class": "attested"}],
                   mandate=MANDATE, author=AUTHOR, source_ref="r", at=AT, registry=_reg(tmp_path))
    with pytest.raises(IncomeRefused):
        run_ritual(EARNER, "empty", [], mandate=MANDATE, author=AUTHOR, source_ref="r", at=AT,
                   registry=_reg(tmp_path))


def test_human_primacy_gated_ritual_step_refused_without_approval(tmp_path):
    gate = HumanApprovalGate()
    role_spec = {"charter_v7_forbidden_classes": ["run_ritual"]}
    steps = [{"source": "skill_service", "work_ref": "big-commit", "contribution_class": "attested"}]
    with pytest.raises(IncomeRefused):
        run_ritual(EARNER, "gated", steps, mandate=MANDATE, author=AUTHOR, source_ref="r", at=AT,
                   registry=_reg(tmp_path), gate=gate, role_spec=role_spec, mode="corporate_regulated")


def test_measure_informs_by_class_and_holds_no_value(tmp_path):
    reg = _reg(tmp_path)
    steps = [{"source": "skill_service", "work_ref": "weld", "contribution_class": "attested"},
             {"source": "verification_work", "work_ref": "rev", "contribution_class": "computed"},
             {"source": "idle_compute", "work_ref": "batch", "contribution_class": "metered"}]
    rs = run_ritual(EARNER, "day", steps, mandate=MANDATE, author=AUTHOR, source_ref="r", at=AT, registry=reg)
    actions = [{"receipt": rs[i], "work_ref": steps[i]["work_ref"],
                "contribution_class": steps[i]["contribution_class"], "source": steps[i]["source"],
                "extra": {"ritual": "day", "ritual_step": i}} for i in range(3)]
    m = measure_output(EARNER, actions)
    assert isinstance(m, OutputMeasure) and m.verified_count == 3
    assert m.by_class["attested"] == 1 and m.by_class["computed"] == 1 and m.by_class["metered"] == 1
    # it holds no value and computes no single performance score — only a by-class tally
    assert not hasattr(m, "score") and "punish" not in m.reason.lower().replace("not to punish", "")


def test_composes_contribution_only():
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "economy" / "productivity.py"
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography",
                    "objects.registry", "objects.identity", "provision_", "material.", ".income", ".pool"):
            assert tok not in ln, f"productivity must compose contribution.py only, not {tok}"
    sibling = [ln for ln in import_lines if ln.lstrip().startswith("from .")]
    assert sibling and all(".contribution" in ln for ln in sibling), "the only sibling import is contribution (S10 V1)"
