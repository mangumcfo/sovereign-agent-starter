"""lifecycle.py — governed object lifecycle (S5-05-E1-2, E5-1, E5-2, E5-4).

An object changes only by appending a version; prior versions stay readable and
are never rewritten. Value-at-a-stated-date returns the value WITH its approver.
Retirement is a closing version, not a deletion. A change outside the declared
envelope is refused with the rule cited — never silently applied (the object-
granularity binding of the policy-refusal-at-the-write law; the obligation-
granularity half lives in AA's write_rules lane).
"""
from __future__ import annotations

from .registry import ObjectRegistry


class EnvelopeRefusal(PermissionError):
    """Raised with the violated rule CITED. Refusal is the message, not silence."""


class Closed(ValueError):
    """A closed object accepts no further change versions (it stays readable)."""


class Envelope:
    """Declared change envelope for an object class: per-field bounds or allowed
    sets. Anything outside needs a human-gated approval (approver + approval_ref)."""

    def __init__(self, rules: dict):
        # rules: field -> {"max_delta": n} | {"range": (lo, hi)} | {"allowed": [...]}
        self.rules = rules

    def check(self, prior_payload: dict, changes: dict) -> list[str]:
        """Return the CITED rule violations (empty = inside the envelope)."""
        out = []
        for field, new in changes.items():
            rule = self.rules.get(field)
            if rule is None:
                continue
            if "max_delta" in rule:
                old = prior_payload.get(field, 0)
                if abs(new - old) > rule["max_delta"]:
                    out.append(f"envelope rule {field}.max_delta={rule['max_delta']}: "
                               f"change {old}->{new} exceeds it")
            if "range" in rule:
                lo, hi = rule["range"]
                if not (lo <= new <= hi):
                    out.append(f"envelope rule {field}.range=({lo},{hi}): {new} is outside")
            if "allowed" in rule and new not in rule["allowed"]:
                out.append(f"envelope rule {field}.allowed={rule['allowed']}: {new!r} is not")
        return out


def apply_change(reg: ObjectRegistry, obj_id: str, changes: dict, *, author: str,
                 source_ref: str, at: str, envelope: Envelope | None = None,
                 approver: str | None = None, approval_ref: str | None = None) -> dict:
    """Append a change version. Out-of-envelope without a human approval is refused
    with the rule cited (S5-05-E5-2). Prior versions are never touched (E5-1)."""
    prior = reg.versions(obj_id)
    if not prior:
        raise ValueError(f"{obj_id}: unknown object — register it before changing it")
    if prior[-1]["kind"] == "close":
        raise Closed(f"{obj_id} is closed; its history stays readable but accepts no change")
    payload = dict(prior[-1]["payload"])
    if envelope is not None:
        violations = envelope.check(payload, changes)
        if violations and not (approver and approval_ref):
            raise EnvelopeRefusal(
                f"change to {obj_id} refused, not silently applied — " + "; ".join(violations)
                + " — a human-gated approval (approver + approval_ref) is required")
    payload.update(changes)
    return reg.append(obj_id, payload, author=author, source_ref=source_ref, at=at,
                      mandate=reg.mandate_of(obj_id), approver=approver,
                      approval_ref=approval_ref)


def close_object(reg: ObjectRegistry, obj_id: str, *, author: str, source_ref: str,
                 at: str, approver: str | None = None,
                 approval_ref: str | None = None) -> dict:
    """Retirement is a closing VERSION (kind='close'), never a deletion (E5-4)."""
    prior = reg.versions(obj_id)
    if not prior:
        raise ValueError(f"{obj_id}: unknown object")
    return reg.append(obj_id, dict(prior[-1]["payload"]), author=author,
                      source_ref=source_ref, at=at, mandate=reg.mandate_of(obj_id),
                      kind="close", approver=approver, approval_ref=approval_ref)


def value_at(reg: ObjectRegistry, obj_id: str, as_of: str) -> tuple[dict, str | None, dict]:
    """The object's payload at a stated past date, WITH its approver (E1-2):
    (payload, approver, full_version). Versions carry caller-stated ISO `at`
    stamps, so lexicographic comparison is chronological."""
    candidates = [v for v in reg.versions(obj_id) if v["at"] <= as_of]
    if not candidates:
        raise ValueError(f"{obj_id}: no version at or before {as_of}")
    v = candidates[-1]
    return v["payload"], v.get("approver"), v
