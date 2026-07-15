#!/usr/bin/env python3
"""
Universal Sovereign Node — Playbook Loading Demo (Capstone Integration)

Demonstrates:
- Booting the USN
- Discovering and loading a real playbook from the Agentic AI Playbooks vault
- Treating it as an attested constitutional module
- Running a sample task (CFO-style attested financial reasoning)
- Full attestation chain using breathline_primitives

This shows how the Universal Sovereign Node acts as the executable capstone kernel for the entire series.
"""

from sovereign_agent import UniversalSovereignNode

def main():
    print("=" * 75)
    print("UNIVERSAL SOVEREIGN NODE — PLAYBOOK LOADING DEMO")
    print("Capstone for the Agentic AI Playbooks Series")
    print("=" * 75)
    print()

    # Boot the node in corporate context (natural home for CFO playbook)
    node = UniversalSovereignNode(
        name="CFO-Sovereign-Node-01",
        context_type="corporate",
        memory_path="./memory/cfo_node_memory.json"
    )

    print("Node Status:")
    print(node.get_status())
    print()

    # Discover available playbooks from the vault
    print("Discovering playbooks in the vault...")
    available = node.playbook_loader.discover_playbooks()
    print(f"Found {len(available)} playbooks: {available[:5]}..." if len(available) > 5 else available)
    print()

    # Load the CFO playbook as an attested constitutional module
    print("Loading '01_cfos_finance' as constitutional module...")
    module = node.load_playbook("01_cfos_finance")

    print("\nLoaded Module:")
    print(f"  ID: {module['id']}")
    print(f"  Title: {module['title']}")
    print(f"  Module Root (Merkle): {module['module_root']}")
    print(f"  Load Attestation: {module.get('load_attestation', {}).get('event', 'N/A')}")
    print()

    # Execute a role-based task using the loaded playbook's context
    print("Executing attested task using CFO playbook context...")
    task = "Generate an attested 12-month cash flow forecast with LGP risk analysis and governance audit trail"

    result = node.execute_role_action("cfo_agent", task, context={"playbook": "01_cfos_finance"})

    print("\nTask Result (Attested):")
    print(result.get("result", str(result)[:300]))
    print(f"\nMemory Root after task: {node.get_memory_root()}")
    print(f"Executing Role: {result.get('executing_role')}")

    print("\n" + "=" * 75)
    print("The Universal Sovereign Node has loaded a real playbook from the series")
    print("as a live, attested constitutional module and executed work against it.")
    print("This is the executable capstone behavior the series was designed for.")
    print("=" * 75)


if __name__ == "__main__":
    main()
