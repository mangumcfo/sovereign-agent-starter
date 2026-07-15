#!/usr/bin/env python3
"""
Example: Loading a Playbook as Constitutional Module

Demonstrates the Universal Sovereign Node loading "01_cfos_finance" (CFO Financial Intelligence)
from the Agentic AI Playbooks series as an attested constitutional module.
"""

from sovereign_agent.universal_sovereign_node import create_universal_sovereign_node

def main():
    print("=== Universal Sovereign Node — Loading CFO Playbook ===\n")

    # Create node in "corporate" context (or "family" for family_cfo)
    node = create_universal_sovereign_node(name="CFO-Node-01", context="corporate")

    print("Node initialized:")
    print(node.get_status())
    print()

    # Load the CFO playbook as attested constitutional module
    print("Loading playbook '01_cfos_finance' as constitutional module...")
    module = node.load_playbook("01_cfos_finance")

    print("\nLoaded Playbook Module:")
    print(f"  ID: {module['id']}")
    print(f"  Title: {module['title']}")
    print(f"  Core Roles: {module['core_roles']}")
    print(f"  Attestation: {module.get('load_attestation', {})}")

    print("\nNode status after loading:")
    print(node.get_status())

    # Example: Execute a role action from the loaded playbook
    print("\nExecuting role action from loaded playbook (cfo_agent:generate_forecast)...")
    try:
        result = node.execute_role_action("cfo_agent", "generate_forecast", {"period": "Q3 2026"})
        print("Action result (attested):", result.get("status"))
    except Exception as e:
        print(f"Role action note: {e} (roles are illustrative in this scaffold)")

    print("\n=== CFO Playbook successfully loaded as attested constitutional module ===")

if __name__ == "__main__":
    main()
