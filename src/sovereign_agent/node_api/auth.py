"""
principal_id-bearer auth middleware.

Per contract_v1.yaml `auth`:

    model:       "principal_id-bearer"
    source:      "node-local credential file at
                  ~/.breathline/credentials/<principal_id>.token (chmod 0600)"
    enforcement: "every request maps to a principal_id; no hardcoded principals
                  (CONSTITUTION §1)"

This is a minimal viable implementation. It accepts any non-empty bearer
token in the form `<principal_id>:<token>` and binds the principal_id to
`flask.g.principal_id` for downstream handlers. The actual token-file
verification is sketched as `_verify_token_against_file()` so it can be
hardened in a follow-up without changing the call site.

Embodies Principle 1 (Human Primacy & Sovereign Agency) — every request
flows under an explicit principal_id; no implicit roots.
"""

from __future__ import annotations

import hmac
import os
from functools import wraps
from pathlib import Path
from typing import Callable

from flask import g, jsonify, request

from .errors import invalid_bearer_token, missing_bearer_token


CREDENTIALS_DIR = Path(os.path.expanduser("~/.breathline/credentials"))


def _extract_bearer() -> str | None:
    """Pull the `Authorization: Bearer <token>` header value, or None."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:].strip()
    return token or None


def _verify_token_against_file(token: str) -> tuple[bool, str | None, str]:
    """
    Minimal-viable token verification.

    Accepts a token of the form `<principal_id>:<secret>` and looks for
    a corresponding file at ~/.breathline/credentials/<principal_id>.token.
    The file's contents (trimmed) must equal the `<secret>` portion.

    Returns: (ok, principal_id, reason_if_not_ok)
    """
    if ":" not in token:
        return False, None, "token missing principal_id prefix (expected '<principal_id>:<secret>')"

    principal_id, secret = token.split(":", 1)
    principal_id = principal_id.strip()
    secret = secret.strip()

    if not principal_id or not secret:
        return False, None, "empty principal_id or secret"

    cred_file = CREDENTIALS_DIR / f"{principal_id}.token"
    if not cred_file.exists():
        return False, None, f"no credential file for principal_id '{principal_id}'"

    try:
        # 0600 check is informational here — the OS enforces the actual access
        stored = cred_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        return False, None, f"credential read failed: {exc}"

    if not hmac.compare_digest(stored, secret):  # constant-time compare — no timing oracle (audit)
        return False, None, "stored secret does not match presented token"

    return True, principal_id, ""


def _is_dev_mode() -> bool:
    return os.environ.get("BREATHLINE_NODE_API_DEV", "").lower() in {"1", "true", "yes"}


def _loopback_owner() -> str | None:
    """
    Loopback-trust (KM-1176 ratified 2026-06-03, personal-sovereign-node posture).

    When the operator starts the node with BREATHLINE_NODE_LOOPBACK_OWNER=<principal_id>,
    requests originating from this machine's loopback interface authenticate as that
    principal WITHOUT a bearer token. This is NOT a hardcoded principal (CONSTITUTION §1):
    the principal flows in explicitly from operator-set config at node start, and applies
    ONLY to loopback (127.0.0.1 / ::1). Remote / federation peers are unaffected — they
    still present a verified token. Rationale: on your own machine you ARE the sovereign
    operator; requiring a token to talk to your own loopback node is burden, not sovereignty.
    """
    return (os.environ.get("BREATHLINE_NODE_LOOPBACK_OWNER", "") or "").strip() or None


def _is_loopback() -> bool:
    ra = request.remote_addr or ""
    return ra in {"127.0.0.1", "::1", "::ffff:127.0.0.1", "localhost"}


def require_principal(fn: Callable):
    """
    Decorator: enforce principal_id-bearer auth on a route.

    On success, binds `flask.g.principal_id` for the handler's lifetime.
    On failure, returns a loud contextual JSON error per CONSTITUTION §4.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_bearer()
        dev_mode = _is_dev_mode()

        # Dev mode allows either (a) no Authorization header at all, or
        # (b) a token with the "dev:" prefix. The "dev:" form is needed for
        # browsers that always send Authorization once it is set in
        # localStorage. Both paths set g.auth_dev_mode = True so handlers and
        # logs can surface the dev-mode condition.
        if dev_mode:
            if not token:
                g.principal_id = "dev:anonymous"
                g.auth_dev_mode = True
                return fn(*args, **kwargs)
            if token.startswith("dev:"):
                g.principal_id = token  # carries the chosen dev label
                g.auth_dev_mode = True
                return fn(*args, **kwargs)
            # Fall through to real verification if a non-dev token was sent
            # while in dev mode — production tokens still must verify.

        # Loopback-trust: on this machine's own loopback, with no token presented,
        # authenticate as the operator-configured node owner (if set). Remote peers and
        # any request that DOES present a token fall through to real verification.
        loop_owner = _loopback_owner()
        if loop_owner and _is_loopback() and not token:
            g.principal_id = loop_owner
            g.auth_dev_mode = False
            g.auth_loopback = True
            return fn(*args, **kwargs)

        if not token:
            return jsonify(missing_bearer_token()), 401

        ok, principal_id, reason = _verify_token_against_file(token)
        if not ok:
            return jsonify(invalid_bearer_token(reason or "verification failed")), 401

        g.principal_id = principal_id
        g.auth_dev_mode = False
        return fn(*args, **kwargs)

    return wrapper


def current_principal() -> str:
    """Helper for handlers: return the verified principal_id for this request."""
    return getattr(g, "principal_id", "unknown")


def _node_owner() -> str | None:
    """The principal authorized for high-impact (code-executing) routes. BREATHLINE_NODE_OWNER if set,
    else the loopback owner the operator started the node with."""
    return (os.environ.get("BREATHLINE_NODE_OWNER", "") or "").strip() or _loopback_owner()


def require_owner(fn: Callable):
    """Authorization gate for routes that execute code / mutate the operator's machine
    (/produce, /apply, /recompile). Authentication (require_principal) must run FIRST — apply this
    decorator BELOW @require_principal. Allows ONLY the node owner principal; rejects dev/anonymous and
    any non-owner principal (incl. authenticated federation peers). 'Execute-after-Approve' becomes
    enforced authorization, not a docstring (audit 2026-06-10)."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        p = getattr(g, "principal_id", None)
        owner = _node_owner()
        if (not owner) or getattr(g, "auth_dev_mode", False) or str(p or "").startswith("dev:") or p != owner:
            return jsonify({
                "error": "forbidden",
                "what": "This route executes code or changes files on the operator's machine and is "
                        "restricted to the node owner principal.",
                "next_step": "Authenticate as the node owner. Dev/anonymous and non-owner principals "
                             "(including federation peers) are rejected here.",
            }), 403
        return fn(*args, **kwargs)

    return wrapper
