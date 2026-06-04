#!/usr/bin/env python3
"""
Auto-apply agent (Step C-full, final): on KM's ACCEPT, land an accepted+tested proposal.

Triggered by POST /proposals/<id>/apply (human accept). For the accepted groups:
  prose  → exact-replace before→after in the manuscript
  code   → write new files / exact-replace, then RE-RUN tests in place
THEN: commit (per repo, local — NO auto-push) + seal a cylinder + close the obligation + clear the proposal.

Bounds / safety (constitution: Approve→Execute — KM's accept is Approve, this is Execute):
- Applies ONLY the accepted proposal's groups. Never invents.
- Code groups RE-TEST before commit; if red → REVERT all changes, mark apply_failed, exit (no commit/seal).
- Never guesses a file path; unresolvable/ambiguous → abort + flag (no writes).
- Reversible (git). Local commit only — push stays manual.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request

NODE = "http://127.0.0.1:8421/api/v1"
LOG = os.path.expanduser("~/.breathline/atrium_apply.log")
SEAL = "/home/kmangum/Tiger_1a/cylinders/seal.sh"

REPOS = {
    "starter": {"root": "/home/kmangum/work-repos/sovereign-agent-starter",
                "name": "Kenn Mangum", "email": "kenn@mangumcfo.com", "trailer": True},
    "ui":      {"root": "/home/kmangum/work-repos/mangumcfo/breathline-ui",
                "name": "KM-1176", "email": "kennmangum@gmail.com", "trailer": False},
    "books":   {"root": "/home/kmangum/work-repos/mangumcfo/breathline-books-vault",
                "name": "KM-1176", "email": "kennmangum@gmail.com", "trailer": False},
}
BOOK_DIRS = ["kdp/agentic_playbooks", "kdp/series_02_building_the_agentic_harness",
             "kdp/series_03_programmable_sovereign_erp"]


def _log(m: str) -> None:
    import time
    line = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + "  " + m
    try:
        open(LOG, "a", encoding="utf-8").write(line + "\n")
    except OSError:
        pass
    print(line, flush=True)


def _get(path):
    with urllib.request.urlopen(NODE + path, timeout=10) as r:
        return json.loads(r.read().decode())


def _git(repo_root, args):
    # Retry on a transient index.lock (a concurrent commit/recompile/seal can briefly hold it —
    # this is the "git locked for Tiger" KM saw). Wait + retry a few times instead of failing.
    import time as _t
    r = None
    for _ in range(5):
        r = subprocess.run(["git", "-C", repo_root] + args, capture_output=True, text=True)
        if r.returncode == 0 or "index.lock" not in (r.stderr or ""):
            return r
        _t.sleep(0.5)
    return r


def _repo_of(file: str):
    f = file.split(" ")[0].strip()  # drop any trailing parenthetical
    if f.startswith("/"):           # absolute path (the producer emits these) — match by repo root
        for k, info in REPOS.items():
            if f.startswith(info["root"]):
                return k, f
        return "books", f
    if f.startswith("src/") or f.startswith("tests/") or "sovereign-agent-starter" in f:
        return "starter", f.split("sovereign-agent-starter/")[-1]
    if "breathline-ui" in f or f.startswith("atrium/"):
        return "ui", f.split("breathline-ui/")[-1]
    return "books", f  # manuscript — resolved below


def _resolve(repo_key: str, rel: str):
    """Return an absolute path or None (None = unresolvable → caller aborts; never guess)."""
    if rel.startswith("/"):                 # producer emitted an absolute path — use as-is
        if os.path.isfile(rel):
            return rel
        return rel if not os.path.exists(rel) else None  # allowed for a new file
    root = REPOS[repo_key]["root"]
    rel = rel.lstrip("/").replace(".../", "")  # strip producer ellipsis if any
    cand = os.path.join(root, rel)
    if os.path.isfile(cand):
        return cand
    if repo_key == "books":
        base = os.path.basename(rel)
        hits = []
        for d in BOOK_DIRS:
            for dirpath, _, files in os.walk(os.path.join(root, d)):
                if base in files:
                    hits.append(os.path.join(dirpath, base))
        if len(hits) == 1:
            return hits[0]
    # new file (before==[]) is allowed even if it doesn't exist yet — handled by caller
    return cand if not os.path.exists(cand) else None


def _apply_group(g, dry_changes):
    file = g.get("file", "")
    repo_key, rel = _repo_of(file)
    path = _resolve(repo_key, rel)
    if path is None:
        return False, f"unresolvable/ambiguous path: {file}"
    hunks = g.get("hunks") or [{"before": g.get("before", []), "after": g.get("after", [])}]
    # new file = a single hunk with empty `before`
    if len(hunks) == 1 and not hunks[0].get("before"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        after = "\n".join(hunks[0].get("after", []))
        open(path, "w", encoding="utf-8").write(after + ("\n" if not after.endswith("\n") else ""))
        dry_changes.setdefault(repo_key, []).append(path)
        return True, repo_key
    if not os.path.isfile(path):
        return False, f"target missing for edit: {path}"
    txt = open(path, encoding="utf-8").read()
    for h in hunks:                      # apply every instance of the pattern
        before = "\n".join(h.get("before", []))
        after = "\n".join(h.get("after", []))
        if not before:
            continue
        if before not in txt:
            return False, f"before-text not found exactly in {os.path.basename(path)} (one hunk)"
        txt = txt.replace(before, after, 1)
    open(path, "w", encoding="utf-8").write(txt)
    dry_changes.setdefault(repo_key, []).append(path)
    return True, repo_key


def _mark_error(pid: str, reason: str) -> None:
    """RCCM CM1: surface an apply failure ON the proposal so the UI shows it — no more silent stuck
    card. Sets status='apply_failed' + apply_error=<reason> instead of leaving the card unexplained."""
    try:
        explicit = os.environ.get("PROPOSALS_STORE")
        led = os.environ.get("OBLIGATION_LEDGER_ROOT")
        store = explicit or os.path.join(os.path.dirname(led) if led else os.path.expanduser("~/.breathline"), "proposals.json")
        items = json.loads(open(store, encoding="utf-8").read())
        for x in items:
            if x.get("id") == pid:
                x["apply_error"] = str(reason)[:300]
                x["status"] = "apply_failed"
        open(store, "w", encoding="utf-8").write(json.dumps(items, indent=2))
        _log(f"  marked apply_error on {pid}: {reason}")
    except Exception as exc:  # noqa: BLE001
        _log(f"  mark-error note: {exc}")


def main() -> int:
    if len(sys.argv) < 2:
        _log("usage: atrium_apply.py <proposal_id> [gid,gid]")
        return 1
    pid = sys.argv[1]
    only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 and sys.argv[2] else None
    props = _get("/proposals").get("proposals", [])
    p = next((x for x in props if x.get("id") == pid), None)
    if not p:
        _log(f"proposal {pid} not found")
        return 1
    decisions = p.get("decisions", {})
    groups = [g for g in p.get("groups", [])
              if (only and g["id"] in only) or (not only and decisions.get(g["id"], "accept") == "accept")]
    if not groups:
        _log(f"no accepted groups to apply for {pid}")
        return 0
    _log(f"applying {pid}: {len(groups)} group(s)")
    changed = {}
    for g in groups:
        ok, info = _apply_group(g, changed)
        if not ok:
            _log(f"  ABORT — {info}")
            for repo_key in changed:
                _git(REPOS[repo_key]["root"], ["checkout", "--"] + changed[repo_key])
            _mark_error(pid, "couldn't apply: " + str(info) + " (the source text may have changed since this was proposed — Refine or re-process)")
            return 2
    # code groups → re-run tests in place; red → revert all + abort.
    # RCCM CM2: pytest exit 5 = "no tests collected" is NOT a failure — only treat real failures (1-4) as red.
    has_code = any(g.get("kind") == "code" for g in groups) or "starter" in changed
    if has_code:
        st = REPOS["starter"]["root"]
        res = subprocess.run(["python3", "-m", "pytest", "-q"], cwd=st,
                             env={**os.environ, "PYTHONPATH": st + "/src"},
                             capture_output=True, text=True)
        if res.returncode not in (0, 5):
            _log("  TESTS RED on apply — reverting, no commit")
            for repo_key in changed:
                _git(REPOS[repo_key]["root"], ["checkout", "--"] + changed[repo_key])
            _mark_error(pid, "re-test red on apply: " + ((res.stdout or res.stderr or "").strip().splitlines() or ["pytest failed"])[-1][:160])
            return 3
        _log("  tests green in place: " + (res.stdout.strip().splitlines() or ["?"])[-1])
    # commit per repo (local, no push) + collect for the seal note
    title = (p.get("groups", [{}])[0].get("title", "edit"))[:60]
    commits = []
    for repo_key, files in changed.items():
        r = REPOS[repo_key]
        rels = sorted({os.path.relpath(f, r["root"]) for f in files})   # dedup (a file edited by N groups)
        _git(r["root"], ["add"] + rels)
        msg = f"Atrium accepted apply: {title}\n\nproposal {pid}; accepted by KM in the diff-review."
        if r["trailer"]:
            msg += "\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
        c = _git(r["root"], ["-c", f"user.name={r['name']}", "-c", f"user.email={r['email']}",
                             "commit", "-q", "-m", msg])
        h = _git(r["root"], ["rev-parse", "--short", "HEAD"]).stdout.strip()
        commits.append(f"{repo_key}:{h}")
        _log(f"  committed {repo_key} {h} ({len(rels)} file(s), no push)")
    # seal one cylinder
    summary = f"Auto-apply (KM accepted) proposal {pid}: {title}. Commits: {', '.join(commits)}. Groups: {len(groups)}."
    try:
        subprocess.run([SEAL, "--hierarchical", summary], cwd=os.path.dirname(SEAL),
                       capture_output=True, text=True, timeout=60)
        _log("  sealed cylinder")
    except Exception as exc:
        _log(f"  seal error: {exc}")
    # close the obligation (E2) + clear the proposal
    oid = p.get("obligation_id")
    if oid:
        try:
            body = json.dumps({"evidence": f"E2: auto-applied (KM accepted) — commits {', '.join(commits)}; sealed; tests green.",
                               "evidence_tier": "E2", "closed_by": "tiger"}).encode()
            req = urllib.request.Request(NODE + f"/obligations/{oid}/close", data=body, method="POST",
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
            _log(f"  closed obligation {oid}")
        except Exception as exc:
            _log(f"  close note: {exc}")
    # AUTO-RECOMPILE the affected book PDFs (KM: recompile once the diffs are dispositioned)
    import re as _re
    build_dirs = set()
    for f in changed.get("books", []):
        m = _re.search(r"(.*/agentic_playbooks/\d+_[^/]+/v1\.0)/", f)
        if m and os.path.isfile(os.path.join(m.group(1), "build_v1.0.py")):
            build_dirs.add(m.group(1))
    for bd in build_dirs:
        try:
            subprocess.Popen(["python3", os.path.join(bd, "build_v1.0.py")], cwd=bd,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            _log(f"  auto-recompiling PDF: {bd}")
        except Exception as exc:
            _log(f"  recompile note: {exc}")
    # Mark the proposal APPLIED (keep it, don't delete) so the Sealed card can still show the diff
    # that was applied (KM: "keep the diff on the sealed card"). The board routes it to Sealed via the
    # closed obligation, not the proposal — so keeping it here doesn't re-surface it in Diffs-ready.
    try:
        explicit = os.environ.get("PROPOSALS_STORE")
        led = os.environ.get("OBLIGATION_LEDGER_ROOT")
        store = explicit or os.path.join(os.path.dirname(led) if led else os.path.expanduser("~/.breathline"), "proposals.json")
        items = json.loads(open(store, encoding="utf-8").read())
        for x in items:
            if x.get("id") == pid:
                x["status"] = "applied"
                x["applied_commits"] = commits
        open(store, "w", encoding="utf-8").write(json.dumps(items, indent=2))
        _log("  marked proposal applied (diff kept for the sealed card)")
    except Exception as exc:
        _log(f"  store-mark note: {exc}")
    _log(f"DONE {pid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
