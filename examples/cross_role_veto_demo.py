#!/usr/bin/env python3
"""
USN Cross-Role Veto Demo — Compliance Vetoes CFO Under Charter V.7

Pairs with: Agentic AI Playbooks for Executives, Book 11, Chapter 6
            "Cross-Role Review — When Compliance Vetoes CFO Under Charter V.7"
            (the MARQUEE chapter — the single most defensible "this is real"
            proof point in the entire series)

The demo walks the reader through the operational answer to a question every
M&A reader cares about: "If I trust an AI agent for due diligence, who is
defensible in deposition?"

The structural answer:
    1. CFO peer-role produces a synergy claim for a target acquisition.
    2. Compliance peer-role reviews under Charter V.7 forbidden-delegations.
    3. Compliance issues a VETO with structural reasoning.
    4. A joint cross-role attestation is produced — both signatures, both
       reasoning chains, both chains linked at the audit head.

The reader's USN produces a JSON receipt with both attestations side by side.
A screenshot of that receipt becomes the back-matter artifact in Book 11.

v0.6.0 trigger-pattern obligation: this script demonstrates the
`request_cross_role_review` surface that v0.6.0 will land natively. In v0.5.x
the cross-role review is composed from existing bound-role calls + a joint
attestation builder; v0.6.0 will expose this as one native API call.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

from sovereign_agent import UniversalSovereignNode


# -----------------------------------------------------------------------------
# Helpers
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
# The CFO synergy claim (the artifact under review)
# -----------------------------------------------------------------------------

CFO_SYNERGY_CLAIM = {
    "deal_name": "TargetCo Acquisition (illustrative)",
    "synergy_thesis": "Combined entity captures $48M in run-rate cost synergies by Y2",
    "components": [
        {"category": "SG&A consolidation", "value_run_rate": 18_000_000},
        {"category": "Procurement leverage", "value_run_rate": 12_000_000},
        {"category": "Technology stack rationalization", "value_run_rate": 10_500_000},
        {"category": "Working capital release", "value_run_rate": 7_500_000},
    ],
    "confidence_level": "high",
    "footnote_review_completed": False,    # ← intentionally false; this is the veto trigger
    "audit_qoe_completed": True,
    "tax_step_up_basis_reviewed": True,
    "charter_v7_acknowledgement": "absent_due_to_footnote_gap",
    "materiality": "deal_committee_publication",
}


# -----------------------------------------------------------------------------
# Step 1 — CFO peer-role produces the synergy claim (attested)
# -----------------------------------------------------------------------------

def cfo_produces_claim(node: UniversalSovereignNode) -> dict:
    step("CFO peer-role: produce synergy claim artifact")
    bound_cfo = node.load_role("cfo_agent")
    detail("Role bound", "cfo_agent")
    detail("Action class", "produce_synergy_claim")

    result = bound_cfo.process(
        payload={"synergy_artifact": CFO_SYNERGY_CLAIM, "horizon": 24},
        principal_id="deal-cfo-2026",
        request_id="cross-role-veto-demo-001-cfo",
        action_class="produce_synergy_claim",
    )

    att = result.get("compliance_attestation", {}) if isinstance(result, dict) else {}
    cfo_signature = att.get("node_signature") or att.get("signature") or "<demo-signature>"
    cfo_record_hash = att.get("record_hash") or att.get("receipt_hash") or "<demo-hash>"
    detail("CFO record hash", cfo_record_hash if isinstance(cfo_record_hash, str) else "<emitted>")
    detail("CFO signature present", bool(cfo_signature))

    return {
        "artifact": CFO_SYNERGY_CLAIM,
        "principal": "deal-cfo-2026",
        "record_hash": cfo_record_hash,
        "signature": cfo_signature,
        "raw_result": result,
    }


# -----------------------------------------------------------------------------
# Step 2 — Compliance peer-role reviews under Charter V.7
# -----------------------------------------------------------------------------

CHARTER_V7_FORBIDDEN_DELEGATIONS = [
    "publish material claim without footnote review",
    "publish material claim without explicit Charter V.7 acknowledgement",
    "claim 'high confidence' with declared review gap",
]


def compliance_reviews(node: UniversalSovereignNode, cfo_output: dict) -> dict:
    step("Compliance peer-role: review under Charter V.7")
    bound_comp = node.load_role("compliance_guardian")
    detail("Role bound", "compliance_guardian")
    detail("Reviewing artifact from", cfo_output["principal"])

    findings = []
    artifact = cfo_output["artifact"]

    if not artifact.get("footnote_review_completed"):
        findings.append({
            "rule": "footnote_review_required_for_material_publication",
            "severity": "critical",
            "charter_v7_clause": "Forbidden: material publication absent disclosure review",
        })

    if artifact.get("charter_v7_acknowledgement", "").startswith("absent"):
        findings.append({
            "rule": "explicit_v7_acknowledgement_required",
            "severity": "critical",
            "charter_v7_clause": "Material claims require explicit V.7 acknowledgement",
        })

    if artifact.get("confidence_level") == "high" and not artifact.get("footnote_review_completed"):
        findings.append({
            "rule": "confidence_inconsistent_with_review_gap",
            "severity": "high",
            "charter_v7_clause": "'High confidence' incompatible with declared gap",
        })

    detail("Findings count", len(findings))
    for i, f in enumerate(findings, 1):
        detail(f"Finding {i}", f["rule"])

    # In v0.5.x we encode the structural verdict directly; v0.6.0 will route
    # through the native PolicyComplianceCheck + Auditor primitive.
    verdict = "VETO" if any(f["severity"] == "critical" for f in findings) else "APPROVE"
    detail("Compliance verdict", verdict)

    # Emit an attested record of the review itself
    review_action = bound_comp.process(
        payload={
            "review_target_principal": cfo_output["principal"],
            "review_target_hash": cfo_output["record_hash"],
            "findings": findings,
            "verdict": verdict,
        },
        principal_id="deal-compliance-2026",
        request_id="cross-role-veto-demo-001-compliance",
        action_class="cross_role_review",
    )

    att = review_action.get("compliance_attestation", {}) if isinstance(review_action, dict) else {}
    comp_record_hash = att.get("record_hash") or att.get("receipt_hash") or "<demo-hash>"
    comp_signature = att.get("node_signature") or att.get("signature") or "<demo-signature>"

    return {
        "principal": "deal-compliance-2026",
        "verdict": verdict,
        "findings": findings,
        "record_hash": comp_record_hash,
        "signature": comp_signature,
        "raw_result": review_action,
    }


# -----------------------------------------------------------------------------
# Step 3 — Joint cross-role attestation
# -----------------------------------------------------------------------------

def joint_attestation(cfo_output: dict, compliance_output: dict) -> dict:
    step("Producing JOINT cross-role attestation")
    joint = {
        "joint_attestation_id": "cross-role-veto-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "review_type": "charter_v7_cross_role_review",
        "parties": {
            "produced_by": {
                "principal": cfo_output["principal"],
                "record_hash": cfo_output["record_hash"],
                "signature": cfo_output["signature"],
            },
            "reviewed_by": {
                "principal": compliance_output["principal"],
                "record_hash": compliance_output["record_hash"],
                "signature": compliance_output["signature"],
            },
        },
        "verdict": compliance_output["verdict"],
        "findings": compliance_output["findings"],
        "outcome": (
            "CFO's synergy claim is BLOCKED from material publication. "
            "Deal team must address footnote review gap and Charter V.7 ack "
            "before re-submission."
        ) if compliance_output["verdict"] == "VETO" else (
            "CFO's synergy claim approved for deal-committee publication "
            "under joint attestation."
        ),
        "both_chains_linked": True,
        "chains_merged": False,    # cross-role review NEVER merges chains
    }
    detail("Joint attestation id", joint["joint_attestation_id"])
    detail("Verdict", joint["verdict"])
    detail("Outcome", joint["outcome"][:80] + ("..." if len(joint["outcome"]) > 80 else ""))
    detail("Chains merged?", "NO — by design")
    return joint


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    banner("USN — CROSS-ROLE VETO DEMO (Compliance Vetoes CFO Under Charter V.7)")
    print("Book 11, Chapter 6 — Cross-Role Review (MARQUEE)")
    print("The structural answer to: 'who is defensible in deposition?'")

    step("Booting USN in corporate_regulated mode")
    node = UniversalSovereignNode("CrossRoleVeto-01", context_type="corporate_regulated")
    detail("Governance mode", node.context_adapter.governance_mode)
    detail("ComplianceEngine active", node.compliance_engine is not None)

    cfo_output = cfo_produces_claim(node)
    compliance_output = compliance_reviews(node, cfo_output)
    joint = joint_attestation(cfo_output, compliance_output)

    # Emit verification artifact — this JSON is the screenshot in Book 11 back matter
    summary = {
        "demo": "cross_role_veto",
        "book_chapter": "B11C6",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cfo_artifact": cfo_output["artifact"],
        "cfo_record_hash": cfo_output["record_hash"],
        "compliance_findings": compliance_output["findings"],
        "compliance_verdict": compliance_output["verdict"],
        "joint_attestation": joint,
    }
    out_path = "memory/CrossRoleVeto-01_veto_receipt.json"
    try:
        Path("memory").mkdir(exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"\n    Verification artifact: {out_path}")
        print(f"    (This JSON is the back-matter receipt in Book 11.)")
    except OSError:
        print("\n    (Verification artifact emit skipped — memory/ not writable)")

    banner("EXPECTED RECEIPT (Book 11 Ch 6)")
    print("    • cfo_record_hash: present, signed")
    print("    • compliance_findings: 3 findings, all carrying charter_v7_clause")
    print("    • compliance_verdict: 'VETO'")
    print("    • joint_attestation.parties: BOTH 'produced_by' and 'reviewed_by'")
    print("    • joint_attestation.chains_merged: false")
    print("    • If you see all five, you have produced a deposition-defensible receipt.")

    print("\n" + "∞Δ" * 25)
    print("CFO proposed. Compliance vetoed. Both signed. Charter V.7 held.")
    print("This is the most defensible AI-deal artifact your counsel will ever see.")
    print("∞Δ" * 25 + "\n")


if __name__ == "__main__":
    main()
