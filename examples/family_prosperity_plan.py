#!/usr/bin/env python3
"""
End-to-End: 50-Year Family Prosperity Plan using the self-contained Universal Sovereign Node.

NOTE (post-2026-05 unification): The capabilities/ layer (EconomicEngine, LegacyPlanner)
is retained for backward compatibility with earlier examples in the series but is
considered deprecated in favor of loading real roles directly from breathline-federation
via UniversalSovereignNode.load_role() / load_playbook() (see load_role_demo.py).

Run with minimal shell:
    python examples/family_prosperity_plan.py

(or set PYTHONPATH to src if not using the package in development mode)
"""

from sovereign_agent import UniversalSovereignNode
from sovereign_agent.capabilities.economics import EconomicEngine
from sovereign_agent.capabilities.legacy import LegacyPlanner

def main():
    print("=== Universal Sovereign Node — Family Prosperity Plan (Self-Contained) ===\n")

    # Pure Python boot — the package handles discovery
    node = UniversalSovereignNode(
        "LGP-Family-Architect",
        context_type="family",
        memory_path="./memory/family_prosperity.json"
    )

    print("Node initialized with auto-bootstrap.")
    print(node.get_status())
    print()

    # Economic reasoning
    econ = EconomicEngine()
    econ_plan = econ.lgp_capital_allocation(8_000_000, generations=3, threat_model="tyranny_or_inflation")

    # Legacy planning
    legacy = LegacyPlanner()
    will = legacy.create_sovereign_will_template(
        "Founding Generation", ["Gen2", "Gen3"],
        ["Bitcoin", "Land", "Businesses"],
        ["Constitutional knowledge", "Technical tradecraft"]
    )
    governance = legacy.create_family_governance_protocol(
        "Sovereign Lineage", ["Founders"], ["Gen2", "Gen3"],
        ["SOURCE", "TRUTH", "INTEGRITY", "LGP"]
    )

    # Execute full attested plan
    attestation = node.act(
        "Generate complete 50-year family prosperity plan",
        context={"economic": econ_plan, "legacy": will, "governance": governance}
    )

    print("Attested Plan:")
    print(attestation["result"])
    print(f"\nMemory Root: {attestation['memory_root']}")
    print(f"Node Memory Root: {node.get_memory_root()}")

    print("\nPlan is fully verifiable and inheritable by future generations.")

if __name__ == "__main__":
    main()
