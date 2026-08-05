"""Federation — Federation Node Governance (s5_26): cross-node validation, scoped sharing, and reconciliation
across a federation of sovereign nodes, with NO central hub and NO second authority center. Each node validates a
shared packet independently (a pure, offline function over the packet's own bytes), a crossing is gated by a
peer-declared sharing rule, and two nodes reconcile by comparing independently-computed integrity roots — neither
authoritative over the other. It composes the sealed Sovereign Object Model (scope, successor packets, manifests,
mandate roots); it builds no federation registry and no central validator of its own."""
from .node_gov import (
    share_node_state, validate_received, authorize_crossing, node_root, reconcile_roots,
    FederationError, ScopeRefusal,
)

__all__ = ["share_node_state", "validate_received", "authorize_crossing", "node_root",
           "reconcile_roots", "FederationError", "ScopeRefusal"]
