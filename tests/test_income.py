# -*- coding: utf-8 -*-
"""Proof-first tests for economy.income (S10 Vol 1, The Income Primitive, the S10 opener).

Kill-targets pinned: records/attributes-never-moves-or-settles · money-path-OFF (in-node money-path field
refused; amount+port_ref+credit-splits permitted) · owned-by-the-earner / no-in-node-custodian ·
verify-ownership-by-receipt (weakest-party) · human-primacy · composes-bridge-rolls-no-crypto.
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry, MandateViolation
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate
from sovereign_agent.economy.income import (
    attribute_income,
    verify_income,
    income_record,
    IncomeRefused,
    IncomeStatus,
    MONEY_PATH_BREACH_FIELDS,
)

EARNER, WORK = "ridgeline-kenn", "welding-qms-buildout"
MANDATE, SRC, AT, AUTHOR = "ridgeline-kenn", "income:ridgeline-welding", "2026-08-09T00:00:00Z", "Kenneth Mangum"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def test_attributes_income_as_owned_governed_object(tmp_path):
    r = attribute_income(EARNER, WORK, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                         registry=_reg(tmp_path))
    assert r["kind"] == "income"
    assert r["mandate"] == MANDATE          # owned by the earner (its mandate)
    assert r["object_id"] == "IncomeEvent:ridgeline-kenn:welding-qms-buildout"
    assert r["payload"]["earner"] == EARNER and r["payload"]["work_ref"] == WORK
    assert r["version_hash"]


def test_amount_and_port_directive_permitted(tmp_path):
    # PERMITTED carve-outs: record an amount (attribution) + reference a Port directive (value crosses the rail)
    r = attribute_income(EARNER, WORK, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                         registry=_reg(tmp_path), amount=1200.0, unit="credits", port_ref="port-receipt-abc123")
    assert r["payload"]["amount"] == 1200.0 and r["payload"]["unit"] == "credits"
    assert r["payload"]["port_ref"] == "port-receipt-abc123"


def test_split_credit_as_records_permitted(tmp_path):
    # PERMITTED: split credit as records (extra attribution fields)
    r = attribute_income(EARNER, WORK, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                         registry=_reg(tmp_path), extra={"credit_split": "kenn:60,partner:40"})
    assert r["payload"]["credit_split"] == "kenn:60,partner:40"


def test_receipt_carries_no_in_node_money_path_field(tmp_path):
    r = attribute_income(EARNER, WORK, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                         registry=_reg(tmp_path), amount=1200.0, port_ref="port-abc")
    assert set(k.lower() for k in r["payload"]).isdisjoint(MONEY_PATH_BREACH_FIELDS)


@pytest.mark.parametrize("breach", ["balance", "custody", "settle", "wallet", "token", "mint", "bearer", "yield", "apy"])
def test_money_path_breach_field_refused(tmp_path, breach):
    # BREACH -> refused: any in-node field that holds/moves/custodies/settles value or mints a bearer instrument
    with pytest.raises(IncomeRefused):
        attribute_income(EARNER, WORK, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                         registry=_reg(tmp_path), extra={breach: 500})


def test_verify_income_confirms_ownership_by_receipt(tmp_path):
    # the earner verifies OWNERSHIP from the receipt alone — no platform, no balance shown to them
    r = attribute_income(EARNER, WORK, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                         registry=_reg(tmp_path), amount=1200.0)
    st = verify_income(r, EARNER, WORK, amount=1200.0)
    assert st.provisioned is True and st.reason == "provisioned"


def test_verify_income_detects_a_tampered_attribution(tmp_path):
    r = attribute_income(EARNER, WORK, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                         registry=_reg(tmp_path), amount=1200.0)
    st = verify_income(r, "impostor-platform", WORK, amount=1200.0)   # someone else claims the earning
    assert st.provisioned is False


def test_no_in_node_custodian_two_earners_own_theirs(tmp_path):
    # the intermediary that owns your income stream — refused: each earner owns theirs, in their own registry
    kenn = _reg(tmp_path, "kenn")
    partner = _reg(tmp_path, "partner")
    rk = attribute_income(EARNER, WORK, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT, registry=kenn)
    rp = attribute_income("cedar-partner", "landscaping-job", mandate="cedar-partner", author=AUTHOR,
                          source_ref="income:cedar-landscaping", at=AT, registry=partner)
    assert len(kenn.entries()) == 1 and len(partner.entries()) == 1
    # each verifies their OWN ownership by receipt; no shared custodian holds either stream
    assert verify_income(rk, EARNER, WORK).provisioned is True
    assert verify_income(rp, "cedar-partner", "landscaping-job").provisioned is True


def test_human_primacy_gated_income_refused_without_approval(tmp_path):
    gate = HumanApprovalGate()
    role_spec = {"charter_v7_forbidden_classes": ["attribute_income"]}
    with pytest.raises(IncomeRefused):
        attribute_income(EARNER, WORK, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                         registry=_reg(tmp_path), gate=gate, role_spec=role_spec, mode="corporate_regulated")


def test_composes_the_bridge_rolls_no_crypto():
    # composes the s9_01 bridge (verify_provision) + the Object Model; rolls no crypto of its own
    src = pathlib.Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "economy" / "income.py"
    import_lines = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                    if ln.lstrip().startswith(("import ", "from "))]
    for ln in import_lines:
        for tok in ("hashlib", "hmac", "ecdsa", "secrets", "cryptography"):
            assert tok not in ln.lower(), f"income must not roll its own {tok} — compose the sealed floors"
    joined = " ".join(import_lines)
    assert "provision_local" in joined and "objects.identity" in joined, "compose the s9_01 bridge + Object Model"


def test_weakest_party_verdict_is_a_plain_bool(tmp_path):
    r = attribute_income(EARNER, WORK, mandate=MANDATE, author=AUTHOR, source_ref=SRC, at=AT,
                         registry=_reg(tmp_path))
    st = verify_income(r, EARNER, WORK)
    assert isinstance(st, IncomeStatus) and isinstance(st.provisioned, bool)
