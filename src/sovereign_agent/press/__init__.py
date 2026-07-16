"""sovereign_agent.press — the Press: manifest-driven, receipted, human-gated build
conductor (P5a engine move, staged 2026-07-16). The engine has no home: PRESS_HOME =
where a node's manifests/runs live; PRESS_DATA_ROOT = node data. The human seal is
outside this package by construction — nothing here publishes or seals.

Run: python -m sovereign_agent.press <build|status|selftest|cycle|harden|report> …
"""
from . import engine  # noqa: F401
