"""Continuity — Generational Continuity (s5_27): the governed generational handoff. It assembles a verifiable
successor package (the sealed successor packet + manifest) and governs the handoff fail-closed — the package must
verify AND a named human must approve — so a business passes to the next generation as provable evidence a successor
can re-derive, gated by a human, never a silent transfer. Composes the sealed Sovereign Object Model (packet,
manifest) + the human-gate convention; it builds no successor-packet engine of its own."""
from .handoff import assemble_successor_package, govern_handoff, HandoffError

__all__ = ["assemble_successor_package", "govern_handoff", "HandoffError"]
