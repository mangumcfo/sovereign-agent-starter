"""inheritance.py — the successor packet (S5-05-E8-1, E8-4).

A successor packet assembles from the registry, a manifest, and proofs, and
verifies on a machine holding none of the operator's systems: verification below
is a pure function over the packet's own bytes — no registry, no store, no
network. Objects marked unsourced are disclosed in EVERY packet; the disclosure
is part of what the packet hash covers, so stripping it is detectable.
"""
from __future__ import annotations

from ..evidence.export_packet import _canon, _merkle_root, _sha
from .identity import version_leaf
from .registry import ObjectRegistry


def build_packet(reg: ObjectRegistry, manifest: dict) -> dict:
    """Assemble the packet: full object list (current versions), the manifest,
    and the permanent unsourced disclosure. The disclosure key is ALWAYS present
    — an empty list is a statement, absence would be silence (E8-4)."""
    state = reg.current()
    objects = [state[k] for k in sorted(state)]
    packet = {"kind": "successor_packet",
              "manifest": manifest,
              "objects": objects,
              "unsourced_disclosure": sorted(
                  o["object_id"] for o in objects if o.get("payload", {}).get("unsourced")
                  or o.get("unsourced"))}
    packet["packet_hash"] = _sha(_canon(packet))
    return packet


def verify_packet(packet: dict) -> tuple[bool, list[str]]:
    """Offline verification — pure function of the packet (E8-1). Checks:
    packet_hash recomputes · the manifest root recomputes from the included
    object list · count matches · the unsourced disclosure matches the objects'
    own marks. Returns (ok, failures)."""
    fails = []
    body = {k: packet[k] for k in ("kind", "manifest", "objects", "unsourced_disclosure")}
    if _sha(_canon(body)) != packet.get("packet_hash"):
        fails.append("packet_hash does not recompute — the packet was altered")
    objects = packet["objects"]
    root = _merkle_root([version_leaf(v) for v in
                         sorted(objects, key=lambda v: v["object_id"])])
    if root != packet["manifest"]["root"]:
        fails.append("manifest root does not recompute from the included object list")
    if len(objects) != packet["manifest"]["count"]:
        fails.append(f"object count {len(objects)} != manifest count "
                     f"{packet['manifest']['count']}")
    marked = sorted(o["object_id"] for o in objects
                    if o.get("payload", {}).get("unsourced") or o.get("unsourced"))
    if marked != packet.get("unsourced_disclosure"):
        fails.append("unsourced disclosure does not match the objects' own marks")
    return (not fails), fails
