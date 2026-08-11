# -*- coding: utf-8 -*-
"""Proof-first tests for peerhood.genesis (S14 Vol 1, the OPENER:
Genesis of a Sovereign Peer).

Kill-targets pinned:
- composes sealed floors + D1 ONLY (D1 keystore · S7 Vol 1 present_evidence · S6 Vol 5 declare_trust_anchor ·
  S5 Vol 5 Object Model · S5 Vol 16 human gate · S12 Vol 1 open_key_epoch/family_quorum_recovery); invents no
  mechanism; rolls no crypto (composes D1);
- establish_self_held_identity mints/holds the peer's OWN key on its OWN iron (D1) and presents it as the node's
  own evidence (S7) — no central attestation;
- declare_birth_boundary is a default-deny boundary SIGNED with the peer's key (no key → fail-loud); no second
  admission authority;
- issue_first_receipt is HUMAN-GATED (no approver → refused) and signed with the key; verify_peer_existence
  proves existence from a receipt the peer holds (public-only), no registry;
- genesis_green_light is the weakest-party test: ON only while the self-held key is under sole control and no
  external permanent claim exists; external claim → OFF; absent key → ABSENT;
- recovery composes sealed S12 (open_key_epoch/family_quorum_recovery) over the peer's OWN fingerprint — no
  custodian, never inside genesis;
- KILL-TARGET: an issuer/registrar/registry/custodian/second-authority/seal-key field is refused (GENESIS_
  BREACH_FIELDS).
"""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.keystore import has_node_key
from sovereign_agent.peerhood import (
    establish_self_held_identity, PeerIdentity, declare_birth_boundary,
    issue_first_receipt, verify_peer_existence, genesis_green_light, GreenLight,
    genesis_recovery_epoch, GENESIS_BREACH_FIELDS, PeerhoodError,
)

PEER, AT = "peer-genesis", "2026-08-11T15:00:00Z"


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path / "node"))


def test_establish_self_held_identity_mints_own_key_and_own_evidence(tmp_path):
    ks = str(tmp_path / "ks")
    ident = establish_self_held_identity(ks, PEER, at=AT, registry=_reg(tmp_path))
    assert isinstance(ident, PeerIdentity) and ident.peer_id == PEER
    assert len(ident.public_hex) == 128 and len(ident.fingerprint) == 16 and ident.evidence_hash
    assert has_node_key(ks, PEER) is True                                  # the key is held on the peer's own iron
    # idempotent: re-establishing loads the SAME self-held key (no re-mint, no orphaning)
    again = establish_self_held_identity(ks, PEER, at=AT, registry=_reg(tmp_path))
    assert again.public_hex == ident.public_hex


def test_declare_birth_boundary_is_default_deny_signed_by_the_peer(tmp_path):
    ks = str(tmp_path / "ks")
    reg = _reg(tmp_path)
    ident = establish_self_held_identity(ks, PEER, at=AT, registry=reg)
    b = declare_birth_boundary(ks, PEER, at=AT, registry=reg)
    assert b["default_deny"] is True and b["signed_by"] == PEER and b["signature"]
    # a boundary cannot be declared without the peer's own key (fail-loud)
    with pytest.raises(PeerhoodError):
        declare_birth_boundary(str(tmp_path / "empty-ks"), "no-key-peer", at=AT, registry=reg)


def test_first_receipt_is_human_gated_and_proves_existence(tmp_path):
    ks = str(tmp_path / "ks")
    reg = _reg(tmp_path)
    ident = establish_self_held_identity(ks, PEER, at=AT, registry=reg)
    with pytest.raises(PeerhoodError):                                     # genesis is human-gated — no approver refused
        issue_first_receipt(ks, PEER, "first-act", at=AT, registry=reg, approver="", approval_ref="b:1")
    rcpt = issue_first_receipt(ks, PEER, "first-act", at=AT, registry=reg, approver="km-1176", approval_ref="b:1")
    assert rcpt["peer_id"] == PEER and rcpt["signature"]
    assert verify_peer_existence(rcpt, ident) is True                      # existence proved from the peer's own receipt
    # a different peer's identity does not verify this peer's existence receipt
    other = establish_self_held_identity(ks, "peer-other", at=AT, registry=reg)
    assert verify_peer_existence(rcpt, other) is False


def test_genesis_green_light_is_the_weakest_party_test(tmp_path):
    ks = str(tmp_path / "ks")
    assert genesis_green_light(ks, PEER).on is False                       # absent key — the peer does not yet exist
    establish_self_held_identity(ks, PEER, at=AT, registry=_reg(tmp_path))
    gl = genesis_green_light(ks, PEER)
    assert isinstance(gl, GreenLight) and gl.on is True                    # sole control, no external claim — sovereign
    assert "sole control" in gl.reason
    off = genesis_green_light(ks, PEER, external_claim={"registrar": "acme-id"})
    assert off.on is False and "external permanent claim" in off.reason    # any external claim turns the light off


def test_recovery_composes_sealed_s12_without_a_custodian(tmp_path):
    from sovereign_agent.estate.generational_transfer import family_quorum_recovery
    ks = str(tmp_path / "ks")
    reg = _reg(tmp_path)
    ident = establish_self_held_identity(ks, PEER, at=AT, registry=reg)
    kin = establish_self_held_identity(ks, "peer-kin", at=AT, registry=reg)
    epoch = genesis_recovery_epoch(ident, [kin.fingerprint], epoch=1)       # composes sealed S12 open_key_epoch
    assert ident.fingerprint in epoch.keyholders and kin.fingerprint in epoch.keyholders
    assert family_quorum_recovery(epoch, [ident.fingerprint, kin.fingerprint], quorum=2) is True  # family's own keys


def test_the_fence_refuses_issuer_registry_custodian_and_seal_key(tmp_path):
    ks = str(tmp_path / "ks")
    reg = _reg(tmp_path)
    for bad in ("issuer", "registrar", "registry", "custodian", "escrow", "admission_authority",
                "external_claim", "seal_key"):
        with pytest.raises(PeerhoodError):
            establish_self_held_identity(ks, f"p-{bad}", at=AT, registry=reg, extra={bad: "acme"})
    assert {"issuer", "registry", "custodian", "admission_authority", "seal_key"} <= GENESIS_BREACH_FIELDS


def test_composes_sealed_floors_and_d1_only():
    import pathlib
    import sovereign_agent.peerhood.genesis as m
    src = pathlib.Path(m.__file__).read_text()
    for sealed in ("keystore", "zero_trust.node_arch", "trust.boundaries", "estate.generational_transfer"):
        assert sealed in src                                               # composes D1 + S7 + S6 + S12
