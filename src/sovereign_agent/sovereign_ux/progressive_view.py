# -*- coding: utf-8 -*-
"""sovereign_ux.progressive_view — Generational UX (S8 Vol 5).

`progressive_view` renders the **same governed object** at a chosen complexity **level** — a
novice/operator/expert projection for cognitive diversity, and a **handoff** projection a successor can
read in full. It composes the Sovereign Lens (V01): the object is never changed, a simpler level **omits**
detail but never **distorts** it, and every level's View fingerprints the FULL object, so a simple view
can still be verified against the whole and can never quietly hide drift.

Kill-targets: **the same object at every level** (a level filters which fields are shown; it never
substitutes a different or wrong value) · **read-only** (renders through the Lens; never mutates the
object) · **handoff completeness** (the successor level omits nothing an heir needs — it shows the whole
object) · **no second authority** (renders, owns nothing; imports only the Lens) · **deny-by-default**
(an unknown level shows nothing). Composes the Sovereign Lens (S8 Vol 1) and the Atrium host (S8 Vol 4)
at the volume level; continuity homes to Generational Continuity (S5 Vol 29) and onboarding to Node
Onboarding (S6 Vol 6); estate/handoff logic homes OUT to Generational Transfer (S12). **Rolls no
cryptography.**
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from .lens import render_view, verify_view, View, ViewStatus    # V01 The Sovereign Lens

__all__ = ["LevelSet", "progressive_view", "handoff_view", "verify_level", "HANDOFF"]

HANDOFF = "handoff"   # the successor level — shows the WHOLE object, omits nothing


@dataclass(frozen=True)
class LevelSet:
    """A node's declared progressive-disclosure levels — ``{level_name: [field names]}`` — the owner's
    frozen governed object. The `HANDOFF` level is implicit and always shows the whole object; an
    undeclared level shows nothing (deny-by-default)."""
    levels: Mapping[str, Sequence[str]]

    def fields_for(self, level: str) -> Optional[list]:
        """The Lens `fields` allow-list for a level: `None` = all fields (the HANDOFF/successor level);
        the declared list for a known level; `[]` (deny-by-default) for an unknown level."""
        if level == HANDOFF:
            return None                              # the successor sees the whole object
        if level not in self.levels:
            return []                                # deny-by-default: an unknown level shows nothing
        return list(self.levels[level])


def progressive_view(obj: Any, level_set: LevelSet, *, level: str = "operator",
                     mandate: Optional[str] = None,
                     scope: Optional[Mapping[str, Sequence[str]]] = None) -> View:
    """Render the SAME governed object at a chosen complexity `level` through the Sovereign Lens. A
    simpler level omits fields but never distorts them (the values shown are the object's own); the
    `HANDOFF` level shows the whole object; an unknown level shows nothing (deny-by-default). The View
    fingerprints the FULL object regardless of level, so any level can be verified against the whole.
    Read-only; composes the Lens; rolls no cryptography."""
    fields = level_set.fields_for(level)
    return render_view(obj, mandate=mandate, scope=scope, fields=fields)


def handoff_view(obj: Any, level_set: Optional[LevelSet] = None, *, mandate: Optional[str] = None,
                 scope: Optional[Mapping[str, Sequence[str]]] = None) -> View:
    """The successor handoff view — the whole governed object, omitting nothing an heir needs to inherit
    it. Renders read-only through the Lens (the `HANDOFF` level). `level_set` is accepted for symmetry
    but the handoff always shows the full object."""
    return render_view(obj, mandate=mandate, scope=scope, fields=None)


def verify_level(view: View, current_source: Any) -> ViewStatus:
    """Freshness of a level-scoped View against the object's current full state — because every level
    fingerprints the FULL object, a simpler level's View detects drift in the whole exactly as the
    handoff view would, so no level can silently show a stale object."""
    return verify_view(view, current_source)
