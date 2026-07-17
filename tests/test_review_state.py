"""R-1 review_state: schema RS-1 append/derive/summary + visibility-never-blocks."""
import json
import os
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from sovereign_agent.press import review_state as rs  # noqa: E402


def _env(tmp_path):
    env = dict(os.environ)
    env["PRESS_DATA_ROOT"] = str(tmp_path)
    return env


def test_append_derive_supersede(tmp_path, monkeypatch):
    monkeypatch.setenv("PRESS_DATA_ROOT", str(tmp_path))
    rs.append_event("VOL-1", "board_r1", "run", hand="the builder")
    rs.append_event("VOL-1", "board_r1", "findings_open", hand="the builder")
    rs.append_event("VOL-1", "board_r1", "closed", hand="the builder", note="all fixed")
    rs.append_event("VOL-1", "peer_fidelity", "run", hand="the peer")
    state = rs.derive("VOL-1")
    assert state["board_r1"]["status"] == "closed"  # later lines supersede
    assert state["peer_fidelity"]["status"] == "run"
    # append-only on disk: all four lines still present
    p = tmp_path / "artifacts" / "review_state" / "VOL-1.ndjson"
    assert len(p.read_text().splitlines()) == 4


def test_summary_shapes(tmp_path, monkeypatch):
    monkeypatch.setenv("PRESS_DATA_ROOT", str(tmp_path))
    assert rs.summary("NOPE") == "no review state recorded"
    rs.append_event("VOL-2", "board_r1", "closed", hand="the builder")
    rs.append_event("VOL-2", "lens_book_ux", "findings_open", hand="g")
    s = rs.summary("VOL-2")
    assert "R1:✓" in s and "LENS:OPEN" in s and "OP:—" in s


def test_unknown_status_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("PRESS_DATA_ROOT", str(tmp_path))
    try:
        rs.append_event("VOL-3", "board_r1", "done", hand="x")
    except ValueError:
        return
    raise AssertionError("unknown status must be refused loud")


def test_malformed_lines_skipped_with_count(tmp_path, monkeypatch):
    monkeypatch.setenv("PRESS_DATA_ROOT", str(tmp_path))
    rs.append_event("VOL-4", "operator_read", "run", hand="the operator")
    p = tmp_path / "artifacts" / "review_state" / "VOL-4.ndjson"
    with open(p, "a") as f:
        f.write("not json at all\n")
        f.write(json.dumps({"layer": "x", "status": "bogus"}) + "\n")
    events, skipped = rs.load_events("VOL-4")
    assert len(events) == 1 and skipped == 2


def test_harden_visibility_never_blocks(tmp_path):
    """A floor-passing harden with ZERO review state still stages its proposal
    (exit 3) and the proposal carries the visibility line — R-1 blocks nothing."""
    home = tmp_path / "home"
    home.mkdir()
    code = home / "mod.py"
    code.write_text("def act(x):\n    if not x:\n        raise ValueError('refused')\n"
                    "    return 'receipt: ok'\n")
    (home / "press_manifest.yaml").write_text(
        "volumes:\n  RV-01:\n    title: T\n    series: RV\n    stage: drafting\n"
        "    build: sh -c 'true'\n    artifact: mod.py\n"
        "harden:\n  RV-01:\n    code_file: mod.py\n    workdir: .\n"
        "    checks:\n      - sh -c 'true'\n")
    env = dict(os.environ)
    env.update({"PRESS_HOME": str(home), "PRESS_DATA_ROOT": str(home),
                "PRESS_MANIFEST": str(home / "press_manifest.yaml"),
                "PRESS_RUNS_DIR": str(home / "press_runs"),
                "PYTHONPATH": str(SRC)})
    r = subprocess.run([sys.executable, "-m", "sovereign_agent.press", "harden", "RV-01"],
                       cwd=home, env=env, capture_output=True, text=True)
    assert r.returncode == 3, r.stdout + r.stderr  # proposal staged, not blocked
    assert "no review state recorded" in r.stdout
    assert "visibility only" in r.stdout
    # and the receipt carries it
    bundles = list((home / "press_runs").glob("*harden_RV-01/harden.json"))
    assert bundles and "human_review_visibility" in bundles[0].read_text()
