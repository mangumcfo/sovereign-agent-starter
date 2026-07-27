"""scope.py — multi-mandate object isolation (S5-05-E6-1, E6-4).

Every object is scoped to exactly one mandate (enforced at the registry append —
see registry.MandateViolation), and each mandate derives its OWN root. A scoped-
sharing rule grants a named read or write scope across a boundary and nothing
wider: no rule, no access; a read grant never authorizes a write.
"""
from __future__ import annotations

from ..evidence.export_packet import _merkle_root
from .identity import version_leaf
from .registry import ObjectRegistry


class ScopeRefusal(PermissionError):
    """Cross-mandate access without a rule granting exactly that scope."""


def mandate_root(reg: ObjectRegistry, mandate: str) -> str:
    """The integrity root over ONE mandate's objects only — isolation at the
    root level, not just the row level (E6-1)."""
    state = {k: v for k, v in reg.current().items() if v.get("mandate") == mandate}
    return _merkle_root([version_leaf(state[k]) for k in sorted(state)])


class SharingRule:
    """One declared crossing: this object, from its home mandate, readable or
    writable by exactly one other mandate. Nothing implicit, nothing wider."""

    def __init__(self, obj_id: str, to_mandate: str, scope: str):
        if scope not in ("read", "write"):
            raise ValueError(f"scope must be 'read' or 'write', not {scope!r}")
        self.obj_id, self.to_mandate, self.scope = obj_id, to_mandate, scope


def check_access(reg: ObjectRegistry, rules: list[SharingRule], *,
                 principal_mandate: str, obj_id: str, want: str) -> bool:
    """True if the principal's mandate may `want` ('read'|'write') the object.
    Own-mandate access is whole; cross-mandate access needs a rule naming this
    object, this mandate, and a scope at least as strong. Raises ScopeRefusal
    otherwise — refusal, not silence (E6-4)."""
    home = reg.mandate_of(obj_id)
    if home is None:
        raise ValueError(f"{obj_id}: unknown object")
    if home == principal_mandate:
        return True
    for r in rules:
        if r.obj_id == obj_id and r.to_mandate == principal_mandate:
            if want == "read" or (want == "write" and r.scope == "write"):
                return True
            raise ScopeRefusal(
                f"{principal_mandate} holds a {r.scope!r} grant on {obj_id}; "
                f"{want!r} refused — a grant is exactly its declared scope, nothing wider")
    raise ScopeRefusal(
        f"{principal_mandate} holds no sharing rule on {obj_id} "
        f"(home mandate {home!r}) — cross-boundary access refused")
