#!/usr/bin/env bash
# Start the Breathline Node API (Flask) for the Atrium's ?api=live mode.
# Serves /api/v1/obligations from a REAL ObligationLedger on 127.0.0.1:8421 (CORS open for the local Atrium).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"; export PYTHONPATH="$HERE/src"
# Which ledger the live node serves. Default = atrium_review — the ledger the Atrium Working-tab board
# READS and DISMISSES/CLOSES against. These MUST match: the board feed + dismiss/close both use this one
# root via get_obligation_ledger(); a mismatch makes dispositions land in the wrong file and cards resurface.
export OBLIGATION_LEDGER_ROOT="${OBLIGATION_LEDGER_ROOT:-$HERE/memory/obligations/atrium_review}"
echo "Node API -> http://127.0.0.1:8421/api/v1  (ledger: $OBLIGATION_LEDGER_ROOT)"
exec python3 -c "from sovereign_agent.node_api.server import create_app; create_app().run(host='127.0.0.1', port=8421, threaded=True)"
