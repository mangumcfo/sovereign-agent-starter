#!/usr/bin/env python3
"""
Coherence Reconciliation Queue — turn the harvested gaps (Partial + Missing) into a governed,
prioritized proposal queue for KM's one-gate review (book→code AND code→book reconciliation).

Reads memory/coherence_capabilities.json (G's 2026-05-30 harvest: 47 rows, Partial/Missing = the gaps),
DEDUPES the per-book gaps into distinct cross-cutting platform capabilities, scores them by leverage
(how many books + harness-strengthening), writes a prioritized queue artifact, and (with --open) opens
the HIGH-priority ones as atrium_review obligations routed to KM's gate.

Flow (KM steer 2026-06-06): ideation → KM review/accept (one gate) → Tiger updates the relevant book
passages + raises the platform-promotion → coherence monitor re-pins. Books stay source; gaps flow back.

Fence: Tiger authors the queue + opens obligations in atrium_review (Tiger-writable). GB owns the roadmap;
the platform-promotion builds run the governed dev loop. KM ratifies.

  python3 scripts/coherence_reconciliation_queue.py            # write artifact + print
  python3 scripts/coherence_reconciliation_queue.py --open     # also open HIGH obligations (idempotent)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CAPS = REPO / "memory" / "coherence_capabilities.json"
ART = REPO / "artifacts" / "Coherence_Reconciliation_Queue_2026-06-06.md"

# Dedup map: distinct platform capability ← matching (book_id, capability-substring) gaps.
# priority by leverage (HIGH = multi-book or core harness-strengthening). proposed = the reconciliation action.
GROUPS = [
    {"ref": "recon:tiered-qualified-gates", "title": "Tiered + qualified-reviewer breath-gates (materiality/audience/role)",
     "priority": "HIGH", "books": ["01_cfos_finance", "05_hr_talent", "06_compliance_audit", "07_sales_revenue", "02_executives_decisions"],
     "match": ["tiered approval", "qualified", "human gate before", "progressive review", "trust level"],
     "leverage": "5 books — the single highest-leverage harness primitive; turns the binary gate into materiality/audience/role-aware.",
     "proposed": "Promote tiered/qualified-reviewer gate types in breath-gate + role_spec (with receipt attribution); update the cited book passages to reference the real gate tiers; re-pin."},
    {"ref": "recon:source-citation-lineage", "title": "Source-citation + methodology lineage in the receipt envelope",
     "priority": "HIGH", "books": ["01_cfos_finance"],
     "match": ["source-citation", "methodology versioning"],
     "leverage": "Constitutional per Book 1 ('every number cites its source'); strengthens every financial receipt.",
     "proposed": "Add first-class source-citation + methodology-version fields to the receipt envelope; update Book 1 passages; pin to compliance_engine.py."},
    {"ref": "recon:actions-projection", "title": "Queryable .actions[] projection over Merkle leaves",
     "priority": "HIGH", "books": ["10_scaling_enterprise"],
     "match": ["queryable .actions", "runtime-exercise verify"],
     "leverage": "One fix, three consumers (books + SDK + Atrium audit); also clears the B10-12 verify-command drift.",
     "proposed": "Add an .actions[] projection over core.py Merkle leaves; update the B10-12 Runtime-Exercise verify passages; re-pin to core.py."},
    {"ref": "recon:cross-role-veto", "title": "Cross-role review / veto primitive (joint_attestation)",
     "priority": "HIGH", "books": ["11_ma_due_diligence", "09_multi_agent"],
     "match": ["cross-role review", "veto"],
     "leverage": "Supports Book 11 (compliance vetoes CFO per Charter) + Series 2 Vol 3 governed dev loop.",
     "proposed": "First-class cross-role veto with joint_attestation receipts + escalation; update Book 11 passage; pin to compliance_engine.py."},
    {"ref": "recon:evidence-packet-exports", "title": "Standardized evidence-packet exports (verification/decision/deal/communication)",
     "priority": "HIGH", "books": ["06_compliance_audit", "07_sales_revenue", "09_multi_agent", "11_ma_due_diligence"],
     "match": ["verification-packet", "decision packet", "deal packet", "communication audit", "multi-agent decision packet"],
     "leverage": "4 books — auditor/regulator/board-facing proof export; one packet primitive serves all.",
     "proposed": "One standardized evidence-packet export (receipt + chain + optional ledger anchor); update the 4 books' passages; pin to node_api."},
    {"ref": "recon:monitoring-companions", "title": "Always-on monitoring companions (data-quality / safety / regulatory / bias)",
     "priority": "MED", "books": ["04_supply_chain", "08_manufacturing_ops", "06_compliance_audit", "05_hr_talent"],
     "match": ["continuous data-quality", "always-on safety", "regulatory-intelligence", "bias auditing"],
     "leverage": "4 books — a persistent-monitor companion pattern (receipted) generalizes across domains.",
     "proposed": "A receipted monitoring-companion primitive (domain-parameterized); update the 4 books' passages; pin once built."},
    {"ref": "recon:trust-calibration", "title": "Trust calibration + override-rate feedback + promotion history",
     "priority": "MED", "books": ["02_executives_decisions", "03_leading_agents"],
     "match": ["trust calibration", "override-rate", "promotion surface", "shadow-mode"],
     "leverage": "2 books — 5-level calibration + shadow→production advancement; leadership-grade tooling.",
     "proposed": "Per-agent/per-person trust level + override-rate feedback + promotion history; update Books 2/3; pin."},
    {"ref": "recon:bind-role-action", "title": "First-class bind_role action class on node.load_role()",
     "priority": "MED", "books": ["10_scaling_enterprise"],
     "match": ["bind_role"],
     "leverage": "Small, clean governance-event win; clears a B10 verify gap.",
     "proposed": "Emit a bind_role governance action class on load_role(); update Book 10 passage; pin to core.py."},
    {"ref": "recon:agent-brief-artifact", "title": "Structured Agent Brief / decision-handoff-protocol (with 'unknowns') as receipted artifact",
     "priority": "MED", "books": ["02_executives_decisions", "03_leading_agents"],
     "match": ["agent brief", "decision_handoff", "override_log_entry", "structured agent brief"],
     "leverage": "2 books — delegation discipline as a versionable, receipted artifact type.",
     "proposed": "Receiptable Agent-Brief / handoff artifact (incl. 'what the agent does not know'); update Books 2/3; pin."},
    {"ref": "recon:role-matrix", "title": "Role Definition Matrix + layered domain roles (accountability-first)",
     "priority": "MED", "books": ["03_leading_agents", "04_supply_chain", "08_manufacturing_ops"],
     "match": ["role definition matrix", "four-layer human-role", "non-overridable safety"],
     "leverage": "3 books — accountability-classified roles + domain layering on role_spec.",
     "proposed": "Extend role_spec with accountability class + domain layers (incl. non-overridable safety); update Books 3/4/8; pin to role_spec."},
    {"ref": "recon:domain-cockpits", "title": "Domain cockpit surfaces (Sales / Safety / Compliance / Governor / Ops)",
     "priority": "MED", "books": ["07_sales_revenue", "08_manufacturing_ops", "06_compliance_audit", "09_multi_agent"],
     "match": ["cockpit", "governor dashboard", "safety monitoring view", "sqdc"],
     "leverage": "4 books — Atrium domain lenses (UI-heavy); group + sequence after primitives land.",
     "proposed": "Atrium domain-lens framework; update the 4 books' surface passages; pin to atrium surfaces (next-edition)."},
    {"ref": "recon:data-subject-access", "title": "Data-subject access / individual transparency (HR)",
     "priority": "MED", "books": ["05_hr_talent"],
     "match": ["individual transparency", "data-subject", "no-suppression"],
     "leverage": "Book 5 — controlled subject access; an ethics-critical HR gap.",
     "proposed": "Controlled data-subject access + no-suppression enforcement; update Book 5; pin."},
    {"ref": "recon:component-registry", "title": "Component registry for reusable patterns (ARET template) + clean-room constraints",
     "priority": "MED", "books": ["09_multi_agent", "11_ma_due_diligence"],
     "match": ["component registry", "composable 4-agent", "clean-room", "information-volume"],
     "leverage": "Reuse-case foundation (Book 9) + diligence clean-room (Book 11).",
     "proposed": "Versionable ARET template registry + clean-room/info-volume constraint primitives; update Books 9/11; pin."},
]


def main(argv) -> int:
    do_open = "--open" in argv
    doc = json.loads(CAPS.read_text(encoding="utf-8"))
    caps = doc.get("capabilities", [])
    gaps = [c for c in caps if c.get("review_status") in ("partial", "missing")]
    lines = ["# Coherence Reconciliation Queue — Partial + Missing → governed proposals",
             "",
             f"**Source:** G's 2026-05-30 review harvest (`coherence_capabilities.json`). **Gaps:** {len(gaps)} "
             f"({sum(c['review_status']=='partial' for c in caps)} partial + {sum(c['review_status']=='missing' for c in caps)} missing), "
             f"deduped into **{len(GROUPS)}** cross-cutting platform capabilities.",
             "**Flow (KM 2026-06-06):** ideation → KM review/accept (one gate) → Tiger updates the relevant book "
             "passages + raises the platform-promotion → monitor re-pins. Books stay source; gaps flow back.",
             "**Fence:** Tiger authors + opens atrium_review obligations; GB owns roadmap; KM ratifies.",
             ""]
    order = {"HIGH": 0, "MED": 1, "LOW": 2}
    for g in sorted(GROUPS, key=lambda x: order.get(x["priority"], 9)):
        lines += [f"## [{g['priority']}] {g['title']}",
                  f"- **ref:** `{g['ref']}` · **books:** {', '.join(g['books'])}",
                  f"- **leverage:** {g['leverage']}",
                  f"- **proposed reconciliation:** {g['proposed']}", ""]
    lines += ["∞Δ∞ Bidirectional reconciliation — book as source, code informs refinement, one gate. ∞Δ∞"]
    ART.write_text("\n".join(lines), encoding="utf-8")
    highs = [g for g in GROUPS if g["priority"] == "HIGH"]
    print(f"✓ wrote queue artifact ({len(GROUPS)} items; {len(highs)} HIGH) → {ART.name}")

    if do_open:
        sys.path.insert(0, str(REPO / "src"))
        from sovereign_agent.obligations.ledger import ObligationLedger
        L = ObligationLedger(root=str(REPO / "memory" / "obligations" / "atrium_review"), principal_id="tiger")
        existing = {e.get("ref") for e in L._entries() if e.get("type") == "debit"}  # ledger writes 'debit', not 'open' (audit bonus fix)
        opened = 0
        for g in highs:
            if g["ref"] in existing:
                print(f"• exists, skip: {g['ref']}"); continue
            intent = (f"[Coherence reconciliation — {g['priority']}] {g['title']}\n\n"
                      f"Books affected: {', '.join(g['books'])}\nLeverage: {g['leverage']}\n"
                      f"Proposed: {g['proposed']}\n\nAccept = Tiger updates the cited book passage(s) + raises the "
                      f"platform-promotion (governed dev loop); monitor re-pins. Source: G review 2026-05-30. "
                      f"Queue: artifacts/{ART.name}.")
            L.open(title=f"Reconcile: {g['title']}", owner="km-1176", classification="C2",
                   intent=intent, ref=g["ref"], material=True, next_gate="KM review/accept (one gate)")
            opened += 1; print(f"✓ opened obligation: {g['ref']}")
        print(f"opened {opened} HIGH reconciliation obligations (KM gate).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
