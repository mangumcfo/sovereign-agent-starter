#!/usr/bin/env python3
"""
qualification_gate.py — R22-5 Tiered + Qualified-Reviewer Breath-Gates (the peer spec 2026-06-12).

`require_owner` generalized: a reviewer may dispose an action only if their qualification RANK meets
the tier the action's class requires. The tier policy lives in governance-skin YAML (config/gate_tiers.yaml),
NEVER in code — amounts/severity/class tier the required reviewer by editing the table, not the source.

Composes R22-4: joint attestation gathers N roles; this gate decides whether EACH role is qualified for
the action's class. The sittings projection already lanes by act; this binds the platform side to it.

Success metric (R22-5): a class-Y action is rejected for an under-qualified reviewer and accepted for a
qualified one; the policy is data (YAML), not code.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = REPO / "config" / "gate_tiers.yaml"


def load_policy(path: Path | None = None) -> dict:
    return yaml.safe_load((path or DEFAULT_POLICY).read_text(encoding="utf-8"))


def _rank(qual: str, policy: dict) -> int:
    quals = policy.get("qualifications", [])
    return quals.index(qual) if qual in quals else -1


def required_qualification(action_class: str, policy: dict) -> str | None:
    return policy.get("gate_tiers", {}).get(action_class)


def meets(principal_qual: str, action_class: str, policy: dict) -> bool:
    req = required_qualification(action_class, policy)
    if req is None:
        return False                      # unknown class → default-deny (loud caller decides)
    return _rank(principal_qual, policy) >= _rank(req, policy) >= 0


def check(principal_qual: str, action_class: str, policy: dict | None = None) -> tuple[bool, str]:
    policy = policy or load_policy()
    req = required_qualification(action_class, policy)
    if req is None:
        return False, f"unknown action class '{action_class}' — no tier policy (default-deny)"
    if meets(principal_qual, action_class, policy):
        return True, f"'{principal_qual}' meets tier '{req}' for class '{action_class}'"
    return False, f"'{principal_qual}' under-qualified for class '{action_class}' (requires '{req}')"


def main() -> int:
    ap = argparse.ArgumentParser(description="R22-5 qualification gate check")
    ap.add_argument("--qual", required=True); ap.add_argument("--class", dest="cls", required=True)
    ap.add_argument("--policy", default=None)
    a = ap.parse_args()
    pol = load_policy(Path(a.policy)) if a.policy else load_policy()
    ok, why = check(a.qual, a.cls, pol)
    print(("✓ " if ok else "✗ ") + why)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

# ∞Δ∞ SEAL: graduated gates — the tier policy is data, the gate is one rank comparison. A controller
#          disposes class_x; only the owner disposes class_y; edit the YAML, never the code. ∞Δ∞
