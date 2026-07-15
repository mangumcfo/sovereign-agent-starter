"""
Thin launcher shim for the 'start-sovereign-portal' console script.

After `pip install -e ".[portal]"`, the user can run `start-sovereign-portal`.
This shim either launches a co-located portal or prints exact, friendly instructions.
"""

import os
import sys
from pathlib import Path


def launch():
    here = Path(__file__).resolve().parent
    # Common co-located locations
    candidates = [
        here.parent.parent.parent / "six-sov-portal" / "app.py",   # when starter is in work-repos
        Path.cwd().parent / "six-sov-portal" / "app.py",
        Path(os.environ.get("SIX_SOV_PORTAL", "")) / "app.py",
    ]
    for cand in candidates:
        if cand.exists():
            print(f"Launching portal from {cand.parent} ...")
            os.execv(sys.executable, [sys.executable, str(cand)])
            return

    print("""
∞Δ∞ start-sovereign-portal

The Breathline Portal was not found in the expected sibling location.

Recommended path (after running sovereign-install.sh):
  1. source ../sovereign-agent-starter/.venv/bin/activate
  2. cd ../six-sov-portal
  3. ./start-breathline-portal.sh

Legacy fallback:
  PYTHONPATH=../sovereign-agent-starter/src:$PYTHONPATH python ../six-sov-portal/app.py
""")
    sys.exit(1)


if __name__ == "__main__":
    launch()
