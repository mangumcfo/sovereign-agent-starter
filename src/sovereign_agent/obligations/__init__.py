"""Obligation ledger — the node's B32 record of truth (Phase 1 of R-23).

Vendors the proven patterns from the live B32 primitives WITHOUT importing or driving them
(hard boundary: the node never touches the node's live seal chain):
  - state/receipt/draft-proposal/approval-gate shape  <- the host seal-chain's cylinder shape (CYL-006)
  - dr/cr obligation lifecycle + E0/E1/E2 evidence tiers <- the constitutional task-chain tooling
  - canonical spec                                       <- the B32 ledger specification (v2.1)

Series principle: receipts as the transactional record of truth; SOURCE (principal_id on every
entry); INTEGRITY (append-only hash chain, draft->approval gate, no close without evidence).
"""
from .ledger import (
    ObligationLedger, classify_evidence, EvidenceTier, LedgerBoundaryError, AlreadyClosedError,
)

__all__ = ["ObligationLedger", "classify_evidence", "EvidenceTier", "LedgerBoundaryError",
           "AlreadyClosedError"]
