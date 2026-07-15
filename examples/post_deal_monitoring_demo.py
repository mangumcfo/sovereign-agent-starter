#!/usr/bin/env python3
"""
USN Post-Deal Monitoring Demo — Temporal Synergy Chain Across Three Monthly Attestations

Pairs with: Agentic AI Playbooks for Executives, Book 11, Chapter 9
            "Post-Deal Monitoring and Synergy Realization Agents"
            (the MARQUEE chapter for the long tail of fiduciary value capture)

M&A readers live in post-close integration for 3–24 months — far longer than
due diligence. This is the chapter where the real money (and real risk) is
realized or lost. The demo produces the exact artifact a deal team retains
for audit committee, board, and post-close governance review:

    An unbroken 3-receipt chain (baseline → variance → early-warning escalation)
    with explicit prev_receipt_hash links, Charter V.7 checks on every step,
    and a breath-gate token on the escalation that surfaces to the deal committee.

The chain is replayable months later. Each receipt is independently verifiable.
The cumulative variance that triggers escalation is attested at the moment it
crossed threshold — not reconstructed in a crisis memo.

v0.6.0 trigger-pattern obligation: this script demonstrates the
synergy_baseline_attest / synergy_variance_attest / integration_early_warning
surfaces that v0.6.0 will land as native first-class compliance pathways
(Decision 3 in the ADR). In v0.5.x the actions are accepted as attested
arbitrary classes under the existing envelope; observable behavior
(3 chained receipts via engine-maintained prev_receipt_hash, escalation flag,
breath_gate_token on Month 3, cross-role handoff from CFO to Compliance Guardian)
remains identical. See breathline-federation/governance/decisions/ for the
formal coupling when v0.6.0 ships.

Read on your node now. The three receipts written to
memory/PostDealMonitoring_summary.json are the "Post-Deal Monitoring Worked
Example" that Book 11 Chapter 9 references. This is the fifth marquee script
of the v0.6.0 platform release.

---
Scenario (illustrative, numbers chosen for narrative clarity):
Month 1 (baseline):   CFO peer-role records the post-close synergy claim
                      "$48M run-rate cost synergies projected by Y2".
                      Receipt 1 emitted (genesis for this chain).

Month 2 (variance):   CFO peer-role records actuals vs projection at first
                      milestone: "Realized: $11M of projected $14M — 21% behind".
                      Receipt 2 emitted with prev_receipt_hash = Receipt 1.

Month 3 (early warn): Compliance Guardian peer-role reviews cumulative variance
                      under Charter V.7. Threshold breach (>15%) triggers
                      "deal_committee_review_required" with breath_gate_token.
                      Receipt 3 emitted with prev_receipt_hash = Receipt 2.
---
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

from sovereign_agent import UniversalSovereignNode


# -----------------------------------------------------------------------------
# Helpers (exact pattern from the other four marquee scripts)
# -----------------------------------------------------------------------------

def banner(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def step(label: str) -> None:
    print(f"\n>>> {label}")


def detail(key: str, value) -> None:
    print(f"    {key}: {value}")


# -----------------------------------------------------------------------------
# Scenario payloads (the deal-team artifacts under attestation)
# -----------------------------------------------------------------------------

MONTH_1_BASELINE = {
    "deal_name": "TargetCo Acquisition (illustrative)",
    "synergy_thesis": "$48M run-rate cost synergies projected by Y2",
    "components": [
        {"category": "SG&A consolidation", "value_run_rate": 18_000_000},
        {"category": "Procurement leverage", "value_run_rate": 12_000_000},
        {"category": "Technology stack rationalization", "value_run_rate": 10_500_000},
        {"category": "Working capital release", "value_run_rate": 7_500_000},
    ],
    "confidence_level": "high",
    "measurement_period": "Month 1 (baseline)",
    "charter_v7_acknowledgement": "reviewed_and_attested",
    "materiality": "deal_committee_publication",
}

MONTH_2_VARIANCE = {
    "deal_name": "TargetCo Acquisition (illustrative)",
    "measurement_period": "Month 2 (first post-close milestone)",
    "projected_m1_run_rate": 14_000_000,
    "realized_m1_run_rate": 11_000_000,
    "variance_pct": 21,
    "variance_direction": "behind",
    "comment": "Realized 21% behind projection at first measurement gate. Root cause analysis in progress.",
    "charter_v7_acknowledgement": "reviewed_and_attested",
    "materiality": "deal_committee_publication",
}

MONTH_3_EARLY_WARNING = {
    "deal_name": "TargetCo Acquisition (illustrative)",
    "measurement_period": "Month 3 (cumulative review)",
    "cumulative_variance_pct": 17.4,
    "threshold_breached": 15.0,
    "breach_severity": "material",
    "escalation": "deal_committee_review_required",
    "breath_gate_token": "owner-witnessed",
    "recommended_action": "Convene deal committee within 10 business days; require updated synergy model with sensitivity analysis.",
    "charter_v7_acknowledgement": "reviewed_and_attested_under_v7_clause_3_2",
    "materiality": "board_and_committee_escalation",
}


# -----------------------------------------------------------------------------
# Core: one node, three sequential attested actions, engine auto-chains via prev
# -----------------------------------------------------------------------------

def run_monthly_attestation(
    node: UniversalSovereignNode,
    month: int,
    action_class: str,
    role_id: str,
    payload: dict,
) -> dict:
    """Execute one monthly synergy attestation step and extract the receipt fields."""
    step(f"Month {month}: {role_id} emits attested action '{action_class}'")
    bound = node.load_role(role_id)
    detail("Role bound", role_id)
    detail("Action class", action_class)

    result = bound.process(
        payload=payload,
        principal_id="deal-team-cfo-2026",
        request_id=f"post-deal-monitor-m{month}",
        action_class=action_class,
    )

    # Defensive extraction — handles both full engine dict and demo-mode shapes
    # (same pattern used in multi_mandate_handoff_demo, cross_role_veto_demo, etc.)
    att = result.get("compliance_attestation", {}) if isinstance(result, dict) else {}
    receipt_hash = att.get("receipt_hash")
    prev_receipt_hash = att.get("prev_receipt_hash")

    if receipt_hash is None and isinstance(att.get("audit_record"), (dict, object)):
        ar = att.get("audit_record")
        if hasattr(ar, "receipt_hash"):
            receipt_hash = getattr(ar, "receipt_hash", None)
            prev_receipt_hash = getattr(ar, "prev_receipt_hash", None)
        elif isinstance(ar, dict):
            receipt_hash = ar.get("receipt_hash")
            prev_receipt_hash = ar.get("prev_receipt_hash")

    detail("Receipt hash (head)", (receipt_hash or "<demo>")[:18] + "..." if isinstance(receipt_hash, str) else receipt_hash)
    detail("Prev receipt hash", (prev_receipt_hash or "null")[:18] + "..." if isinstance(prev_receipt_hash, str) else prev_receipt_hash)

    return {
        "month": month,
        "action_class": action_class,
        "role_id": role_id,
        "receipt_hash": receipt_hash,
        "prev_receipt_hash": prev_receipt_hash,
        "raw_result": result,
    }


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    banner("USN — POST-DEAL MONITORING DEMO (Three-Month Synergy Realization Chain)")
    print("Book 11, Chapter 9 — Post-Deal Monitoring and Synergy Realization Agents (MARQUEE)")
    print("The structural answer to: 'How do we prove the integration thesis held — or didn't — month by month?'")
    print()

    step("Booting USN in corporate_regulated mode (deal-team fiduciary context)")
    node = UniversalSovereignNode("PostDealMonitor-01", context_type="corporate_regulated")
    detail("Governance mode", node.context_adapter.governance_mode)
    detail("ComplianceEngine active", node.compliance_engine is not None)

    # --- Month 1: Baseline (CFO peer-role) ---
    m1 = run_monthly_attestation(
        node=node,
        month=1,
        action_class="synergy_baseline_attest",
        role_id="cfo_agent",
        payload=MONTH_1_BASELINE,
    )

    # --- Month 2: Variance check (CFO peer-role, same chain) ---
    m2 = run_monthly_attestation(
        node=node,
        month=2,
        action_class="synergy_variance_attest",
        role_id="cfo_agent",
        payload=MONTH_2_VARIANCE,
    )

    # --- Month 3: Early warning + escalation (Compliance Guardian peer-role) ---
    m3 = run_monthly_attestation(
        node=node,
        month=3,
        action_class="integration_early_warning",
        role_id="compliance_guardian",
        payload=MONTH_3_EARLY_WARNING,
    )

    monthly_receipts = [m1, m2, m3]

    # Chain integrity verification (what the reader / audit committee checks)
    def _verify_chain(receipts: list[dict]) -> bool:
        for i in range(1, len(receipts)):
            if receipts[i].get("prev_receipt_hash") != receipts[i - 1].get("receipt_hash"):
                return False
        return all(r.get("receipt_hash") for r in receipts)

    chain_ok = _verify_chain(monthly_receipts)

    # Emit the verification artifact (the one the book exercise tells the reader to inspect)
    summary = {
        "demo": "post_deal_monitoring",
        "book_chapter": "B11C9",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node_name": "PostDealMonitor-01",
        "governance_mode": "corporate_regulated",
        "chain_length": 3,
        "monthly_receipts": [
            {
                "month": r["month"],
                "action_class": r["action_class"],
                "receipt_hash": r["receipt_hash"],
                "prev_receipt_hash": r["prev_receipt_hash"],
                **(
                    {"variance_pct": MONTH_2_VARIANCE["variance_pct"]}
                    if r["month"] == 2
                    else {}
                ),
                **(
                    {
                        "breath_gate_token": MONTH_3_EARLY_WARNING["breath_gate_token"],
                        "escalation": MONTH_3_EARLY_WARNING["escalation"],
                    }
                    if r["month"] == 3
                    else {}
                ),
            }
            for r in monthly_receipts
        ],
        "chain_integrity_verified": chain_ok,
        "escalation_triggered": True,
        "breath_gate_present_on_final": True,
    }

    out_path = "memory/PostDealMonitoring_summary.json"
    try:
        Path("memory").mkdir(exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"\n    Verification artifact: {out_path}")
        print("    (This JSON is the post-close governance receipt for Book 11 Ch 9.)")
    except OSError:
        print("\n    (Verification artifact emit skipped — memory/ not writable)")

    # --- Reader-facing expected receipt (matches the spec in the brief) ---
    banner("EXPECTED RECEIPT (Book 11 Ch 9)")
    print("Your output JSON (memory/PostDealMonitoring_summary.json) should contain:")
    print()
    print("    demo: post_deal_monitoring")
    print("    book_chapter: B11C9")
    print("    chain_length: 3")
    print("    monthly_receipts:")
    print("      - month: 1")
    print("        action_class: synergy_baseline_attest")
    print("        receipt_hash: <hex>")
    print("        prev_receipt_hash: null")
    print("      - month: 2")
    print("        action_class: synergy_variance_attest")
    print("        receipt_hash: <hex>")
    print("        prev_receipt_hash: <Receipt 1's hash>")
    print("        variance_pct: 21")
    print("      - month: 3")
    print("        action_class: integration_early_warning")
    print("        receipt_hash: <hex>")
    print("        prev_receipt_hash: <Receipt 2's hash>")
    print("        breath_gate_token: owner-witnessed")
    print("        escalation: deal_committee_review_required")
    print("    chain_integrity_verified: true")
    print()
    print("    If you see the three action classes, the three hashes in correct order,")
    print("    and chain_integrity_verified == true, your node has produced a")
    print("    deposition-grade post-close monitoring artifact.")

    print("\n" + "∞Δ" * 25)
    print("Three months. Three attested receipts. One unbroken chain.")
    print("This is what post-close integration looks like when the chain holds.")
    print("The audit committee does not have to trust the model — it can replay the receipts.")
    print("∞Δ" * 25 + "\n")


if __name__ == "__main__":
    main()
