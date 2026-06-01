#!/usr/bin/env python3
"""
Example: Research Antifragile Yield Strategy

Demonstrates Research + Economic capabilities with constitutional oversight.
"""

from sovereign_agent import SovereignAgent
from sovereign_agent.capabilities.research import ResearchModule
from sovereign_agent.capabilities.economics import EconomicEngine

def main():
    print("=== Sovereign Agent: Research Antifragile Yield Strategy ===\n")

    agent = SovereignAgent("Yield-Researcher")

    research = ResearchModule()
    econ = EconomicEngine()

    query = "Identify the most antifragile, multi-generational real yield strategies in an era of monetary instability and technological disruption."

    # Research with attestation hook
    findings = research.research_and_attest(query)
    print("Research Findings (to be attested):")
    print(findings)
    print()

    # Economic synthesis
    strategy = econ.analyze_yield_strategy(capital=1_500_000, horizon_years=75, risk_tolerance="medium")
    print("Synthesized Economic Recommendation:")
    print(strategy)

    # Agent executes with full constitutional + attestation pipeline
    attestation = agent.act(f"Produce attested research + capital allocation plan for: {query}")

    print("\nAgent Attestation:")
    print(attestation["result"])
    print(f"\nMemory Root: {attestation['memory_root']}")

if __name__ == "__main__":
    main()
