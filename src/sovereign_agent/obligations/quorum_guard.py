"""Multi-role quorum guard — pure helpers over an obligation's `debit` entry (no ledger import;
no cycle; crypto-free — this is authorization logic).

DOCTRINE (S2-V3 *The Harness That Builds Itself*, Ch 5 "The Veto Quorum and the Failure Modes It
Closes", manuscript_v1.6 L481-483 + Ch 2 playbook `cross_role_veto_quorum: 2`):
  "A quorum above one closes the single-compromised-reviewer failure mode: a drifting reviewer
   cannot wave a proposal through alone... The quorum is a Charter decision, not a technical
   default — the operator sets it per proposal class." The book's Ch 5 receipt names this exact
  build: "the multi-role quorum + federation-portable cross_role_review_v0.1.yaml (planned)."

RULE (Slice 2.2, graduates the "quorum enforcement" designed-toward item — spec
artifacts/specs/cross_role_review_v0.1.yaml):
  A MATERIAL obligation that declares quorum N (`debit.quorum`, set via ObligationLedger.open(quorum=…))
  is approved only when N DISTINCT principals have each recorded a gate-valid approval — each
  individually passing AH-1 (opener≠approver / real-gate) and the Slice-2.1 mandate guard. The OPENER
  never counts toward a multi-party quorum: declaring quorum > 1 is the operator's explicit opt-in to
  multi-party review, so the AH-1 single-owner real-gate exception governs the quorum-1 default only
  ("reviewing roles" review someone else's proposal — Ch 5). Fail-closed: below quorum ⇒ not approved
  (obligation stays open/pending; material close() stays barred via the same is_approved read).

SCOPE + INTERPLAY (stated loudly per the operator discipline #1):
  • MATERIAL_ONLY — same boundary as AH-1 and 2.1; GREEN/non-material routine actions keep quorum-1.
  • No `quorum` field ⇒ quorum 1 ⇒ today's single-approval flow, byte-identical (backward-compatible).
  • VETO is NOT re-implemented here: the existing R22-4 joint-attestation machinery (requires_attestation
    + veto/veto_clear entries, projection.attestation_status, default-deny can_execute) already carries
    the book's veto lane at the execution gate. This slice adds the APPROVAL-side quorum count the book
    names as designed-toward; the cross-node federation-portable review (Ch 5 receipt) remains
    designed-toward.
"""
from __future__ import annotations


def required_quorum(debit: dict | None) -> int:
    """The approval quorum an obligation declares (1 ⇒ default single-approval flow).
    Fail-closed on malformed values: anything non-castable or < 1 reads as 1 (never 0/negative —
    a quorum can never be satisfied by zero approvals)."""
    if not debit:
        return 1
    try:
        q = int(debit.get("quorum") or 1)
    except (TypeError, ValueError):
        return 1
    return q if q >= 1 else 1


def class_quorum_floor(class_quorum: dict | None, classification: str | None) -> int:
    """Charter-level MINIMUM approval quorum for a proposal CLASS (S2-V3 Ch 5: "the operator sets it
    per proposal class" — the playbook's class-level cross_role_veto_quorum mapping, now first-class).
    `class_quorum` is the Charter decision supplied at ledger construction, e.g. {"C2": 2, "C3": 3}.
    Fail-closed parse: no config / unknown class / malformed value / < 1 ⇒ floor 1 (never 0)."""
    if not class_quorum or not classification:
        return 1
    try:
        q = int(class_quorum.get(classification) or 1)
    except (TypeError, ValueError):
        return 1
    return q if q >= 1 else 1


def effective_quorum(declared: int | None, floor: int) -> int:
    """Compose an obligation's declared quorum with its class floor. The Charter's class decision is a
    FLOOR: a per-obligation declaration may RAISE the bar above it, never lower it below — an opener
    cannot undercut the Charter by declaring a smaller quorum (fail-closed toward more review)."""
    try:
        d = int(declared or 1)
    except (TypeError, ValueError):
        d = 1
    if d < 1:
        d = 1
    return d if d >= floor else floor
