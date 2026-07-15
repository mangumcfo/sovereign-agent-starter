"""Breath Inventory Tier-1 defaults (P0-4) — the 'always approve on' cluster, embedded.

Per the peer's optimization analysis + the Breath Inventory: every role's action classes should
DEFAULT-SUGGEST the Tier-1 patterns that apply, so new roles (incl. those extruded from
series-pipeline L1 packets) inherit the battle-tested primitives instead of re-deriving them.

This is suggestion + embedding, NOT enforcement: agents PROPOSE with these defaults attached;
the human still disposes. B32 receipt + the breath-gate remain the hard rules (BG-1/2).
"""
from __future__ import annotations
from typing import Any, Dict, List

# The Tier-1 "always approve on" cluster (from Breath_Inventory_25-55).
TIER1: Dict[str, str] = {
    "B32": "Obligation Cylinder — dr/cr receipts + immutable audit (receipt everything material)",
    "B35": "Helix — deterministic 'book writes the backend' rendering (living-spec output)",
    "B51": "Agent-to-Agent Handoffs (A4) — safe multi-agent coordination trace",
    "B42": "Deterministic Agent Swarms — receipted, reproducible coordination",
    "B43": "Unified Crypto Stack — auditable cryptography",
    "B39": "Crypto Primitive Wiring — canonical primitives for packet immutability",
    "B31": "SIX — Sovereign Inference Exchange — receipts & verification (attestation)",
    "B30": "Autonomy Spine — directive/spec/prompt triad for governed agents",
    "B26": "Yield Organisms & XRPL — economic / yield layer (families-first value)",
    "B28": "Legal Framework Hardening — lex mercatoria / jus cogens for contracts",
    "B25": "Federation / resonant shards — opt-in, non-devouring federation + privacy",
}

# keyword → breath rules (matched against action id + description, lowercased).
_RULES = [
    (("zk", "proof", "profile", "privacy", "sign", "hash", "crypt"), ["B43", "B39", "B25"]),
    (("attest", "six", "verify", "receipt"), ["B31"]),
    (("optim", "coordinat", "match", "swarm", "run_"), ["B42", "B51"]),
    (("handoff", "agent", "negotiat", "propose"), ["B51"]),
    (("render", "spec", "plan", "document", "report", "draft", "living"), ["B35"]),
    (("value", "yield", "distribut", "pool", "procure", "guild", "order"), ["B26"]),
    (("contract", "agreement", "order", "legal", "commit", "guild"), ["B28"]),
]


def suggest_for_action(action: Dict[str, Any]) -> List[Dict[str, str]]:
    """Return the Tier-1 breaths that apply to one action_class, with reasons.

    Always includes B32 (every action is a receipted obligation). Material actions add B51
    (a visible handoff trace becomes evidence) + B28 where a commitment/contract is implied.
    """
    text = (str(action.get("id", "")) + " " + str(action.get("description", ""))).lower()
    gate = str(action.get("breath_gate", "")).upper()
    material = bool(action.get("material")) or gate.startswith("RED")

    picked: List[str] = ["B32"]  # always: receipt everything
    if material:
        picked += ["B51"]  # material → a visible handoff trace is part of the evidence
    for keys, breaths in _RULES:
        if any(k in text for k in keys):
            picked += breaths

    seen, out = set(), []
    for b in picked:
        if b not in seen and b in TIER1:
            seen.add(b)
            out.append({"breath": b, "why": TIER1[b]})
    return out


def enrich_role(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of a role_spec with Tier-1 defaults attached per action_class + at role level.

    Non-destructive: existing fields are preserved; we only ADD `tier1_defaults` (list of breath ids)
    to each action and a `breath_inventory` summary block to the role. Idempotent.
    """
    out = dict(spec)
    out["breath_inventory"] = {
        "tier1_applied": True,
        "cluster": list(TIER1.keys()),
        "note": "Defaults suggested per action; agents propose, human disposes. B32 receipt + breath-gate are hard.",
    }
    actions = []
    for a in spec.get("action_classes", []) or []:
        a2 = dict(a)
        a2["tier1_defaults"] = [d["breath"] for d in suggest_for_action(a)]
        actions.append(a2)
    if actions:
        out["action_classes"] = actions
    return out


# ∞Δ∞ SEAL: Breath Inventory Tier-1 defaults — embedded suggestion, human still disposes ∞Δ∞
