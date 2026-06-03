"""ARC guardrail demo — proves the card-first, dormant guardrail (KM's choice: build, don't auto-run).

Shows:
  1. ARC identifies GREEN Tier-1 candidates (eligible to surface as cards).
  2. A material (RED/YELLOW) obligation is REJECTED — the human gate stays hard.
  3. Even an eligible + card-ratified candidate does NOT auto-run while ARC is DORMANT (off).
  4. Only with ARC explicitly activated AND a good cadence would it auto-run (shown last, hypothetical).

Run:  PYTHONPATH=src python3 examples/arc_guardrail_demo.py
"""
from sovereign_agent.obligations.arc_guardrail import (
    arc_eligible, arc_guardrail, cadence_ok,
)

GREEN = {"id": "obl_green_1", "title": "Refresh the obligations master index", "owner": "gb",
         "classification": "C2", "material": False}
RED = {"id": "obl_red_1", "title": "FEC · propose_pooled_order (material)", "owner": "KM-1176",
       "classification": "C1", "material": True}


def line(label, d):
    print(f"  {label}: allow_autorun={d['allow_autorun']} · {d['status']}")
    for r in d["eligibility"] + d["cadence"]:
        print(f"      - {r}")


def main():
    print("ARC guardrail demo — KM choice: BUILD, do NOT activate (dormant).\n")

    print("1) GREEN Tier-1 candidate — eligible to surface as a card:")
    ok, reasons = arc_eligible(GREEN)
    print("   eligible:", ok)
    for r in reasons:
        print("     -", r)

    print("\n2) Material (RED) obligation — guardrail REJECTS autonomy:")
    line("RED", arc_guardrail(RED, card_ratified=True, arc_activated=True))
    assert arc_guardrail(RED, card_ratified=True, arc_activated=True)["allow_autorun"] is False

    print("\n3) Eligible + card-ratified, but ARC DORMANT (KM's standing choice) — still no auto-run:")
    line("GREEN (dormant)", arc_guardrail(GREEN, card_ratified=True, arc_activated=False))
    assert arc_guardrail(GREEN, card_ratified=True, arc_activated=False)["allow_autorun"] is False

    print("\n4) Eligible but NOT yet card-ratified — awaits the human card (card-first):")
    line("GREEN (no card)", arc_guardrail(GREEN, card_ratified=False, arc_activated=True))

    print("\n5) Hypothetical: if KM activated ARC AND card-ratified AND cadence holds — only then:")
    cad = cadence_ok(coherence=0.95, vitality=0.7, consecutive=1, max_consecutive=5)
    line("GREEN (activated, ratified)", arc_guardrail(GREEN, card_ratified=True, arc_activated=True, cadence=cad))

    print("\n6) Cadence guard (CONSTITUTION §2.1) pauses low coherence/vitality:")
    bad = cadence_ok(coherence=0.7, vitality=0.5, consecutive=6, max_consecutive=5)
    print("   cadence_ok:", bad[0])
    for r in bad[1]:
        print("     -", r)

    print("\n∞Δ∞ ARC guardrail proven: GREEN-only, card-first, DORMANT by default — human primacy structural. ∞Δ∞")


if __name__ == "__main__":
    main()
