"""Vulture whitelist — names that are DYNAMICALLY used and would otherwise false-flag as dead
(audit 2026-06-16 #8/M1, peer review [369] refinement #1). Curated, not auto-generated: each entry is a real
dynamic-dispatch surface this codebase uses. `_.<name>` marks <name> as used (vulture matches by name).

Pass this file as an extra vulture input: `vulture src scripts analysis/vulture_whitelist.py`.
"""


class _Whitelist:  # noqa
    pass


_ = _Whitelist()

# Refinement #1 (peer review [369]) — substrate-lazy conditional imports: present ONLY when the sealed substrate
# is wired (`try: from six import ... except ImportError`). Not dead — conditionally bound.
_.six_attestation
_.six_compliance
_.six_crypto

# [project.scripts] console-script entry points — referenced as "module:func" strings by pip, not call sites.
_.cli_connect
_.cli_create_node
_.launch
_.cli_serve

# Flask route handlers are registered via @bp.get/@bp.post decorators (called by Flask, not by name).
# _REGISTRY handlers (atrium_executor) dispatch by ref-class string. __all__ re-exports (obligations.ledger).
# gate/attestor are duck-typed injected callables. pytest fixtures are invoked by name by pytest.
# Add specific names here if a future scan at lower confidence surfaces one of these as a false positive.
