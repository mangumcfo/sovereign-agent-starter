#!/usr/bin/env bash
# cockpit_tray launcher — loopback only, no state, no store.
set -euo pipefail
cd "$(dirname "$0")/../.."
exec ./.venv/bin/python apps/cockpit_tray/server.py "$@"
