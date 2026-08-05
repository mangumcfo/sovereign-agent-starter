"""Private Series Templates (s5_28 / reading Vol 30) — family and enterprise constitutions as governed objects.

A long-lived sovereign enterprise -- a family office, a multi-generational business -- runs on a constitution: the
written articles that say who decides, what is core, how succession works. The legacy constitution is a document in
a drawer: implicit where it should be explicit, edited in place where it should be versioned, and amendable by
whoever holds the pen with no record of what changed or why. This module makes a constitution a governed object.

It builds **one new act -- a governed constitution template whose core is protected and whose amendments are
governed versions** -- by composing the sealed Sovereign Object Model, not by building a constitution store of its
own:

  * `open_constitution` -- a constitution is registered as a governed object under a mandate (composing the sealed
    object registry): its articles are the payload, authored and provenance-checked, under exactly one mandate.
  * `core_envelope` -- declares which articles are CORE and how far they may move (composing the sealed change
    `Envelope`): the immutable or bounded articles a constitution must protect.
  * `amend` -- an amendment is a governed VERSION (composing the sealed `apply_change`): an amendment inside the
    envelope is a new authored version appended to the constitution's history; a change to a core article beyond the
    envelope is REFUSED unless it carries a human-gated approval (an approver + an approval reference); prior
    versions are never touched, so the constitution's full history -- what changed, when, by whom -- is preserved.

No constitution store, no amendment engine -- only the constitution framing over the sealed object model, so the
core truth is preserved by the object model's own law. Pure composition (the object model is hashlib-based): runs
green on a bare clone."""
from __future__ import annotations

from typing import Dict, Mapping, Sequence

from ..objects.lifecycle import Envelope, apply_change, EnvelopeRefusal  # noqa: F401  (re-exported context)


class ConstitutionError(ValueError):
    """Raised when a constitution cannot be opened or amended honestly. A core amendment beyond the envelope surfaces
    as the sealed object model's EnvelopeRefusal (with the violated article cited), so a constitution's core is
    protected by the same law that governs every object's change envelope."""


def open_constitution(reg, constitution_id: str, articles: Mapping, *, mandate: str,
                      author: str, source_ref: str, at: str) -> Dict[str, object]:
    """Open a constitution as a governed object under a mandate -- composing the sealed object registry. Its
    `articles` become the object's payload, authored and provenance-checked, registered under exactly one mandate
    (the family's or the enterprise's). The constitution is now a governed object like any other: versioned,
    integrity-hashed, and owned by one mandate -- not a document in a drawer."""
    if not constitution_id:
        raise ConstitutionError("a constitution needs an id")
    if not articles:
        raise ConstitutionError("a constitution needs at least one article")
    obj_id = f"constitution:{constitution_id}"
    return reg.append(obj_id, dict(articles), author=author, source_ref=source_ref, at=at,
                      mandate=mandate, kind="ratify")


def core_envelope(core_rules: Mapping) -> Envelope:
    """Declare the CORE-protection envelope for a constitution -- composing the sealed change `Envelope`. `core_rules`
    maps a core article to its bound (an `allowed` set, a `range`, or a `max_delta`); an article named here is core,
    and an amendment moving it outside its bound is refused unless human-gated. Articles not named are freely
    amendable within the governed-version discipline. This is where a constitution declares what may not quietly
    change -- its immutable or bounded core."""
    return Envelope(dict(core_rules))


def amend(reg, constitution_id: str, changes: Mapping, *, envelope: Envelope, author: str,
          source_ref: str, at: str, approver: str = None, approval_ref: str = None) -> Dict[str, object]:
    """Amend a constitution -- a governed VERSION via the sealed `apply_change`, drift-safe and fail-closed. An
    amendment inside the core envelope is appended as a new authored version; an amendment that would move a CORE
    article beyond its envelope is REFUSED with the article cited, unless it carries a human-gated approval (an
    `approver` and an `approval_ref`). Prior versions are never touched -- the constitution's full history is
    preserved, so every amendment is a governed act on the record, never an in-place edit of the core truth."""
    obj_id = f"constitution:{constitution_id}"
    return apply_change(reg, obj_id, dict(changes), author=author, source_ref=source_ref, at=at,
                        envelope=envelope, approver=approver, approval_ref=approval_ref)
