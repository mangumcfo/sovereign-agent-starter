"""ARC autonomy guardrail (CONSTITUTION §2.1) — audit 2026-06-13d #17 (was zero-coverage).

A fail-open-class boundary: a regression letting allow_autorun=True past the operator's gate would auto-execute
without ratification. These pin the truth table: dormant-by-default, GREEN-Tier-1-only, cadence gates.
"""
from sovereign_agent.obligations.arc_guardrail import (
    arc_candidates, arc_eligible, cadence_ok, arc_guardrail,
)
from sovereign_agent.obligations.ledger import ObligationLedger

GREEN = {"classification": "C2", "material": False}


def test_eligibility_green_only():
    assert arc_eligible(GREEN)[0] is True
    assert arc_eligible({**GREEN, "material": True})[0] is False          # material → never
    assert arc_eligible({**GREEN, "classification": "C1"})[0] is False    # non-GREEN → never


def test_dormant_unless_activated():
    """Eligible + ratified + cadence-ok but NOT activated ⇒ still no auto-run (the operator's standing choice)."""
    r = arc_guardrail(GREEN, card_ratified=True, arc_activated=False, cadence=(True, []))
    assert r["allow_autorun"] is False and "DORMANT" in r["status"]


def test_awaiting_ratification_blocks():
    r = arc_guardrail(GREEN, card_ratified=False, arc_activated=True, cadence=(True, []))
    assert r["allow_autorun"] is False and "ratification" in r["status"]


def test_would_autorun_only_when_all_four_hold():
    r = arc_guardrail(GREEN, card_ratified=True, arc_activated=True, cadence=(True, []))
    assert r["allow_autorun"] is True


def test_cadence_gates():
    assert cadence_ok(0.95, 0.8, 0)[0] is True
    assert cadence_ok(0.85, 0.8, 0)[0] is False    # coherence < 0.9
    assert cadence_ok(0.95, 0.5, 0)[0] is False    # vitality < 0.6
    assert cadence_ok(0.95, 0.8, 5)[0] is False     # at max_consecutive → renew consent


def test_cadence_pause_blocks_autorun():
    r = arc_guardrail(GREEN, card_ratified=True, arc_activated=True, cadence=cadence_ok(0.5, 0.5, 0))
    assert r["allow_autorun"] is False and "cadence" in r["status"].lower()


def test_arc_candidates_green_non_material_only(tmp_path):
    led = ObligationLedger(root=str(tmp_path / "obl"), principal_id="node")
    g = led.open("green routine", classification="C2", material=False)
    led.open("material gate", classification="C1", material=True)
    led.open("constitutional", classification="C1", material=False)
    ids = {c["id"] for c in arc_candidates(led)}
    assert ids == {g["id"]}    # only the GREEN non-material open obligation surfaces
