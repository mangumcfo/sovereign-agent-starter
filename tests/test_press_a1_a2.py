"""Campaign 0 remedies: A1 (font shas in the bundle env manifest) and
A2 (gate scripts travel with the volume)."""
import json
import os
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"

GATE_SH = "#!/bin/sh\ngrep -q 'human decision' \"$1\"\n"


def _mk_catalog(root: Path, font: Path | None = None):
    wd = root / "vol_src"
    wd.mkdir()
    (wd / "doc.md").write_text("a human decision closes every gate\n")
    gates_home = root / "node_gates"
    gates_home.mkdir()
    gate = gates_home / "content_gate.sh"
    gate.write_text(GATE_SH)
    gate.chmod(0o755)
    font_line = f"    font_files: [{font}]\n" if font else ""
    (root / "press_manifest.yaml").write_text(
        "volumes:\n"
        "  AV-01:\n"
        "    title: Traveling Gates\n"
        "    series: AV\n"
        "    stage: drafting\n"
        f"    workdir: {wd}\n"
        "    build: sh -c \"cp doc.md doc.txt\"\n"
        "    gates:\n"
        "      - sh $PRESS_GATE_DIR/content_gate.sh doc.txt\n"
        f"    gate_files: [{gate}]\n"
        f"{font_line}"
        "    artifact: doc.txt\n")
    return wd, gate


def _env(root: Path):
    env = dict(os.environ)
    env.update({"PRESS_HOME": str(root), "PRESS_DATA_ROOT": str(root),
                "PRESS_MANIFEST": str(root / "press_manifest.yaml"),
                "PRESS_RUNS_DIR": str(root / "press_runs"),
                "PYTHONPATH": str(SRC)})
    return env


def _press(root, *args):
    return subprocess.run([sys.executable, "-m", "sovereign_agent.press", *args],
                          cwd=root, env=_env(root), capture_output=True, text=True)


def test_a2_gate_travels_online_and_offline(tmp_path):
    wd, gate = _mk_catalog(tmp_path)
    r = _press(tmp_path, "build", "AV-01")
    assert r.returncode == 0, r.stdout + r.stderr          # online: staged + expanded
    assert (wd / ".press_gates" / "content_gate.sh").is_file()
    r = _press(tmp_path, "bundle", "AV-01")
    assert r.returncode == 0 and "1 traveling gates" in r.stdout
    meta = json.loads((wd / "bundle" / "bundle.json").read_text())
    assert "content_gate.sh" in meta["gate_shas"]
    gate.unlink()                                          # the authoring node forgets its gate
    (wd / ".press_gates" / "content_gate.sh").unlink()
    r = _press(tmp_path, "build", "--offline", "AV-01")
    assert r.returncode == 0, r.stdout + r.stderr          # the bundle still carries it
    run_dirs = list((tmp_path / "press_runs").glob("*_AV-01"))
    latest = json.loads(sorted(p / "run.json" for p in run_dirs)[-1].read_text())
    assert latest["gate_shas"].get("content_gate.sh")      # receipt names the traveled gate


def test_a2_missing_gate_file_refuses(tmp_path):
    _, gate = _mk_catalog(tmp_path)
    gate.unlink()
    r = _press(tmp_path, "build", "AV-01")
    assert r.returncode != 0 and "gates must travel" in (r.stdout + r.stderr)


def test_a2_tampered_bundled_gate_refuses_offline(tmp_path):
    wd, _ = _mk_catalog(tmp_path)
    assert _press(tmp_path, "bundle", "AV-01").returncode == 0
    bg = wd / "bundle" / "gates" / "content_gate.sh"
    bg.write_text(GATE_SH + "# tampered\n")
    r = _press(tmp_path, "build", "--offline", "AV-01")
    assert r.returncode != 0 and "tampered: gate" in (r.stdout + r.stderr)


def test_a1_font_shas_recorded_and_drift_warns(tmp_path):
    font = tmp_path / "SomeFace.ttf"
    font.write_bytes(b"not-really-a-font-but-bytes-are-bytes")
    wd, _ = _mk_catalog(tmp_path, font=font)
    assert _press(tmp_path, "bundle", "AV-01").returncode == 0
    meta = json.loads((wd / "bundle" / "bundle.json").read_text())
    assert str(font) in meta["env_manifest"]["fonts"]
    assert "pinned-env hosts" in meta["env_manifest"]["parity_domain"]
    r = _press(tmp_path, "build", "--offline", "AV-01")   # same host, same font: quiet
    assert r.returncode == 0 and "WARNING (A1)" not in r.stdout
    font.write_bytes(b"a different font version arrived")  # host drifts
    r = _press(tmp_path, "build", "--offline", "AV-01")
    assert "WARNING (A1)" in r.stdout and "font drift" in r.stdout
    assert r.returncode == 0                                # warns loud, parity law decides


def test_a1_declared_missing_font_refuses_bundle(tmp_path):
    font = tmp_path / "Ghost.ttf"
    _mk_catalog(tmp_path, font=font)                        # never written to disk
    r = _press(tmp_path, "bundle", "AV-01")
    assert r.returncode != 0 and "font_files" in (r.stdout + r.stderr)
