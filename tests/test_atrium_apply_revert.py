"""Transactional revert — audit 2026-06-13 W5 #8.

A failed apply must leave the tree byte-clean: NEW (untracked) files deleted, edited (tracked) files
reverted, and one untracked path must not abort the whole revert (the git checkout pathspec hazard).
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import atrium_apply as A  # noqa: E402


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_confinement_rejects_writes_outside_repo_roots(tmp_path, monkeypatch):
    """audit 2026-06-13c #7: a proposal group targeting a path outside every REPOS root is refused."""
    repo = tmp_path / "starter"
    repo.mkdir()
    monkeypatch.setattr(A, "REPOS", {"starter": {"root": str(repo)}})
    # inside a repo root → confined
    assert A._confined(str(repo / "src" / "x.py")) is True
    # outside every root (e.g. a dotfile / creds) → refused
    assert A._confined(str(tmp_path / "evil" / ".bashrc")) is False
    assert A._confined("/etc/passwd") is False
    # a `..` escape attempt is realpath-normalized and refused
    assert A._confined(str(repo / ".." / "escape.txt")) is False


def test_revert_deletes_new_files_and_reverts_edits(tmp_path, monkeypatch):
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    tracked = repo / "a.txt"
    tracked.write_text("orig\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")

    # simulate a mid-apply state: a tracked file edited + a new untracked file created
    tracked.write_text("EDITED\n")
    new = repo / "sub" / "new.txt"
    new.parent.mkdir()
    new.write_text("CREATED\n")

    monkeypatch.setattr(A, "REPOS", {"r": {"root": str(repo)}})
    A._revert({"r": [str(tracked), str(new)]}, {"r": [str(new)]})

    assert tracked.read_text() == "orig\n", "tracked edit was not reverted"
    assert not new.exists(), "newly-created untracked file leaked through the revert"
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo,
                            capture_output=True, text=True).stdout
    assert status.strip() == "", f"tree not byte-clean after revert: {status!r}"
