# -*- coding: utf-8 -*-
"""onboarding.onboard — the 5-turn human onboard (Phase 1, KM GO 2026-08-11).

A fresh human brings a node into existence on THEIR OWN iron, offline. The AI proposes; the human disposes.
Order is fixed and every write is traceable to a human turn:

  1. Key ceremony  — state the terms plainly (key on this machine only · no passphrase · no recovery service ·
                     lose the file = lose the identity) → the human ACCEPTS → **only then** is the key minted.
                     No key is written before the turn-1 accept.
  2. Name          — the human names this node.
  3. Gated acts    — a DEFAULT-DENY minimal set of acts that will always require the human's hand; the human edits it.
  4. First gate    — the first gated act is routed through the sealed HumanApprovalGate (S5 V16); the human gates it.
  5. Receipt       — a signed onboard receipt + how to verify it WITHOUT the AI (offline, from the human's own key).

No cloud is required for turns 1–5. No telemetry, no phone-home, no default peers, no account. It composes the
sealed gate + the D1 keystore's own verify surface — it invents no new authority. UAT receipts carry `uat: true`,
never use principal `KM-1176`, and never enter the seal ledger (they land in a local onboard log only).
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Sequence, Tuple

from ..keystore.node_keystore import (
    generate_node_key, has_node_key, load_node_key, sign_node_act, verify_node_act, KeystoreError,
)
from ..compliance.human_approval_gate import HumanApprovalGate, ApprovalRequest

__all__ = ["OnboardTurn", "OnboardReceipt", "OnboardOutcome", "run_onboard", "verify_onboard_receipt",
           "KEY_CEREMONY_TEXT", "DEFAULT_GATED_ACTS", "OnboardError"]

# Turn-1 ceremony text — shown to the human BEFORE any key is written.
KEY_CEREMONY_TEXT = (
    "KEY CEREMONY — read before you accept.\n"
    "  • This key is generated on THIS machine only. It never leaves your iron.\n"
    "  • There is NO passphrase on it (it is a file under your control).\n"
    "  • There is NO recovery service. No one — not us, not any cloud — can restore it for you.\n"
    "  • If you lose the key file, you lose this identity permanently.\n"
    "No key is written until you accept. Accept? (yes/no)"
)

# Turn-3 default-DENY minimal set — the human edits this. These acts will always require the human's hand.
DEFAULT_GATED_ACTS: Tuple[str, ...] = (
    "send_value", "delegate_authority", "change_governance", "share_data_externally",
)


class OnboardError(ValueError):
    """An onboarding turn was refused (e.g. a UAT receipt tried to use the sovereign principal)."""


@dataclass(frozen=True)
class OnboardTurn:
    """One human turn. `kind` tells the prompter what disposition to return:
    accept→bool · name→str · edit_set→list[str] · gate→"approved"/"denied" · show→(ignored)."""
    n: int
    title: str
    kind: str
    text: str
    payload: Any = None


@dataclass(frozen=True)
class OnboardOutcome:
    """A terminal onboarding outcome that did NOT produce a node (e.g. declined at turn 1). `key_written` is
    False — the whole point of turn 1 is that nothing is written until the human accepts."""
    status: str
    turn: int
    key_written: bool
    message: str
    writes: Tuple[dict, ...] = ()


@dataclass(frozen=True)
class OnboardReceipt:
    """The turn-5 receipt: the human's node, its fingerprint, the acts they reserved to their hand, the first
    gate disposition, and every write traced to its turn. Signed with the node's OWN key; verifiable offline
    without the AI. `uat` marks a test run; UAT receipts never enter the seal ledger."""
    node_id: str
    node_name: str
    fingerprint: str
    gated_acts: Tuple[str, ...]
    first_act: str
    first_gate: dict
    turns: Tuple[dict, ...]
    writes: Tuple[dict, ...]
    uat: bool
    principal: str
    created_at: str
    signed_payload: str          # the exact bytes (hex) the signature covers
    signature: str
    verify_instructions: str
    receipt_path: str


def _receipt_body(node_id, name, fingerprint, gated_acts, first_act, first_gate, uat, principal, created_at) -> dict:
    return {
        "kind": "onboard_receipt", "node_id": str(node_id), "node_name": str(name),
        "fingerprint": str(fingerprint), "gated_acts": list(gated_acts), "first_act": str(first_act),
        "first_gate": {"status": first_gate.get("status"), "approver": first_gate.get("approver")},
        "uat": bool(uat), "principal": str(principal), "created_at": str(created_at),
    }


def _append_local_receipt(keystore_dir: Optional[str], row: dict) -> str:
    """Append the onboard receipt to a LOCAL onboard log on the operator's own iron — NEVER the seal ledger.
    Onboarding is not a seal; this record is the human's own, beside their key."""
    base = keystore_dir or os.environ.get("NODE_KEYSTORE_DIR") or "."
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, "onboard_receipts.ndjson")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    return path


