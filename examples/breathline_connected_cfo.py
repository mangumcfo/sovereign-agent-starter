#!/usr/bin/env python3
"""
Breathline Connected CFO — The Flagship USN Experience

This is the canonical demonstration of the Universal Sovereign Node as the
easiest, most sovereign, and most credible agentic system for both personal
and regulated use.

The experience begins with the question:
    "Are you connected to the breathline?"

Everything else flows from there.
"""

from sovereign_agent import connect_to_breathline, UniversalSovereignNode


def main():
    print("\n" + "∞Δ" * 25)

    # The magical one-liner that changes everything
    breathline = connect_to_breathline(auto_detect_context=True, print_welcome=True)

    if not breathline["connected"]:
        print("Connection to the breathline could not be established.")
        return

    # Create the node using the recommended context
    context = breathline.get("recommended_context", "sovereign")
    print(f">>> Activating Universal Sovereign Node in '{context}' context")

    node = UniversalSovereignNode(
        "BreathlineCFO-01",
        context_type=context
    )

    print(f"    Governance mode: {node.context_adapter.governance_mode}")
    print(f"    ComplianceEngine active: {node.compliance_engine is not None}")

    # Load a compliance-aware role (the capstone integration)
    print("\n>>> Loading regulated role from the living breathline-federation")
    try:
        cfo = node.load_role("cfo_agent")
        print(f"    cfo_agent loaded and bound: {cfo.handler is not None}")
    except Exception as e:
        print(f"    (Role loading note: {e})")
        cfo = None

    # Demonstrate governance when in regulated mode
    if node.context_adapter.governance_mode.startswith("corporate") and node.compliance_engine:
        print("\n>>> Executing under full policy-as-code governance")
        payload = {
            "financial_data": {"revenue": [1200, 1350], "expenses": [800, 820]},
            "forecast_horizon": 3
        }

        # Policy-driven check (dynamic)
        verdict = node.compliance_engine.run_policy_compliance_check(
            role_spec=getattr(cfo, "spec", {}),
            action_class="produce_forecast_artifact",
            context={"materiality": "board"}
        )
        print(f"    Policy verdict: approved={verdict.approved}, risk={verdict.risk_score}")

        # Execute with full hardened audit + receipt
        if cfo:
            result = cfo.process(payload, "km-1176", "breathline-flagship-001")
            comp = result.get("compliance_attestation", {})
            print(f"    SIX-style receipt generated: {'six_style_receipt' in comp}")
            print(f"    Chain-of-custody active: {bool(comp.get('prev_receipt_hash'))}")

    print("\n" + "∞Δ" * 25)
    print("You are connected to the breathline.")
    print("The Universal Sovereign Node is the runtime for the entire series.")
    print("∞Δ" * 25 + "\n")


if __name__ == "__main__":
    main()
