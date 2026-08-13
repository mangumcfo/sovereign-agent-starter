#!/usr/bin/env python3
"""compute_share.py — thin USN compute-share wrapper (AA_COMPUTE_SHARE_WRAPPER_BAR).

USN-ONLY LAW: this composes ONLY the sealed tip verbs — it adds no backend, no scheduler, no broker,
no side channel. A refused job returns a refusal; it is NEVER routed anywhere else.

Composed sealed verbs (kernel unchanged):
  · compute.distributed.offer_capacity  — governed capacity offer (version_hash, units, mandate)
  · compute.distributed.admit_job        — deny-by-default admission, four ordered refusals
  · objects.scope.SharingRule            — exact-scope declared crossing (no expiry field — none added)
  · peerhood.delegation.delegate_governed / verify_delegation — TIME-BOUND, human-gated, revocable grant
  · keystore.node_keystore.verify_node_act — PUBLIC-ONLY signature check (requester = verified public_hex)
  · objects.registry.ObjectRegistry.append — P1-signed governed receipts, offline-verifiable

The five GAPs this wrapper exists to close (nothing more):
  admission/refuse/complete receipting · cumulative metering (receipted re-offer) · time-bound rule loading
  · signature-to-mandate binding · the execution bridge (to a LOOPBACK model API only).

Honest label everywhere: "governed, receipted, integrity-verified — observable in transit."
No channel-secrecy claim appears on ANY surface — integrity-only, per W10 (no cipher exists to claim).
"""
from __future__ import annotations

import json
import re
import urllib.request
from decimal import Decimal
from typing import Any, Callable, Mapping, Optional, Sequence

from sovereign_agent.compute.distributed import offer_capacity, admit_job, ComputeError
from sovereign_agent.objects.scope import SharingRule
from sovereign_agent.keystore.node_keystore import verify_node_act, sign_node_act, load_node_key
from sovereign_agent.peerhood.delegation import verify_delegation
from sovereign_agent.peerhood.genesis import PeerIdentity

LABEL = "governed, receipted, integrity-verified — observable in transit"

# W8 — the inference allowlist. A job envelope may carry ONLY these keys; the payload that reaches the
# model is exactly {model, prompt, max_tokens}. Anything else is an escape attempt, refused by name.
_ALLOWED_JOB_KEYS = {"job_id", "model", "prompt", "units", "requester_mandate", "sig", "max_tokens"}
_MODEL_KEYS = {"model", "prompt", "max_tokens"}
# escape shapes we refuse in any string value (shell, paths, keystore, container, Port bypass)
_ESCAPE = re.compile(
    r"(;|\|\||&&|`|\$\(|\bsh\b|/bin/|\bbash\b|\bimport os\b|\.\./|/etc/|/root/|\.nodekey|"
    r"keystore|docker|--privileged|container:|file://|port[_-]?bypass|crossing:)",
    re.IGNORECASE,
)


class ShareRefusal(PermissionError):
    """The wrapper's terminal refusal on the product path — never a fallback, never a reroute."""