def run_onboard(keystore_dir: Optional[str], *, prompter: Callable[[OnboardTurn], Any], at: str,
                node_id: str = "node", uat: bool = False, gate: Optional[HumanApprovalGate] = None):
    """Run the fixed 5-turn onboard. `prompter(turn)` presents each turn to the human and returns their
    disposition. Returns an `OnboardReceipt` on completion, or an `OnboardOutcome` if the human declines at
    turn 1 (in which case NO key is written). Every write is recorded against its turn."""
    writes: list = []

    def _wrote(turn: int, what: str) -> None:
        writes.append({"turn": turn, "write": what})

    turns: list = []

    # ---- TURN 1 · Key ceremony — the terms are shown, then accepted, BEFORE any key is written ----
    t1 = OnboardTurn(1, "Key ceremony", "accept", KEY_CEREMONY_TEXT)
    accepted = bool(prompter(t1))                                                    # the human reads, then disposes
    turns.append({"turn": 1, "kind": "accept", "disposition": accepted})
    if not accepted:
        # No mint, no config, no file — declining costs nothing and leaves nothing behind.
        return OnboardOutcome(status="declined", turn=1, key_written=False, writes=tuple(writes),
                              message="onboarding declined at the key ceremony — NO key was written")
    if has_node_key(keystore_dir, node_id):
        nodekey = load_node_key(keystore_dir, node_id)                               # existing identity — never silently re-mint
    else:
        nodekey = generate_node_key(keystore_dir, node_id, at=at)                    # ONLY after the turn-1 accept
        _wrote(1, f"generate_node_key:{node_id}")

    # ---- TURN 2 · Name this node ----
    name = str(prompter(OnboardTurn(2, "Name this node", "name",
                                    "Give THIS node (this machine) a short label — e.g. 'Dragon', 'home-laptop', "
                                    "'ada-desktop'. It is a public label, NOT a password and NOT your legal name. "
                                    "You can leave it blank to use the default.")) or node_id).strip() or node_id
    if uat and name == "KM-1176":
        raise OnboardError("a UAT onboard must not use the sovereign principal KM-1176")
    turns.append({"turn": 2, "kind": "name", "disposition": name})
    _wrote(2, f"node_name:{name}")

    # ---- TURN 3 · Which acts require your hand? (default-deny minimal set; the human edits) ----
    t3 = OnboardTurn(3, "Which acts require your hand?", "edit_set",
                     "These acts will ALWAYS require your explicit approval (a safe default-deny minimal set). "
                     "Keep them as-is (recommended), or replace them with your own list.", payload=list(DEFAULT_GATED_ACTS))
    edited = prompter(t3)
    gated_acts: Tuple[str, ...] = tuple(edited) if edited else DEFAULT_GATED_ACTS
    turns.append({"turn": 3, "kind": "edit_set", "disposition": list(gated_acts)})
    _wrote(3, f"gated_acts:{','.join(gated_acts)}")

    # ---- TURN 4 · First gated act → the human gate (compose the sealed HumanApprovalGate, S5 V16) ----
    gate = gate or HumanApprovalGate()
    first_act = gated_acts[0] if gated_acts else DEFAULT_GATED_ACTS[0]
    req_id = gate.request_approval(ApprovalRequest(
        action_class=first_act, role_id=name, principal_id=name, risk_level="high",
        rationale="onboarding: first gated act needs the human's hand", required_approvers=[name]))
    t4 = OnboardTurn(4, "First gated act", "gate",
                     f"Your first gated act '{first_act}' needs your hand. Approve or deny.",
                     payload={"req_id": req_id, "act": first_act})
    decision = str(prompter(t4)).strip().lower()
    status = "approved" if decision.startswith("a") else "denied"
    first_gate = gate.record_disposition(req_id, status=status, approver=name,
                                         reason="onboarding first-gated-act disposition")
    turns.append({"turn": 4, "kind": "gate", "disposition": status})
    _wrote(4, f"gate:{first_act}:{status}")

    # ---- TURN 5 · Receipt + how to verify WITHOUT the AI ----
    principal = name
    if uat and str(principal).strip() == "KM-1176":
        raise OnboardError("a UAT onboard must not use the sovereign principal KM-1176")
    # The fifth turn is recorded ON the signed record (AA P1-F1): append its marker and fold the WHOLE 5-turn
    # sequence into the signed body, so the node's signature attests turns 1–5, not just 1–4.
    turns.append({"turn": 5, "kind": "receipt", "disposition": "receipt_emitted"})
    body = _receipt_body(node_id, name, nodekey.fingerprint, gated_acts, first_act, first_gate,
                         uat, principal, at)
    body["turns"] = turns                                                            # the 5-turn sequence is INSIDE the signed payload
    payload = json.dumps(body, sort_keys=True).encode("utf-8")
    signature = sign_node_act(keystore_dir, node_id, payload)                        # self-attested with the node's own key
    verify_instructions = (
        "Verify this receipt yourself — no AI, no cloud, no account:\n"
        "  from sovereign_agent.keystore.node_keystore import load_node_key, verify_node_act\n"
        "  import json\n"
        f"  body = {json.dumps(body, sort_keys=True)}\n"
        "  payload = json.dumps(body, sort_keys=True).encode('utf-8')\n"
        f"  k = load_node_key({json.dumps(keystore_dir)}, {json.dumps(node_id)})\n"
        f"  assert k.fingerprint == {json.dumps(nodekey.fingerprint)}\n"
        f"  assert verify_node_act(k.public_hex, payload, {json.dumps(signature)}) is True\n"
        "Your identity is your key's fingerprint. If the two asserts pass, the receipt is genuinely yours.")
    row = dict(body, signature=signature, signed_payload=payload.hex(), writes=writes,
               receipt_kind="onboard")                                              # body already carries the 5 turns
    receipt_path = _append_local_receipt(keystore_dir, row)                          # local log, NEVER the seal ledger
    _wrote(5, "onboard_receipt")
    return OnboardReceipt(node_id=node_id, node_name=name, fingerprint=nodekey.fingerprint,
                          gated_acts=gated_acts, first_act=first_act, first_gate=first_gate,
                          turns=tuple(turns), writes=tuple(writes), uat=bool(uat), principal=principal,
                          created_at=str(at), signed_payload=payload.hex(), signature=signature,
                          verify_instructions=verify_instructions, receipt_path=receipt_path)


