"""
sovereign_agent.evidence — packaged evidence-export core (Universalize Wave §5).

The R22-1 evidence packet + R22-2 actions projection, moved out of `scripts/` into the installed package
so the Node API imports them as proper modules (no `scripts/` on the runtime sys.path — which breaks in a
container / non-editable install). The CLI scripts are thin wrappers over these. G4 law: scripts may
import package code; package code must NEVER import scripts.
"""
from .actions_projection import query_actions, verify_proof
from .export_packet import build_packet, verify_packet

__all__ = ["build_packet", "verify_packet", "query_actions", "verify_proof"]
