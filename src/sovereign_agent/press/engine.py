#!/usr/bin/env python3
"""press.py v0.1 — the Press: manifest-driven build conductor (P0 + lightweight P1).

Ratified plan-of-record baseline, 2026-07-16.
Scope of this version: build / status / topo-sort on depends_on / closed stage
enum / gate chain execution / receipt bundles / byte-parity (reprint) check.
NO model calls, NO adversary, NO extrusion, NO editions in v0.1 — those are
P2/P4, contracts in CONTRACTS_P2_P4.md. Engine code is kernel-clean: stdlib
only, no private paths (all roots come from the manifest or environment),
so Phase 5 is a move, not a rewrite.

Sovereignty invariants (enforced here, not promised):
- The Press never publishes, never seals: it stops at the receipt bundle and
  reports; the human seal is outside this program by construction.
- Reprint builds MUST reproduce the frozen sha or the run fails loud.
- Receipt bundles are append-only: an existing run directory is never reused.
- A volume not in the manifest cannot build (default-deny).

Usage:
  python3 press.py build VOL-01            # one volume
  python3 press.py build S0               # a series (manifest prefix match)
  python3 press.py build S0,S3            # multiple series
  python3 press.py build --all
  python3 press.py status
  python3 press.py selftest               # fixture catalog, no real sources
Environment:
  PRESS_MANIFEST   path to press_manifest.yaml (default: ./press_manifest.yaml)
  PRESS_RUNS_DIR   receipt bundle root (default: ./press_runs)
"""
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time

# ── The closed stage enum (lightweight P1). A stage outside this set fails the
#    build outright — "a stale status ... fails the build outright, rather than
#    shipping as a quiet lie." (UE Ch. 18, gate e)

# ── P4b.1 (reviewer finding D1): ONE declared anchor — every default path resolves from the press
#    file's own location, never the caller's cwd. "A floor that answers differently
#    by cwd" is not a floor. Env overrides always win.
# P5a-S1 anchor generalization: the engine has NO home of its own. PRESS_HOME is where
# manifests/runs/reports live (default: cwd — a node runs the press from its press dir);
# PRESS_DATA_ROOT is where node data (adversary records, helper scripts) lives.
_HERE = os.environ.get("PRESS_HOME") or os.getcwd()
_ROOT = os.environ.get("PRESS_DATA_ROOT") or _HERE


def _env_path(var, default):
    return os.environ.get(var) or default

STAGE_ENUM = {
    "concept-formation",
    "outline-locked",
    "drafting",
    "built-in-review",
    "sealed-publication-ready",
    "sealed-awaiting-author",
    "pre-order",
    "published",
    "shelved",
}

