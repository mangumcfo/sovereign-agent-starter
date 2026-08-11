# -*- coding: utf-8 -*-
"""Proof-first tests for peerhood.recognition (S14 Vol 2:
Recognition Without a Registry).

Kill-targets pinned:
- composes sealed floors + genesis ONLY (S14 V1 genesis · D1 keystore · S8 V6 reconcile_roots · S6 V1
  send_message · S5 V5 Object Model); invents no mechanism; rolls no crypto;
- directory_free_discovery reconciles two INDEPENDENT roots (S8 V6) — opt-in, local, no central index;
- mutual_recognition is a BILATERAL receipted ceremony (S6 V1 message) signed by BOTH peers' own keys; verify_
  recognition is public-only and true only when BOTH verify; no third party;
- scoped_visibility is human-gated (no approver refused), reversible, minimal;
- recognition_as_receipt is an owned TALLY, not a score (scored reputation homes OUT to S11 V1);
- refuse_recognition is a first-class SIGNED act that leaves NO residual claim (hostage-free);
- KILL-TARGET: a registry / directory / name-service / scored-authority / custodian field is refused
  (RECOGNITION_BREACH_FIELDS).
"""
import pathlib

import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.peerhood.genesis import establish_self_held_identity, PeerhoodError
from sovereign_agent.peerhood.recognition import (
    directory_free_discovery, mutual_recognition, verify_recognition,
    scoped_visibility, recognition_as_receipt, refuse_recognition, RECOGNITION_BREACH_FIELDS,
)

AT = "2026-08-11T16:00:00Z"


def _reg(tmp_path, name="node"):
    return ObjectRegistry(str(tmp_path / name))


def test_directory_free_discovery_reconciles_without_a_directory(tmp_path):
    d = directory_free_discovery("root-abc", "root-abc")
    assert d["discovered"] is True and d["aligned"] is True and d["central_index"] is None
    assert directory_free_discovery("root-abc", "root-xyz")["aligned"] is False   # divergence surfaced, not resolved
    with pytest.raises(PeerhoodError):
        directory_free_discovery("root-abc", "root-abc", extra={"directory": "acme-index"})


def test_mutual_recognition_is_bilateral_and_signed_by_both(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    a = establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    b = establish_self_held_identity(ks, "peer-b", at=AT, registry=reg)
    rec = mutual_recognition(ks, "peer-a", "peer-b", at=AT, registry=reg)
    assert rec["third_party"] is None and rec["sig_a"] and rec["sig_b"]
    assert verify_recognition(rec, a, b) is True                                  # both sides verify, public-only
    c = establish_self_held_identity(ks, "peer-c", at=AT, registry=reg)
    assert verify_recognition(rec, a, c) is False                                 # a non-party does not verify
    with pytest.raises(PeerhoodError):                                            # a peer with no key cannot recognize
        mutual_recognition(str(tmp_path / "empty"), "ghost", "peer-b", at=AT, registry=reg)


def test_scoped_visibility_is_human_gated_and_reversible(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    with pytest.raises(PeerhoodError):                                            # human-gated — no approver refused
        scoped_visibility(ks, "peer-a", "peer-b", ["name"], at=AT, registry=reg, approver="", approval_ref="b:1")
    g = scoped_visibility(ks, "peer-a", "peer-b", ["name"], at=AT, registry=reg, approver="km-1176", approval_ref="b:1")
    assert g["reversible"] is True and g["scope"] == ["name"] and g["signature"]


def test_recognition_as_receipt_is_a_tally_not_a_score(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    establish_self_held_identity(ks, "peer-b", at=AT, registry=reg)
    r1 = mutual_recognition(ks, "peer-a", "peer-b", at=AT, registry=reg)
    tally = recognition_as_receipt("peer-a", [r1])
    assert tally["recognitions"] == 1 and tally["is_score"] is False
    with pytest.raises(PeerhoodError):
        recognition_as_receipt("peer-a", [], extra={"reputation_score": 99})


def test_refusal_is_first_class_and_leaves_no_residual_claim(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    ref = refuse_recognition(ks, "peer-a", "peer-b", at=AT, registry=reg, reason="not now")
    assert ref["residual_claim"] is None and ref["hostage_free"] is True and ref["signature"]
    with pytest.raises(PeerhoodError):
        refuse_recognition(str(tmp_path / "empty"), "ghost", "peer-b", at=AT, registry=reg)


def test_refusal_kills_a_live_recognition(tmp_path):
    # AA bar: a signed refusal must actually END a live recognition — not a dead letter.
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    a = establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    b = establish_self_held_identity(ks, "peer-b", at=AT, registry=reg)
    rec = mutual_recognition(ks, "peer-a", "peer-b", at=AT, registry=reg)
    assert verify_recognition(rec, a, b) is True                                  # live: verifies
    ref = refuse_recognition(ks, "peer-a", "peer-b", at=AT, registry=reg)
    assert verify_recognition(rec, a, b, revocations=[ref]) is False               # refusal KILLS the live recognition
    # a refusal naming other peers does not kill this recognition
    other = refuse_recognition(ks, "peer-a", "peer-c", at=AT, registry=reg)
    assert verify_recognition(rec, a, b, revocations=[other]) is True


def test_the_fence_refuses_registry_directory_and_scored_authority(tmp_path):
    ks = str(tmp_path / "ks"); reg = _reg(tmp_path)
    establish_self_held_identity(ks, "peer-a", at=AT, registry=reg)
    establish_self_held_identity(ks, "peer-b", at=AT, registry=reg)
    for bad in ("registry", "directory", "name_service", "central_index", "scored_authority", "custodian"):
        with pytest.raises(PeerhoodError):
            mutual_recognition(ks, "peer-a", "peer-b", at=AT, registry=reg, extra={bad: "acme"})
    assert {"registry", "directory", "scored_authority", "second_authority"} <= RECOGNITION_BREACH_FIELDS


def test_composes_sealed_floors_and_genesis():
    import sovereign_agent.peerhood.recognition as m
    src = pathlib.Path(m.__file__).read_text()
    for sealed in ("genesis", "keystore", "federation.node_gov", "messaging.inter_node"):
        assert sealed in src                                                      # composes genesis + D1 + S8 V6 + S6 V1
