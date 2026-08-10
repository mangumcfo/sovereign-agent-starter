# -*- coding: utf-8 -*-
"""Proof-first tests for estate.venture_continuity (S12 Vol 3:
Forkable Ventures, Business Continuity & Verifiable Handoff).

Kill-targets pinned:
- composes the sealed layers ONLY — the OPENER execute_transfer/verify_transfer (S12 V1), the governance skin
  fork_governance_skin (S11 V4), and the material covenant verify_under_covenant (S9, the F2 material-estate
  handoff fold); re-implements none; rolls no crypto; composes NOT the sibling key volume (V2, not-yet-sealed);
- capture_venture_state needs an id + a governance skin (a venture with no governance cannot be forked);
- fork_venture forks the governance into a new versioned skin for the heir (composition of S11 V4);
- handoff_package is complete iff the governance governs a class AND every material good verifies under S9 —
  the material-estate handoff; an ungoverned or unverified estate is not a complete handoff (deny-by-default);
- continue_venture RE-ATTRIBUTES the venture's estate to the heir via the sealed execute_transfer — continued
  iff the handoff is complete and the estate transfers; an incomplete handoff does not continue;
- THE SUCCESSION-FENCE: any escrow / custodian / handoff-firm / second-authority field is refused (continuity
  is re-attribution of owned records, not an escrowed handoff a firm releases); SEAL-KEY-CLOSED holds.
"""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.economy.contribution import record_contribution
from sovereign_agent.material.provision_covenant import provision_under_covenant
from sovereign_agent.risk.governance import load_governance_skin, GovernanceSkin
from sovereign_agent.estate.generational_transfer import verify_transfer, EstateRefused
from sovereign_agent.estate.venture_continuity import (
    VentureState, capture_venture_state, fork_venture, VentureHandoff, handoff_package, VentureStatus,
    continue_venture, VENTURE_BREACH_FIELDS,
)

DEC, HEIR, AUTHOR, AT = "ridgeline-kenn", "ridgeline-heir", "Kenneth Mangum", "2026-08-10T09:00:00Z"


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path / "node"))


def _skin():
    return load_governance_skin("ridgeline-mill", gated_classes=["dissolve_venture", "sell_major_asset"])


def _state(reg, *, material=True, livelihood=True):
    good = provision_under_covenant("good", {"id": "mill-lathe", "name": "lathe"}, mandate=DEC, author=AUTHOR,
                                    source_ref="m", at=AT, registry=reg)
    contrib = record_contribution(DEC, "milled_lumber", "aug-mill", contribution_class="metered", mandate=DEC,
                                  author=AUTHOR, source_ref="c", at=AT, registry=reg, amount=120.0)
    return capture_venture_state(
        "ridgeline-mill", _skin(),
        material=([{"receipt": good, "good": good["payload"]}] if material else []),
        livelihood=([{"kind": "contribution", "receipt": contrib, "work_ref": "aug-mill",
                      "contribution_class": "metered", "source": "milled_lumber", "amount": 120.0}]
                    if livelihood else []),
        relationships=[{"party": "cedar-supply", "receipt_ref": "contract-7"}])


def test_capture_venture_state_needs_an_id_and_a_governance_skin(tmp_path):
    reg = _reg(tmp_path)
    st = _state(reg)
    assert isinstance(st, VentureState) and st.venture_id == "ridgeline-mill"
    assert isinstance(st.governance, GovernanceSkin) and st.governance.gated_classes
    with pytest.raises(EstateRefused):
        capture_venture_state("", _skin())
    with pytest.raises(EstateRefused):
        capture_venture_state("v", "not-a-skin")               # a venture needs governance to be forkable


def test_fork_venture_forks_the_governance_for_the_heir(tmp_path):
    reg = _reg(tmp_path)
    st = _state(reg)
    forked = fork_venture(st, "heir-mill", add_gated=["hire_steward"], remove_gated=["sell_major_asset"])
    assert forked.venture_id == "heir-mill"
    assert "hire_steward" in forked.governance.gated_classes
    assert "sell_major_asset" not in forked.governance.gated_classes
    assert "dissolve_venture" in forked.governance.gated_classes      # preserved
    assert forked.material == st.material                             # same inheritable estate


def test_handoff_package_complete_only_when_governed_and_material_verifies(tmp_path):
    reg = _reg(tmp_path)
    pkg = handoff_package(_state(reg))
    assert isinstance(pkg, VentureHandoff) and pkg.complete is True and pkg.governed is True
    assert pkg.material_ok is True and pkg.goods == 1                 # the S9 material-estate handoff verified
    # a tampered material good breaks the handoff (deny-by-default)
    st = _state(reg)
    bad = dict(st.material[0]); bad["good"] = {**bad["good"], "id": "swapped"}
    st_bad = VentureState(st.venture_id, st.governance, (bad,), st.livelihood, st.relationships)
    assert handoff_package(st_bad).complete is False


def test_continue_venture_reattributes_the_estate_to_the_heir(tmp_path):
    reg = _reg(tmp_path)
    st = _state(reg)
    status = continue_venture(DEC, HEIR, st, "mill-2026", at=AT, author=AUTHOR, source_ref="t", registry=reg)
    assert isinstance(status, VentureStatus) and status.continued is True
    assert status.transfer is not None and status.transfer.transferred is True
    assert status.transfer.by_stack == {"material": True, "livelihood": True}
    assert "mine to continue" in status.reason
    # weakest-party: the heir verifies the venture estate passed to them from the receipt
    assert verify_transfer(status.transfer.receipt, HEIR, DEC, "mill-2026") is True


def test_an_incomplete_handoff_does_not_continue(tmp_path):
    reg = _reg(tmp_path)
    st = _state(reg)
    bad = dict(st.material[0]); bad["good"] = {**bad["good"], "id": "swapped"}
    st_bad = VentureState(st.venture_id, st.governance, (bad,), st.livelihood, st.relationships)
    status = continue_venture(DEC, HEIR, st_bad, "mill-2026", at=AT, author=AUTHOR, source_ref="t", registry=reg)
    assert status.continued is False and status.transfer is None


def test_the_succession_fence_refuses_escrow_custodian_handoff_firm(tmp_path):
    reg = _reg(tmp_path)
    st = _state(reg)
    for bad in ("escrow", "custodian", "handoff_firm", "business_broker", "second_authority", "venture_authority"):
        with pytest.raises(EstateRefused):
            continue_venture(DEC, HEIR, st, "m", at=AT, author=AUTHOR, source_ref="t", registry=reg,
                             extra={bad: "acme-succession-co"})
    assert {"escrow", "custodian", "handoff_firm", "second_authority"} <= VENTURE_BREACH_FIELDS


def test_seal_key_closed_a_press_or_seal_key_field_is_refused(tmp_path):
    reg = _reg(tmp_path)
    st = _state(reg)
    for bad in ("seal_key", "press_key", "sealing_key"):
        with pytest.raises(EstateRefused):
            fork_venture(st, "heir-mill", extra={bad: "x"})
    assert {"seal_key", "press_key", "sealing_key"} <= VENTURE_BREACH_FIELDS


def test_composes_the_sealed_design_layers_only_not_the_sibling_volume():
    import sovereign_agent.estate.venture_continuity as m
    src = __import__("pathlib").Path(m.__file__).read_text()
    assert "generational_transfer" in src and "governance" in src and "provision_covenant" in src  # V1+S11V4+S9
    assert "key_succession" not in src                          # NOT the not-yet-sealed sibling (V2)
