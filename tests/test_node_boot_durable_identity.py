# -*- coding: utf-8 -*-
"""Phase 0 BOOT (KM GO 2026-08-11) — the node boots on a DURABLE self-held key (D1), never an ephemeral one.

AA execute-verify probes, proven here:
- PERSIST      — the key is written to the keystore file on the operator's iron and survives the process.
- FINGERPRINT  — the SAME fingerprint across process restart (two independent boots of the same node_id).
- REFUSE ABSENT— a node cannot boot without a durable self-held key: default boot on an empty keystore FAILS LOUD.
- REFUSE TAMPER— a tampered keystore file is refused (the private scalar must derive the stored public key).
- NO EPHEMERAL — `generate_keypair` is gone from the boot path (core.py no longer calls it at __init__).
"""
import json
import os
import pathlib

import pytest

from _substrate import substrate_available  # noqa: E402  (F-1 GUARD)
pytestmark = pytest.mark.skipif(not substrate_available(),
    reason="breathline_primitives (sealed crypto substrate) absent — honest skip, not a broken clone")

from sovereign_agent import SovereignAgent
from sovereign_agent.keystore.node_keystore import (
    generate_node_key, has_node_key, load_node_keypair, KeystoreError,
)


def test_boot_persists_a_durable_key(tmp_path):
    ks = str(tmp_path / "ks")
    assert has_node_key(ks, "node-a") is False
    generate_node_key(ks, "node-a", at="2026-08-11T00:00:00Z")                    # explicit onboarding
    assert has_node_key(ks, "node-a") is True                                     # written to disk
    assert pathlib.Path(ks, "node-a.nodekey.json").exists()
    agent = SovereignAgent("node-a", keystore_dir=ks)                             # boot LOADS it (load-only)
    assert agent.fingerprint and agent.identity.private_key                       # a real self-held key


def test_same_fingerprint_across_process_restart(tmp_path):
    ks = str(tmp_path / "ks")
    generate_node_key(ks, "node-a", at="2026-08-11T00:00:00Z")                    # onboard once
    # each boot LOADS the same durable key — no new keypair, so the fingerprint is stable across restarts
    first = SovereignAgent("node-a", keystore_dir=ks).fingerprint
    second = SovereignAgent("node-a", keystore_dir=ks).fingerprint
    third = SovereignAgent("node-a", keystore_dir=ks).fingerprint
    assert first == second == third


def test_boot_refuses_an_absent_key(tmp_path):
    ks = str(tmp_path / "empty")                                                  # no key provisioned
    with pytest.raises(KeystoreError):
        SovereignAgent("ghost", keystore_dir=ks)                                  # boot = load-only, fail-loud
    # and it stays refused for the node runtime too (UniversalSovereignNode inherits the same boot)
    from sovereign_agent.universal_sovereign_node import UniversalSovereignNode, create_universal_sovereign_node
    with pytest.raises(KeystoreError):
        UniversalSovereignNode(name="ghost", keystore_dir=ks)
    # AA's exact RED-baseline repro path (the factory) now FAILS LOUD instead of minting an ephemeral key:
    # NODE_KEYSTORE_DIR points at the hermetic dir (no 'uat-node' key), so the factory boot refuses.
    with pytest.raises(KeystoreError):
        create_universal_sovereign_node("uat-node")


def test_boot_refuses_a_tampered_key(tmp_path):
    ks = str(tmp_path / "ks")
    generate_node_key(ks, "node-a", at="2026-08-11T00:00:00Z")                    # a real key
    p = pathlib.Path(ks, "node-a.nodekey.json")
    rec = json.loads(p.read_text())
    rec["private_hex"] = "%064x" % ((int(rec["private_hex"], 16) + 1))            # scalar no longer derives the pub
    p.write_text(json.dumps(rec, sort_keys=True))
    with pytest.raises(KeystoreError):
        SovereignAgent("node-a", keystore_dir=ks)                                 # tamper refused at boot
    with pytest.raises(KeystoreError):
        load_node_keypair(ks, "node-a")


def test_no_ephemeral_generate_keypair_in_boot_path():
    # the boot path must not mint an ephemeral keypair — generate_keypair is removed from core's boot.
    import sovereign_agent.core as core
    src = pathlib.Path(core.__file__).read_text()
    assert "self.identity = generate_keypair" not in src                          # the removed ephemeral line
    assert "load_node_keypair" in src                                             # durable load wired in
