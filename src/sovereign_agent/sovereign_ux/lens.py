# -*- coding: utf-8 -*-
"""sovereign_ux.lens — The Sovereign Lens (S8 Vol 1).

`render_view` renders ANY governed object into an honest, drift-detected **View** the node owns.

Kill-targets, enforced here:
  * **Renders, never writes.** The Lens produces a View; it exposes no path that mutates the source
    governed object. `render_view`, `verify_view`, and `show` are read-only. `View` is frozen.
  * **Content-agnostic.** It composes node_api's `_to_jsonable` serialisation seam, which renders any
    type (primitive, bytes, datetime, Enum, dataclass, dict, list/tuple, set, attribute carriers) and
    *raises* rather than silently losing structure. No object type is privileged.
  * **Honest views / drift detection.** A View fingerprints the FULL source at render time. A source
    that has since changed is DRIFT — `verify_view` flags it and `show` REFUSES to display a drifted
    view. A view that diverges from its source is never silently shown.
  * **Multi-mandate scoped rendering.** Given a `mandate` (the scoping principal, S5 Vol 28) and a
    `scope` map (mandate → visible fields), the Lens projects only the fields that mandate admits;
    an unknown mandate is deny-by-default (sees nothing). In deployment the scope resolves from the
    node's `role_binder` role/mandate config; here it is supplied explicitly and enforced.
  * **No second UI authority.** This is a pure function library over objects the node already owns.

Composes sealed floors only — the node_api render seam, `role_binder` scoping, and the Sovereign
Object Model (S5 Vol 5) objects it renders under the owner's mandate (S5 Vol 28). **Rolls no
cryptography**: drift is a canonical-content comparison, not a signature.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from ..node_api.json_provider import _to_jsonable  # the content-agnostic render seam (composed, not copied)

__all__ = ["View", "ViewStatus", "LensDrift", "render_view", "verify_view", "show"]


class LensDrift(Exception):
    """Raised when a drifted View is asked to be shown — an honest view is never silently stale."""


def _canonical(obj: Any) -> Any:
    """A content-agnostic, JSON-safe snapshot of ``obj``. Composes node_api's ``_to_jsonable``.

    Read-only: the seam builds new structures and reads attributes; the source object is untouched.
    """
    return _to_jsonable(obj)


def _fingerprint(canonical: Any) -> str:
    """A stable, **crypto-free** content fingerprint = the canonical JSON of the snapshot.

    Two sources are 'the same' iff their canonical content matches. This rolls no cryptography — it
    is a deterministic serialisation, not a hash or signature. Drift = fingerprint mismatch.
    """
    return json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class View:
    """An honest, read-only projection of a governed object.

    Frozen by construction: you cannot write the governed object back through a View. ``content`` is
    the (possibly mandate-scoped) projection; ``fingerprint`` is the canonical content of the FULL
    source at render time, so later drift can be detected against the live object.
    """
    content: Any
    fingerprint: str
    mandate: Optional[str]
    fields: Optional[tuple]
    object_type: str


@dataclass(frozen=True)
class ViewStatus:
    """The freshness verdict for a View against a current source."""
    fresh: bool
    drift: bool
    rendered_fingerprint: str
    current_fingerprint: str


def _allowed_fields(snapshot: Any, mandate: Optional[str],
                    scope: Optional[Mapping[str, Sequence[str]]],
                    fields: Optional[Sequence[str]]) -> Optional[list]:
    """Resolve which top-level field names this view may expose. ``None`` = all (unscoped).

    Precedence: an explicit ``fields`` allow-list wins; else a ``mandate`` + ``scope`` map
    (deny-by-default: an unknown mandate sees nothing); else ``None`` — an unscoped render, which is
    the single-mandate sovereign node's default (backward-compatible).
    """
    if fields is not None:
        return list(fields)
    if mandate is not None and scope is not None:
        if mandate not in scope:
            return []  # deny-by-default: an un-mapped mandate is admitted nothing
        return list(scope[mandate])
    return None


def _project(snapshot: Any, allowed: Optional[list]) -> Any:
    """Return a deep copy of ``snapshot`` restricted to ``allowed`` top-level fields.

    A deep copy guarantees the returned content shares no mutable state with the source. Field
    scoping applies to mapping snapshots (the common governed-object shape); for a non-mapping
    snapshot, an empty allow-list withholds it entirely and any other allow-list renders it whole
    (there are no named fields to filter).
    """
    if allowed is None:
        return copy.deepcopy(snapshot)
    if isinstance(snapshot, dict):
        return {k: copy.deepcopy(v) for k, v in snapshot.items() if k in allowed}
    if not allowed:
        return None  # deny-by-default withheld a non-mapping object
    return copy.deepcopy(snapshot)


def render_view(obj: Any, *, mandate: Optional[str] = None,
                scope: Optional[Mapping[str, Sequence[str]]] = None,
                fields: Optional[Sequence[str]] = None) -> View:
    """Render ANY governed object into an honest, read-only :class:`View`.

    * **Read-only** — ``obj`` is never mutated; the returned content is a deep copy.
    * **Content-agnostic** — composes ``_to_jsonable``; any type renders, none is privileged.
    * **Scoped** — with ``mandate`` + ``scope`` (or an explicit ``fields`` allow-list), only the
      admitted fields are exposed (multi-mandate scoped rendering, S5 Vol 28); deny-by-default.
    * **Honest** — the View fingerprints the FULL source, so :func:`verify_view` / :func:`show` can
      detect drift later.
    """
    snapshot = _canonical(obj)                 # content-agnostic, read-only snapshot
    fp = _fingerprint(snapshot)                # honest baseline over the FULL source
    allowed = _allowed_fields(snapshot, mandate, scope, fields)
    content = _project(snapshot, allowed)      # mandate-scoped projection (deep-copied)
    return View(
        content=content,
        fingerprint=fp,
        mandate=mandate,
        fields=tuple(allowed) if allowed is not None else None,
        object_type=type(obj).__name__,
    )


def verify_view(view: View, current_source: Any) -> ViewStatus:
    """Re-fingerprint ``current_source`` and report whether ``view`` is still fresh (no drift)."""
    now = _fingerprint(_canonical(current_source))
    fresh = now == view.fingerprint
    return ViewStatus(fresh=fresh, drift=not fresh,
                      rendered_fingerprint=view.fingerprint, current_fingerprint=now)


def show(view: View, current_source: Any) -> Any:
    """Return the view's content ONLY if it is still fresh against ``current_source``.

    A drifted view is **never silently shown** — showing a stale view raises :class:`LensDrift`.
    """
    status = verify_view(view, current_source)
    if status.drift:
        raise LensDrift(
            f"view of {view.object_type} has drifted from its source since render — "
            f"refusing to show a stale view (honest views: a divergent view is flagged, never shown)"
        )
    return view.content
