"""Kernel-side press engine tests (P5a-S1). Self-contained: fixture catalogs only,
no node data — the engine must prove its laws on a fresh clone with nothing but itself.
The node harness still runs the full set incl. node-data proofs.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from sovereign_agent.press import engine  # noqa: E402


def _run(args, cwd, env_extra=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("PRESS_")}
    env["PYTHONPATH"] = str(SRC)
    env.update(env_extra or {})
    return subprocess.run([sys.executable, "-m", "sovereign_agent.press", *args],
                          cwd=cwd, env=env, capture_output=True, text=True)


def test_selftest_fixture_suite_green_from_anywhere(tmp_path):
    """The kernel selftest (fixture proofs) passes — run from an empty tmp dir, the
    exact fresh-clone posture: no manifest, no node data, PRESS_HOME defaulting to cwd."""
    r = _run(["selftest"], cwd=str(tmp_path))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert "tampered frozen sha failed the PARITY check loud" in r.stdout
    assert "node-data proofs NOT RUN" in r.stdout  # loud, never silent


def test_default_deny_no_manifest(tmp_path):
    r = _run(["build", "--all"], cwd=str(tmp_path))
    assert r.returncode != 0
    assert "default-deny" in (r.stdout + r.stderr)


def test_residual_args_fail_loud(tmp_path):
    r = _run(["status", "--verbose"], cwd=str(tmp_path))
    assert r.returncode != 0
    assert "unrecognized argument" in (r.stdout + r.stderr)


def test_build_and_parity_on_fixture_catalog(tmp_path):
    art = tmp_path / "a.txt"
    manifest = f"""volumes:
  FIX-01:
    series: FIX
    stage: drafting
    build: sh -c "printf alpha > {art}"
    gates:
      - sh -c "test -s {art}"
    artifact: {art}
"""
    (tmp_path / "press_manifest.yaml").write_text(manifest)
    r = _run(["build", "FIX-01"], cwd=str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    q = json.loads((tmp_path / "press_runs" / "seal_queue.json").read_text())
    assert q and not q[0]["sealed"], "seal queue holds unsealed — the human word only"


def test_engine_carries_no_workbench_paths():
    """Anchor generalization: zero hardcoded workbench/home paths in the package."""
    pkg = SRC / "sovereign_agent" / "press"
    offenders = []
    for p in pkg.glob("*.py"):
        t = p.read_text()
        for needle in ("/home/", "breathline-workbench", "work-repos", "tools/press"):
            if needle in t:
                offenders.append(f"{p.name}: {needle}")
    assert not offenders, offenders


def test_wave_approval_still_k1(tmp_path):
    art_a, art_b = tmp_path / "wa.txt", tmp_path / "wb.txt"
    manifest = f"""volumes:
  WVA-01:
    series: WVA
    stage: drafting
    workdir: {tmp_path}
    build: sh -c "printf a > wa.txt"
    gates: ["sh -c 'test -s wa.txt'"]
    artifact: wa.txt
  WVB-01:
    series: WVB
    stage: drafting
    workdir: {tmp_path}
    build: sh -c "printf b > wb.txt"
    gates: ["sh -c 'test -s wb.txt'"]
    artifact: wb.txt
"""
    (tmp_path / "press_manifest.yaml").write_text(manifest)
    r = _run(["build", "--all", "--mode", "parallel"], cwd=str(tmp_path))
    assert r.returncode == 3, "the Press must not open waves — exit 3 awaiting the human word"
    r2 = _run(["build", "--all", "--mode", "parallel", "--approve-wave", "WVA,WVB"],
              cwd=str(tmp_path))
    assert r2.returncode == 0, r2.stdout + r2.stderr


def test_example_catalog_end_to_end(tmp_path):
    """The shipped two-document example builds, bundles, and offline-rebuilds —
    a fresh node's first run, exactly as documented."""
    import shutil
    ex_src = Path(__file__).resolve().parents[1] / "examples" / "two_document_catalog"
    ex = tmp_path / "catalog"
    shutil.copytree(ex_src, ex)
    r = _run(["build", "--all"], cwd=str(ex))
    assert r.returncode == 0, r.stdout + r.stderr
    r2 = _run(["bundle", "EX-01"], cwd=str(ex))
    assert r2.returncode == 0 and (ex / "charter_src" / "bundle" / "bundle.json").exists()
    r3 = _run(["build", "--offline", "EX-01"], cwd=str(ex))
    assert r3.returncode == 0, r3.stdout + r3.stderr
    assert "offline" in r3.stdout


def test_offline_refuses_without_bundle(tmp_path):
    import shutil
    ex_src = Path(__file__).resolve().parents[1] / "examples" / "two_document_catalog"
    ex = tmp_path / "catalog"
    shutil.copytree(ex_src, ex)
    r = _run(["build", "--offline", "EX-02"], cwd=str(ex))
    assert r.returncode != 0 and "NO bundle" in (r.stdout + r.stderr)


def test_offline_refuses_tampered_bundle(tmp_path):
    import shutil
    ex_src = Path(__file__).resolve().parents[1] / "examples" / "two_document_catalog"
    ex = tmp_path / "catalog"
    shutil.copytree(ex_src, ex)
    assert _run(["bundle", "EX-01"], cwd=str(ex)).returncode == 0
    victim = ex / "charter_src" / "bundle" / "sources" / "charter.md"
    victim.write_text(victim.read_text() + "\ntampered line\n")
    r = _run(["build", "--offline", "EX-01"], cwd=str(ex))
    assert r.returncode != 0 and "tampered" in (r.stdout + r.stderr)
