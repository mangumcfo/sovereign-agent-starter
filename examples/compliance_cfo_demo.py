#!/usr/bin/env python3
"""
Universal Sovereign Node — Enterprise Compliance CFO Demo

Demonstrates the USN operating as a governed enterprise node (Playbook 6 + SIX patterns)
while remaining fully compatible with sovereign / family use cases.

What this demo shows:
- Boot in "corporate_regulated" context (stricter defaults)
- Load a real compliance-aware CFO role from breathline-federation
- Execute a high-materiality task with automatic:
    - Risk scoring
    - Policy compliance check
    - Audit trail + USN attestation
    - Simulated human approval gate (for regulated actions)
- Full cryptographic (or Merkle-based) receipt-style record

This is the executable embodiment of Playbook 6 (AI Agents for Compliance)
and SIX verifiable inference patterns inside the Universal Sovereign Node.
"""

from sovereign_agent import UniversalSovereignNode


def main():
    print("=" * 78)
    print("USN — ENTERPRISE COMPLIANCE CFO DEMO (Playbook 6 + SIX embodied)")
    print("=" * 78)
    print()

    # 1. Boot the node in regulated corporate context
    print(">>> Booting USN in corporate_regulated mode")
    node = UniversalSovereignNode(
        "EnterpriseCFO-Node-01",
        context_type="corporate_regulated"
    )
    print(f"    Context: {node.context_adapter.context_type}")
    print(f"    Governance mode: {node.context_adapter.governance_mode}")
    print(f"    Active roles: {node.roles}")
    print(f"    ComplianceEngine active: {node.compliance_engine is not None}")
    print()

    # 2. Load a real compliance-aware role from the federation
    print(">>> Loading cfo_agent (with compliance awareness)")
    bound = node.load_role("cfo_agent")
    print(f"    Role: {bound.role_id}")
    print(f"    Handler bound: {bound.handler is not None}")
    print(f"    Allowed actions (from real spec): {bound.get_allowed_action_classes()}")
    print()

    # 3. Prepare a high-materiality payload (simulated board forecast)
    payload = {
        "financial_data": {
            "revenue": [1200, 1350, 1100],
            "expenses": [800, 820, 790],
            "cash_position": 2450
        },
        "forecast_horizon": 6,
        "materiality": "board_level"
    }

    # 4. Run policy compliance check before execution (Playbook 6 pattern)
    print(">>> Running PolicyComplianceCheck (policy-as-code + Charter V.7)")
    policy_verdict = node.compliance_engine.run_policy_compliance_check(
        role_spec=bound.spec,
        action_class="produce_forecast_artifact",
        context={"materiality": "board_level"}
    )
    print(f"    Approved: {policy_verdict.approved}")
    print(f"    Risk score: {policy_verdict.risk_score}")
    print(f"    Rationale: {policy_verdict.rationale}")
    print(f"    Required approvals: {policy_verdict.required_approvals}")
    print()

    # 5. Simulate human approval gate (required in regulated mode for high risk)
    if policy_verdict.required_approvals:
        print(">>> Human Approval Gate (simulated — Playbook 6 human judgment layer)")
        approval = node.compliance_engine.request_human_approval(
            record={"event": "board_forecast", "risk": policy_verdict.risk_score},
            policy_note="Board-level forecast requires CFO + Compliance sign-off"
        )
        print(f"    Approval status: {approval['status']}")
        print(f"    Note: {approval['policy_note']}")
        print()

    # 6. Execute through the bound role (governed path)
    print(">>> Executing governed forecast (full audit trail + attestation)")
    result = bound.process(
        payload=payload,
        principal_id="km-1176",
        request_id="compliance-cfo-demo-001"
    )

    print("\n--- Governed Execution Result ---")
    print(f"Status: {result.get('status')}")
    print(f"Framework: {result.get('framework')}")
    print(f"USN Attestation present: {'usn_attestation' in result}")
    print(f"Compliance Attestation present: {'compliance_attestation' in result}")

    if "compliance_attestation" in result:
        ca = result["compliance_attestation"]
        audit = ca.get("audit_record")
        risk = getattr(audit, "risk_level", "N/A") if audit else "N/A"
        print(f"    Risk level: {risk}")
        print(f"    Receipt hash: {ca.get('receipt_hash', 'N/A')[:32] if isinstance(ca, dict) else 'N/A'}...")

    # 7. Show the audit trail
    print("\n>>> Recent Audit Trail (SOX-style immutable records)")
    trail = node.compliance_engine.get_audit_trail(limit=5)
    for rec in trail:
        print(f"  - {rec.event} | {rec.role_id} | risk={rec.risk_level} | {rec.timestamp[:19]}")

    print("\n" + "=" * 78)
    print("Enterprise governance demo complete.")
    print("The same USN binary now supports both sovereign personal use and")
    print("regulated corporate environments with cryptographic-grade auditability.")
    print("=" * 78)


if __name__ == "__main__":
    main()
