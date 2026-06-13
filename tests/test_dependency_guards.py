"""Dependency-integrity guards — audit 2026-06-13 Phase D.

  1. The package imports on a host with breathline_primitives present (the common path).
  2. The fcntl write-fence degrades to a LOUD no-op (never a silent weakening) when fcntl is absent
     (the Windows import-crash the audit flagged).
"""
import os
import subprocess
import sys
import textwrap
import warnings
from pathlib import Path

import pytest


def test_package_imports():
    import sovereign_agent  # noqa: F401
    from sovereign_agent.obligations.ledger import ObligationLedger  # noqa: F401


def test_import_succeeds_without_substrate():
    """CRIT-2 gate (audit 2026-06-13): with breathline_primitives BLOCKED, `import sovereign_agent`
    (and the core/playbook/policy modules) must still succeed via the lazy crypto surface, and a crypto
    USE must raise a clear RuntimeError — never an ImportError at package load. Runs in a clean subprocess
    so the block takes effect before first import."""
    repo = Path(__file__).resolve().parents[1]
    script = textwrap.dedent('''
        import sys
        class _Block:
            def find_spec(self, name, path=None, target=None):
                if name == "breathline_primitives" or name.startswith("breathline_primitives."):
                    raise ModuleNotFoundError(name)
                return None
        sys.meta_path.insert(0, _Block())
        import warnings; warnings.simplefilter("ignore")
        import sovereign_agent
        from sovereign_agent import UniversalSovereignNode  # core path
        from sovereign_agent.playbook_loader import PlaybookLoader
        from sovereign_agent.compliance.policy_loader import PolicyLoader
        from sovereign_agent._lazy_bp import hash_function
        try:
            hash_function(b"x")
            print("CRYPTO_RAN_WITHOUT_SUBSTRATE"); raise SystemExit(3)
        except RuntimeError:
            print("CLEAN_IMPORT_CRYPTO_GUARDED")
    ''')
    env = {**os.environ, "PYTHONPATH": str(repo / "src")}
    r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, env=env)
    assert r.returncode == 0, f"clean-env import failed:\n{r.stderr}"
    assert "CLEAN_IMPORT_CRYPTO_GUARDED" in r.stdout, r.stdout + r.stderr


def test_flock_shim_degrades_loud_when_fcntl_absent(monkeypatch):
    from sovereign_agent.obligations import ledger
    monkeypatch.setattr(ledger, "_HAS_FCNTL", False)
    monkeypatch.setattr(ledger, "_FLOCK_WARNED", False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ledger._flock_ex(None)      # no-op on non-POSIX; must warn
        ledger._flock_un(None)      # no-op, no crash
        ledger._flock_ex(None)      # second call must NOT warn again (one-time)
    runtime_warnings = [w for w in caught if issubclass(w.category, RuntimeWarning)]
    assert len(runtime_warnings) == 1
    assert "write fence is NOT enforced" in str(runtime_warnings[0].message)


def test_flock_ex_uses_fcntl_when_present(monkeypatch):
    """When fcntl IS present the fence is real (no warning, calls flock)."""
    from sovereign_agent.obligations import ledger
    if not ledger._HAS_FCNTL:
        pytest.skip("fcntl not available on this platform")
    calls = []
    monkeypatch.setattr(ledger._fcntl, "flock", lambda fd, op: calls.append((fd, op)))

    class _FO:
        def fileno(self): return 7
    ledger._flock_ex(_FO())
    assert calls and calls[0][0] == 7