# Stages from which a reprint build is permitted (sealed or shipped states).
REPRINTABLE = {"sealed-publication-ready", "sealed-awaiting-author",
               "pre-order", "published"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── Minimal YAML subset loader (stdlib-only; the manifest sticks to it).
#    Supports: nested maps by 2-space indent, lists of scalars ("- x"),
#    inline lists ("[a, b]"), scalars, comments. Enough for the manifest;
#    swap for pyyaml when the kernel move happens (it is already a dep there).
def load_manifest(path):
    if not os.path.exists(path):
        fail(f"manifest not found: {path} (default-deny: nothing can build)")
    root, stack = {}, [(-1, None)]  # (indent, container)
    stack[0] = (-1, root)
    with open(path, encoding="utf-8") as f:
        for ln, raw in enumerate(f, 1):
            line = raw.rstrip("\n")
            stripped = line.split("#", 1)[0].rstrip() if not line.lstrip().startswith("#") else ""
            if not stripped.strip():
                continue
            indent = len(stripped) - len(stripped.lstrip())
            key_part = stripped.strip()
            while stack and stack[-1][0] >= indent:
                stack.pop()
            container = stack[-1][1]
            if key_part.startswith("- "):
                val = _scalar(key_part[2:].strip())
                if isinstance(container, (_Pending, list)):
                    container.append(val)
                else:
                    fail(f"manifest line {ln}: list item outside a list")
                continue
            if ":" not in key_part:
                fail(f"manifest line {ln}: expected 'key:' — got {key_part!r}")
            key, _, rest = key_part.partition(":")
            key, rest = key.strip(), rest.strip()
            if not isinstance(container, dict):
                fail(f"manifest line {ln}: mapping entry inside a list")
            if rest == "":
                # Container: dict unless next meaningful line is a "- " list —
                # we defer by creating a dict and converting on first list item.
                new = _Pending()
                container[key] = new
                stack.append((indent, new))
            elif rest.startswith("[") and rest.endswith("]"):
                inner = rest[1:-1].strip()
                container[key] = [
                    _scalar(x.strip()) for x in inner.split(",")] if inner else []
            else:
                container[key] = _scalar(rest)
    return _resolve_pending(root)


class _Pending(dict):
    """Dict that converts itself to a list if list items arrive."""
    def append(self, item):
        self.setdefault("__list__", []).append(item)


def _resolve_pending(node):
    if isinstance(node, _Pending):
        if "__list__" in node and len(node) == 1:
            return [_resolve_pending(x) for x in node["__list__"]]
        return {k: _resolve_pending(v) for k, v in node.items() if k != "__list__"}
    if isinstance(node, dict):
        return {k: _resolve_pending(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_pending(x) for x in node]
    return node


def _scalar(tok):
    if tok in ("null", "~", ""):
        return None
    if tok in ("true", "True"):
        return True
    if tok in ("false", "False"):
        return False
    if tok.startswith(("'", '"')) and tok.endswith(("'", '"')) and len(tok) >= 2:
        return tok[1:-1]
    return tok


def fail(msg):
    print(f"PRESS FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


# ── Validation (gate e discipline: loud, precise, no warn-and-continue).
def validate(manifest):
    vols = manifest.get("volumes")
    if not isinstance(vols, dict) or not vols:
        fail("manifest has no volumes: (default-deny holds)")
    for vid, v in vols.items():
        stage = v.get("stage", "")
        base_stage = stage.split("(")[0].strip() if stage else ""
        if base_stage not in STAGE_ENUM:
            fail(f"{vid}: stage {stage!r} not in closed enum "
                 f"{sorted(STAGE_ENUM)} — stale or invented stage fails the build")
        for dep in v.get("depends_on", []) or []:
            if dep.startswith("roadmap:"):
                continue  # event-class dependency, not a volume
            if dep not in vols:
                fail(f"{vid}: depends_on {dep!r} not in manifest — "
                     f"the DAG must resolve against the live record")
        if "PLACEHOLDER" in json.dumps(v):
            fail(f"{vid}: manifest entry contains PLACEHOLDER fields — "
                 f"fill them on the node before building this volume")
    return vols


def toposort(vols, targets):
    order, seen, visiting = [], set(), set()

    def visit(vid):
        if vid in seen:
            return
        if vid in visiting:
            fail(f"dependency cycle at {vid}")
        visiting.add(vid)
        for dep in vols[vid].get("depends_on", []) or []:
            if not dep.startswith("roadmap:") and dep in targets:
                visit(dep)
        visiting.discard(vid)
        seen.add(vid)
        order.append(vid)

    for vid in sorted(targets):
        visit(vid)
    return order


def select_targets(vols, spec):
    if spec == "--all":
        return set(vols)
    out = set()
    for part in spec.split(","):
        part = part.strip()
        if part in vols:
            out.add(part)
        else:
            hits = {vid for vid in vols if vid.startswith(part + "-") or
                    vols[vid].get("series") == part}
            if not hits:
                fail(f"target {part!r} matches nothing in the manifest (default-deny)")
            out |= hits
    return out


def run_step(label, cmd, cwd, log_lines, model=None):
    t0 = time.time()
    proc = subprocess.run(cmd if isinstance(cmd, list) else shlex.split(cmd),
                          cwd=cwd or None, capture_output=True, text=True)
    entry = {
        "step": label,
        "cmd": cmd,
        "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(t0)),
        "exit": proc.returncode,
        "secs": round(time.time() - t0, 2),
        "model": model or "none",  # deterministic stages bind to no model (floor law)
        "stdout_sha": sha256_text(proc.stdout or ""),
        "stderr_tail": (proc.stderr or "")[-2000:],
    }
    log_lines.append(entry)
    if proc.returncode != 0:
        return False
    return True


# ── P3: queue infrastructure — per-transition log, FIFO seal queue, stage locks.
import threading

_QLOCK = threading.Lock()



def _read_jsonl(path):
    """All ndjson reads route through the kernel gateway (§1) when the package is
    importable; standalone script mode falls back to the same tolerant law inline."""
    text = open(path, encoding="utf-8").read()
    try:
        from sovereign_agent.ndjson import parse_ndjson_text  # noqa: PLC0415
        return parse_ndjson_text(text, source=path).entries
    except ImportError:
        out = []
        for _raw in text.splitlines():
            try:
                out.append(json.loads(_raw))
            except ValueError:
                continue
        return out


def _qlog(runs_root, **event):
    """Append-only per-transition queue log (P3 deliverable)."""
    event["ts"] = time.strftime("%Y%m%dT%H%M%S", time.gmtime()) + f".{int(time.time()*1000)%1000:03d}Z"
    with _QLOCK:
        with open(os.path.join(runs_root, "queue_log.jsonl"), "a") as f:
            f.write(json.dumps(event) + "\n")


def _seal_enqueue(runs_root, vid, run_sha):
    """FIFO seal queue — the one gate that never parallelizes and never automates.
    The Press only APPENDS here; sealing is a human act outside this program."""
    with _QLOCK:
        qp = os.path.join(runs_root, "seal_queue.json")
        q = json.load(open(qp)) if os.path.exists(qp) else []
        q.append({"volume": vid, "completed_utc": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
                  "run_sha256": run_sha, "sealed": False,
                  "note": "awaiting the human word — FIFO, serialized, never automated"})
        json.dump(q, open(qp, "w"), indent=2)


def _isolate_lane(vol, lane, runs_root):
    """Per-series isolation for parallel mode: git worktree when the workdir lives
    in a git repo, plain copy otherwise. Returns (new_workdir, isolation_stamp)."""
    import shutil
    wd = vol.get("workdir")
    if not wd:
        return wd, "none"
    top = subprocess.run(["git", "-C", wd, "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    lane_root = os.path.join(runs_root, "lanes", lane)
    if top.returncode == 0:
        repo = top.stdout.strip()
        rel = os.path.relpath(wd, repo)
        wt = os.path.join(lane_root, "worktree")
        if not os.path.isdir(wt):
            r = subprocess.run(["git", "-C", repo, "worktree", "add", "--detach", wt],
                               capture_output=True, text=True)
            if r.returncode != 0:
                return wd, f"worktree-failed({r.stderr.strip()[:60]}) — building in place"
        return os.path.join(wt, rel), "git-worktree"
    dst = os.path.join(lane_root, os.path.basename(wd.rstrip("/")))
    if not os.path.isdir(dst):
        os.makedirs(lane_root, exist_ok=True)
        # Guard (P3.1): if the runs root lives INSIDE the workdir, a naive copy
        # recurses into its own output — skip that subtree instead of overflowing.
        wd_abs, runs_abs = os.path.realpath(wd), os.path.realpath(runs_root)
        skip = ({os.path.relpath(runs_abs, wd_abs).split(os.sep)[0]}
                if runs_abs.startswith(wd_abs + os.sep) else set())

        def _ignore(src, names):
            return skip if os.path.realpath(src) == wd_abs else set()
        shutil.copytree(wd, dst, ignore=_ignore)
    return dst, "copy"


def _adversary_fresh(vid, workdir, freshness_exclude=None):
    """Return None if a fresh PASS seed-adversary record exists for vid, else the
    refusal reason (default-deny). Records live in PRESS_ADVERSARY_DIR (default
    ./artifacts/adversary)/<vid>/*.json per the P2 contract."""
    root = os.path.join(_env_path("PRESS_ADVERSARY_DIR", os.path.join(_ROOT, "artifacts", "adversary")), vid)
    recs = sorted(
        (os.path.join(root, f) for f in (os.listdir(root) if os.path.isdir(root) else [])
         if f.endswith(".json")), key=os.path.getmtime)
    passing = [p for p in recs if json.load(open(p)).get("result") == "PASS"]
    if not passing:
        return f"no PASS adversary record for {vid} under {root} (P2 default-deny)"
    newest_rec = os.path.getmtime(passing[-1])
    import fnmatch
    excl = freshness_exclude or []
    newest_src = 0.0
    if workdir and os.path.isdir(workdir):
        for dirpath, _, files in os.walk(workdir):
            for f in files:
                if not f.endswith((".md", ".yaml")):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, f), workdir)
                # generated outputs are projections, not prose — declared, never guessed
                if any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(f, g) for g in excl):
                    continue
                newest_src = max(newest_src, os.path.getmtime(os.path.join(dirpath, f)))
    if newest_src > newest_rec:
        return (f"adversary record for {vid} is STALE (prose newer than record) — "
                f"rerun seed_adversary (P2 default-deny)")
    return None


def build_volume(vid, vol, runs_root, mode_note):
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    uniq = os.urandom(2).hex()
    bundle = os.path.join(runs_root, f"{ts}_{uniq}_{vid}")
    if os.path.exists(bundle):
        fail(f"receipt bundle already exists: {bundle} (append-only law)")
    os.makedirs(bundle)
    steps, ok = [], True
    cwd = vol.get("workdir")

    # Reprint safety (v0.1.1, P0 parity-run finding): a reprint must never
    # leave a sealed final/ altered on parity failure. Snapshot the artifact
    # bytes before building; restore them if parity fails; always copy the
    # rebuilt artifact into the receipt bundle for inspection.
    sealed_bytes = None  # {path: bytes} snapshot of the artifact's whole dir
    _art = vol.get("artifact")
    _apath = (os.path.join(cwd, _art) if cwd and _art and not os.path.isabs(_art)
              else _art)
    if mode_note == "reprint" and _apath and os.path.exists(_apath):
        _fdir = os.path.dirname(_apath)
        sealed_bytes = {}
        for name in os.listdir(_fdir):
            p = os.path.join(_fdir, name)
            if os.path.isfile(p):
                with open(p, "rb") as f:
                    sealed_bytes[p] = f.read()

    gen = vol.get("generator")
    if ok and gen:
        # P2 default-deny (contract): a generator step REQUIRES a fresh PASS
        # adversary record — no fresh record => no generation. "Fresh" v0.1:
        # newest PASS record is newer than the newest prose source in workdir.
        adv_reason = _adversary_fresh(vid, cwd, vol.get('freshness_exclude'))
        steps.append({"step": "adversary_gate", "cmd": "(internal default-deny check)",
                      "exit": 0 if adv_reason is None else 1, "secs": 0,
                      "stdout_sha": sha256_text(adv_reason or "fresh PASS record"),
                      "stderr_tail": adv_reason or ""})
        if adv_reason is not None:
            ok = False
    if ok and gen:
        ok = run_step("generator", gen, cwd, steps)
    if ok and vol.get("build"):
        ok = run_step("build", vol["build"], cwd, steps)
    for gate in (vol.get("gates") or []):
        if not ok:
            break
        ok = run_step(f"gate:{gate}", gate, cwd, steps)

    parity = None
    frozen = vol.get("freeze_sha")
    artifact = vol.get("artifact")
    if ok and artifact:
        apath = os.path.join(cwd, artifact) if cwd and not os.path.isabs(artifact) else artifact
        if not os.path.exists(apath):
            ok, parity = False, {"error": f"artifact not found: {apath}"}
        else:
            actual = sha256_file(apath)
            parity = {"artifact": artifact, "sha256": actual}
            if frozen:
                parity["frozen_sha"] = frozen
                parity["byte_parity"] = actual.startswith(frozen) or actual == frozen
                if not parity["byte_parity"]:
                    ok = False  # reprint MUST reproduce the frozen sha — fail loud
            # Preserve the rebuilt artifact in the bundle either way (evidence),
            # then restore sealed bytes to final/ if this reprint failed parity.
            try:
                with open(apath, "rb") as f:
                    rebuilt = f.read()
                with open(os.path.join(bundle, os.path.basename(apath)), "wb") as f:
                    f.write(rebuilt)
            except OSError as e:
                parity["bundle_copy_error"] = str(e)
            if sealed_bytes is not None and parity.get("byte_parity") is False:
                for p, data in sealed_bytes.items():
                    with open(p, "wb") as f:
                        f.write(data)
                parity["final_restored"] = True  # entire final/ dir restored

    run = {
        "press_version": "0.1.1",
        "volume": vid,
        "stage": vol.get("stage"),
        "mode": mode_note,
        "started_utc": ts,
        "steps": steps,
        "parity": parity,
        "result": "PASS" if ok else "FAIL",
        "note": "The Press stops here. Sealing and publishing are human acts "
                "outside this program by construction.",
    }
    payload = json.dumps(run, indent=2, sort_keys=True)
    run["run_sha256"] = sha256_text(payload)
    with open(os.path.join(bundle, "run.json"), "w") as f:
        json.dump(run, f, indent=2, sort_keys=True)
    print(f"[{run['result']}] {vid} → {bundle}  run_sha={run['run_sha256'][:16]}")
    return ok


def _build_one(vid, vols, runs_root, qmode, lane=None, stage_locks=None, isolate=False):
    vol = dict(vols[vid])
    iso = "none"
    if isolate:
        vol["workdir"], iso = _isolate_lane(vol, lane or vol.get("series") or vid, runs_root)
    base_stage = (vol.get("stage") or "").split("(")[0].strip()
    bmode = "reprint" if (vol.get("freeze_sha") and base_stage in REPRINTABLE) else "new-edition"
    _qlog(runs_root, vid=vid, lane=lane, stage="volume", event="start",
          qmode=qmode, isolation=iso)
    if stage_locks is not None:
        # double mode law: never two volumes in the same gate — one lock per stage class
        def guarded(label, fn):
            with stage_locks.setdefault(label, threading.Lock()):
                _qlog(runs_root, vid=vid, lane=lane, stage=label, event="enter", qmode=qmode)
                r = fn()
                _qlog(runs_root, vid=vid, lane=lane, stage=label, event="exit", qmode=qmode)
                return r
        ok = guarded("build+gates", lambda: build_volume(vid, vol, runs_root, bmode))
    else:
        _qlog(runs_root, vid=vid, lane=lane, stage="build+gates", event="enter", qmode=qmode)
        ok = build_volume(vid, vol, runs_root, bmode)
        _qlog(runs_root, vid=vid, lane=lane, stage="build+gates", event="exit", qmode=qmode)
    _qlog(runs_root, vid=vid, lane=lane, stage="volume", event="pass" if ok else "fail", qmode=qmode)
    if ok:
        _seal_enqueue(runs_root, vid, "(see bundle run.json)")
    return ok


def cmd_build(spec, qmode="single", approve_wave=None):
    manifest = load_manifest(_env_path("PRESS_MANIFEST", os.path.join(_HERE, "press_manifest.yaml")))
    vols = validate(manifest)
    targets = select_targets(vols, spec)
    order = toposort(vols, targets)
    runs_root = _env_path("PRESS_RUNS_DIR", os.path.join(_HERE, "press_runs"))
    os.makedirs(runs_root, exist_ok=True)
    print(f"press build [{qmode}] — {len(order)} volume(s), order: {' → '.join(order)}")

    if qmode == "single":
        for vid in order:
            if not _build_one(vid, vols, runs_root, qmode):
                fail(f"{vid} failed — halting the run (no silent continuation)")
        print("press build complete — all volumes PASS · seal queue awaits the human word")
        return 0

    from concurrent.futures import ThreadPoolExecutor

    if qmode == "double":
        # Two slots, never two volumes in the same stage (stage locks), FIFO seal queue.
        locks, results = {}, {}
        with ThreadPoolExecutor(max_workers=2) as ex:
            futs = {ex.submit(_build_one, vid, vols, runs_root, qmode, None, locks): vid
                    for vid in order}
            for f in futs:
                results[futs[f]] = f.result()
        if not all(results.values()):
            fail(f"double-mode failures: {[v for v, ok in results.items() if not ok]}")
        print("press build complete [double] — all volumes PASS · seal queue FIFO")
        return 0

    if qmode == "parallel":
        # The wave model, machine-enforced: the Press PROPOSES; the human click-through
        # opens the wave (K1). Lanes = series; within a lane volumes stay sequential
        # (DAG/promise-chain law); lanes isolate (worktree/copy); width cap 3.
        lanes = {}
        for vid in order:
            lanes.setdefault(vols[vid].get("series") or vid, []).append(vid)
        wave = ",".join(sorted(lanes))
        if approve_wave is None:
            print(f"WAVE PROPOSAL (parallel): lanes = {wave} — width {len(lanes)}")
            print("The Press does not open waves. Re-run with:")
            print(f"  press.py build {spec} --mode parallel --approve-wave {wave}")
            return 3  # awaiting the human word
        if approve_wave != wave:
            fail(f"wave approval {approve_wave!r} does not match proposal {wave!r} — "
                 "the approved wave must be exactly the proposed wave (K1)")
        if len(lanes) > 3:
            fail(f"wave width {len(lanes)} exceeds the ratified cap (3)")
        _qlog(runs_root, stage="wave", event="opened_by_human", wave=wave, qmode=qmode)

        def run_lane(lane, vids):
            for vid in vids:
                if not _build_one(vid, vols, runs_root, qmode, lane, None, isolate=True):
                    return False
            return True

        with ThreadPoolExecutor(max_workers=len(lanes)) as ex:
            futs = {ex.submit(run_lane, ln, vids): ln for ln, vids in lanes.items()}
            results = {futs[f]: f.result() for f in futs}
        if not all(results.values()):
            fail(f"parallel-mode lane failures: {[l for l, ok in results.items() if not ok]}")
        print(f"press build complete [parallel wave {wave}] — all lanes PASS · "
              "seal queue FIFO, serialized, human-only")
        return 0

    fail(f"unknown queue mode {qmode!r}")


def cmd_cycle(vol_id, seeds_dir):
    """P3: one full chapter cycle — adversary → (draft-fix on the local host) → re-verify —
    zero frontier calls by construction (every model order resolves through the
    local_30b tier; no api/frontier endpoint exists in this code path). Orders are
    batched by model per the single-GPU law; receipts stamp model per transition."""
    import shutil
    tiers = load_manifest(_env_path("PRESS_MODEL_TIERS", os.path.join(_HERE, "model_tiers.yaml")))
    prose_model = tiers["tiers"]["local_30b"]["prose_model"]
    adv_cmd = _env_path("PRESS_ADVERSARY_CMD", f"{sys.executable} -m sovereign_agent.press.adversary")
    fix_cmd = _env_path("PRESS_SEEDFIX_CMD", f"{sys.executable} -m sovereign_agent.press.fixer")
    adv_dir = _env_path("PRESS_ADVERSARY_DIR", os.path.join(_ROOT, "artifacts", "adversary"))
    runs_root = _env_path("PRESS_RUNS_DIR", os.path.join(_HERE, "press_runs"))
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    bundle = os.path.join(runs_root, f"{ts}_cycle_{vol_id}")
    os.makedirs(os.path.join(bundle, "seeds"))
    for f in os.listdir(seeds_dir):
        shutil.copy(os.path.join(seeds_dir, f), os.path.join(bundle, "seeds", f))
    work_seeds = os.path.join(bundle, "seeds")

    # Batch plan (single-GPU law): all model orders this cycle resolve to ONE
    # resident model — grouped up front, no model swaps mid-cycle.
    batch_plan = [{"model": prose_model, "orders": ["adversary_L1", "draft_fix?"],
                   "note": "single resident model; no swap mid-cycle"}]
    steps = []

    def newest_record():
        d = os.path.join(adv_dir, vol_id)
        recs = sorted(os.listdir(d)) if os.path.isdir(d) else []
        return os.path.join(d, recs[-1]) if recs else None

    def adversary(level):
        label = f"adversary_{level}"
        model = prose_model if level == "L1" else None
        ok = run_step(label, f"{adv_cmd} {vol_id} --level {level} --seeds {work_seeds}",
                      None, steps, model=model)
        _qlog(runs_root, vid=vol_id, stage=label, event="pass" if ok else "kill",
              model=model or "none", qmode="cycle")
        return ok

    def fix_round():
        rec = newest_record()
        card = next(os.path.join(work_seeds, f) for f in sorted(os.listdir(work_seeds))
                    if f.endswith(".yaml") and not f.endswith("_fixed.yaml"))
        ok = run_step("draft_fix", f"{fix_cmd} {card} {rec} --out {work_seeds}",
                      None, steps, model=prose_model)
        _qlog(runs_root, vid=vol_id, stage="draft_fix", event="done" if ok else "fail",
              model=prose_model, qmode="cycle")
        if ok:  # the fixed card replaces the killed one in the work set
            os.replace(card + "", os.path.join(work_seeds, "_retired_" + os.path.basename(card) + ".orig"))
            fixed = card[:-5] + "_fixed.yaml"
            os.replace(fixed, card)
        return ok

    result = "KILL"
    for level in ("L0", "L1"):
        passed = adversary(level)
        if not passed:
            if not fix_round() or not adversary(level):
                break
    else:
        result = "PASS"

    cycle = {"volume": vol_id, "cycle": "seed→adversary→fix→re-verify",
             "batch_plan": batch_plan, "steps": steps, "result": result,
             "zero_frontier": True,
             "note": "all model orders resolved via local_30b tier (local host); the human "
                     "seal remains outside this program — a PASS only queues, never ships"}
    payload = json.dumps(cycle, indent=2, sort_keys=True)
    cycle["cycle_sha256"] = sha256_text(payload)
    with open(os.path.join(bundle, "cycle.json"), "w") as f:
        json.dump(cycle, f, indent=2, sort_keys=True)
    print(f"[{result}] cycle {vol_id} → {bundle}  cycle_sha={cycle['cycle_sha256'][:16]}")
    return 0 if result == "PASS" else 1


# ── P4b: the Provisional/Hardened code lane (LOCKED design v1.0, operator rulings baked).
#    code_status: built|provisional|sealed — books' stage enum untouched.
#    Promotion ALWAYS human (exit-3 proposal → --approve-report <report-sha>).
#    Demotion NEVER waits for one (fail-closed, receipted reopen).

def _code_status_store():
    p = _env_path("PRESS_CODE_STATUS", os.path.join(_HERE, "code_status.json"))
    return p, (json.load(open(p)) if os.path.exists(p) else {})


def _code_status_write(p, store, vid, new, reason, by, approval=None):
    ent = store.setdefault(vid, {"status": "built", "history": []})
    ent["history"].append({"ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
                           "from": ent["status"], "to": new, "reason": reason, "by": by,
                           **({"approval_id": approval} if approval else {})})
    ent["status"] = new
    if approval:
        ent["approval_id"] = approval
    json.dump(store, open(p, "w"), indent=2)


def _posture_lint(code_file):
    """Deterministic K2/K3/K4 posture heuristics (v0.1, labeled honest):
    a refusal path must exist and be receipted (fail-closed, K2/K1); receipts must
    be appended (K3); no dynamic self-extension via exec/eval (K4)."""
    if not code_file or not os.path.isfile(code_file):
        return f"posture FAIL: code_file missing: {code_file}"
    s = open(code_file, encoding="utf-8").read()
    probs = []
    if "raise" not in s:
        probs.append("no refusal path (K2 fail-closed)")
    if "receipt" not in s.lower():
        probs.append("no receipt evidence (K3)")
    if "exec(" in s or "eval(" in s:
        probs.append("dynamic self-extension present (K4)")
    return ("posture FAIL: " + "; ".join(probs)) if probs else None


def _latest_report_sha(reports_dir):
    """sha256 of each report file, newest first — approval must cite one."""
    out = {}
    rd = reports_dir
    if os.path.isdir(rd):
        for f in os.listdir(rd):
            p = os.path.join(rd, f)
            if f.endswith(".md") and os.path.isfile(p):
                out[hashlib.sha256(open(p, "rb").read()).hexdigest()] = f
    return out


import hashlib


def cmd_harden(target, approve_report=None):
    manifest = load_manifest(_env_path("PRESS_MANIFEST", os.path.join(_HERE, "press_manifest.yaml")))
    hsec = manifest.get("harden") or {}
    if target not in hsec:
        fail(f"{target} has no harden entry (default-deny: nothing to promote)")
    h = hsec[target]
    runs_root = _env_path("PRESS_RUNS_DIR", os.path.join(_HERE, "press_runs"))
    os.makedirs(runs_root, exist_ok=True)
    sp, store = _code_status_store()
    current = store.get(target, {}).get("status", "built")

    # THE HARDENING FLOOR — every check must pass; gates never relax.
    steps, ok = [], True
    for chk in (h.get("checks") or []):
        if ok:
            ok = run_step(f"floor:{chk[:60]}", chk, h.get("workdir"), steps)
    posture = _posture_lint(h.get("code_file"))
    steps.append({"step": "floor:posture(K2/K3/K4 v0.1 heuristics)", "cmd": "(builtin)",
                  "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
                  "exit": 1 if posture else 0, "secs": 0, "model": "none",
                  "stdout_sha": sha256_text(posture or "posture OK"),
                  "stderr_tail": posture or ""})
    if posture:
        ok = False
    adv_vol = h.get("adversary_vol")
    if adv_vol:
        reason = _adversary_fresh(adv_vol, h.get("workdir"), h.get("freshness_exclude"))
        steps.append({"step": "floor:adversary_fresh", "cmd": "(builtin)",
                      "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
                      "exit": 1 if reason else 0, "secs": 0, "model": "none",
                      "stdout_sha": sha256_text(reason or "fresh PASS record"),
                      "stderr_tail": reason or ""})
        if reason:
            ok = False

    bundle = os.path.join(runs_root, f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
                                     f"_{os.urandom(2).hex()}_harden_{target}")
    os.makedirs(bundle)
    rec = {"volume": target, "kind": "harden", "floor": steps,
           "floor_pass": ok, "code_status_before": current}

    if not ok and current == "provisional":
        # AUTO-DEMOTION (operator ruling: demotion is ungated): fail-closed, receipted reopen, no gate needed.
        _code_status_write(sp, store, target, "built",
                           "hardening finding — automatic demotion (fail-closed)",
                           "press harden (auto)")
        rec["action"] = "AUTO-DEMOTED provisional → built (reopen receipted)"
        _qlog(runs_root, vid=target, stage="code_status", event="reopen_demotion", qmode="harden")
    elif not ok:
        rec["action"] = f"floor FAILED — {target} stays {current}"
    elif approve_report:
        shas = _latest_report_sha(_env_path("PRESS_REPORTS_DIR", os.path.join(_HERE, "reports")))
        full = next((s for s in shas if s.startswith(approve_report)), None)
        if not full:
            fail(f"--approve-report {approve_report!r} matches no report on file — "
                 "the human word must cite a real report (K1)")
        _code_status_write(sp, store, target, "provisional",
                           f"the operator's series-level approval citing report {shas[full]}",
                           "the human word", approval=f"approve-report:{full[:16]}")
        rec["action"] = f"PROMOTED built → provisional (approval {full[:16]}, report {shas[full]})"
        _qlog(runs_root, vid=target, stage="code_status", event="promoted_by_human", qmode="harden")
    else:
        rec["action"] = ("floor PASS — PROMOTION PROPOSAL staged; the Press does not promote. "
                         "Re-run with --approve-report <report-sha> after reviewing the "
                         "Series Status Report.")
    payload = json.dumps(rec, indent=2, sort_keys=True)
    rec["record_sha256"] = sha256_text(payload)
    json.dump(rec, open(os.path.join(bundle, "harden.json"), "w"), indent=2, sort_keys=True)
    print(f"[{'PASS' if ok else 'FAIL'}] harden {target} — {rec['action']}")
    print(f"  bundle: {bundle}")
    if ok and not approve_report:
        return 3  # awaiting the human word
    return 0 if ok else 1



# ── P5a-S2 (D3): OFFLINE RECOVERY — the Book Source Bundle + --offline builds.
#    LOCKED design DESIGN_OFFLINE_RECOVERY v1.0: a volume's bundle/ dir (inside its own
#    tree — git is the offline distribution channel, operator ruling) carries everything a
#    node needs to rebuild WITHOUT network: sources, manifest entry, pinned env record,
#    shas. --offline rebuilds from the bundle ONLY (default-deny on anything missing).

def _bundle_dir(vol):
    wd = vol.get("workdir")
    if not wd:
        fail("bundle requires a workdir (the bundle lives inside the volume's own tree)")
    return os.path.join(wd, "bundle")


def cmd_bundle(target):
    import shutil
    manifest = load_manifest(_env_path("PRESS_MANIFEST", os.path.join(_HERE, "press_manifest.yaml")))
    vols = validate(manifest)
    if target not in vols:
        fail(f"{target} not in manifest (default-deny)")
    vol = vols[target]
    bdir = _bundle_dir(vol)
    wd = vol["workdir"]
    if os.path.isdir(bdir):
        shutil.rmtree(bdir)  # a bundle is a projection of the tree — regenerate, never merge
    srcs = os.path.join(bdir, "sources")
    os.makedirs(srcs)
    shas = {}
    for dirpath, dirs, files in os.walk(wd):
        dirs[:] = [d for d in dirs if d not in ("bundle", "final", "__pycache__", "press_runs")]
        for f in files:
            fp = os.path.join(dirpath, f)
            rel = os.path.relpath(fp, wd)
            dst = os.path.join(srcs, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(fp, dst)
            shas[rel] = sha256_file(fp)
    env_rec = {"python": sys.version.split()[0]}
    try:
        import weasyprint  # noqa: PLC0415
        env_rec["weasyprint"] = weasyprint.__version__
    except Exception:
        env_rec["weasyprint"] = "not-installed"
    epoch = None
    for tok in shlex.split(vol.get("build") or ""):
        if tok.startswith("SOURCE_DATE_EPOCH="):
            epoch = tok.split("=", 1)[1]
    meta = {"volume": target, "manifest_entry": vol, "source_shas": shas,
            "env_manifest": {**env_rec, "SOURCE_DATE_EPOCH": epoch},
            "frozen_sha": vol.get("freeze_sha"),
            "bundled_utc": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
            "law": "rebuildable from this bundle alone; git carries it; nothing here seals"}
    with open(os.path.join(bdir, "bundle.json"), "w") as f:
        json.dump(meta, f, indent=2, sort_keys=True)
    print(f"[bundled] {target} → {bdir}  ({len(shas)} source files, env pinned)")
    return 0


def cmd_build_offline(target):
    """Rebuild from the bundle ONLY: sources restored to an offline workdir; anything
    absent from the bundle fails loud (K2). Receipts stamp mode: offline. Parity law
    unchanged — the pinned env makes byte-parity achievable."""
    import shutil
    manifest = load_manifest(_env_path("PRESS_MANIFEST", os.path.join(_HERE, "press_manifest.yaml")))
    vols = validate(manifest)
    if target not in vols:
        fail(f"{target} not in manifest (default-deny)")
    vol = dict(vols[target])
    bdir = _bundle_dir(vol)
    bj = os.path.join(bdir, "bundle.json")
    if not os.path.isfile(bj):
        fail(f"{target} has NO bundle at {bdir} — offline rebuild is default-deny without one "
             "(run: press bundle {0})".format(target))
    meta = json.load(open(bj))
    runs_root = _env_path("PRESS_RUNS_DIR", os.path.join(_HERE, "press_runs"))
    work = os.path.join(runs_root, "offline_work", target)
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work)
    for rel, expect in meta["source_shas"].items():
        src = os.path.join(bdir, "sources", rel)
        if not os.path.isfile(src):
            fail(f"bundle incomplete: {rel} missing — offline build refuses (K2)")
        if sha256_file(src) != expect:
            fail(f"bundle tampered: {rel} sha mismatch — offline build refuses loud")
        dst = os.path.join(work, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    vol["workdir"] = work
    _qlog(runs_root, vid=target, stage="volume", event="offline_rebuild_from_bundle",
          qmode="offline", bundle=bdir)
    base_stage = (vol.get("stage") or "").split("(")[0].strip()
    bmode = "reprint" if (vol.get("freeze_sha") and base_stage in REPRINTABLE) else "new-edition"
    ok = build_volume(target, vol, runs_root, f"offline-{bmode}")
    print(("[PASS]" if ok else "[FAIL]") + f" offline rebuild of {target} from bundle only")
    return 0 if ok else 1


def cmd_status():
    manifest = load_manifest(_env_path("PRESS_MANIFEST", os.path.join(_HERE, "press_manifest.yaml")))
    vols = validate(manifest)
    print(f"{'VOLUME':12} {'STAGE':28} {'FROZEN SHA':18} DEPENDS_ON")
    for vid in sorted(vols):
        v = vols[vid]
        deps = ",".join(v.get("depends_on", []) or []) or "—"
        print(f"{vid:12} {v.get('stage', '—'):28} "
              f"{(v.get('freeze_sha') or '—')[:16]:18} {deps}")
    print("\nstatus is a projection of the manifest — never a guess. "
          "RUNS TODAY: build/status/parity. DESIGNED-TOWARD: adversary (P2), "
          "extrusion+editions (P4), kernel module (P5).")
    return 0


def cmd_selftest():
    """Fixture catalog: proves conductor, DAG, gates, parity, receipts —
    with zero real sources. Run anywhere."""
    with tempfile.TemporaryDirectory() as td:
        art_a, art_b = os.path.join(td, "a.txt"), os.path.join(td, "b.txt")
        manifest = f"""
volumes:
  FIX-01:
    series: FIX
    stage: sealed-publication-ready
    build: sh -c "printf 'alpha' > {art_a}"
    gates:
      - sh -c "test -s {art_a}"
    artifact: {art_a}
    freeze_sha: {sha256_text('alpha')}
  FIX-02:
    series: FIX
    stage: built-in-review
    depends_on: [FIX-01]
    build: sh -c "printf 'beta' > {art_b}"
    gates:
      - sh -c "test -s {art_b}"
    artifact: {art_b}
"""
        mpath = os.path.join(td, "press_manifest.yaml")
        open(mpath, "w").write(manifest)
        os.environ["PRESS_MANIFEST"] = mpath
        os.environ["PRESS_RUNS_DIR"] = os.path.join(td, "press_runs")
        rc = cmd_build("--all")

        # P2 wiring proof: a generator volume is REFUSED without a fresh PASS
        # adversary record, and builds once one exists (default-deny, both ways).
        os.environ["PRESS_ADVERSARY_DIR"] = os.path.join(td, "adversary")
        art_c = os.path.join(td, "c.txt")
        gen_manifest = manifest + f"""  FIX-03:
    series: FIX
    stage: drafting
    workdir: {td}
    generator: sh -c "printf 'gen' > {art_c}"
    build: sh -c "test -s {art_c}"
    artifact: {art_c}
"""
        open(mpath, "w").write(gen_manifest)
        denied = False
        try:
            cmd_build("FIX-03")
        except SystemExit as e:
            denied = bool(e.code)
        if not denied:
            print("selftest: GENERATOR RAN WITHOUT ADVERSARY RECORD — defect", file=sys.stderr)
            return 1
        print("selftest: generator refused without adversary record (default-deny) ✔")
        advdir = os.path.join(td, "adversary", "FIX-03")
        os.makedirs(advdir)
        with open(os.path.join(advdir, "rec_L0.json"), "w") as f:
            json.dump({"volume": "FIX-03", "level": "L0", "result": "PASS"}, f)
        if cmd_build("FIX-03") != 0:
            print("selftest: FRESH PASS RECORD DID NOT UNLOCK GENERATOR — defect", file=sys.stderr)
            return 1
        print("selftest: fresh PASS record unlocked the generator ✔")
        os.environ.pop("PRESS_ADVERSARY_DIR", None)
        open(mpath, "w").write(manifest)

        # ── P3 queue-mode proofs on two-series fixtures (sleepy builds → measurable overlap)
        def qmanifest(base):
            out = ["volumes:"]
            for series, n in (("FIXA", 2), ("FIXB", 1)):
                src = os.path.join(base, f"src_{series}")
                os.makedirs(src, exist_ok=True)
                open(os.path.join(src, "seed.md"), "w").write(f"{series} source\n")
                for i in range(1, n + 1):
                    out += [f"  {series}-0{i}:", f"    series: {series}", "    stage: drafting",
                            f"    workdir: {src}",
                            f"    build: sh -c \"sleep 0.4; printf {series}{i} > out{i}.txt\"",
                            f"    gates:", f"      - sh -c \"test -s out{i}.txt\"",
                            f"    artifact: out{i}.txt"]
                    if i == 2:
                        out.insert(-4, f"    depends_on: [{series}-01]")
            return "\n".join(out) + "\n"

        def read_qlog(root):
            return _read_jsonl(os.path.join(root, "queue_log.jsonl"))

        def intervals(evts, stage):
            spans, opened = {}, {}
            for e in evts:
                if e.get("stage") == stage and e.get("event") == "enter":
                    opened[e["vid"]] = e["ts"]
                if e.get("stage") == stage and e.get("event") == "exit":
                    spans[e["vid"]] = (opened[e["vid"]], e["ts"])
            return spans

        for mode_n in ("single", "double", "parallel"):
            qd = os.path.join(td, f"q_{mode_n}")
            os.makedirs(qd)
            open(mpath, "w").write(qmanifest(qd))
            os.environ["PRESS_RUNS_DIR"] = qd
            if mode_n == "parallel":
                rc3 = cmd_build("--all", qmode="parallel")            # no approval
                if rc3 != 3:
                    print("selftest: PARALLEL RAN WITHOUT WAVE APPROVAL — defect", file=sys.stderr)
                    return 1
                print("selftest: parallel refused without wave approval (K1) ✔")
                if cmd_build("--all", qmode="parallel", approve_wave="FIXA,FIXB") != 0:
                    print("selftest: approved wave failed — defect", file=sys.stderr)
                    return 1
                evts = read_qlog(qd)
                sp = intervals(evts, "build+gates")
                a_ivals = [v for k, v in sp.items() if k.startswith("FIXA")]
                b_ivals = [v for k, v in sp.items() if k.startswith("FIXB")]
                lane_overlap = any(a[0] < b[1] and b[0] < a[1] for a in a_ivals for b in b_ivals)
                if not lane_overlap:
                    print("selftest: PARALLEL LANES NEVER OVERLAPPED — defect", file=sys.stderr)
                    return 1
                iso = {e.get("isolation") for e in evts if e.get("event") == "start" and e.get("stage") == "volume"}
                print(f"selftest: parallel lanes overlapped w/ isolation {sorted(iso - {None})} ✔")
            else:
                if cmd_build("--all", qmode=mode_n) != 0:
                    print(f"selftest: {mode_n} mode failed — defect", file=sys.stderr)
                    return 1
                sp = intervals(read_qlog(qd), "build+gates")
                pairs = list(sp.values())
                overlap = any(x is not y and x[0] < y[1] and y[0] < x[1] for x in pairs for y in pairs)
                if overlap and mode_n == "double":
                    print("selftest: DOUBLE MODE HAD TWO VOLUMES IN THE SAME STAGE — defect",
                          file=sys.stderr)
                    return 1
                print(f"selftest: {mode_n} mode — no same-stage overlap, FIFO seal queue ✔")
            q = json.load(open(os.path.join(qd, "seal_queue.json")))
            if len(q) != 3 or any(e["sealed"] for e in q):
                print("selftest: SEAL QUEUE WRONG (must hold 3 unsealed, FIFO) — defect",
                      file=sys.stderr)
                return 1
        print("selftest: seal queue held 3 unsealed volumes in all modes — human word only ✔")

        # ── P4b lifecycle proofs: floor → proposal → human approval → auto-demotion.
        hd = os.path.join(td, "harden")
        os.makedirs(hd)
        code_p = os.path.join(hd, "gate.py")
        open(code_p, "w").write("def f():\n    raise ValueError('refused')  # receipt appended\n")
        chk = os.path.join(hd, "ok.flag")
        open(chk, "w").write("ok")
        hman = manifest + f"""harden:
  FIXH-01:
    code_file: {code_p}
    checks:
      - sh -c "test -s {chk}"
"""
        open(mpath, "w").write(hman)
        os.environ["PRESS_CODE_STATUS"] = os.path.join(td, "code_status.json")
        os.environ["PRESS_REPORTS_DIR"] = os.path.join(td, "reports")
        os.makedirs(os.environ["PRESS_REPORTS_DIR"])
        rep = os.path.join(os.environ["PRESS_REPORTS_DIR"], "FIXH_report.md")
        open(rep, "w").write("# fixture series report\nPROPOSED: FIXH-01\n")
        rep_sha = hashlib.sha256(open(rep, "rb").read()).hexdigest()
        if cmd_harden("FIXH-01") != 3:
            print("selftest: FLOOR PASS DID NOT STAGE A PROPOSAL (exit 3) — defect", file=sys.stderr)
            return 1
        print("selftest: harden floor PASS staged a proposal — the Press did not promote ✔")
        try:
            cmd_harden("FIXH-01", approve_report="deadbeef")
            print("selftest: BOGUS REPORT SHA ACCEPTED — defect", file=sys.stderr)
            return 1
        except SystemExit as e:
            if not e.code:
                print("selftest: bogus approval exited 0 — defect", file=sys.stderr)
                return 1
        print("selftest: approval citing a nonexistent report refused (K1) ✔")
        if cmd_harden("FIXH-01", approve_report=rep_sha[:16]) != 0:
            print("selftest: VALID APPROVAL FAILED — defect", file=sys.stderr)
            return 1
        cs = json.load(open(os.environ["PRESS_CODE_STATUS"]))
        if cs["FIXH-01"]["status"] != "provisional":
            print("selftest: PROMOTION DID NOT LAND — defect", file=sys.stderr)
            return 1
        print("selftest: human word promoted built → provisional, approval recorded ✔")
        os.remove(chk)  # break the floor
        rc_dem = cmd_harden("FIXH-01")
        cs = json.load(open(os.environ["PRESS_CODE_STATUS"]))
        ent = cs["FIXH-01"]
        if rc_dem == 0 or ent["status"] != "built" or \
                not any("demotion" in h.get("reason", "") for h in ent["history"]):
            print("selftest: AUTO-DEMOTION DID NOT FIRE — defect", file=sys.stderr)
            return 1
        print("selftest: hardening finding auto-demoted provisional → built (reopen receipted) ✔")
        os.environ.pop("PRESS_CODE_STATUS", None)
        os.environ.pop("PRESS_REPORTS_DIR", None)

        # Data-dependent proofs (real volume + real roadmap) run only where node data
        # exists — the kernel fixture suite is self-contained; the node harness runs ALL.
        # consult the NODE's real manifest at PRESS_HOME directly — the selftest itself
        # overrides PRESS_MANIFEST for its fixtures, so the env var is the wrong witness here
        _node_vol = os.environ.get("PRESS_SELFTEST_NODE_VOL", "")
        _mani_real = os.path.join(_HERE, "press_manifest.yaml")
        if not (_node_vol and os.path.exists(_mani_real) and _node_vol in open(_mani_real).read()):
            print("selftest: node-data proofs NOT RUN (no node manifest here) — "
                  "fixture proofs above are the kernel suite; the node harness runs the full set")
            open(mpath, "w").write(manifest)
            os.environ["PRESS_RUNS_DIR"] = os.path.join(td, "press_runs")
            return _finish_selftest(td, mpath, manifest, rc)
        # ── P4b.1 (reviewer spec): CWD-INVARIANCE — one real floor check from BOTH cwds,
        #    DEFAULT env (no PRESS_* except a tmp runs dir), verdicts MUST match.
        # post-flip invariant: same verdict from ANY cwd given the same PRESS_HOME anchor
        env = {k: v for k, v in os.environ.items()
               if not k.startswith("PRESS_") or k in ("PRESS_HOME", "PRESS_DATA_ROOT")}
        env.setdefault("PRESS_HOME", _HERE)
        env.setdefault("PRESS_DATA_ROOT", _ROOT)
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))), env.get("PYTHONPATH")]))
        env["PRESS_RUNS_DIR"] = os.path.join(td, "cwd_runs")
        env["PRESS_CODE_STATUS"] = os.path.join(td, "cwd_cs.json")
        press_path = os.path.abspath(__file__)
        verdicts = []
        for wd in (_HERE, "/"):  # the press home and an unrelated root
            r = subprocess.run([sys.executable, press_path, "harden", _node_vol],
                               cwd=wd, env=env, capture_output=True, text=True)
            verdicts.append(r.returncode)
        if verdicts[0] != verdicts[1]:
            print(f"selftest: CWD-VARIANT FLOOR (rc {verdicts[0]} vs {verdicts[1]}) — defect",
                  file=sys.stderr)
            return 1
        print(f"selftest: same floor verdict (rc={verdicts[0]}) from PRESS_HOME AND / — cwd-invariant ✔")
        # D2 regression: report accepts S-prefixed ids and refuses junk gracefully.
        r_ok = subprocess.run([sys.executable, press_path, "report", "S2"],
                              cwd="/", env=env, capture_output=True, text=True)
        r_bad = subprocess.run([sys.executable, press_path, "report", "SX"],
                               cwd="/", env=env, capture_output=True, text=True)
        if r_ok.returncode != 0 or "Traceback" in (r_ok.stderr + r_bad.stderr) or r_bad.returncode == 0:
            print("selftest: REPORT WIRING (S2 must pass; SX must refuse gracefully) — defect",
                  file=sys.stderr)
            return 1
        print("selftest: report S2 works from any cwd; junk id refused without traceback ✔")

        return _finish_selftest(td, mpath, manifest, rc)


