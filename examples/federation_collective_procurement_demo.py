#!/usr/bin/env python3
"""
Federation Collective Procurement (FEC) Demo — R-52 Packet Example 3 (from 2026-06-02 B51 voice capture)

Exercises:
- Current ObligationLedger (R-23 Phase 1 in this starter) with packet_payload + citation_bundle.
- Simulated B51-style handoff trace (using patterns from multi_mandate_handoff_demo).
- GREEN → YELLOW → close with E2 evidence (node receipt stub).
- Full citation back to the exact capture session (export 2026-06-02_034153_capture-session_9156c992).

This is the first runnable sketch of the "B to F / C to F" value optimization vision:
- ZK-private profile pooling (stub)
- Agent swarm optimization via handoff chain (B51)
- Guild-style supply coordination (B26 evolution)
- Value to families first (LGP)
- Receipted close on the live ledger pattern

Run:
  python examples/federation_collective_procurement_demo.py

Honesty: Uses the starter's standalone ledger (no live the node cylinder). Gate is simulated.
Real human gate + full B51 production handoff_handler + Helix render + SIX anchor come after R-52 seal + R-53 gate.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# Import the live R-23 ledger implementation (vendored B32 patterns, hard boundary respected)
from sovereign_agent.obligations.ledger import ObligationLedger, EvidenceTier


def banner(text: str) -> None:
    print(f"\n{'='*70}")
    print(text)
    print('='*70)


def detail(label: str, value: str) -> None:
    print(f"  {label:28s} : {value}")


def main() -> None:
    banner("USN — FEDERATION COLLECTIVE PROCUREMENT (FEC) DEMO")
    print("Source thought: 2026-06-02 voice capture (B51 cyl_9156c99236ea)")
    print("Packet: Level 1 'federation_procurement_coordinator' (R-52 example 3)")
    print("Cites: B26 (guild evolution) + B25 (federation) + B51 (handoffs) + B35 (surfaces)")
    print("Ledger: node-local obligations (R-23 Phase 1) — the host's live seal chain is never touched.")

    # Resolve a demo root (node-local, never the protected live seal chain)
    demo_root = Path(__file__).resolve().parents[1] / "memory" / "obligations" / "fec_demo"
    demo_root.mkdir(parents=True, exist_ok=True)

    # Wire a simple simulated gate (Phase 2 will replace with real breath-gate + HumanApprovalGate)
    def simulated_gate(action: str, obligation: dict) -> dict:
        # In real use: this is the Atrium / NLP human disposition (the operator for R-53)
        if action == "approve":
            return {"status": "approved", "by": "the operator-NLP", "note": "Voice seed packet approved for first human-gated re-seat."}
        return {"status": "approved"}

    def stub_attestor(action_class: str, principal: str, payload: dict, summary: str) -> dict:
        # In real node: USN._self_attest or ComplianceEngine path
        receipt_hash = f"node_rcpt_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        return {
            "receipt_hash": receipt_hash,
            "principal": principal,
            "action_class": action_class,
            "summary": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    led = ObligationLedger(
        root=demo_root,
        principal_id="family_head_alpha",
        gate=simulated_gate,
        attestor=stub_attestor,
    )

    # The packet payload — directly from the logged capture + R-52 contract draft
    packet_payload = {
        "packet_id": "pkt_20260602_fec_procurement_coordinator_v1",
        "level": 1,
        "title": "Federation Procurement Coordinator — ZK-Pooled Buying Power, Guild Value Optimization & C2F/B2F Coordination",
        "subtitle": "Agent-orchestrated, privacy-preserving collective procurement and supply-chain guilds (voice seed 2026-06-02)",
        "role_spec": {
            "id": "federation_procurement_coordinator",
            "action_classes": [
                "pool_procurement_requests",
                "generate_zk_statistical_profile",
                "match_to_guild_or_pool",
                "run_optimization_coordination",
                "propose_pooled_order",
                "execute_value_distribution",
                "attest_receipts_to_SIX",
            ],
        },
        "surfaces": {
            "helix": {"manifest_id": "federation_pool_cockpit_v1", "targets": ["atrium_card", "portal_flow"]},
            "atrium": {"card_type": "federation_procurement_review"},
        },
        "tests": ["test_zk_profile_privacy", "test_handoff_chain_GREEN_to_close", "test_RED_escalation_on_material_pool"],
        "LGP_alignment": "Direct value optimization to families (C2F) and businesses (B2F). Guild re-coordination serves LGP north-star. No raw private data leaves sovereign boundary.",
        "citation_bundle": [
            {
                "book": "B26 Yield Organisms & XRPL Economic Seeds",
                "section_anchor": "collective_procurement_guilds",
                "passage_hash": "sha256:9350cf097bf5cd7d87e408db6952b643aafaf0845889a0b4106fca0690648dfc",
                "human_seed": {
                    "export_id": "2026-06-02_034153_capture-session_9156c992",
                    "session_id": "cyl_9156c99236ea",
                    "entry_ids": ["cap_4a5a0a7554b5", "cap_fd60428b8242"],
                    "session_root_hash": "sha256:409d1bf92a28c611873a9eaf4edf5a1fc91ddec91c02b01d2e06e21cd291493d",
                    "source_artifact": "artifacts/B51_Captured_Thought_Federation_Collective_Economic_Coordination_2026-06-02.md",
                },
            },
            {"book": "B25 Sovereign Federation Architecture", "section_anchor": "resonant_shards"},
            {"book": "B51 Agent-to-Agent Handoffs (A4)", "section_anchor": "A4 for economic swarms"},
            {"book": "B35 Helix Protocol", "section_anchor": "federation_pool_cockpit_render"},
        ],
    }

    banner("1. OPEN — Debit (draft B32 obligation carrying the FEC packet)")
    ob = led.open(
        title="Open FEC Procurement Coordinator packet (from 2026-06-02 voice seed)",
        owner="family_head_alpha",
        classification="C1",
        intent="First Level 1 economic packet: ZK-pooled procurement + B51 handoffs + guild value to families",
        ref="R-52 / R-53 + B51_Captured_Thought_2026-06-02 + capture export 2026-06-02_034153_capture-session_9156c992",
        material=True,
    )
    # Attach the packet (current ledger stores via intent/ref; R-52 will add native packet_payload field)
    ob["packet_payload"] = packet_payload
    ob["packet_level"] = 1
    print(json.dumps({k: v for k, v in ob.items() if k in ("id", "title", "packet_level", "draft", "material")}, indent=2))

    banner("2. B51-STYLE HANDOFF CHAIN (simulated aligned intelligences)")
    print("ResearchAgent (ZK profiles) → OptimizerSwarm (helix match + value calc) → Negotiator → ValueDistributor")
    handoff_trace = [
        {"from": "ResearchAgent", "to": "OptimizerSwarm", "goal_state": "GREEN", "note": "ZK statistical profiles for 12 families + 3 businesses generated (no raw data leaked)."},
        {"from": "OptimizerSwarm", "to": "Negotiator", "goal_state": "GREEN", "note": "Matched to 2 contract manufacturers + Amazon bulk terms. Projected +18% value to families."},
        {"from": "Negotiator", "to": "ValueDistributor", "goal_state": "YELLOW", "note": "Pooled order draft ready. Material commitment — requires human disposition (R-53 gate)."},
    ]
    for h in handoff_trace:
        detail(f"{h['from']} → {h['to']}", f"{h['goal_state']} — {h['note'][:60]}...")

    banner("3. APPROVE — Human (NLP) disposition via breath-gate (R-53 target)")
    try:
        appr = led.approve(ob["id"], approved_by="the operator (NLP gate per R-53)", rationale="Voice seed packet approved. First governed re-seat of B51 A4 primitives into economic coordination role.")
        detail("Disposition", appr.get("disposition", "approved"))
    except Exception as e:
        print(f"  Gate denied (expected in stricter mode): {e}")

    banner("4. CLOSE — Credit with E2 evidence (receipted, node-attested)")
    evidence = (
        "E2: FEC packet sealed. "
        "handoff_trace.json (B51 primitives exercised). "
        "zk_profiles_stub.json (privacy preserved). "
        "pooled_order_draft_v1.pdf (contract manufacturer + Amazon terms). "
        "value_distribution_ledger.csv (families first: +18% effective purchasing power). "
        "node_receipt: node_rcpt_... (USN attestor). "
        "six_candidate: six-rcpt-... (B31 pattern). "
        f"citation: {packet_payload['citation_bundle'][0]['human_seed']['export_id']}"
    )
    closed = led.close(
        ob["id"],
        evidence=evidence,
        evidence_tier=EvidenceTier.E2_VERIFIED.value,
        closed_by="family_head_alpha",
    )
    detail("Receipt minted", closed.get("receipt", {}).get("receipt_id", "rcpt_..."))
    detail("Evidence tier", closed.get("evidence_tier", "E2"))
    if "node_receipt_hash" in closed.get("receipt", {}):
        detail("Node receipt hash", closed["receipt"]["node_receipt_hash"])

    banner("5. REPLAY & VERIFY")
    state = led.replay()
    print(f"  Open: {len(state['open'])} | Closed: {len(state['closed'])} | Chain OK: {led.verify_chain()}")

    banner("6. CITATION (immutable human source)")
    seed = packet_payload["citation_bundle"][0]["human_seed"]
    print(f"  Export: {seed['export_id']}")
    print(f"  Session: {seed['session_id']}")
    print(f"  Merkle root: {seed['session_root_hash'][:32]}...")
    print(f"  Artifact: {seed['source_artifact']}")
    print("  This packet is now a typed B32 obligation. Ready for Helix render + Mait flow integration.")

    banner("Done — FEC packet demo complete")
    print("Next (real path):")
    print("  - R-52 seal of the contract + this packet as example 3")
    print("  - R-53: the operator human gate on live ledger (non-sim)")
    print("  - Wire real B51 handoff_handler + AgentBus (from molt B51 exports)")
    print("  - Helix (B35) renders the federation_pool_cockpit inside Mait portal / Atrium")
    print("  - Close produces real SIX receipt (B31)")
    print()
    print("The 2026-06-02 voice thought is now logged, packetized, and runnable against the R-23 ledger.")
    print("∞Δ∞ Capture. Chain. Prove. Packet. ∞Δ∞")


if __name__ == "__main__":
    main()
