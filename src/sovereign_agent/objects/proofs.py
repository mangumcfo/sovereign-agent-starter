"""proofs.py — Merkle membership proofs (S5-05-E4-1, E4-4).

A proof of membership can be issued for any single object against a manifest
root, and verified from the leaf + sibling path alone. The tree convention is
EXACTLY evidence.export_packet's (sha256 pairwise, odd level duplicates the last
leaf) — pinned by a cross-check test, extended here with path extraction, which
the substrate did not have. Full-population replay and proof-only checking must
agree on the same root; the sizing figures in the book are design targets, so the
acceptance test asserts agreement, never timing.
"""
from __future__ import annotations

import hashlib

from ..evidence.export_packet import _merkle_root
from .registry import ObjectRegistry


def _levels(leaf_hashes: list[str]) -> list[list[bytes]]:
    """All tree levels bottom-up, same convention as export_packet._merkle_root."""
    if not leaf_hashes:
        return [[hashlib.sha256(b"").digest()]]
    level = [bytes.fromhex(h) for h in leaf_hashes]
    levels = [list(level)]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
            levels[-1] = list(level)
        level = [hashlib.sha256(level[i] + level[i + 1]).digest()
                 for i in range(0, len(level), 2)]
        levels.append(list(level))
    return levels


def issue_proof(leaf_hashes: list[str], index: int) -> list[tuple[str, str]]:
    """Sibling path for the leaf at `index`: [(sibling_hex, 'L'|'R'), ...] bottom-up.
    'L' means the sibling hashes on the left of the running value."""
    if not (0 <= index < len(leaf_hashes)):
        raise IndexError(f"leaf index {index} outside population of {len(leaf_hashes)}")
    path = []
    for level in _levels(leaf_hashes)[:-1]:
        sib = index ^ 1
        sib = min(sib, len(level) - 1)  # odd-duplicated level: last pairs with itself
        path.append((level[sib].hex(), "L" if sib < index else "R"))
        index //= 2
    return path


def verify_proof(leaf_hash: str, path: list[tuple[str, str]], root: str) -> bool:
    """Recompute the root from one leaf + its sibling path. No store, no registry —
    512-ish bytes of siblings against a 32-byte root (E4-1)."""
    h = bytes.fromhex(leaf_hash)
    for sib_hex, side in path:
        sib = bytes.fromhex(sib_hex)
        h = hashlib.sha256((sib + h) if side == "L" else (h + sib)).digest()
    return h.hex() == root


def replay_root(reg: ObjectRegistry) -> str:
    """Full-population replay: rebuild state from the append-only record and derive
    the root — the slow, total check."""
    return reg.population_root()


def proof_only_check(reg: ObjectRegistry, obj_id: str, stated_root: str) -> bool:
    """Proof-only checking: verify ONE object's membership against a stated root
    without replaying the population (E4-4's fast path)."""
    state = reg.current()
    ids = sorted(state)
    leaves = reg.population_leaves(state)
    return verify_proof(leaves[ids.index(obj_id)],
                        issue_proof(leaves, ids.index(obj_id)), stated_root)


def tree_root(leaf_hashes: list[str]) -> str:
    """The root by this module's levels — must always equal export_packet's
    _merkle_root (the convention cross-check the test pins)."""
    root = _levels(leaf_hashes)[-1][0].hex()
    assert root == _merkle_root(leaf_hashes), "tree convention drifted from export_packet"
    return root
