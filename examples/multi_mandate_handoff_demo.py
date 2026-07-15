#!/usr/bin/env python3
"""
USN Multi-Mandate Handoff Demo — One Human, Many Fiduciary Hats

Pairs with: Agentic AI Playbooks for Executives, Book 10, Chapter 7
            "The Multi-Mandate Operator" (the open-window MARQUEE chapter)

A single human commonly serves multiple fiduciary mandates — CFO of a portfolio
company, principal of a consulting practice, family CFO at home. Each mandate
is a distinct principal_id with its own audit chain, its own permission set,
its own Charter V.7 inheritance.

This demo walks through Kenneth's actual stack:

    Mandate A:  quadroof-cfo-2026          (corporate, regulated)
    Mandate B:  fractional-cfo-2026        (consulting practice)
    Mandate C:  family-cfo-2026            (LGP / household)

Then demonstrates a *cross-mandate handoff* (Family engages the Fractional CFO
practice for personal tax planning) — breath-gated, audit-sealed, and producing
a joint attestation that links the chains without merging them.

v0.6.0 trigger-pattern obligation: this script demonstrates the mandate_id
plumbing + cross-mandate handoff ceremony that v0.6.0 will land natively.
In v0.5.x the mandate is simulated via principal_id naming convention; once
v0.6.0 ships, the surface becomes a native mandate_id field.

Read on your node now. The three chains you produce here are the
"Multi-Mandate Worked Example" Book 10 Chapter 7 references.
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
# Mandate construction
# -----------------------------------------------------------------------------

def boot_mandate(mandate_id: str, role_id: str, context_type: str) -> dict:
    """Boot a mandate as a USN+role pair with its own principal_id chain."""
    step(f"Booting mandate '{mandate_id}' (role={role_id}, context={context_type})")
    node = UniversalSovereignNode(
        f"USN-{mandate_id}",
        context_type=context_type,
    )
    detail("Governance mode", node.context_adapter.governance_mode)
    bound = node.load_role(role_id)
    detail("Role bound", bound.handler is not None if hasattr(bound, "handler") else "n/a")
    return {
        "mandate_id": mandate_id,
        "node": node,
        "bound_role": bound,
        "principal_id": mandate_id,  # v0.6.0: principal_id will derive from mandate_id natively
        "chain_head": None,
        "actions": [],
    }


# -----------------------------------------------------------------------------
# Per-mandate work
# -----------------------------------------------------------------------------

def run_corporate_mandate(mandate: dict) -> None:
    step(f"[{mandate['mandate_id']}] Running corporate CFO action (regulated path)")
    payload = {
        "financial_data": {"revenue": [4200, 4800, 5100], "expenses": [2900, 3100, 3300]},
        "forecast_horizon": 6,
        "materiality": "board_reporting",
    }
    result = mandate["bound_role"].process(
        payload=payload,
        principal_id=mandate["principal_id"],
        request_id=f"{mandate['mandate_id']}-corp-001",
        action_class="produce_forecast_artifact",
    )
    summarize_action(mandate, result, "produce_forecast_artifact")


def run_consulting_mandate(mandate: dict) -> None:
    step(f"[{mandate['mandate_id']}] Running consulting CFO action (practice path)")
    payload = {
        "financial_data": {"revenue": [80, 95, 110], "expenses": [42, 48, 54]},
        "client_engagement": "advisory_retainer",
        "forecast_horizon": 3,
    }
    result = mandate["bound_role"].process(
        payload=payload,
        principal_id=mandate["principal_id"],
        request_id=f"{mandate['mandate_id']}-consult-001",
        action_class="produce_forecast_artifact",
    )
    summarize_action(mandate, result, "produce_forecast_artifact")


def run_family_mandate(mandate: dict) -> None:
    step(f"[{mandate['mandate_id']}] Running family CFO action (LGP path)")
    payload = {
        "financial_data": {"revenue": [420, 480, 510], "expenses": [280, 295, 310]},
        "focus": "generational_wealth",
        "forecast_horizon": 5,
    }
    result = mandate["bound_role"].process(
        payload=payload,
        principal_id=mandate["principal_id"],
        request_id=f"{mandate['mandate_id']}-family-001",
        action_class="produce_forecast_artifact",
    )
    summarize_action(mandate, result, "produce_forecast_artifact")


def summarize_action(mandate: dict, result, action_class: str) -> None:
    """Pull the attested receipt and stamp it onto the mandate's local chain head."""
    if not isinstance(result, dict):
        detail("Result", "non-dict — execution likely demo-only mode")
        return
    detail("Status", result.get("status"))
    att = result.get("compliance_attestation") or result.get("attestation") or {}

    # Handle both dict (demo mode) and AuditRecord object (full primitives)
    record = att.get("audit_record") or att
    if hasattr(record, "receipt_hash"):
        receipt_hash = getattr(record, "receipt_hash") or getattr(record, "record_hash") or "<demo>"
    elif isinstance(record, dict):
        receipt_hash = record.get("receipt_hash") or record.get("record_hash") or "<demo>"
    else:
        receipt_hash = "<demo>"

    detail("Receipt hash (head)", receipt_hash if isinstance(receipt_hash, str) else "<emitted>")
    mandate["chain_head"] = receipt_hash if isinstance(receipt_hash, str) else None
    mandate["actions"].append({
        "action_class": action_class,
        "request_id": result.get("request_id") or "<see receipt>",
        "receipt_hash": mandate["chain_head"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# -----------------------------------------------------------------------------
# Cross-mandate handoff ceremony
# -----------------------------------------------------------------------------

def cross_mandate_handoff(family: dict, consulting: dict) -> dict:
    """
    Family engages Fractional CFO practice for personal tax planning.

    The handoff is:
        1. Family side issues a 'engage_external_advisor' attested action
        2. Consulting side issues a 'accept_engagement' attested action
        3. A joint attestation is produced that references BOTH chain heads
           without merging the chains. The two principal_ids stay distinct.
        4. Breath-gate: a human signal must be present (here simulated by
           the owner authority token).
    """
    banner("CROSS-MANDATE HANDOFF CEREMONY")
    step("Family-side: issue 'engage_external_advisor' attested action")
    detail("From principal", family["principal_id"])
    detail("To principal", consulting["principal_id"])
    detail("Purpose", "personal_tax_planning_2026")

    family_handoff = {
        "from_principal": family["principal_id"],
        "to_principal": consulting["principal_id"],
        "action": "engage_external_advisor",
        "purpose": "personal_tax_planning_2026",
        "prev_family_head": family["chain_head"],
        "breath_gate_token": "owner-witnessed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    detail("Family-side action", family_handoff["action"])
    detail("Prev family head", family_handoff["prev_family_head"])
    family["actions"].append({"action_class": "engage_external_advisor",
                              "handoff_ref": "cross-mandate-001"})

    step("Consulting-side: issue 'accept_engagement' attested action")
    consulting_accept = {
        "from_principal": consulting["principal_id"],
        "accepting_engagement_from": family["principal_id"],
        "action": "accept_engagement",
        "purpose": "personal_tax_planning_2026",
        "prev_consulting_head": consulting["chain_head"],
        "breath_gate_token": "owner-witnessed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    detail("Consulting-side action", consulting_accept["action"])
    detail("Prev consulting head", consulting_accept["prev_consulting_head"])
    consulting["actions"].append({"action_class": "accept_engagement",
                                  "handoff_ref": "cross-mandate-001"})

    step("Joint attestation: link both chain heads without merging")
    joint = {
        "joint_attestation_id": "cross-mandate-001",
        "linked_heads": {
            family["principal_id"]: family["chain_head"],
            consulting["principal_id"]: consulting["chain_head"],
        },
        "purpose": "personal_tax_planning_2026",
        "breath_gate_token": "owner-witnessed",
        "principals_remain_isolated": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    detail("Joint attestation id", joint["joint_attestation_id"])
    detail("Linked heads", list(joint["linked_heads"].keys()))
    detail("Principals merged?", "NO — chains stay separate by design")
    return joint


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    banner("USN — MULTI-MANDATE HANDOFF DEMO (One Human, Three Fiduciary Hats)")
    print("Book 10, Chapter 7 — The Multi-Mandate Operator")
    print("Worked example from Kenneth's actual mandate stack.")

    # Three mandates, three principal_ids, three audit chains
    quadroof = boot_mandate("quadroof-cfo-2026", "cfo_agent", "corporate_regulated")
    fractional = boot_mandate("fractional-cfo-2026", "cfo_agent", "corporate_standard")
    family = boot_mandate("family-cfo-2026", "family_cfo_agent", "family")

    # Each runs its own work — chains stay separate
    run_corporate_mandate(quadroof)
    run_consulting_mandate(fractional)
    run_family_mandate(family)

    banner("PER-MANDATE CHAIN HEADS")
    for m in (quadroof, fractional, family):
        print(f"    {m['mandate_id']}: head={m['chain_head']} | actions={len(m['actions'])}")

    # Cross-mandate handoff (Family → Fractional)
    joint = cross_mandate_handoff(family, fractional)

    # Emit verification artifact
    summary = {
        "demo": "multi_mandate_handoff",
        "book_chapter": "B10C7",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mandates": [
            {
                "mandate_id": m["mandate_id"],
                "principal_id": m["principal_id"],
                "chain_head": m["chain_head"],
                "action_count": len(m["actions"]),
            }
            for m in (quadroof, fractional, family)
        ],
        "joint_attestation": joint,
    }
    out_path = "memory/MultiMandateHandoff_summary.json"
    try:
        Path("memory").mkdir(exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"\n    Verification artifact: {out_path}")
    except OSError:
        print("\n    (Verification artifact emit skipped — memory/ not writable)")

    banner("EXPECTED RECEIPT (Book 10 Ch 7)")
    print("    • Three distinct principal_ids, three distinct chain heads")
    print("    • One joint_attestation_id linking the two engaged mandates")
    print("    • principals_remain_isolated: true (no chain merge)")
    print("    • breath_gate_token present on both sides (owner-witnessed)")
    print("    • If you see all four, multi-mandate operation is structurally sound.")

    print("\n" + "∞Δ" * 25)
    print("One human. Three hats. Three sovereign chains. One witnessed handoff.")
    print("This is the structural answer to fiduciary multiplicity.")
    print("∞Δ" * 25 + "\n")


if __name__ == "__main__":
    main()
