#!/usr/bin/env python3
"""
Multi-Node Federation Demo — Attested Collaboration & Handoff

This demo shows the long-term vision of the Sovereign System:

- Multiple independent nodes (e.g., different family members, advisors, or entities)
- Secure, attested handoff of information (legacy notes, decisions, memory roots)
- Cross-node verification using sovereign attestations
- All without any central authority

This is the foundation for real mesh collaboration while remaining radically simple and local-first.
"""

from sovereign_agent import UniversalSovereignNode


def main():
    print("=" * 80)
    print("USN — MULTI-NODE FEDERATION DEMO (Attested Collaboration & Generational Handoff)")
    print("=" * 80)
    print()

    # Create two independent sovereign nodes
    print(">>> Creating independent sovereign nodes")
    family_head = UniversalSovereignNode("FamilyHead-Alpha", context_type="family")
    trusted_advisor = UniversalSovereignNode("TrustedAdvisor-Beta", context_type="family")

    # Register for local discovery simulation
    UniversalSovereignNode.register_node(family_head)
    UniversalSovereignNode.register_node(trusted_advisor)

    print(f"    Node 1: {family_head.name} (memory root: {family_head.get_memory_root()[:20]}...)")
    print(f"    Node 2: {trusted_advisor.name} (memory root: {trusted_advisor.get_memory_root()[:20]}...)")
    print()

    # Family head prepares an important legacy artifact
    print(">>> Family Head prepares an attested Legacy Note")
    legacy_payload = {
        "type": "Family Constitution Update 2026",
        "key_decision": "Establishment of the Mangum Legacy Trust",
        "memory_snapshot": family_head.get_memory_root(),
        "principles": "SOURCE / TRUTH / INTEGRITY / Lasting Generational Prosperity",
    }

    # Use the enhanced collaboration system
    handoff = family_head.collaborate_with_node(
        other_node=trusted_advisor,
        message="Please review and witness this generational decision.",
        payload=legacy_payload
    )

    print(f"    Handoff status: {handoff['status']}")
    print(f"    From: {handoff['from']} → To: {handoff['to']}")
    print(f"    Attestation recorded with sender memory root")
    print()

    # Trusted advisor receives and verifies the handoff
    print(">>> Trusted Advisor receives and verifies the attested handoff")
    print(f"    Received message: \"{handoff['message']}\"")
    print(f"    Payload summary: {str(handoff['payload'])[:80]}...")
    print(f"    Sender memory root: {handoff['sender_memory_root'][:28]}...")
    print(f"    Verifiable via USN attestation: {handoff['verifiable']}")
    print()

    # Advisor creates their own attestation of having witnessed/received it
    witness_attestation = trusted_advisor._self_attest("witnessed_handoff", {
        "from_node": family_head.name,
        "handoff_message": handoff['message'],
        "received_memory_root": handoff['sender_memory_root'],
    })

    print(">>> Trusted Advisor creates independent witness attestation")
    print(f"    Witness attestation created with advisor's memory root")
    print()

    # Discovery simulation
    print(">>> Local Node Discovery (light federation simulation)")
    known = UniversalSovereignNode.list_known_nodes()
    print(f"    Known nodes in local mesh: {known}")

    discovered = UniversalSovereignNode.discover_node("FamilyHead-Alpha")
    if discovered:
        print(f"    Successfully discovered: {discovered.name}")

    print("\n" + "=" * 80)
    print("Multi-node federation demo complete.")
    print("Attested handoffs between independent sovereign nodes — no central server required.")
    print("This is the seed of real generational and institutional mesh collaboration.")
    print("=" * 80)


if __name__ == "__main__":
    main()