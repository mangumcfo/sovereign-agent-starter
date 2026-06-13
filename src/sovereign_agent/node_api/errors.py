"""
Loud, contextual error builder per CONSTITUTION §4 and contract_v1.yaml.

Error shape (from contract_v1.yaml `errors.shape`):

    {
        "code":         "<machine-readable error code>",
        "what":         "<one-sentence description of what failed>",
        "why":          "<one-sentence cause>",
        "next_step":    "<one-sentence remediation hint>",
        "cylinder_ref": "<string|null — sealed evidence pointer if available>"
    }

No silent corruption. No bare 500s with stack traces. Every error names a
remediation. Embodies Principle 4 (Default-Deny + Constitutional Boundaries)
from SERIES_1_PRINCIPLES_TO_EMBODY_IN_THE_HARNESS.md.
"""

from __future__ import annotations

from typing import Optional


def build_error(
    code: str,
    what: str,
    why: str,
    next_step: str,
    cylinder_ref: Optional[str] = None,
) -> dict:
    """Build the canonical JSON error body."""
    return {
        "code": code,
        "what": what,
        "why": why,
        "next_step": next_step,
        "cylinder_ref": cylinder_ref,
    }


def route_error(
    error: str,
    what: str,
    why: str,
    next_step: str,
    cylinder_ref: Optional[str] = None,
) -> dict:
    """Route-handler error body (audit 2026-06-13d #9). The Atrium route modules historically returned
    ad-hoc `{"error": "<slug>", ...}` bodies with inconsistent fields (some had `what`, none had `why`
    or `code`). This unifies them onto the canonical shape WHILE preserving the friendly `error` slug the
    Atrium banner copy + existing tests read: `code` mirrors the slug (machine-readable), `error` stays the
    slug (back-compat). Every route error now carries code · error · what · why · next_step · cylinder_ref."""
    body = build_error(code=error, what=what, why=why, next_step=next_step, cylinder_ref=cylinder_ref)
    body["error"] = error
    return body


# ----------------------------------------------------------------------------
# Canonical error catalogue. Keep names stable; they appear in audit logs and
# Atrium UI banner copy. Adding new codes is fine; renaming existing codes
# requires a contract version bump.
# ----------------------------------------------------------------------------

def missing_bearer_token() -> dict:
    return build_error(
        code="AUTH_MISSING_TOKEN",
        what="Request lacks an Authorization bearer token.",
        why="Every Node API call must carry a principal_id-bearer token "
            "(CONSTITUTION §1, no hardcoded principals).",
        next_step="Add header: Authorization: Bearer <principal_id-token> "
                  "from ~/.breathline/credentials/<principal_id>.token (chmod 0600).",
    )


def invalid_bearer_token(reason: str = "unknown") -> dict:
    return build_error(
        code="AUTH_INVALID_TOKEN",
        what="Bearer token rejected.",
        why=f"Token verification failed: {reason}.",
        next_step="Re-issue the credential file via sovereign-install.sh "
                  "or check that the principal_id matches a registered node operator.",
    )


def not_implemented(endpoint_id: str, planned_at: str = "A1+") -> dict:
    return build_error(
        code="NOT_IMPLEMENTED",
        what=f"Endpoint '{endpoint_id}' is a contract placeholder.",
        why="The minimal Node API shell (Track A1) implements node + roles "
            "first; this endpoint lands in a follow-up increment.",
        next_step=f"Tracked for Track {planned_at}. Consume via the Python "
                  "core (UniversalSovereignNode / ComplianceEngine) in the "
                  "meantime; same receipt envelope.",
    )


def unknown_role(role_id: str) -> dict:
    return build_error(
        code="ROLE_NOT_FOUND",
        what=f"Role '{role_id}' is not registered on this node.",
        why="The PlaybookLoader could not discover a role_spec.yaml + "
            "handler binding for this role_id.",
        next_step="Call GET /api/v1/roles to list discoverable roles, or "
                  "verify the role lives under the federation primary source "
                  "(see sovereign_agent.config.resolve_primary_source).",
    )


def role_action_denied(role_id: str, action_class: str, reason: str) -> dict:
    return build_error(
        code="ROLE_ACTION_DENIED",
        what=f"Role '{role_id}' rejected action_class '{action_class}'.",
        why=reason,
        next_step="Verify the role's allowed_action_classes envelope, or "
                  "route the action through the breath-gate (YELLOW/RED) "
                  "with explicit operator witness.",
    )


def kernel_exception(detail: str) -> dict:
    return build_error(
        code="KERNEL_EXCEPTION",
        what="The Python core raised an unhandled exception while servicing the request.",
        why=f"{detail[:240]}",
        next_step="Capture the request_id, inspect the node's audit trail "
                  "(GET /api/v1/audit/cylinders), and re-run with "
                  "BREATHLINE_DEBUG=1 for a verbose handler trace.",
    )
