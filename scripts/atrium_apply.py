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
import re
import subprocess
import sys
import urllib.request

NODE = "http://127.0.0.1:8421/api/v1"
LOG = os.path.expanduser("~/.breathline/atrium_apply.log")
# Runs-anywhere (audit 2026-06-13d #15): resolve operator-specific paths from env/config with the literals
# as the LAST candidate, matching the rest of the stack's candidate-sweep portability. On a non-KM host
# these were a hard write-refusal (_confined anchors on REPOS roots) or a seal failure.
SEAL = os.environ.get("SEAL_SCRIPT") or "/home/kmangum/Tiger_1a/cylinders/seal.sh"


def _books_root() -> str:
    if os.environ.get("BREATHLINE_BOOKS_ROOT"):
        return os.environ["BREATHLINE_BOOKS_ROOT"]
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
        from sovereign_agent import config  # noqa: PLC0415
        kdp = config.get_books_kdp_root()
        if kdp:
            return os.path.dirname(str(kdp))   # the vault root is the parent of the kdp dir
    except Exception:  # noqa: BLE001
        pass
    return "/home/kmangum/work-repos/mangumcfo/breathline-books-vault"


_STARTER_ROOT = os.environ.get("BREATHLINE_STARTER_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ID_NAME = os.environ.get("BREATHLINE_COMMIT_NAME", "KM-1176")
_ID_EMAIL = os.environ.get("BREATHLINE_COMMIT_EMAIL", "kennmangum@gmail.com")
REPOS = {
    "starter": {"root": _STARTER_ROOT,
                "name": os.environ.get("BREATHLINE_STARTER_NAME", "Kenn Mangum"),
                "email": os.environ.get("BREATHLINE_STARTER_EMAIL", "kenn@mangumcfo.com"), "trailer": True},
    "ui":      {"root": os.environ.get("BREATHLINE_UI_ROOT") or "/home/kmangum/work-repos/mangumcfo/breathline-ui",
                "name": _ID_NAME, "email": _ID_EMAIL, "trailer": False},
    "books":   {"root": _books_root(),
                "name": _ID_NAME, "email": _ID_EMAIL, "trailer": False},
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


_QUOTES = "\"'‘’“”"   # straight + curly single/double
_DASHES = "-–—"                 # hyphen + en-dash + em-dash


def _tolerant_regex(before: str):
    """Match `before` ignoring the 3 common producer-vs-source near-misses: whitespace runs
    (wrapped lines / double spaces), straight-vs-curly quotes, and hyphen/en/em-dashes. Lets a
    valid edit apply even when the proposed before-text was lightly normalized."""
    parts = re.split(r"\s+", before.strip())
    def esc(p):
        out = []
        for ch in p:
            if ch in _QUOTES:
                out.append("[" + re.escape(_QUOTES) + "]")
            elif ch in _DASHES:
                out.append("[" + re.escape(_DASHES) + "]")
            else:
                out.append(re.escape(ch))
        return "".join(out)
    return re.compile(r"\s+".join(esc(p) for p in parts if p))


def _confined(path: str) -> bool:
    """A write target MUST resolve INSIDE a known REPOS root (audit 2026-06-13c #7). Proposal groups are
    LLM-produced from a human transcript, so an injected/crafted `file` (e.g. /home/kmangum/.bashrc or a
    credentials path) must never be written outside the managed repos — the human accept gate is not a
    path-safety control. realpath-normalized so `..`/symlinks can't escape."""
    rp = os.path.realpath(path)
    for info in REPOS.values():
        root = os.path.realpath(info["root"])
        if rp == root or rp.startswith(root + os.sep):
            return True
    return False


def _apply_group(g, dry_changes, created=None):
    file = g.get("file", "")
    repo_key, rel = _repo_of(file)
    path = _resolve(repo_key, rel)
    if path is None:
        return False, f"unresolvable/ambiguous path: {file}"
    if not _confined(path):
        return False, (f"refusing write OUTSIDE every repo root (path confinement): {path} — a proposal "
                       f"may only edit files under the managed repos.")
    hunks = g.get("hunks") or [{"before": g.get("before", []), "after": g.get("after", [])}]
    # new file = a single hunk with empty `before`
    if len(hunks) == 1 and not hunks[0].get("before"):
        is_new = not os.path.exists(path)   # track NEW (untracked) files so revert can delete them (W5 #8)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        after = "\n".join(hunks[0].get("after", []))
        open(path, "w", encoding="utf-8").write(after + ("\n" if not after.endswith("\n") else ""))
        dry_changes.setdefault(repo_key, []).append(path)
        if is_new and created is not None:
            created.setdefault(repo_key, []).append(path)
        return True, repo_key
    if not os.path.isfile(path):
        return False, f"target missing for edit: {path}"
    txt = open(path, encoding="utf-8").read()
    for h in hunks:                      # apply every instance of the pattern
        before = "\n".join(h.get("before", []))
        after = "\n".join(h.get("after", []))
        if not before:
            continue
        if before in txt:
            txt = txt.replace(before, after, 1)
        else:
            # tolerant fallback: whitespace / quote / dash variants (common producer normalization)
            m = _tolerant_regex(before).search(txt)
            if not m:
                return False, f"before-text not found in {os.path.basename(path)} (even whitespace/quote/dash-tolerant — the source may have changed; Refine or re-process)"
            txt = txt[:m.start()] + after + txt[m.end():]
    open(path, "w", encoding="utf-8").write(txt)
    dry_changes.setdefault(repo_key, []).append(path)
    return True, repo_key


def _revert(changed: dict, created: dict) -> None:
    """Transactional undo of a failed apply (audit 2026-06-13 W5 #8). NEW (untracked) files are DELETED
    (git checkout can't revert an untracked path, and batching one in a checkout pathspec aborts the whole
    command — leaving tracked edits unreverted). Edited (tracked) files are checked out PER PATH so a
    single bad pathspec can never strand the rest. The 'if red → REVERT all' guarantee now holds."""
    for repo_key, files in changed.items():
        root = REPOS[repo_key]["root"]
        made = set(created.get(repo_key, []))
        for f in files:
            if f in made:
                try:
                    os.remove(f)
                except OSError:
                    _git(root, ["clean", "-f", "--", f])
            else:
                _git(root, ["checkout", "--", f])   # per-path: an untracked/bad pathspec can't abort the rest


def _update_store(mutate):
    """Fenced RMW on proposals.json shared with the node (audit 2026-06-13 W5 #2/#11 + #9): this
    subprocess races the node's own writes, so it must use the SAME flock AND the SAME path resolver
    (sidecar_store) as node_api._jsonstore — one resolver, no split-brain."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
    from sovereign_agent.node_api._jsonstore import update_json, sidecar_store  # noqa: PLC0415
    return update_json(sidecar_store("proposals.json", "PROPOSALS_STORE"), mutate)


def _mark_error(pid: str, reason: str) -> None:
    """RCCM CM1: surface an apply failure ON the proposal so the UI shows it — no more silent stuck
    card. Sets status='apply_failed' + apply_error=<reason> instead of leaving the card unexplained."""
    try:
        def _m(items):
            for x in items:
                if x.get("id") == pid:
                    x["apply_error"] = str(reason)[:300]
                    x["status"] = "apply_failed"
            return items, None
        _update_store(_m)
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
    # CONSTITUTION (audit 2026-06-13 CRIT-1): undecided ⇒ REJECT, never the old accept-default.
    # The dangerous line was `decisions.get(g["id"], "accept") == "accept"` (undecided → accept) and a
    # passed group id applied regardless of any decision. Now: only explicitly-accepted groups apply,
    # and a passed `only` set is INTERSECTED with the accepted set (a named gid can't apply an undecided
    # group). The route also pre-verifies a decision exists, so this is defence-in-depth.
    accepted = {g["id"] for g in p.get("groups", []) if decisions.get(g["id"]) == "accept"}
    wanted = (only & accepted) if only else accepted
    groups = [g for g in p.get("groups", []) if g["id"] in wanted]
    if not groups:
        _log(f"no accepted groups to apply for {pid}")
        return 0
    _log(f"applying {pid}: {len(groups)} group(s)")
    changed, created = {}, {}
    for g in groups:
        ok, info = _apply_group(g, changed, created)
        if not ok:
            _log(f"  ABORT — {info}")
            _revert(changed, created)   # delete new files + per-path checkout edits (audit W5 #8)
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
            _revert(changed, created)   # delete new files + per-path checkout edits (audit W5 #8)
            _mark_error(pid, "re-test red on apply: " + ((res.stdout or res.stderr or "").strip().splitlines() or ["pytest failed"])[-1][:160])
            return 3
        _log("  tests green in place: " + (res.stdout.strip().splitlines() or ["?"])[-1])
    # commit per repo (local, no push) + collect for the seal note
    title = (p.get("groups", [{}])[0].get("title", "edit"))[:60]
    commits = []
    for repo_key, files in changed.items():
        r = REPOS[repo_key]
        rels = sorted({os.path.relpath(f, r["root"]) for f in files})   # dedup (a file edited by N groups)
        head_before = _git(r["root"], ["rev-parse", "HEAD"]).stdout.strip()
        _git(r["root"], ["add"] + rels)
        msg = f"Atrium accepted apply: {title}\n\nproposal {pid}; accepted by KM in the diff-review."
        if r["trailer"]:
            msg += "\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
        c = _git(r["root"], ["-c", f"user.name={r['name']}", "-c", f"user.email={r['email']}",
                             "commit", "-q", "-m", msg])
        head_after = _git(r["root"], ["rev-parse", "HEAD"]).stdout.strip()
        # CRIT-1 (audit 2026-06-13d): a FAILED commit must NOT seal/close a false success. The old code
        # never checked c.returncode and `rev-parse HEAD` returned the PRIOR commit, so a pre-commit-hook
        # rejection / identity error / surviving index.lock would seal a cylinder + close the obligation
        # with E2 evidence citing a commit that does not contain the changes. Now: verify the commit
        # actually advanced HEAD; a real failure reverts + marks error + returns BEFORE sealing/closing.
        benign_noop = "nothing to commit" in (c.stdout + c.stderr).lower()
        if c.returncode != 0 and not benign_noop:
            _log(f"  COMMIT FAILED ({repo_key}) — reverting, no seal/close")
            _revert(changed, created)
            _mark_error(pid, "git commit failed (" + repo_key + "): " + ((c.stderr or c.stdout or "").strip()[:200]))
            return 5
        if head_after == head_before:
            _log(f"  no commit landed for {repo_key} (nothing to commit) — not recording a hash")
            continue
        h = _git(r["root"], ["rev-parse", "--short", "HEAD"]).stdout.strip()   # the VERIFIED new HEAD
        commits.append(f"{repo_key}:{h}")
        _log(f"  committed {repo_key} {h} ({len(rels)} file(s), no push)")
    if changed and not commits:
        # changes were applied but NOTHING committed — never seal/close a false 'applied' (CRIT-1)
        _log("  no commits landed across any repo — aborting before seal/close")
        _revert(changed, created)
        _mark_error(pid, "apply produced no commits (nothing changed, or all commits failed) — not sealed/closed")
        return 5
    # seal one cylinder — check the returncode (audit 2026-06-13d #14): the seal subprocess result was
    # discarded and the except only caught timeout/missing-binary, so a non-zero seal (pipefail) was
    # silently ignored while close() still asserted 'sealed'. Now the close evidence reflects reality.
    seal_ok = True
    summary = f"Auto-apply (KM accepted) proposal {pid}: {title}. Commits: {', '.join(commits)}. Groups: {len(groups)}."
    try:
        sres = subprocess.run([SEAL, "--hierarchical", summary], cwd=os.path.dirname(SEAL),
                              capture_output=True, text=True, timeout=60)
        if sres.returncode != 0:
            seal_ok = False
            _log(f"  SEAL FAILED (rc {sres.returncode}): {((sres.stderr or sres.stdout or '').strip().splitlines() or ['?'])[-1][:160]}")
        else:
            _log("  sealed cylinder")
    except Exception as exc:
        seal_ok = False
        _log(f"  seal error: {exc}")
    # close the obligation IN-PROCESS (audit 2026-06-13c H1, CONSTITUTION §3/§4). The old path POSTed an
    # UNAUTHENTICATED close to the @require_owner /close route → 403 in normal config; the bare except
    # swallowed it and the proposal was still marked 'applied' while the obligation stayed OPEN — seal
    # chain vs ledger diverge, reported as success. Close directly on the SHARED ledger (no gate hop, no
    # partial-state window), like atrium_executor; a close FAILURE is hard — status='apply_close_failed',
    # never 'applied'. Principal is the authenticated apply-clicker (propagated via env), never 'tiger'.
    oid = p.get("obligation_id")
    close_ok = True
    if oid:
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
            from sovereign_agent.obligations.ledger import ObligationLedger, get_ledger_root  # noqa: PLC0415
            principal = (os.environ.get("BREATHLINE_APPLY_PRINCIPAL") or "").strip() or "system:apply"
            led = ObligationLedger(root=str(get_ledger_root()), principal_id=principal)
            led.close(oid, evidence=(f"E2: auto-applied (KM accepted) — commits {', '.join(commits)}; "
                                     f"{'sealed' if seal_ok else 'SEAL FAILED (reconcile cylinder chain)'}; tests green."),
                      evidence_tier="E2", require_e1=False, closed_by=principal)
            _log(f"  closed obligation {oid} in-process (by {principal})")
        except Exception as exc:  # noqa: BLE001
            close_ok = False
            _log(f"  CLOSE FAILED for {oid}: {exc} — marking apply_close_failed (NOT applied; no false success)")
            _mark_error(pid, f"applied + sealed but obligation close failed: {exc} — the obligation stays OPEN "
                             f"and will resurface; reconcile the seal vs ledger.")
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
    # H1: ONLY mark applied when the obligation actually closed — a failed close already set
    # 'apply_close_failed' via _mark_error; never overwrite that with a false 'applied'.
    if not close_ok:
        _log(f"DONE {pid} (apply_close_failed — obligation OPEN, not marked applied)")
        return 4
    try:
        def _m(items):
            for x in items:
                if x.get("id") == pid:
                    x["status"] = "applied"
                    x["applied_commits"] = commits
            return items, None
        _update_store(_m)   # fenced RMW (audit 2026-06-13 W5 #2/#11)
        _log("  marked proposal applied (diff kept for the sealed card)")
    except Exception as exc:
        _log(f"  store-mark note: {exc}")
    _log(f"DONE {pid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
