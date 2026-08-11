# -*- coding: utf-8 -*-
"""Session fixtures for the test suite.

D1 boot identity (Phase 0, KM 2026-08-11): node boot now LOADS a DURABLE self-held key from the keystore and
FAILS LOUD if it is absent (no ephemeral per-boot key, no mint-on-missing fallback in the boot path). For the
suite:
  - point NODE_KEYSTORE_DIR at a hermetic tmp dir for the whole session (never the operator's real keystore);
  - ONBOARD the default Node-API node once (explicit generate_node_key) so deps.get_node() — which is load-only
    — boots on a durable key. This mirrors an operator who onboarded before serving.
Tests that pass an explicit keystore_dir are unaffected (explicit wins). The refuse-absent probe uses its own
empty keystore dir, so it still fails loud.
"""
import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def _hermetic_node_keystore(tmp_path_factory):
    d = str(tmp_path_factory.mktemp("node_keystore"))
    prev = os.environ.get("NODE_KEYSTORE_DIR")
    os.environ["NODE_KEYSTORE_DIR"] = d
    # Onboard the default Node-API node once (explicit — never a silent boot mint).
    try:
        from sovereign_agent.keystore.node_keystore import has_node_key, generate_node_key
        for nid in ("UniversalSovereignNode",):
            if not has_node_key(d, nid):
                generate_node_key(d, nid, at="2026-08-11T00:00:00Z")
    except Exception:
        # substrate absent (bare clone) — node_api tests are skipped in that case anyway.
        pass
    try:
        yield d
    finally:
        if prev is None:
            os.environ.pop("NODE_KEYSTORE_DIR", None)
        else:
            os.environ["NODE_KEYSTORE_DIR"] = prev
