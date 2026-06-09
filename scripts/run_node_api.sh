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
# Loopback-trust (KM-1176 ratified 2026-06-03): the operator's own 127.0.0.1 cockpit authenticates as the
# owner WITHOUT a bearer token — "requiring a token to talk to your own loopback node is burden, not
# sovereignty." MUST be set, or the Atrium browser gets 401'd and every lens shows "node unreachable".
export BREATHLINE_NODE_LOOPBACK_OWNER="${BREATHLINE_NODE_LOOPBACK_OWNER:-KM-1176}"
echo "Node API -> http://127.0.0.1:8421/api/v1  (ledger: $OBLIGATION_LEDGER_ROOT · loopback-owner: $BREATHLINE_NODE_LOOPBACK_OWNER)"
exec python3 -c "from sovereign_agent.node_api.server import create_app; create_app().run(host='127.0.0.1', port=8421, threaded=True)"
