#!/usr/bin/env bash
# sovereign_node_up.sh — stand a DURABLE, loopback-only sovereign node (Dragon / Beard / any iron).
#
# Idempotent: provisions the node's durable self-held key ONCE (never re-mints on reboot — a re-mint would
# orphan the identity), aligns the owner principal, and serves the node_api on 127.0.0.1 only.
#
#   NODE_KEYSTORE_DIR      durable keystore dir (default: $HOME/.sovereign_keystore) — key lives here, on iron
#   BREATHLINE_NODE_NAME   this node's stable id (default: UniversalSovereignNode) — the key file is <name>.nodekey.json
#   BREATHLINE_NODE_LOOPBACK_OWNER   your principal (REQUIRED) — must match how you call owner-gated routes
#   BREATHLINE_NODE_API_HOST/PORT    default 127.0.0.1 / 8421 (loopback only; off-loopback dev fails loud)
#
# Prereq: the starter is installed (`pip install -e .`) so `sovereign_agent` imports. No BREATHLINE_SEALED_ROOT
# needed — the crypto substrate is vendored in-tree. No escrow, no second recovery authority: root-on-iron.
set -euo pipefail

export NODE_KEYSTORE_DIR="${NODE_KEYSTORE_DIR:-$HOME/.sovereign_keystore}"
export BREATHLINE_NODE_NAME="${BREATHLINE_NODE_NAME:-UniversalSovereignNode}"
: "${BREATHLINE_NODE_LOOPBACK_OWNER:?set BREATHLINE_NODE_LOOPBACK_OWNER=<your-principal> (owner of the owner-gated routes)}"
HOST="${BREATHLINE_NODE_API_HOST:-127.0.0.1}"
PORT="${BREATHLINE_NODE_API_PORT:-8421}"

# Footgun guard (AA Beard R2 §4): a durable key inside a web-served dir can be served to the internet, and if the
# default $HOME/.sovereign_keystore lands there, an omitted override silently MINTS a NEW identity in the web root.
case "$NODE_KEYSTORE_DIR" in
  /var/www/*|*/public_html/*|/usr/share/nginx/*|/srv/www/*|*/htdocs/*)
    echo "⚠⚠ WARNING: NODE_KEYSTORE_DIR ($NODE_KEYSTORE_DIR) is inside a WEB-SERVED directory."
    echo "   A private key here can be exposed to the internet. Set HOME (or NODE_KEYSTORE_DIR) OUTSIDE any web root"
    echo "   — e.g. export HOME=/root/node-home — so the SAFE path is the default, not a flag you must remember." ;;
esac
mkdir -p "$NODE_KEYSTORE_DIR"; chmod 700 "$NODE_KEYSTORE_DIR" 2>/dev/null || true

# Provision the DURABLE key once (load-only if present). Boot never mints a new identity.
python3 - <<'PY'
import os, datetime
from sovereign_agent.keystore.node_keystore import has_node_key, generate_node_key, load_node_key
ks = os.environ["NODE_KEYSTORE_DIR"]; nid = os.environ["BREATHLINE_NODE_NAME"]
if has_node_key(ks, nid):
    k = load_node_key(ks, nid); print(f"[node] existing durable identity: {nid}  fp={k.fingerprint}")
else:
    at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    k = generate_node_key(ks, nid, at=at); print(f"[node] provisioned durable identity: {nid}  fp={k.fingerprint}")
print(f"[node] key file: {os.path.join(ks, nid + '.nodekey.json')} (0600, on this iron; no escrow)")
PY

echo "[node] serving on http://$HOST:$PORT (loopback only) — owner=$BREATHLINE_NODE_LOOPBACK_OWNER"
echo "[node] Node Home: set BREATHLINE_ATRIUM_UI_DIR=<console-dist> then open http://$HOST:$PORT/atrium/"
exec python3 -m sovereign_agent.node_api.server --host "$HOST" --port "$PORT"
