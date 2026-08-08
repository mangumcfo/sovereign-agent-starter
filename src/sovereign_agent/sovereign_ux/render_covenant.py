# -*- coding: utf-8 -*-
"""sovereign_ux.render_covenant — UX as Executable Covenant (S8 Vol 8, the capstone).

`render_covenant` renders the governing covenant/constitution — a sealed Constitutions object — as an
**inspectable, read-only, drift-checked** surface a successor can read and trust. It composes the
Sovereign Lens (V01): it **renders** the covenant, never rewrites it; it lets a reader **inspect** any
one article; and because every view fingerprints the WHOLE covenant, `verify_covenant` gives a plain
fresh-or-drifted **green light** that the covenant a successor reads is the one in force — a change to
any article flips it to drift. The covenant is not a dead document but a living, checkable surface.

Kill-targets: **renders, never rewrites** (read-only; the covenant is never mutated) · **no second
authority** (it renders the sealed Constitutions object; it authors, enforces, and amends nothing —
imports only the Lens) · **drift-checked / living** (`verify_covenant` detects any change to the
covenant) · **inspectable** (any article renders read-only; an unknown article shows nothing,
deny-by-default) · **weakest-party verifiable** (a green light on any article proves the WHOLE covenant
unaltered, checkable without a second device or expertise). The volume composes the Lens (S8 Vol 1), the
Atrium host (S8 Vol 4), the breath-gate (S8 Vol 2), and the verification surface (S8 Vol 7) at the volume
level, and renders the sealed Constitutions object (S5 Vol 30); the voice/discourse covenant homes OUT to
Sovereign Discourse (S13). **Rolls no cryptography** — the covenant's integrity rests on the sealed
Constitutions floor; this surface only renders and drift-checks it.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from .lens import render_view, verify_view, View, ViewStatus    # V01 The Sovereign Lens

__all__ = ["render_covenant", "inspect_article", "verify_covenant"]


def render_covenant(covenant: Any, *, mandate: Optional[str] = None,
                    scope: Optional[Mapping[str, Sequence[str]]] = None) -> View:
    """Render the whole governing covenant as an inspectable, read-only Lens View. The covenant is
    rendered, never rewritten; the View fingerprints the whole covenant so `verify_covenant` can give a
    fresh-or-drifted green light. Read-only, honest, mandate-scoped; rolls no cryptography."""
    return render_view(covenant, mandate=mandate, scope=scope)


def inspect_article(covenant: Mapping[str, Any], article: str, *, mandate: Optional[str] = None,
                    scope: Optional[Mapping[str, Sequence[str]]] = None) -> View:
    """Render ONE article of the covenant, read-only. An unknown article shows nothing (deny-by-default).
    The article view fingerprints the WHOLE covenant, so verifying it detects a change ANYWHERE in the
    covenant — a successor reading one article can confirm the whole covenant is in force."""
    return render_view(covenant, mandate=mandate, scope=scope, fields=[article])


def verify_covenant(view: View, current_covenant: Any) -> ViewStatus:
    """Weakest-party check: a plain fresh-or-drifted green light that the rendered covenant surface
    matches the current sealed covenant object. A change to any article flips the light to drift, so a
    successor can trust the covenant they read is the one in force — checkable with no second device and
    no expertise. Composes the Lens's verify_view over the WHOLE covenant."""
    return verify_view(view, current_covenant)
