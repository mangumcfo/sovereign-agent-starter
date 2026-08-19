#!/usr/bin/env bash
# Launch the USN ERP Operator Surface against a local node. Loopback only.
#
#   ./apps/usn_erp_surface/launch.sh                 # uses env paths if set
#   SUBSTRATE_STORAGE_ROOT=/path/registry ./apps/usn_erp_surface/launch.sh
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
py="$repo/.venv/bin/python"
[ -x "$py" ] || py="$(command -v python3)"
exec "$py" "$here/server.py" "$@"
