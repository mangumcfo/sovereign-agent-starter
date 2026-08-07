# -*- coding: utf-8 -*-
"""sovereign_ux.tokens — The Governed Aesthetic (S8 Vol 3).

A node's visual surface is governed by a **design-token set the node owns**: named design values
(color, type, spacing, motion) declared as the owner's governed object. `apply_tokens` renders a
governed object into a view **through** that token set — resolving every token reference to a governed
value and **refusing any off-token reference** (a value not in the declared set) deny-by-default.
`validate_drift` reports the off-token references in an object without rendering.

    apply_tokens(obj, token_set)  → a Lens View, with every token reference resolved to a governed
                                    value; an off-token reference is REFUSED (TokenDrift)
    validate_drift(obj, token_set) → the list of off-token references (drift); empty == consistent

The PRESENT capability is **token governance + drift validation** — a real registry and a real
validator, proven by tests. This volume makes **no claim about beauty, taste, or feeling**; those are
framing, never a built claim. It **composes the Sovereign Lens (Vol 1) only** — `render_view` — and
imports nothing else from the operator layer. It **rolls no cryptography**.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from .lens import render_view, View  # compose the Sovereign Lens (Vol 1) ONLY

__all__ = ["TokenSet", "TokenDrift", "apply_tokens", "validate_drift"]

# A token reference is a string of the form "$name" (dot/dash/underscore segments), e.g. "$brand.primary".
_TOKEN_REF = re.compile(r"^\$([A-Za-z0-9_][A-Za-z0-9_.\-]*)$")


class TokenDrift(Exception):
    """Raised when an object references a token that is not in the declared governed set (off-token)."""


@dataclass(frozen=True)
class TokenSet:
    """A governed design-token set the node owns — a frozen registry of named design values.

    Frozen by construction: the token set is a governed object, not a mutable palette the surface can
    edit. ``tokens`` maps a governed token name to its value.
    """
    name: str
    tokens: Mapping[str, Any]

    def has(self, token_name: str) -> bool:
        return token_name in self.tokens

    def resolve(self, token_name: str) -> Any:
        """The governed value for ``token_name``. An off-token name is refused, deny-by-default."""
        if token_name not in self.tokens:
            raise TokenDrift(f"off-token reference {token_name!r} is not in the governed set {self.name!r}")
        return self.tokens[token_name]


def _ref_name(value: Any) -> Optional[str]:
    """If ``value`` is a token reference ('$name'), return its name; else None."""
    if isinstance(value, str):
        m = _TOKEN_REF.match(value)
        if m:
            return m.group(1)
    return None


def validate_drift(obj: Any, token_set: TokenSet) -> list:
    """Return every token reference in ``obj`` (recursively) that is NOT in the governed set.

    An empty list means the object is token-consistent — every design value it references is governed.
    A non-empty list is drift: ad-hoc, off-token values the governed set does not sanction.
    """
    drift: list = []

    def walk(v: Any) -> None:
        name = _ref_name(v)
        if name is not None:
            if not token_set.has(name):
                drift.append(name)
            return
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)

    walk(obj)
    return drift


def _resolve(obj: Any, token_set: TokenSet) -> Any:
    """Return a copy of ``obj`` with every token reference resolved to its governed value.

    Assumes ``obj`` has already passed :func:`validate_drift` (no off-token references) — otherwise
    ``token_set.resolve`` raises :class:`TokenDrift`.
    """
    name = _ref_name(obj)
    if name is not None:
        return token_set.resolve(name)
    if isinstance(obj, dict):
        return {k: _resolve(v, token_set) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_resolve(v, token_set) for v in obj]
    return obj


def apply_tokens(obj: Any, token_set: TokenSet, *, mandate: Optional[str] = None,
                 scope: Optional[Mapping[str, Sequence[str]]] = None) -> View:
    """Render ``obj`` into a Lens :class:`View`, resolving every token reference to a governed value.

    * **Governed** — every token reference must be in ``token_set``; an off-token reference is
      **refused** (:class:`TokenDrift`), deny-by-default. The surface cannot apply an ungoverned value.
    * **Composes the Lens** — after resolution, the object is rendered by the Sovereign Lens
      (`render_view`), inheriting its read-only, honest, mandate-scoped rendering.
    * **No aesthetic claim** — this applies a *declared* token set; it asserts nothing about beauty.
    """
    drift = validate_drift(obj, token_set)
    if drift:
        raise TokenDrift(
            f"refusing an off-token render — {len(drift)} reference(s) not in the governed set "
            f"{token_set.name!r}: {sorted(set(drift))}"
        )
    resolved = _resolve(obj, token_set)
    return render_view(resolved, mandate=mandate, scope=scope)
