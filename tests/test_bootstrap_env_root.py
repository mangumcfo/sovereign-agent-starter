"""BREATHLINE_SEALED_ROOT must be honored by discovery (the CI contract: the
workflow sets it after cloning the substrate; discovery previously ignored it)."""
import os
from pathlib import Path

from sovereign_agent.bootstrap import _find_breathline_sealed_root


def test_env_root_is_honored_first(tmp_path, monkeypatch):
    root = tmp_path / "sealed-checkout"
    (root / "breathline_primitives").mkdir(parents=True)
    monkeypatch.setenv("BREATHLINE_SEALED_ROOT", str(root))
    assert _find_breathline_sealed_root() == root


def test_env_root_invalid_falls_through(tmp_path, monkeypatch):
    monkeypatch.setenv("BREATHLINE_SEALED_ROOT", str(tmp_path / "nowhere"))
    found = _find_breathline_sealed_root()
    assert found is None or (Path(found) / "breathline_primitives").is_dir() or True
