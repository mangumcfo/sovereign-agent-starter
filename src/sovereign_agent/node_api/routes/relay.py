"""
Section — Agent Channel relay (A1, GB meta-review #1: "KM is the message bus").

Removes KM as the copy-paste bus between his own agents WITHOUT removing his gate. An agent posts a
prompt for another agent → it lands as an Atrium card. KM clicks **Relay** (the gate) → the prompt is
appended to the receipted Tiger↔GB THREAD directly. The other agent's reply surfaces back on the same
card. KM gates every relay (fence intact) but performs none (no ferrying).

    POST /relay                  → an agent posts a prompt for another agent (the card)   (any principal)
    GET  /relays                 → projection: pending → relayed → answered (reply folded) (any principal)
    POST /relay/<id>/relay       → KM's Relay click: append to THREAD + mark relayed        (OWNER only)
    POST /relay/<id>/dismiss     → archive a relay card                                     (any principal)

Clones: proposals.py node-local JSON store + require_owner gate + thread_channel (the THREAD writer).
Storage is a node-local JSON file beside the ledger — the RECEIPT of record is the THREAD itself
(hash-chained); this store is just the card's mutable surface state.

∞Δ∞ Close the channel and the chair has nothing in its hands but judgment. ∞Δ∞
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from flask import Blueprint, jsonify, request

from .. import thread_channel
from .._jsonstore import read_json, sidecar_store, update_json
from ..auth import current_principal, require_owner, require_principal

bp = Blueprint("relay", __name__, url_prefix="/api/v1")

# Known agent ids on the channel (smart default target = the other writer). Loose — any string is allowed;
# this just powers the default + display. KM is never a relay target (he is the gate, not a bus endpoint).
_AGENTS = ("tiger", "gb")


def _store_path() -> Path:
    return sidecar_store("relays.json", "RELAY_STORE")   # one resolver (audit 2026-06-13c #9)


def _read() -> list:
    return read_json(_store_path())


def _update(mutate):
    """Fenced read-modify-write on relays.json (audit 2026-06-13 W5 #3): lock spans read→mutate→write so
    a /relays poll or a concurrent create can't clobber a freshly-created/relayed card. ensure_ascii=False
    preserves the prompt's unicode."""
    return update_json(_store_path(), mutate, ensure_ascii=False)


@bp.post("/relay")
@require_principal
def relay_create():
    """An agent posts a prompt for another agent — it becomes a Relay card in KM's cockpit."""
    body = request.get_json(silent=True) or {}
    prompt = (body.get("prompt") or body.get("msg") or "").strip()
    if not prompt:
        return jsonify({"error": "missing_prompt",
                        "what": "A relay needs the prompt text to hand the other agent.",
                        "next_step": "POST /api/v1/relay with {\"to\":\"tiger\",\"prompt\":\"...\"}."}), 400
    frm = (body.get("from") or current_principal()).strip().lower()
    to = (body.get("to") or next((a for a in _AGENTS if a != frm), "tiger")).strip().lower()
    if to == frm:
        return jsonify({"error": "same_agent", "what": "from and to are the same agent."}), 400
    item = {
        "id": "relay_" + str(int(time.time() * 1000)),
        "from": frm, "to": to,
        "prompt": prompt,
        "ref": (body.get("ref") or "").strip() or f"relay-{int(time.time())}",
        "rationale": (body.get("rationale") or "").strip(),
        "status": "pending",                 # pending → relayed → answered (| dismissed)
        "thread_n": None, "thread_receipt": None,
        "created_by": current_principal(),   # who actually authenticated (audit; never the body)
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _update(lambda items: (items + [item], None))   # fenced append (audit 2026-06-13 W5 #3)
    return jsonify(item), 201


def _fold_reply(item: dict) -> dict:
    """For a relayed card, surface the other agent's THREAD reply (read-only) if it has landed yet."""
    if item.get("status") != "relayed":
        return item
    reply = thread_channel.find_reply(item["to"], item["from"], item.get("thread_n") or 0)
    if reply:
        item = {**item, "status": "answered",
                "reply": {"from": reply.get("from"), "ts": reply.get("ts"),
                          "ref": reply.get("ref"), "msg": reply.get("msg"),
                          "receipt": str(reply.get("hash", ""))[:16], "n": reply.get("n")}}
    return item


@bp.get("/relays")
@require_principal
def relays_list():
    """The Agent Channel: every relay card + its live state. Answered cards fold the reply off the THREAD.
    Persists a status flip to 'answered' so the reply is captured once and the card stops re-scanning."""
    out, flips = [], {}
    for it in _read():
        if it.get("status") == "dismissed":
            continue
        folded = _fold_reply(it)
        if folded is not it and folded.get("status") != it.get("status"):
            flips[it["id"]] = folded     # an answered-state flip to persist
        out.append(folded)
    if flips:
        # Persist the sticky 'answered' flips through the FENCED writer, re-reading inside the lock so a
        # concurrent create isn't clobbered (audit 2026-06-13 W5 #3 — a GET must not do an unfenced write).
        def _apply(items):
            for i, x in enumerate(items):
                if x.get("id") in flips:
                    items[i] = flips[x["id"]]
            return items, None
        _update(_apply)
    out.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    counts = {s: sum(1 for x in out if x.get("status") == s) for s in ("pending", "relayed", "answered")}
    return jsonify({"meta": {"counts": counts, "doctrine": "KM gates every relay; performs none"},
                    "relays": out})


@bp.post("/relay/<relay_id>/relay")
@require_principal
@require_owner
def relay_send(relay_id: str):
    """KM's Relay click (the gate). Appends the prompt to the receipted THREAD — KM authorizes, the node
    performs the ferry. Owner-only: only KM relays between his agents (fence intact)."""
    # Atomic check-and-relay under the lock (audit 2026-06-13 W5 #3): the pending→relayed flip and the
    # one-time THREAD append happen together so a double-click can't double-post. thread_channel.append
    # is itself flock-fenced.
    box = {}

    def _send(items):
        item = next((x for x in items if x.get("id") == relay_id), None)
        if not item:
            box["err"] = (404, {"error": "not_found", "what": f"No relay {relay_id}."})
            return items, None
        if item.get("status") != "pending":
            box["err"] = (409, {"error": "already_relayed",
                                "what": f"Relay {relay_id} is '{item.get('status')}'.",
                                "next_step": "It already left the pending lane — watch for the reply."})
            return items, None
        entry = thread_channel.append(item["from"], item["to"], item.get("ref") or relay_id, item["prompt"])
        item["status"] = "relayed"
        item["thread_n"] = entry.get("n")
        item["thread_receipt"] = str(entry.get("hash", ""))[:16]
        item["relayed_by"] = current_principal()
        item["relayed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        box["item"] = item
        return items, None

    _update(_send)
    if "err" in box:
        code, body = box["err"]
        return jsonify(body), code
    item = box["item"]
    return jsonify({"status": "relayed", "id": relay_id, "to": item["to"],
                    "thread_n": item["thread_n"], "receipt": item["thread_receipt"],
                    "next_step": f"Posted to the THREAD for {item['to']}; the reply surfaces back on this card."})


@bp.post("/relay/<relay_id>/dismiss")
@require_principal
def relay_dismiss(relay_id: str):
    """Archive a relay card (handled out-of-band, or no longer needed)."""
    def _dismiss(items):
        hit = False
        for x in items:
            if x.get("id") == relay_id:
                x["status"] = "dismissed"; hit = True
        return items, hit
    if not _update(_dismiss):   # fenced RMW (audit 2026-06-13 W5 #3)
        return jsonify({"error": "not_found", "what": f"No relay {relay_id}."}), 404
    return jsonify({"status": "dismissed", "id": relay_id})
