#!/usr/bin/env python3
"""
Example: Generate Sovereign Prosperity Plan

Demonstrates the enhanced SovereignAgent with:
- Constitutional Governor
- Economic capability
- Self-attestation
- Long-horizon LGP reasoning
"""

from sovereign_agent import SovereignAgent
from sovereign_agent.capabilities.economics import EconomicEngine

def main():
    print("=== Sovereign Agent: Generate Multi-Generational Prosperity Plan ===\n")

    agent = SovereignAgent("LGP-Prosperity-Architect", memory_path="./memory/prosperity_architect.json")

    # 1. Constitutional check (now substantive)
    task = "Develop a 100-year antifragile capital allocation and knowledge transfer plan for a sovereign family."
    check = agent.constitutional_check(task, {"horizon": 100, "consistent_with_past": True})
    print(f"Constitutional Score: {check['score']} | Approved: {check['approved']}")
    print("Rationale:", check['rationale'])
    print()

    # 2. Economic reasoning
    econ = EconomicEngine()
    strategy = econ.analyze_yield_strategy(capital=2_000_000, horizon_years=100, risk_tolerance="medium")
    print("Recommended Economic Strategy (100-year horizon):")
    print(strategy)
    print()

    # 3. Execute with full attestation
    attestation = agent.act(task, context={"economic_strategy": strategy})

    print("Final Attested Prosperity Plan Output:")
    print(attestation["result"])
    print(f"\nMemory Root: {attestation['memory_root']}")
    print(f"Constitutional Score of Action: {attestation.get('constitutional_score', 'N/A')}")

    print("\nAgent now holds a verifiable, attested multi-generational plan in its Merkle memory.")

if __name__ == "__main__":
    main()
