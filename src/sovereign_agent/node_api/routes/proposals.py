"""
Section — Proposals (Step C: diff-review).

The producer (an agent reading a captured session) writes grouped diffs here; the Atrium
diff-review surface reads them and lets the operator accept/reject BEFORE anything is written.

    GET  /proposals                  → list proposals (newest first)
    POST /proposals                  → producer writes a proposal {session_ref, groups:[...]}
    POST /proposals/{id}/decide      → record the operator's per-group accept/reject decisions

Storage is a node-local append-style JSON file beside the obligation ledger. This is the REVIEW
queue, not the seal chain: acceptance is the disposition; the actual git-apply + seal is performed
by the agent (and traced in the obligation ledger). No hardcoded principals (CONSTITUTION §1).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from flask import Blueprint, jsonify, request

from ..auth import current_principal, require_principal

bp = Blueprint("proposals", __name__, url_prefix="/api/v1")


def _store_path() -> Path:
    explicit = os.environ.get("PROPOSALS_STORE")
    if explicit:
        return Path(explicit)
    led = os.environ.get("OBLIGATION_LEDGER_ROOT")
    base = Path(led).parent if led else Path(os.path.expanduser("~/.breathline"))
    return base / "proposals.json"


def _read() -> list:
    p = _store_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8")) or []
    except (OSError, ValueError):
        return []


def _write(items: list) -> None:
    p = _store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(items, indent=2), encoding="utf-8")


@bp.get("/proposals")
@require_principal
def proposals_list():
    items = sorted(_read(), key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify({"proposals": items})


@bp.post("/proposals")
@require_principal
def proposals_create():
    body = request.get_json(silent=True) or {}
    groups = body.get("groups") or []
    if not groups:
        return jsonify({
            "error": "missing_groups",
            "what": "A proposal needs at least one grouped diff.",
            "next_step": "POST /api/v1/proposals with {\"session_ref\":\"...\",\"groups\":[{title,kind,scope,rationale,file,before,after}]}.",
        }), 400
    items = _read()
    prop = {
        "id": "prop_" + str(int(time.time() * 1000)),
        "session_ref": body.get("session_ref", ""),
        "obligation_id": body.get("obligation_id"),
        "book": body.get("book", ""),
        "note": body.get("note", ""),
        "produced_by": body.get("produced_by") or current_principal(),
        "groups": groups,
        "status": "proposed",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    items.append(prop)
    _write(items)
    return jsonify(prop), 201


@bp.post("/produce")
@require_principal
def produce():
    """produce — HUMAN-TRIGGERED (the Atrium 'Process' button). Spawns the producer for ONE session:
    it reads the transcript + manuscript and posts grouped diffs to /proposals (proposals only; the
    operator still accepts in the diff-review). Not an autonomous daemon — fires only on this request.
    """
    import subprocess
    import sys
    from pathlib import Path

    body = request.get_json(silent=True) or {}
    oid = (body.get("obligation_id") or "").strip()
    if not oid:
        return jsonify({"error": "missing_obligation_id",
                        "what": "Tell me which session to process.",
                        "next_step": "POST /api/v1/produce with {\"obligation_id\":\"obl_...\"}."}), 400
    repo = Path(__file__).resolve().parents[4]
    script = repo / "scripts" / "atrium_producer.py"
    if not script.exists():
        return jsonify({"error": "producer_missing", "what": f"No producer at {script}."}), 500
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo / "src")
    env["PYTHONUNBUFFERED"] = "1"   # so the agent's progress lines stream to the log live
    # Capture the agent's output to a per-run log + write a run-status file so the cockpit can show
    # 'is an agent working, on what, for how long, what is it doing' (KM: not a black box).
    import json as _json
    import time as _time
    runs = Path(os.path.expanduser("~/.breathline/runs"))
    runs.mkdir(parents=True, exist_ok=True)
    logf = runs / f"{oid}.log"
    proc = subprocess.Popen([sys.executable, str(script), "--session", oid], cwd=str(repo), env=env,
                            stdout=open(logf, "w"), stderr=subprocess.STDOUT, start_new_session=True)
    (runs / f"{oid}.json").write_text(_json.dumps(
        {"session_id": oid, "started_at": _time.time(), "pid": proc.pid, "log": str(logf)}), encoding="utf-8")
    return jsonify({"status": "processing", "obligation_id": oid,
                    "next_step": "The diff(s) appear in the diff-review when ready (~1-3 min)."}), 202


@bp.get("/processing")
@require_principal
def processing():
    """processing — what agents are working on RIGHT NOW: session, elapsed time, live log tail.
    Once a run produces a result (a proposal / info card), its entry drops here and shows in the diff-review."""
    import json as _json
    import time as _time
    from pathlib import Path

    runs = Path(os.path.expanduser("~/.breathline/runs"))
    out = []
    if runs.exists():
        have = {p.get("obligation_id") for p in _read()}
        for jf in sorted(runs.glob("*.json")):
            try:
                meta = _json.loads(jf.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            oid = meta.get("session_id")
            elapsed = int(_time.time() - meta.get("started_at", 0))
            pid = meta.get("pid")
            alive = False
            if pid:
                try:
                    os.kill(int(pid), 0)
                    alive = True
                except (OSError, ValueError):
                    alive = False
            has_result = oid in have
            if has_result or (not alive and elapsed > 150):   # result landed, or it died → hand off / clean
                try:
                    jf.unlink()
                except OSError:
                    pass
                continue
            tail = ""
            lf = meta.get("log")
            if lf and os.path.isfile(lf):
                try:
                    tail = "\n".join(open(lf, encoding="utf-8", errors="replace").read().splitlines()[-14:])
                except OSError:
                    pass
            out.append({"session_id": oid, "elapsed_seconds": elapsed,
                        "status": "processing" if alive else "finishing", "alive": alive, "log_tail": tail})
    out.sort(key=lambda x: x["elapsed_seconds"], reverse=True)
    return jsonify({"runs": out})


@bp.post("/recompile")
@require_principal
def recompile():
    """recompile — HUMAN-TRIGGERED. Rebuild a book's PDF from the (just-edited) manuscript so KM can
    re-load it in the viewer and see the applied changes. Spawns the book's build script."""
    import re
    import subprocess
    import sys

    body = request.get_json(silent=True) or {}
    book = (body.get("book") or "").strip()
    m = re.search(r"Book (\d+)", book)
    sub = {"10": "10_scaling_enterprise", "11": "11_ma_due_diligence",
           "12": "12_agentic_enterprise"}.get(m.group(1) if m else "")
    if not sub:
        return jsonify({"error": "unknown_book", "what": f"No build mapping for '{book}'."}), 400
    vault = "/home/kmangum/work-repos/mangumcfo/breathline-books-vault/kdp/agentic_playbooks"
    cwd = os.path.join(vault, sub, "v1.0")
    script = os.path.join(cwd, "build_v1.0.py")
    if not os.path.isfile(script):
        return jsonify({"error": "no_build_script", "what": f"No build_v1.0.py for {book}."}), 500
    subprocess.Popen([sys.executable, script], cwd=cwd,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return jsonify({"status": "recompiling", "book": book,
                    "next_step": "~30-90s; then re-load the PDF (Browse…) in the viewer to see the changes."}), 202


@bp.post("/proposals/<proposal_id>/apply")
@require_principal
def proposals_apply(proposal_id: str):
    """apply — HUMAN-TRIGGERED by KM's Accept. Spawns the apply agent: land accepted+tested diffs →
    re-test code (abort on red) → commit (local) + seal + close. Execute-after-Approve; reversible."""
    import subprocess
    import sys
    from pathlib import Path

    body = request.get_json(silent=True) or {}
    gids = body.get("group_ids")
    repo = Path(__file__).resolve().parents[4]
    script = repo / "scripts" / "atrium_apply.py"
    if not script.exists():
        return jsonify({"error": "apply_agent_missing"}), 500
    args = [sys.executable, str(script), proposal_id]
    if gids:
        args.append(",".join(gids))
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo / "src")
    subprocess.Popen(args, cwd=str(repo), env=env,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return jsonify({"status": "applying", "proposal_id": proposal_id,
                    "next_step": "Re-tests, commits (local), seals, closes — then the proposal clears. ~10-30s."}), 202


@bp.post("/proposals/<proposal_id>/dismiss")
@require_principal
def proposals_dismiss(proposal_id: str):
    """dismiss — clear an info / no-diff proposal + close its session obligation (nothing to apply)."""
    items = _read()
    prop = next((x for x in items if x.get("id") == proposal_id), None)
    _write([x for x in items if x.get("id") != proposal_id])
    oid = (prop or {}).get("obligation_id")
    if oid:
        try:
            from ..deps import get_obligation_ledger
            get_obligation_ledger().close(
                oid, evidence="E1: dismissed — " + str((prop or {}).get("note", "no diff produced"))[:120],
                evidence_tier="E1", closed_by="tiger")
        except Exception:  # noqa: BLE001 — dismissal must never error the UI
            pass
    return jsonify({"status": "dismissed", "proposal_id": proposal_id})


@bp.post("/proposals/<proposal_id>/decide")
@require_principal
def proposals_decide(proposal_id: str):
    body = request.get_json(silent=True) or {}
    decisions = body.get("decisions") or {}  # {group_id: "accept"|"reject"}
    items = _read()
    found = None
    for it in items:
        if it.get("id") == proposal_id:
            it.setdefault("decisions", {}).update(decisions)
            it["decided_by"] = current_principal()
            it["status"] = "decided"
            found = it
            break
    if not found:
        return jsonify({"error": "not_found", "what": f"No proposal {proposal_id}."}), 404
    _write(items)
    return jsonify(found)
