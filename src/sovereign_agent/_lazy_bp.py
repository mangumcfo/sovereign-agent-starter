"""Lazy breathline_primitives surface (audit 2026-06-13 CRIT-2).

The sealed crypto substrate (P1 ECDSA secp256k1 + P5 Merkle) is provided by the breathline-sealed
checkout, NOT a public PyPI package. Importing it at module top made `import sovereign_agent` HARD-CRASH
on any host without the substrate (the dependency CRITICAL).

This module exposes the SAME names the core used to import directly, but resolves them LAZILY on first
use — so package import always succeeds (clean install / demo / inspection / CI), and a genuine
cryptographic USE without the substrate raises a clear, actionable RuntimeError at the call site instead
of an ImportError at package load. The diagnosability the bootstrap warning already won is preserved; the
runs-anywhere promise becomes true rather than narrated.

Usage is drop-in — `from ._lazy_bp import generate_keypair, sign, verify, MerkleTree, hash_function,
secp256k1_curve` — and every call site stays exactly as it was.
"""
from __future__ import annotations

_BP = None


def _bp():
    """Resolve breathline_primitives on first call; raise an actionable error if the substrate is absent."""
    global _BP
    if _BP is None:
        try:
            import breathline_primitives as bp  # noqa: PLC0415
            _BP = bp
        except ImportError as e:  # substrate not on path — try the bootstrap once, then fail loud
            try:
                from .bootstrap import ensure_breathline_primitives  # noqa: PLC0415
                ensure_breathline_primitives()
                import breathline_primitives as bp  # noqa: PLC0415
                _BP = bp
            except Exception:  # noqa: BLE001
                raise RuntimeError(
                    "breathline_primitives (the sealed crypto substrate) is not available — cryptographic "
                    "attestation cannot run. Set BREATHLINE_SEALED_ROOT to your breathline-sealed checkout "
                    "or `pip install -e` it, then retry. (Import of sovereign_agent itself succeeds without "
                    "it; only crypto operations require it.)"
                ) from e
    return _BP


class _Lazy:
    """A name that resolves to `<module>.<attr>` on first call/attribute access. We resolve via
    importlib.import_module(module) (NOT attribute-walking off the top package) so a submodule name like
    `breathline_primitives.layer1` returns the SAME free function the original `from … import …` bound —
    `bp.layer1` is a facade object whose attributes are bound methods, which would mis-pass `self`.
    Functions resolve on __call__; classes (MerkleTree) construct on __call__ and forward
    classmethods/attrs via __getattr__."""

    __slots__ = ("_module", "_attr")

    def __init__(self, attr: str, module: str = "breathline_primitives"):
        self._module = module
        self._attr = attr

    def _resolve(self):
        _bp()  # ensure availability (+ bootstrap) and a clear error if the substrate is absent
        import importlib  # noqa: PLC0415
        return getattr(importlib.import_module(self._module), self._attr)

    def __call__(self, *args, **kwargs):
        return self._resolve()(*args, **kwargs)

    def __getattr__(self, attr):
        if attr.startswith("_"):
            raise AttributeError(attr)
        return getattr(self._resolve(), attr)


generate_keypair = _Lazy("generate_keypair")
sign = _Lazy("sign")
verify = _Lazy("verify")
hash_function = _Lazy("hash_function")
MerkleTree = _Lazy("MerkleTree")
secp256k1_curve = _Lazy("secp256k1_curve", module="breathline_primitives.layer1")
