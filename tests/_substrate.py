"""Shared probe: is the sealed crypto substrate (breathline_primitives) available?

F-1 GUARD (KM ruling 2026-08-03): a test that exercises the sealed crypto substrate must SKIP loudly on a
pure public clone (substrate absent) — never hard-fail as if the project were broken. This mirrors the proven
`test_merkle_accumulator` pattern (peer review [351] #2: skip on a named condition, never a silent false-green).

The substrate (P1 ECDSA + P5 Merkle) ships with the breathline-sealed checkout, NOT public PyPI; a clone of
the public starter alone does not have it. `import sovereign_agent` still succeeds (the crypto surface is lazy,
see _lazy_bp.py) — only crypto USE requires it, which is exactly what these guarded tests do. Resolve it the
SAME way the runtime does (bootstrap, then genuinely exercise MerkleTree), so the skip reflects real absence.
"""


def substrate_available() -> bool:
    try:
        from sovereign_agent.bootstrap import ensure_breathline_primitives
        ensure_breathline_primitives()
    except Exception:
        pass
    try:
        from sovereign_agent._lazy_bp import MerkleTree as _MT
        _MT([b"probe"]).get_root()
        return True
    except Exception:
        return False