def _finish_selftest(td, mpath, manifest, rc):
        open(mpath, "w").write(manifest)
        os.environ["PRESS_RUNS_DIR"] = os.path.join(td, "press_runs")
        # negative test: parity must fail loud on a wrong frozen sha
        bad = manifest.replace(sha256_text("alpha"), sha256_text("tampered"))
        open(mpath, "w").write(bad)
        try:
            cmd_build("FIX-01")
        except SystemExit as e:
            if e.code:
                runs = os.environ["PRESS_RUNS_DIR"]
                for d in os.listdir(runs):
                    if not d.endswith("FIX-01"):
                        continue
                    rec = json.load(open(os.path.join(runs, d, "run.json")))
                    if rec["result"] == "FAIL" and \
                            rec.get("parity", {}).get("byte_parity") is False:
                        print("selftest: tampered frozen sha failed the "
                              "PARITY check loud ✔")
                        return rc
        print("selftest: PARITY CHECK DID NOT FAIL — defect", file=sys.stderr)
        return 1


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd, args = sys.argv[1], sys.argv[2:]

    def opt(name, default=None):
        if name in args:
            i = args.index(name)
            if i + 1 >= len(args) or args[i + 1].startswith("--"):
                fail(f"option {name} requires a value")
            v = args[i + 1]
            del args[i:i + 2]
            return v
        return default

    def no_residue(expected_positionals):
        """P3.1 (reviewer finding): unknown or leftover arguments FAIL LOUD — the Press
        never silently ignores what a human typed."""
        residue = args[expected_positionals:]
        stray_flags = [a for a in args[:expected_positionals]
                       if a.startswith("--") and a != "--all"]  # --all = documented target literal
        if residue or stray_flags:
            fail(f"unrecognized argument(s): {stray_flags + residue} — "
                 f"nothing is silently ignored; see --help usage in the docstring")

    if cmd == "bundle":
        if not args:
            fail("bundle requires a volume target")
        no_residue(1)
        return cmd_bundle(args[0])
    if cmd == "build" and "--offline" in args:
        args.remove("--offline")
        if not args:
            fail("build --offline requires a volume target")
        no_residue(1)
        return cmd_build_offline(args[0])
    if cmd == "build":
        qmode = opt("--mode", "single")
        if qmode not in ("single", "double", "parallel"):
            fail(f"--mode must be single|double|parallel, got {qmode!r}")
        wave = opt("--approve-wave")
        if not args:
            fail("build requires a target (VOL-01 | S1 | S1,S2 | --all)")
        no_residue(1)
        return cmd_build(args[0], qmode=qmode, approve_wave=wave)
    if cmd == "cycle":
        seeds = opt("--seeds")
        if not args or not seeds:
            fail("cycle requires: cycle <volume-id> --seeds DIR")
        no_residue(1)
        return cmd_cycle(args[0], seeds)
    if cmd == "harden":
        approve = opt("--approve-report")
        if not args:
            fail("harden requires a volume target")
        no_residue(1)
        return cmd_harden(args[0], approve_report=approve)
    if cmd == "report":
        no_residue(1)
        # P4b.1 (reviewer finding D2): accept 'S2' or '2'; refuse anything else loud-but-graceful.
        sid = args[0].upper().lstrip("S") if args[0].upper().startswith("S") else args[0]
        if not sid.isdigit():
            fail(f"report requires a series id like S2 or 2 — got {args[0]!r}")
        rc = subprocess.run(shlex.split(_env_path("PRESS_REPORT_CMD", f"{sys.executable} -m sovereign_agent.press.report")) + [sid])
        return rc.returncode
    if cmd == "status":
        no_residue(0)
        return cmd_status()
    if cmd == "selftest":
        no_residue(0)
        return cmd_selftest()
    fail(f"unknown command {cmd!r}")


if __name__ == "__main__":
    sys.exit(main())
