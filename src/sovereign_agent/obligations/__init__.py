"""Obligation ledger — the node's B32 record of truth (Phase 1 of R-23).

Vendors the proven patterns from the live B32 primitives WITHOUT importing or driving them
(hard boundary: the node never touches Tiger's live seal chain):
  - state/receipt/draft-proposal/approval-gate shape  <- Tiger_1a/cylinders/cylinder_v2.py (CYL-006)
  - dr/cr obligation lifecycle + E0/E1/E2 evidence tiers <- constitution-federation-v2/tools/task_chain.py
  - canonical spec                                       <- breaths/breath_32/v2.1

Series principle: receipts as the transactional record of truth; SOURCE (principal_id on every
entry); INTEGRITY (append-only hash chain, draft->approval gate, no close without evidence).
"""
from .ledger import (
    ObligationLedger, classify_evidence, EvidenceTier, LedgerBoundaryError, AlreadyClosedError,
)

__all__ = ["ObligationLedger", "classify_evidence", "EvidenceTier", "LedgerBoundaryError",
           "AlreadyClosedError"]
