"""
Section — Book↔Code Coherence (Step D).

The alignment lens: for every book→code extrusion, the code cites an exact book passage (hash-pinned).
This endpoint re-reads each cited passage from the book and re-checks the code, so the cockpit can show
— live — whether the code still reflects the book (coherent) or has drifted. Plus the declared Atrium↔Vol2
reconciliation rows. Read-only; no writes.

    GET /coherence  → { extrusions:[…computed status…], reconciliation:{…}, summary:{…} }
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from flask import Blueprint, jsonify

from ..auth import require_principal

bp = Blueprint("coherence", __name__, url_prefix="/api/v1")


def _registry_path() -> Path:
    repo = Path(__file__).resolve().parents[4]
    return repo / "memory" / "coherence_registry.json"


@bp.get("/coherence")
@require_principal
def coherence():
    repo = Path(__file__).resolve().parents[4]
    p = _registry_path()
    if not p.exists():
        return jsonify({"extrusions": [], "reconciliation": {}, "summary": {"coherent": 0, "drift": 0, "gaps": 0}})
    reg = json.loads(p.read_text(encoding="utf-8"))
    out = []
    coherent = drift = 0
    for e in reg.get("extrusions", []):
        bf = e.get("book_file", "")
        passage = e.get("passage", "")
        book_present = False
        hash_ok = False
        try:
            if bf and os.path.isfile(bf):
                txt = open(bf, encoding="utf-8").read()
                book_present = passage in txt
            hash_ok = hashlib.sha256(passage.encode()).hexdigest()[:12] == e.get("passage_hash", "")
        except OSError:
            pass
        code_present = os.path.isfile(os.path.join(repo, e.get("code_file", "")))
        tests_present = os.path.isfile(os.path.join(repo, e.get("tests_file", "")))
        status = "coherent" if (book_present and code_present and hash_ok) else "DRIFT"
        if status == "coherent":
            coherent += 1
        else:
            drift += 1
        out.append({**e, "book_present": book_present, "code_present": code_present,
                    "tests_present": tests_present, "hash_ok": hash_ok, "status": status})
    recon = reg.get("reconciliation", {})
    gaps = sum(1 for r in recon.get("rows", []) if r.get("status") == "gap")
    return jsonify({"extrusions": out, "reconciliation": recon,
                    "summary": {"coherent": coherent, "drift": drift, "gaps": gaps}})
