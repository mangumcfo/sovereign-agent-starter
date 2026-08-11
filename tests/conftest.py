# -*- coding: utf-8 -*-
"""Session fixtures for the test suite.

D1 boot identity (Phase 0, KM 2026-08-11): node boot now loads a DURABLE self-held key from the keystore and
fails loud if it is absent (no ephemeral per-boot key). Point NODE_KEYSTORE_DIR at a hermetic tmp dir for the
whole session so any node the API onboards (deps.get_node → provision_if_absent=True) lands in a throwaway
keystore, never the operator's real one. Tests that pass an explicit keystore_dir are unaffected (explicit wins).
"""
import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def _hermetic_node_keystore(tmp_path_factory):
    d = tmp_path_factory.mktemp("node_keystore")
    prev = os.environ.get("NODE_KEYSTORE_DIR")
    os.environ["NODE_KEYSTORE_DIR"] = str(d)
    try:
        yield str(d)
    finally:
        if prev is None:
            os.environ.pop("NODE_KEYSTORE_DIR", None)
        else:
            os.environ["NODE_KEYSTORE_DIR"] = prev
