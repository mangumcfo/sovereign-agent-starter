"""Engine 95+ #6 behavior-preservation (audit 2026-06-16) — the ObligationLedger read methods delegate to
the pure projection functions over EXACTLY self._entries(), order-aware and byte-identical to the former
in-class computation. the peer-mandated check: projection.replay gets exactly self._entries()."""
from sovereign_agent.obligations import projection
from sovereign_agent.obligations.ledger import ObligationLedger


def _chain(root):
    """A chain exercising every projection path: approve+close (E2), plain close (E1), reopen, and a
    joint-attestation with a veto then clear (order-aware)."""
    L = ObligationLedger(root=str(root), principal_id="the owner")
    # non-material approve+close path (AH-1 Option A: a gate-less ledger cannot self-approve a MATERIAL
    # obligation; this test exercises projection DELEGATION over an approved chain, not materiality).
    a = L.open("approved A", material=False)
    L.approve(a["id"], approved_by="the owner")
    L.close(a["id"], evidence="/art/x sha=abcdef0123456789", evidence_tier="E2")
    b = L.open("plain B")
    L.close(b["id"], evidence="/p/q", evidence_tier="E1")
    c = L.open("reopened C")
    L.close(c["id"], evidence="/y/z", evidence_tier="E1")
    L.reopen(c["id"], reason="correction")
    d = L.open("attested D", requires_attestation=["cfo", "compliance"])
    L.attest(d["id"], "cfo")
    L.veto(d["id"], "compliance", "needs review")
    L.clear_veto(d["id"], "compliance")
    L.attest(d["id"], "compliance")
    return L, d["id"]


def test_replay_delegates_to_projection_over_exact_entries(tmp_path):
    """The class replay() == projection.replay(the exact entries), order-aware (reopen returns C to open)."""
    L, _ = _chain(tmp_path / "obl")
    entries = list(L.iter_entries())
    assert L.replay() == projection.replay(entries)
    # order-aware: C is reopened (back to open), D never closed → 2 open, 2 closed (A, B)
    st = L.replay()
    assert len(st["open"]) == 2 and len(st["closed"]) == 2


def test_all_read_methods_delegate_identically(tmp_path):
    """Every delegated read method returns exactly what the projection function does on the same entries."""
    L, did = _chain(tmp_path / "obl")
    entries = list(L.iter_entries())
    assert L.full_log() == projection.full_log(entries)
    assert L._is_closed(did) == projection.is_closed(entries, did)
    assert L._is_approved(did) == projection.is_approved(entries, did)
    assert L.by_owner() == projection.by_owner(L.replay())
    assert L.by_status() == projection.by_status(L.replay())
    req = (L._get(did) or {}).get("requires_attestation") or []
    assert L.attestation_status(did) == projection.attestation_status(entries, did, set(req))
    assert L.verify_chain() is True
    assert projection.recompute_chain(entries, False) is True
    assert L.manifest()["last_hash"] == entries[-1]["hash"]


def test_public_surface_reexported_unchanged():
    """The extraction kept the public surface: these names still import from .ledger (no caller changes)."""
    from sovereign_agent.obligations.ledger import (  # noqa: F401
        ObligationLedger, AlreadyClosedError, EvidenceTier, classify_evidence,
        LedgerBoundaryError, get_ledger_root,
    )
    from sovereign_agent.obligations import ObligationLedger as _O  # noqa: F401  (package re-export)
