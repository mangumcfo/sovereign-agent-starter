#!/usr/bin/env python3
"""compute_share_offer.py — stand up ONE node's governed compute-share offer + a time-bound grant to ONE peer.

Composes the wrapper's PRESENT verbs (open_offer + delegate_governed) — no kernel change. This is the operator's
one-command way to publish "I offer N units of these models to <peer's public_hex> for <days> days." It writes
governed objects to the node's registry; the model server + transport are separate (loopback Ollama + p2p).

USN-only · integrity-only · deny-by-default. The grant is human-gated (an --approver is required) and TIME-BOUND
(--renew-days); after it, admission denies by default until you re-issue. Beard's public_hex is an INPUT you paste
(out-of-band, from its ceremony) — this tool never fetches a peer key.

  GPU FENCE (Dragon rents on Vast.ai): pass --min-gpu-free-mib to REFUSE to publish an offer while the GPU is
  busy (a rental in progress). Rental income > local convenience — the offer must yield.

Example (run on Dragon, once AA has GREEN'd the wrapper and you hold Beard's public_hex):
  NODE_KEYSTORE_DIR=~/.sovereign_keystore \\
  scripts/compute_share_offer.py \\
    --node UniversalSovereignNode --units 200 --renew-days 7 --approver KM-1176 --approval-ref km-dragon-1 \\
    --requester-name Beard --requester-public-hex <128hex> \\
    --models qwen3-coder:30b qwen2.5-coder:32b llama3.1:8b \\
    --registry ~/.sovereign_share/registry --min-gpu-free-mib 20000
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("compute_share", ROOT / "scripts" / "compute_share.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.keystore.node_keystore import has_node_key, load_node_key
from sovereign_agent.peerhood.delegation import delegate_governed

_HEX128 = __import__("re").compile(r"\A[0-9a-fA-F]{128}\Z")


def _gpu_free_mib() -> int | None:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            text=True, timeout=10)
        return int(out.strip().splitlines()[0])
    except Exception:
        return None


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Publish a governed compute-share offer + a time-bound grant to one peer.")
    p.add_argument("--node", required=True, help="this node's id (its keystore key name)")
    p.add_argument("--units", type=int, required=True, help="capacity units offered (unit = one request)")
    p.add_argument("--renew-days", type=int, default=7, help="grant lifetime in days (deny-by-default after)")
    p.add_argument("--approver", required=True, help="the HUMAN who approves this grant (human-gated)")
    p.add_argument("--approval-ref", required=True)
    p.add_argument("--requester-name", required=True, help="the peer's mandate/name")
    p.add_argument("--requester-public-hex", required=True, help="the peer's 128-hex public key (out-of-band; never fetched)")
    p.add_argument("--models", nargs="+", required=True, help="EXACT model names this offer will run (the allowlist)")
    p.add_argument("--registry", required=True, help="path to this node's share registry dir")
    p.add_argument("--at", default="", help="ISO timestamp (default: now)")
    p.add_argument("--min-gpu-free-mib", type=int, default=0,
                   help="refuse to publish if GPU free < this (Vast.ai fence; 0 disables the check)")
    p.add_argument("--emit-grant", default="", help="path to write the grant JSON (default: <registry>/../grant_<peer>.json)")
    a = p.parse_args(argv)

    ks = os.environ.get("NODE_KEYSTORE_DIR")
    if not has_node_key(ks, a.node):
        print(f"✗ no durable key for node {a.node!r} in {ks} — provision it first (scripts/stand_up_node.sh)."); return 2
    if not _HEX128.match(a.requester_public_hex.strip()):
        print("✗ --requester-public-hex must be exactly 128 hex chars (the peer's public_hex, obtained out-of-band)."); return 2
    if a.requester_public_hex.strip().lower() == load_node_key(ks, a.node).public_hex.lower():
        print("✗ the requester public_hex equals THIS node's own key — a node does not admit itself as a requester."); return 2

    # GPU fence — Dragon rents on Vast.ai; do not publish a serving offer while the GPU is busy.
    if a.min_gpu_free_mib > 0:
        free = _gpu_free_mib()
        if free is None:
            print("✗ could not read GPU free memory (nvidia-smi) — refusing to publish under an unknown GPU state."); return 3
        if free < a.min_gpu_free_mib:
            print(f"✗ GPU free {free} MiB < required {a.min_gpu_free_mib} MiB — a rental may be in progress. "
                  f"Offer NOT published (rental income > local convenience)."); return 3
        print(f"  GPU free {free} MiB ≥ {a.min_gpu_free_mib} MiB — clear to publish.")

    at = a.at or datetime.datetime.now(datetime.timezone.utc).isoformat()
    expires = (datetime.datetime.fromisoformat(at) + datetime.timedelta(days=a.renew_days)).isoformat()
    reg = ObjectRegistry(a.registry)

    offer = cs.open_offer(reg, a.node, a.units, at=at)
    grant = delegate_governed(ks, a.node, a.requester_name, f"compute:{offer['object_id']}",
                              expires_at=expires, at=at, registry=reg,
                              approver=a.approver, approval_ref=a.approval_ref)
    fp = load_node_key(ks, a.node).fingerprint

    # persist the grant (public material — the delegation object + this node's signature over it) so the
    # declared admit listener can load it without re-minting. No private key is written.
    grant_file = a.emit_grant or os.path.join(os.path.dirname(os.path.abspath(a.registry)),
                                              f"grant_{a.requester_name}.json")
    os.makedirs(os.path.dirname(grant_file), exist_ok=True)
    with open(grant_file, "w", encoding="utf-8") as fh:
        __import__("json").dump({"grant": grant, "requester_public_hex": a.requester_public_hex,
                                 "models": a.models, "node": a.node}, fh, sort_keys=True)
    os.chmod(grant_file, 0o600)
    print("∞Δ∞ COMPUTE-SHARE OFFER PUBLISHED — governed, receipted, integrity-verified — observable in transit")
    print(f"  node        : {a.node}  fp={fp}")
    print(f"  offer id    : {offer['object_id']}  version_hash={offer['version_hash']}")
    print(f"  units       : {offer['payload']['units']}  (1 unit = 1 request)")
    print(f"  models      : {a.models}   (jobs naming any other model are refused)")
    print(f"  grant to    : {a.requester_name}  ({a.requester_public_hex[:16]}…)  approver={a.approver}")
    print(f"  grant window: {at}  →  {expires}   (deny-by-default after; re-issue is a new human act)")
    print(f"  delegation  : {grant['delegation']['object_id']}  time_bound={grant['time_bound']} revocable={grant['revocable']}")
    print("  bind the requester_public_hex into your peer book:  scripts/peer_book.py add --label "
          f"{a.requester_name!r} --public-hex {a.requester_public_hex}")
    print(f"  grant file  : {grant_file}   (load it in the admit listener: scripts/compute_share_serve.py)")
    print("  pass --models to submit_job so the model allowlist is enforced on every job.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