def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def _canonical(env: Mapping[str, Any]) -> bytes:
    """The exact bytes the requester signs — the envelope minus its own signature, canonical JSON."""
    body = {k: env[k] for k in sorted(env) if k != "sig"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


# ── W1 · the node's own governed offer ────────────────────────────────────────
def open_offer(reg, node_id: str, units, *, at: str, source_ref: str = "capacity-offer") -> dict:
    """Register THIS node's own governed capacity offer (composes offer_capacity). Authored under the node's
    own mandate; carries version_hash + units. No scheduler assigns it — the node states what it will give."""
    return offer_capacity(reg, node_id, units, mandate=node_id, author=node_id,
                          source_ref=source_ref, at=at)


def latest_offer(reg, node_id: str) -> Optional[dict]:
    return reg.current().get(f"capacity:{node_id}")


# ── W5 · metering re-derivable from receipts alone ────────────────────────────
def receipts(reg, node_id: str) -> list[dict]:
    """All share receipts for this node, in order — the audit surface. Remaining capacity is re-derivable
    from these plus the initial offer; the wrapper keeps NO in-memory counter of record."""
    return [e for e in reg.entries() if e["object_id"].startswith(f"share-receipt:{node_id}:")]


def remaining_units(reg, node_id: str) -> Decimal:
    """Remaining = the LATEST re-offered capacity object's units. That object is itself governed + receipted,
    and equals initial_units − Σ(completed job units) — re-derivable, never a silent counter."""
    off = latest_offer(reg, node_id)
    return _dec((off.get("payload") or {}).get("units", 0)) if off else Decimal(0)


def _receipt_sig_bytes(payload: Mapping[str, Any]) -> bytes:
    """The exact bytes the node signs over a receipt — the payload minus its own signature, canonical."""
    body = {k: payload[k] for k in sorted(payload) if k != "node_sig"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _append_receipt(reg, node_id: str, job_id: str, *, model: str, units, outcome: str,
                    completer_fp: str, at: str, reason: str = "") -> dict:
    """W6 — a governed, offline-verifiable receipt: job id · model · units · outcome · completer fingerprint.
    The node signs the receipt payload with its OWN key; the signature is stored IN the object, so the receipt
    is both re-derivable from the registry AND verifiable offline against the node's public_hex."""
    payload = {"job_id": job_id, "model": str(model), "units": str(units), "outcome": outcome,
               "completer_fingerprint": completer_fp, "reason": reason, "label": LABEL}
    payload["node_sig"] = sign_node_act(_ks_of(), node_id, _receipt_sig_bytes(payload))
    return reg.append(f"share-receipt:{node_id}:{job_id}", payload,
                      author=node_id, source_ref=f"share:{job_id}", at=at, mandate=node_id, kind="ratify")


def verify_receipt(receipt: Mapping[str, Any], node_public_hex: str) -> bool:
    """Offline verify a receipt against the node's OWN public_hex (public-only): the node_sig stored in the
    payload must check out over the rest of the payload. No secret needed; the wrapper's memory is not trusted."""
    payload = dict(receipt.get("payload") or {})
    sig = str(payload.get("node_sig", ""))
    if not sig:
        return False
    return verify_node_act(node_public_hex, _receipt_sig_bytes(payload), sig)


# ── grant: time-bound rule loading (W4) — a live delegation, else deny-by-default (W2) ──
def _grant_live(delegation: Optional[Mapping[str, Any]], node_identity: PeerIdentity,
                revocations: Sequence[Mapping[str, Any]], *, now: str, requester_mandate: str,
                offer_id: str) -> bool:
    """A SharingRule is loaded ONLY while a delegation is: (a) signature-valid & unrevoked (verify_delegation),
    (b) not past its expires_at (the wrapper enforces the clock — verify_delegation checks sig, not time),
    (c) actually for THIS requester and THIS offer capability. Otherwise: no rule → admit_job deny-by-default."""
    if not delegation:
        return False
    if not verify_delegation(delegation, node_identity, revocations=revocations):
        return False
    obj = (delegation.get("delegation") or {}).get("payload") or {}
    exp = str(obj.get("expires_at", "")).strip()
    if not exp or now >= exp:                                   # expired (or unbounded) → dead by default
        return False
    if str(obj.get("delegate_to", "")) != requester_mandate:    # not this requester
        return False
    if str(obj.get("capability", "")) != f"compute:{offer_id}": # not this offer's capability
        return False
    return True


def _loopback_model_call(model_url: str, body: Mapping[str, Any]) -> str:
    """W7 — the execution bridge speaks ONLY to a loopback model API. A non-loopback URL is refused
    (no 0.0.0.0, no external host, no cloud). No shell is ever invoked — pure HTTP to 127.0.0.1."""
    host = re.sub(r"^https?://", "", model_url).split("/")[0].split(":")[0]
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ShareRefusal(f"model API must be loopback-only (got host {host!r}) — the GPU never faces the open network")
    req = urllib.request.Request(model_url, data=json.dumps(dict(body)).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:          # noqa: S310 (loopback-only, enforced above)
        return r.read().decode("utf-8")


# ── the whole admission path — W1..W9 in order, deny-by-default, refusal is terminal ──
def submit_job(reg, node_id: str, envelope: Mapping[str, Any], *, recognized_public_hex: str,
               node_public_hex: str, delegation: Optional[Mapping[str, Any]], now: str,
               model_url: str = "http://127.0.0.1:11434/api/generate",
               model_caller: Callable[[str, Mapping[str, Any]], str] = _loopback_model_call,
               revocations: Sequence[Mapping[str, Any]] = ()) -> dict:
    """Run one job through the governed path. Returns the complete receipt on success; raises ShareRefusal /
    ComputeError (the terminal answer) otherwise. NO non-USN fallback exists — a refusal is returned as-is."""
    # --- W8: allowlist the envelope BEFORE anything touches identity or the model ---
    unknown = set(envelope) - _ALLOWED_JOB_KEYS
    if unknown:
        raise ShareRefusal(f"job refused: keys {sorted(unknown)} are outside the inference allowlist "
                           f"{sorted(_MODEL_KEYS)} — a job may not carry shell, path, keystore, or container directives")
    for k, v in envelope.items():
        if isinstance(v, str) and _ESCAPE.search(v):
            raise ShareRefusal(f"job refused: field {k!r} contains an escape shape (shell/path/keystore/container/"
                               f"Port bypass) — the job stays inside the allowlisted inference API, it cannot reach the machine")

    job_id = str(envelope.get("job_id", "")).strip()
    model = str(envelope.get("model", "")).strip()
    req_mandate = str(envelope.get("requester_mandate", "")).strip()
    if not (job_id and model and req_mandate):
        raise ShareRefusal("job refused: job_id, model, and requester_mandate are all required")
    units = _dec(envelope.get("units", 0))

    # --- W3: admission is KEY-scoped. Verify the requester's signature over the envelope against the
    #         mandate's RECOGNIZED public_hex (from the peer book) — never an envelope-supplied key,
    #         never a token/secret/IP. A different key, or no signature, refuses. ---
    sig = str(envelope.get("sig", "")).strip()
    if not sig:
        raise ShareRefusal("job refused: admission is key-scoped — a signature over the job by the requester's "
                           "recognized public_hex is required (a token, shared secret, or IP is not identity)")
    if recognized_public_hex == node_public_hex:
        raise ShareRefusal("job refused: a node does not admit itself as a requester (self-as-requester)")
    if not verify_node_act(recognized_public_hex, _canonical(envelope), sig):
        raise ShareRefusal("job refused: the job signature does not verify against this requester's recognized "
                           "public_hex — a payload signed by a different key is not this requester")

    # --- W2/W4: build the SharingRule ONLY if a live time-bound delegation authorizes it; else no rule. ---
    node_identity = PeerIdentity(peer_id=node_id, public_hex=node_public_hex, fingerprint="", evidence_hash="")
    offer = latest_offer(reg, node_id)
    if not (offer and offer.get("version_hash") and offer.get("object_id")):
        raise ShareRefusal("job refused: no governed capacity offer exists to admit against (W1)")
    offer_id = offer["object_id"]
    rules = []
    if _grant_live(delegation, node_identity, revocations, now=now, requester_mandate=req_mandate, offer_id=offer_id):
        # admit_job authorizes the crossing with want="write" (running a job IS a write to the offer);
        # the declared SharingRule must therefore grant "write" — the exact scope, nothing wider.
        rules = [SharingRule(offer_id, req_mandate, "write")]

    completer_fp = load_node_key(_ks_of(), node_id).fingerprint

    # --- W5/W1: admit deny-by-default, fail-closed, IN ORDER (offer real · not over-subscribed · rule · named) ---
    try:
        admitted = admit_job(reg, rules, offer, units, requester_mandate=req_mandate)
    except ComputeError as e:
        _append_receipt(reg, node_id, job_id, model=model, units=units, outcome="refused",
                        completer_fp=completer_fp, at=now, reason=str(e))
        raise ShareRefusal(str(e)) from e

    # --- W7/W8: execution bridge — loopback model only, allowlisted body only ---
    body = {k: envelope[k] for k in _MODEL_KEYS if k in envelope}
    try:
        result = model_caller(model_url, body)
    except ShareRefusal:
        _append_receipt(reg, node_id, job_id, model=model, units=units, outcome="refused",
                        completer_fp=completer_fp, at=now, reason="model bridge refused (non-loopback)")
        raise
    except Exception as e:                                       # a model failure is a FAILURE receipt, still terminal
        _append_receipt(reg, node_id, job_id, model=model, units=units, outcome="failed",
                        completer_fp=completer_fp, at=now, reason=f"model error: {type(e).__name__}")
        raise ShareRefusal(f"job failed at the model bridge ({type(e).__name__}) — no fallback, the failure is returned") from e

    # --- W5: receipted re-offer — decrement capacity as a governed object, remaining re-derivable ---
    rem = remaining_units(reg, node_id) - units
    if rem > 0:
        open_offer(reg, node_id, rem, at=now, source_ref=f"re-offer-after:{job_id}")
    else:
        # capacity exhausted — record it as a receipt, not a non-positive offer (offer_capacity refuses <=0)
        _append_receipt(reg, node_id, f"{job_id}:capacity-exhausted", model=model, units=0,
                        outcome="capacity-exhausted", completer_fp=completer_fp, at=now,
                        reason=f"remaining reached {rem}")

    rc = _append_receipt(reg, node_id, job_id, model=model, units=units, outcome="complete",
                         completer_fp=completer_fp, at=now)
    return {"outcome": "complete", "admitted": admitted, "receipt": rc, "result": result,
            "remaining": str(remaining_units(reg, node_id)), "label": LABEL}


def _ks_of():  # keystore dir comes from the environment (NODE_KEYSTORE_DIR), same contract as the node
    import os
    return os.environ.get("NODE_KEYSTORE_DIR")
