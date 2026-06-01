#!/usr/bin/env python3
"""
Family / Legacy Governance Demo — Light, Opt-in, Constitutional

This demo shows the *same* Universal Sovereign Node operating in sovereign/family mode
with optional light governance (policy + legacy handoff attestation).

Key principles demonstrated:
- Governance is opt-in and loadable (never forced)
- Same codebase serves both family LGP and heavily regulated corporate use
- Focus on generational handoff and light constitutional review
"""

from sovereign_agent import UniversalSovereignNode


def main():
    print("=" * 80)
    print("USN — FAMILY / LEGACY GOVERNANCE DEMO (Light, Opt-in, Generational)")
    print("=" * 80)
    print()

    print(">>> Booting USN in family context (light sovereign mode)")
    node = UniversalSovereignNode("FamilyLegacy-01", context_type="family")
    print(f"    Governance mode: {node.context_adapter.governance_mode}")
    print(f"    ComplianceEngine active: {node.compliance_engine is not None}")
    print()

    print(">>> Loading family_cfo_agent (sovereign-friendly role)")
    bound = node.load_role("family_cfo_agent")
    print(f"    Handler bound: {bound.handler is not None}")
    print()

    payload = {
        "financial_data": {"revenue": [420, 480, 510], "expenses": [280, 295, 310]},
        "forecast_horizon": 5,
        "focus": "generational_wealth"
    }

    print(">>> Executing with light constitutional review + attested legacy handoff")
    result = bound.process(
        payload=payload,
        principal_id="family-head",
        request_id="family-legacy-demo-001",
        action_class="produce_forecast_artifact"
    )

    print("\n--- Family Sovereign Result ---")
    print(f"Status: {result.get('status')}")
    print(f"Demo mode: {result.get('demo', False)}")

    # Demonstrate light, opt-in governance via legacy note
    print("\n>>> Preparing Attested Generational Legacy Handoff Note")
    try:
        legacy_note = {
            "type": "Family Legacy Handoff Note",
            "node_name": node.name,
            "context": node.context_adapter.context_type,
            "memory_root": node.get_memory_root(),
            "principles": "SOURCE / TRUTH / INTEGRITY / Lasting Generational Prosperity",
            "message": "This node's attested actions and memory are entrusted to the next generation.",
        }

        # Light attestation (sovereign floor)
        att = node._self_attest("family_legacy_handoff", legacy_note)
        legacy_note["attestation"] = att

        print("Legacy Note prepared with USN attestation.")
        print(f"  Memory Root: {legacy_note['memory_root'][:32]}...")
        print("  This note can be stored with the family constitution or will.")

    except Exception as e:
        print(f"  (Legacy note generation used graceful path: {e})")

    print("\n" + "=" * 80)
    print("Family governance demo complete.")
    print("Same USN. Light, opt-in governance. Full sovereignty preserved.")
    print("=" * 80)


if __name__ == "__main__":
    main()