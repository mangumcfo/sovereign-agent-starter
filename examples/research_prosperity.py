#!/usr/bin/env python3
"""Example task: Research mechanisms for multi-generational prosperity."""

from sovereign_agent import SovereignAgent

def main():
    print("=== Sovereign Agent Example: Research Prosperity ===\n")
    agent = SovereignAgent("LGP-Research-1")
    print(f"Agent created. Public key (truncated): {str(agent.get_identity_public())[:64]}...\n")

    task = "Research and synthesize mechanisms for multi-generational prosperity"
    attestation = agent.act(task)

    print("Attested Result:")
    print(attestation["result"])
    print(f"\nMemory Root: {attestation['memory_root']}")
    print(f"Signature verified: {agent.verify_attestation(attestation)}")

if __name__ == "__main__":
    main()
