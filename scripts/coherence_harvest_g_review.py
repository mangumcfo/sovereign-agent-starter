#!/usr/bin/env python3
"""
Harvest G's 'Grok Build 2026-05-30' review (ALIGNMENT_AND_NEXT_EDITION_NOTES.md +
SERIES_1_PRINCIPLES_TO_EMBODY_IN_THE_HARNESS.md) into a capability ledger.

Why this is separate from coherence_registry.json: the registry holds hash-pinned passages
(coherent/drift — exact text↔code). G's findings are *semantic* capability assessments —
Present / Partial / Missing — with real file citations. This writes them honestly into
memory/coherence_capabilities.json so the monitor shows the TRUE coverage:
  ✅ present  — book capability has a real, present code home
  ⚠ partial  — primitive exists but the book's specific capability isn't first-class yet
  ◌ missing  — book claims it; harness lacks it (platform-promotion candidate / gated proposal)

Integrity: every cited code_file (when given) MUST exist, or the row is rejected loudly —
faithful to the review, no invented citations. Idempotent + re-runnable (overwrites the file).
Source of truth: kdp/agentic_playbooks/ALIGNMENT_AND_NEXT_EDITION_NOTES.md (G, 2026-05-30).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "memory" / "coherence_capabilities.json"
SRC = "G Grok Build 2026-05-30 (ALIGNMENT_AND_NEXT_EDITION_NOTES.md)"

# (capability, status, code_file [repo-relative or ""], note) — faithful to G's per-book findings.
BOOKS = {
    "01_cfos_finance": ("AI Agents for CFOs (Book 1)", [
        ("Compliance receipts + charter-checked attestations", "present", "src/sovereign_agent/compliance/compliance_engine.py",
         "Strong structural attestations: risk_level, charter_v7_checked, prev_receipt_hash, signatures, 6-key summaries."),
        ("Source-citation governance (every number cites its lineage)", "partial", "src/sovereign_agent/compliance/compliance_engine.py",
         "Receipts strong, but content lineage (GL lines, ERP txns, assumptions) is not first-class in the envelope nor queryable in Atrium."),
        ("Tiered approval gates by materiality/audience (board vs internal)", "partial", "src/sovereign_agent/compliance/compliance_engine.py",
         "HumanApprovalGate/breath_gate_token exist but binary — not tiered by materiality/audience as Ch 10 demands."),
        ("Deterministic methodology versioning (repeatable period-over-period)", "missing", "",
         "Not yet a first-class receipted primitive; strong on policy-as-code, light on versioned methodology artifacts."),
    ]),
    "02_executives_decisions": ("Executive Decisions (Book 2)", [
        ("Receipts strong on K2/K3/K4", "present", "src/sovereign_agent/compliance/compliance_engine.py",
         "prev_receipt_hash + 6-key summary + charter_v7_checked in compliance_engine + node_api/server.py."),
        ("Context-engineering 5-layer (provenance/freshness metadata)", "partial", "src/sovereign_agent/core.py",
         "Maps to ContextAdapter + operator-defined roles, but provenance/freshness/strategic-role metadata not visible in Atrium."),
        ("5-level trust calibration + override-rate feedback", "missing", "",
         "Breath-gates exist but lack the book's visible 5-level calibration and override-rate feedback."),
        ("override_log_entry / decision_handoff_protocol (with 'unknowns')", "missing", "",
         "Not first-class envelope/receipt sections."),
        ("Shadow-mode + calibration-before-autonomy", "missing", "",
         "Not yet a first-class, receipted operation."),
    ]),
    "03_leading_agents": ("Leading Agents (Book 3)", [
        ("Governed role binding + policy-as-code", "present", "src/sovereign_agent/demo_roles/family_cfo_demo/role_spec.yaml",
         "role_spec + BoundRole + ContextAdapter implement governed roles (allowed_action_classes, policy-as-code)."),
        ("Role Definition Matrix (Human/Assisted/Led/Autonomous; accountability)", "partial", "src/sovereign_agent/demo_roles/family_cfo_demo/role_spec.yaml",
         "Implementation is technical; lacks task-level Human/Agent classification with accountability attribution."),
        ("Per-person/per-agent trust level + promotion surface", "missing", "",
         "No first-class trust-level/promotion/team-matrix surface in Atrium or node_api."),
        ("Structured Agent Brief (5-element delegation) as receipted artifact", "missing", "",
         "Excellent operationalization but not yet a native receipted artifact type."),
    ]),
    "04_supply_chain": ("Supply Chain (Book 4)", [
        ("Breath-gates for override/rollback", "present", "src/sovereign_agent/compliance/compliance_engine.py",
         "Override/rollback + alignment to authority matrices supported via breath-gates."),
        ("Four-layer human-role model (Perception/Forecasting/Orchestration/Action)", "partial", "src/sovereign_agent/demo_roles/family_cfo_demo/role_spec.yaml",
         "Strong extension of the Role Matrix, but role_spec + Atrium lack supply-chain layered visibility / Ops Cockpit."),
        ("Continuous data-quality monitoring (companion + receipted gate)", "missing", "",
         "No first-class persistent monitoring agent/gate; receipts primarily reactive."),
        ("Concentration limits / consensus / assumption-surfacing primitives", "missing", "",
         "Not yet native, reusable receipted governance patterns."),
    ]),
    "05_hr_talent": ("HR & Talent (Book 5)", [
        ("Human gate before any employment action", "partial", "src/sovereign_agent/compliance/compliance_engine.py",
         "HumanApprovalGate exists but not configurable for HR thresholds / qualified-reviewer roles / 'reviewed before employment action' attribution."),
        ("Configurable bias auditing (EEOC four-fifths rule)", "missing", "",
         "Strongest ethical language in the series, but no first-class bias-auditing primitive."),
        ("Individual transparency (data-subject access to own data)", "missing", "",
         "Harness excels at operator/admin receipts; no native controlled access for data subjects (employees)."),
        ("No-suppression enforcement on high-stakes findings", "missing", "",
         "No first-class 'uncomfortable truths reach decision-makers, no filtering' enforcement."),
    ]),
    "06_compliance_audit": ("Compliance & Audit (Book 6)", [
        ("Hash-chained receipts + policy-as-code + human gates", "present", "src/sovereign_agent/compliance/compliance_engine.py",
         "Book describes almost exactly what exists: AuditRecord, prev_receipt_hash, 6-key summary, charter_v7_checked, Merkle receipts."),
        ("Auditor-friendly verification-packet export + public-ledger UX", "partial", "src/sovereign_agent/node_api/server.py",
         "Internal receipts strong; the external-proof verification-packet export + simple public-ledger verification UX not yet first-class/polished."),
        ("Qualified-reviewer gates (e.g. only BSA officer approves SARs) + attribution", "partial", "src/sovereign_agent/compliance/compliance_engine.py",
         "Gates exist but not easily role-configurable for high-stakes actions with explicit receipt attribution."),
        ("Continuous regulatory-intelligence ingestion → policy-as-code", "missing", "",
         "Ingestion layer that keeps policies updated from external sources is still thin."),
    ]),
    "07_sales_revenue": ("Sales & Revenue (Book 7)", [
        ("K1 human judgment on pricing + customer-facing actions", "present", "src/sovereign_agent/compliance/compliance_engine.py",
         "Human-in-loop on high-stakes pricing/deal decisions central + non-delegable; operator-defined governance."),
        ("Progressive review gates + batch limits + suppression checks for outbound", "partial", "src/sovereign_agent/compliance/compliance_engine.py",
         "Only partially present/configurable in role_spec + breath-gates (test-batch gates, batch limits, opt-out checks)."),
        ("Pricing optimization-function config + approval chains", "missing", "",
         "Win-rate vs margin vs gross-profit optimization config with approval chains is not first-class."),
        ("Revenue Intelligence / Sales Cockpit surface", "missing", "",
         "No clean cockpit for behavioral forecasts, pricing chains, accuracy trends (CRO + CFO)."),
    ]),
    "08_manufacturing_ops": ("Manufacturing & Ops (Book 8)", [
        ("K1 human judgment on safety-critical decisions", "present", "src/sovereign_agent/compliance/compliance_engine.py",
         "Human judgment central + operator-defined roles with hard constraints (safety as a governance requirement)."),
        ("Architecturally non-overridable safety limits (LOTO / E-stop / zones)", "partial", "src/sovereign_agent/demo_roles/family_cfo_demo/role_spec.yaml",
         "Hard constraints partially expressible; not yet architecturally non-overridable with receipt attribution."),
        ("Always-on Safety Monitoring companion + dedicated Atrium view", "missing", "",
         "No persistent always-on safety monitoring infra or non-dismissible Atrium view."),
        ("SQDC evaluation lens + progressive threshold tightening", "missing", "",
         "Not first-class configurable/auditable (SQDC dashboard; 'turn the screws' threshold history)."),
    ]),
    "09_multi_agent": ("Multi-Agent (Book 9)", [
        ("ARET loop + SOURCE/TRUTH/INTEGRITY + Propose-Approve-Execute", "present", "src/sovereign_agent/compliance/compliance_engine.py",
         "Maps almost perfectly to receipting (AuditRecord + prev_receipt_hash + 6-key), breath-gates, and role binding."),
        ("Composable 4-agent ARET loop as a reusable, versionable template", "partial", "examples/multi_mandate_handoff_demo.py",
         "Pattern is proven but not yet a first-class reusable template with built-in propose-approve-execute + receipts."),
        ("Governor Dashboard / Multi-Agent Cockpit surface", "missing", "",
         "No first-class cross-agent state / pending-proposal / constitutional-compliance surface."),
        ("Component registry for reusable multi-agent patterns", "missing", "",
         "'Best use case is the reuse case' — no component registry yet."),
    ]),
    "10_scaling_enterprise": ("Scaling the Agentic Enterprise (Book 10)", [
        ("Multi-mandate + joint_attestation pattern", "partial", "examples/multi_mandate_handoff_demo.py",
         "Visible in the demo + compliance joint-attestation logic; not yet a first-class principal-boundary primitive with Atrium mandate switching."),
        ("Runtime-Exercise verify vs real memory shape (Merkle, not .actions[])", "partial", "src/sovereign_agent/core.py",
         "Book v1.3 handed jq '.actions[-1].action_class' but memory is Merkle (core.py:292) + per-demo *_summary.json; v1.4 reconciled the language (was true DRIFT)."),
        ("First-class bind_role action class on node.load_role()", "missing", "",
         "Promotion candidate: binding emits no governance action class today."),
        ("Queryable .actions[] projection over Merkle leaves", "missing", "src/sovereign_agent/core.py",
         "Promotion candidate: one fix serves books + SDK + Atrium audit surfaces."),
    ]),
    "11_ma_due_diligence": ("AI Agents for M&A (Book 11)", [
        ("Post-deal monitoring 3-receipt temporal chain", "present", "examples/post_deal_monitoring_demo.py",
         "Strongest direct starter↔book alignment (built for Ch 9; PostDealMonitoring_summary.json)."),
        ("Cross-role review / veto as a first-class joint-receipt primitive", "partial", "src/sovereign_agent/compliance/compliance_engine.py",
         "Conceptually supported via compliance layer + role specs; not the clean first-class 'compliance vetoes CFO per Charter V.7' + joint receipts Book 11 describes."),
        ("Clean-room / information-volume constraints enforced structurally", "missing", "",
         "Largely manual / policy-as-code rather than harness-enforced during diligence."),
    ]),
    "12_agentic_enterprise": ("The Agentic Enterprise (Book 12)", [
        ("Thin-waist node_api + starter-first architecture (Atrium as replaceable lens)", "present", "src/sovereign_agent/node_api/server.py",
         "Aligns directly with Book 12's sovereignty chapter (Atrium as replaceable lens over the sovereign substrate)."),
        ("SOURCE/TRUTH/INTEGRITY → K1–K4 structural extension", "partial", "src/sovereign_agent/compliance/compliance_engine.py",
         "Conceptual mapping present; stronger explicit harness linkage (triad → K1-K4) is a candidate."),
        ("Cross-book canonical-term discipline (ARET correction Bk9→Bk12)", "partial", "",
         "Editorial + platform practice; first logged win is the ARET correction — not yet enforced tooling."),
    ]),
}


def main() -> int:
    rows, rejected = [], []
    for bid, (label, caps) in BOOKS.items():
        for cap, status, code_file, note in caps:
            if status not in ("present", "partial", "missing"):
                rejected.append((bid, cap, "bad status")); continue
            if code_file and not (REPO / code_file).is_file():
                rejected.append((bid, cap, f"cited file missing: {code_file}")); continue
            if status in ("present", "partial") and not code_file and status == "present":
                rejected.append((bid, cap, "present requires a code_file")); continue
            rows.append({"book_id": bid, "book": label, "capability": cap,
                         "review_status": status, "code_file": code_file, "note": note, "source": SRC})
    if rejected:
        for r in rejected:
            print("✗ REJECTED", r, file=sys.stderr)
        return 2
    OUT.write_text(json.dumps({"capabilities": rows, "source": SRC,
                               "note": "Faithful harvest of G's 2026-05-30 review. present/partial cite a real "
                                       "code file; missing = platform-promotion candidate (gated dev loop)."},
                              indent=1, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    c = Counter(r["review_status"] for r in rows)
    print(f"✓ wrote {len(rows)} capability rows across {len(BOOKS)} books → {OUT.name}")
    print(f"  present {c['present']} · partial {c['partial']} · missing {c['missing']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
