#!/usr/bin/env python3
"""
USN Regulated CFO Demo — Hardened Enterprise Governance

This demo showcases the hardened governance layer:

- corporate_regulated context with strict defaults
- Dynamic policy awareness (via loaded federation roles + compliance_block)
- Full chain-of-custody AuditTrail (prev_receipt_hash linking)
- SIX-style cryptographic receipts (signed with node identity + compliance metadata)
- Risk scoring + policy checks
- Human approval gate simulation with escalation notes
- Real execution through compliance-aware roles from breathline-federation

The same USN remains fully functional for sovereign/family use cases.
"""

from sovereign_agent import UniversalSovereignNode


def main():
    print("=" * 80)
    print("USN — REGULATED CFO DEMO (Hardened Playbook 6 + SIX Governance)")
    print("=" * 80)
    print()

    # Boot in the strictest mode
    print(">>> Booting USN in corporate_regulated mode (full hardening active)")
    node = UniversalSovereignNode("RegulatedCFO-01", context_type="corporate_regulated")
    print(f"    Governance mode: {node.context_adapter.governance_mode}")
    print(f"    ComplianceEngine: {node.compliance_engine is not None}")
    print()

    # Load a real role that has compliance hooks
    print(">>> Loading cfo_agent (compliance-aware role from federation)")
    bound = node.load_role("cfo_agent")
    print(f"    Handler bound: {bound.handler is not None}")
    print()

    payload = {
        "financial_data": {"revenue": [1200, 1350, 1100], "expenses": [800, 820, 790]},
        "forecast_horizon": 6,
        "materiality": "board_reporting"
    }

    # Explicit policy + risk check (hardened path)
    print(">>> Running hardened PolicyComplianceCheck + Risk Scoring")
    verdict = node.compliance_engine.run_policy_compliance_check(
        role_spec=bound.spec or {},
        action_class="produce_forecast_artifact",
        context={"materiality": "board_reporting"}
    )
    print(f"    Approved: {verdict.approved} | Risk: {verdict.risk_score}")
    print(f"    Rationale: {verdict.rationale}")
    print()

    # Human gate simulation (required in regulated mode for material actions)
    if verdict.required_approvals or node.context_adapter.governance_mode == "corporate_regulated":
        print(">>> Human Approval Gate + Escalation (simulated)")
        approval_req = node.compliance_engine.request_human_approval(
            record=type("obj", (object,), {"event": "board_forecast"})(),  # minimal object for demo
            policy_note="Board-level forecast requires documented human sign-off per SOX/fiduciary policy"
        )
        print(f"    Status: {approval_req['status']}")
        print(f"    Policy note: {approval_req['policy_note']}")
        print()

    # Execute with full hardened audit & receipt generation
    print(">>> Executing with full AuditTrail + Chain-of-Custody + SIX-style Receipt")
    result = bound.process(
        payload=payload,
        principal_id="owner",
        request_id="regulated-cfo-demo-001"
    )

    print("\n--- Hardened Governed Result ---")
    print(f"Status: {result.get('status')}")
    comp_att = result.get("compliance_attestation", {})
    audit = comp_att.get("audit_record")

    if audit:
        print(f"Risk Level: {audit.risk_level}")
        print(f"Chain link (prev_receipt_hash): {audit.prev_receipt_hash[:32] if audit.prev_receipt_hash else 'Genesis'}...")
        print(f"Current receipt_hash: {audit.receipt_hash[:32] if audit.receipt_hash else 'N/A'}...")

    six_receipt = comp_att.get("six_style_receipt", {})
    if six_receipt:
        print(f"SIX-style receipt generated: Yes (node signature present: {'node_identity' in six_receipt.get('signatures', {})})")
        print(f"Compliance block: {six_receipt.get('compliance_block', {})}")

    # Show the audit chain
    print("\n>>> Audit Trail (SOX-style immutable chain)")
    trail = node.compliance_engine.get_audit_trail(limit=3)
    for i, rec in enumerate(trail):
        print(f"  [{i}] {rec.event} | {rec.role_id} | risk={rec.risk_level} | prev={rec.prev_receipt_hash[:16] if rec.prev_receipt_hash else 'GENESIS'}...")

    print("\n" + "=" * 80)
    print("Hardened regulated governance demo complete.")
    print("Full chain-of-custody, SIX-style receipts, and policy enforcement active.")
    print("The USN remains lightweight and sovereign for non-regulated contexts.")

    # New in Phase 4: Export a portable evidence bundle (SOX/auditor ready)
    print("\n>>> Exporting SOX-style Evidence Bundle")
    bundle = node.compliance_engine.export_evidence_bundle(case_id="RegulatedCFO-2026-Q2")
    print(f"    Case ID: {bundle['case_id']}")
    print(f"    Records in bundle: {bundle['record_count']}")
    print(f"    Bundle self-attested: {'bundle_attestation' in bundle}")
    print("=" * 80)


def multi_role_scenario():
    """Expanded multi-role orchestration demo (CFO + Compliance collaboration)."""
    print("\n" + "=" * 80)
    print("MULTI-ROLE ORCHESTRATION SCENARIO (CFO + Compliance Hand-off)")
    print("=" * 80)

    node = UniversalSovereignNode("MultiRoleCFO-Compliance", context_type="corporate_regulated")

    # Load both roles simultaneously
    print("\n>>> Loading multiple roles for coordinated governance")
    roles = node.load_roles(["cfo_agent", "compliance_agent"])
    print(f"    Loaded roles: {list(roles.keys())}")

    # CFO produces a regulated artifact
    cfo = node.loaded_roles["cfo_agent"]
    forecast = cfo.process(
        payload={"financial_data": {"revenue": [5000, 5200]}, "forecast_horizon": 4},
        principal_id="owner",
        request_id="cfo-forecast-001"
    )
    print(f"    CFO produced forecast (status: {forecast.get('status')})")

    # Compliance reviews via cross-role handoff (authority gradient)
    print("\n>>> Cross-role review hand-off (Compliance reviews CFO output)")
    review = node.request_cross_role_review(
        reviewer_role="compliance_agent",
        target_role="cfo_agent",
        artifact=forecast,
        principal_id="owner"
    )
    print(f"    Review status: {review.get('status')}")
    print(f"    Authority gradient note: {review.get('authority_gradient')}")
    print(f"    Cross-role attestation present: {'cross_role_attestation' in review}")

    print("\n>>> Multi-role scenario with full joint audit trail complete.")
    print("=" * 80)


if __name__ == "__main__":
    main()
    multi_role_scenario()


if __name__ == "__main__":
    main()