def verify_onboard_receipt(receipt: OnboardReceipt, keystore_dir: Optional[str]) -> bool:
    """Offline verification of an onboard receipt — the same check the human runs, callable by AA/Dragon UAT.
    Loads the node's PUBLIC key from the keystore and verifies the receipt signature over its exact payload."""
    k = load_node_key(keystore_dir, receipt.node_id)
    if k.fingerprint != receipt.fingerprint:
        return False
    return verify_node_act(k.public_hex, bytes.fromhex(receipt.signed_payload), receipt.signature)


# --- Interactive CLI (a thin prompter over stdin; the flow above is the authority) -------------------------

def _cli_prompter(turn: "OnboardTurn"):
    """Present a turn on the terminal and read the human's disposition from stdin. Purely local I/O — no
    network, no telemetry. The flow calls this once per turn, in order."""
    print(f"\n── Turn {turn.n} · {turn.title} ──")
    print(turn.text)
    if turn.kind == "accept":
        return input("> ").strip().lower() in ("y", "yes", "accept", "i accept")
    if turn.kind == "name":
        return input("Node name (e.g. Dragon) — or press Enter for the default > ").strip()
    if turn.kind == "edit_set":
        print("  default (always gated): " + ", ".join(turn.payload))
        raw = input("Press Enter to KEEP these, or type a comma-separated list to REPLACE them > ").strip()
        chosen = [a.strip() for a in raw.split(",") if a.strip()] if raw else list(turn.payload)
        print("  → kept: " + ", ".join(chosen))
        return chosen
    if turn.kind == "gate":
        return input("Type 'approve' or 'deny' > ").strip().lower()
    return None


def cli_onboard(keystore_dir: Optional[str] = None, *, node_id: str = "node", uat: bool = False):
    """Console entry: run the 5-turn onboard interactively on the operator's own iron, offline. Returns the
    receipt (or the declined outcome). No key is written until the human accepts at turn 1."""
    from datetime import datetime as _dt, timezone as _tz
    ksd = keystore_dir if keystore_dir is not None else os.environ.get("NODE_KEYSTORE_DIR")
    print("\n∞Δ∞ Sovereign Node — onboard (offline · your key, your hand)")
    result = run_onboard(ksd, prompter=_cli_prompter, at=_dt.now(_tz.utc).isoformat(),
                         node_id=node_id, uat=uat)
    if isinstance(result, OnboardOutcome):
        print(f"\n{result.message}")
        return result
    print("\n── Turn 5 · Receipt ──")
    print(f"  node: {result.node_name}  ·  fingerprint: {result.fingerprint}")
    print(f"  acts reserved to your hand: {', '.join(result.gated_acts)}")
    print(f"  first gate '{result.first_act}': {result.first_gate.get('status')}")
    print(f"  receipt written (local, NOT the seal ledger): {result.receipt_path}")
    print("\n" + result.verify_instructions)
    return result
