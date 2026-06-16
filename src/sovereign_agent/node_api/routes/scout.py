"""/goal Scout — on-demand trigger (KM [378] #3). Owner-gated; mirrors /produce: fires the DETERMINISTIC,
propose-only scout_run.py detached. The scout proposes candidates only (status 'proposed') for the cockpit;
it never decides, commits, or seals. The durable OS crontab is the scheduled path; this is the human button."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from flask import Blueprint, jsonify

from ..auth import require_owner, require_principal

bp = Blueprint("scout", __name__, url_prefix="/api/v1")


@bp.post("/scout/run")
@require_principal
@require_owner
def scout_run():
    """scout.run — HUMAN-TRIGGERED on-demand overnight-scout pass (owner-gated, like /produce). Spawns
    scripts/scout_run.py (deterministic, propose-only): derives Book↔Code + static-scan packets, lints them,
    posts candidate proposals KM disposes. Fires only on this owner request; not an autonomous daemon."""
    repo = Path(__file__).resolve().parents[4]
    script = repo / "scripts" / "scout_run.py"
    if not script.exists():
        return jsonify({"error": "scout_missing", "what": f"No scout runner at {script}."}), 500
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo / "src")
    runs = Path(os.path.expanduser("~/.breathline/runs"))
    runs.mkdir(parents=True, exist_ok=True)
    log = runs / "scout_run.log"
    subprocess.Popen([sys.executable, str(script)], cwd=str(repo), env=env,
                     stdout=open(log, "w"), stderr=subprocess.STDOUT, start_new_session=True)
    return jsonify({"status": "scout spawned", "mode": "propose-only (deterministic)",
                    "next_step": "Candidates appear in /proposals (status 'proposed') for your disposition."}), 202
