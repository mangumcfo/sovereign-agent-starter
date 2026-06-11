"""
B51 — the human-memory attention stream (co-extrusion of *Sovereign Inference & Memory* Ch 4).

Brought-To-Your-Attention: a constitutionally-authorized curator surfaces a small, high-signal subset of
the federation's events to the operator, with Merkle integrity proving the curator operated on the WHOLE
considered set (no silent drop), and the structural commitment that the operator's voice *routes attention
but never rules on constitutional authority*.

Book ↔ code anchor (Tech/Arch 17.6):
  Ch 4 "Commitment 1 — Compression (~1% / ~100×)"     → curate() + compression_ratio
  Ch 4 "P5 Merkle Integrity on the considered set"     → considered_root() (Merkle over ALL events)
  Ch 4 "Commitment 3 — Reversibility (deny+suppress)"  → deny()
  Ch 4 '"Voice Routes, Never Rules"'                   → voice_route() returns attention only; rules() refuses
"""
from __future__ import annotations

import hashlib
from typing import Callable

from ..inference import primitives  # sealed P5 Merkle when present, stdlib fallback otherwise (TA-1)


def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def merkle_root(leaves: list[str]) -> str:
    """P5 Merkle root over the leaf hashes (via the sealed MerkleTree when present) — proves the curator
    operated on this exact event set (Ch 4: leaves = considered-event hashes; root = no-silent-drop)."""
    return primitives.merkle_root(leaves)


class VoiceRuledError(PermissionError):
    """Raised if voice input is used to RULE on constitutional authorization — voice routes attention, the
    breath-gate rules (Ch 4 'Voice Routes, Never Rules'). INTEGRITY: the refusal is structural."""


class B51Stream:
    """The curated attention stream. The curator surfaces a subset; the Merkle root over the FULL considered
    set travels with the surfacing so the operator (or next steward) can verify nothing was silently dropped."""

    def __init__(self, *, curator_role: str):
        self.curator_role = curator_role     # constitutionally-authorized curator (SOURCE)
        self._denied_keys: set[str] = set()  # deny-and-suppress feedback (Ch 4 reversibility)

    def considered_root(self, events: list[dict]) -> str:
        """Merkle root over every considered event — the structural defense against curator-side drop."""
        return merkle_root([_h(str(e.get("id"))) + ":" + _h(str(e.get("content", ""))) for e in events])

    def curate(self, events: list[dict], *, surface: Callable[[dict], bool]) -> dict:
        """Surface the high-signal subset (per the curator's `surface` predicate), excluding anything the
        operator previously denied. Returns the surfaced entries + the considered-set Merkle root + the
        compression ratio. Compression is the most visible commitment (Ch 4)."""
        surfaced = [e for e in events
                    if surface(e) and self._key(e) not in self._denied_keys]
        root = self.considered_root(events)
        ratio = (len(events) / len(surfaced)) if surfaced else float(len(events))
        return {
            "surfaced": surfaced,
            "considered": len(events),
            "surfaced_count": len(surfaced),
            "compression_ratio": round(ratio, 2),
            "considered_merkle_root": root,
            "curator_role": self.curator_role,
            "provenance": "curator surfaced this subset; merkle root proves the full considered set",
        }

    def deny(self, entry: dict) -> None:
        """Operator denies an entry — it is suppressed in future curations (reversibility). The denial does
        NOT delete it from the audit chain (Ch 6 coherence: B51 is a projection, not the memory)."""
        self._denied_keys.add(self._key(entry))

    @staticmethod
    def voice_route(entry: dict) -> dict:
        """Voice input ROUTES attention to an entry — it directs focus, it does NOT approve anything."""
        return {"action": "attention_routed", "entry_id": entry.get("id"), "constitutional_effect": None}

    @staticmethod
    def rules(*_args, **_kwargs):
        """Voice can never RULE on constitutional authority — always refuses (Ch 4 structural commitment).
        The constitutional act requires explicit breath at the gate, not voice."""
        raise VoiceRuledError("voice routes attention; it never rules on constitutional authorization — "
                              "the breath-gate is the only ruling surface.")

    @staticmethod
    def _key(entry: dict) -> str:
        """Stable per-entry key for deny-and-suppress: the entry id if present (unique), else a content hash.
        (A richer 'suppress similar by kind' policy is a forward feature; per-entry is the testable core.)"""
        if entry.get("id") is not None:
            return "id:" + str(entry["id"])
        return "c:" + _h(str(entry.get("content", "")))
