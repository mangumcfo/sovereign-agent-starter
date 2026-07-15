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


class _R:
    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def test_commit_failure_does_not_seal_or_close(tmp_path, monkeypatch):
    """CRIT-1 (audit 2026-06-13d): a FAILED git commit must REVERT + mark_error + return non-zero —
    never seal a cylinder or close the obligation with a false-success E2 receipt."""
    repo = tmp_path / "books"
    repo.mkdir()
    f = repo / "x.txt"
    f.write_text("edited")
    monkeypatch.setattr(A, "REPOS", {"books": {"root": str(repo), "name": "t", "email": "t@t", "trailer": False}})

    prop = {"id": "prop_x", "obligation_id": "obl_zzz", "decisions": {"g1": "accept"},
            "groups": [{"id": "g1", "file": str(f), "kind": "books"}]}
    monkeypatch.setattr(A, "_get", lambda path: {"proposals": [prop]})

    def fake_apply(g, changed, created=None):
        changed.setdefault("books", []).append(str(f))
        return True, "books"
    monkeypatch.setattr(A, "_apply_group", fake_apply)

    def fake_git(root, args):
        if args[:2] == ["rev-parse", "HEAD"]:
            return _R(out="HEAD0\n")
        if "commit" in args:
            return _R(rc=1, err="pre-commit hook rejected the commit")   # the failure
        return _R()
    monkeypatch.setattr(A, "_git", fake_git)

    rec = {"revert": 0, "errors": [], "subproc": 0}
    monkeypatch.setattr(A, "_revert", lambda c, cr: rec.__setitem__("revert", rec["revert"] + 1))
    monkeypatch.setattr(A, "_mark_error", lambda pid, reason: rec["errors"].append(reason))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (rec.__setitem__("subproc", rec["subproc"] + 1), _R())[1])
    monkeypatch.setattr(A.sys, "argv", ["atrium_apply.py", "prop_x"])

    rc = A.main()
    assert rc == 5                                   # hard-failed before seal/close
    assert rec["revert"] == 1                        # reverted
    assert any("git commit failed" in e for e in rec["errors"])
    assert rec["subproc"] == 0                       # SEAL never spawned (and no close path reached)


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


def test_repos_seal_resolve_from_env_not_hardcoded(monkeypatch, tmp_path):
    """#15 (audit 2026-06-13d): EXECUTE-half paths resolve from env/config, not operator literals."""
    monkeypatch.setenv("BREATHLINE_BOOKS_ROOT", str(tmp_path / "vault"))
    assert A._books_root() == str(tmp_path / "vault")          # env override honored
    monkeypatch.delenv("BREATHLINE_BOOKS_ROOT", raising=False)
    assert A._books_root()                                      # falls back (config/literal), never empty
    # derived from __file__ (this repo's root), not a /home literal — name-independent
    from pathlib import Path as _P
    assert _P(A._STARTER_ROOT) == _P(A.__file__).resolve().parents[1]


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
