#!/usr/bin/env bash
# node_d6_report.sh — ONE command → the pasteable D6 durability+smoke deposit (Dragon iron / Beard-local).
#
# Proves, on THIS iron: restart fingerprint pair (must match) · keystore digest pair (must match) ·
# recovery-note-exists-before-key (mtimes) · loopback-only sockets · node_smoke.sh AFTER restart ·
# git HEAD + diff --stat vs a baseline. Paste stdout as the deposit — no prose substitute.
#
#   NODE_KEYSTORE_DIR   durable keystore (default $HOME/.sovereign_keystore)
#   BREATHLINE_NODE_NAME   node id (default UniversalSovereignNode)
#   BREATHLINE_NODE_LOOPBACK_OWNER  your principal (REQUIRED)
#   BREATHLINE_NODE_API_HOST/PORT   default 127.0.0.1 / 8421
#   D6_BASELINE         git ref for `git diff --stat` (default: origin/main)
# Prereq: starter installed (`pip install -e .`) OR export PYTHONPATH=src. No BREATHLINE_SEALED_ROOT needed.
set -uo pipefail
cd "$(dirname "$0")/.."

export NODE_KEYSTORE_DIR="${NODE_KEYSTORE_DIR:-$HOME/.sovereign_keystore}"
export BREATHLINE_NODE_NAME="${BREATHLINE_NODE_NAME:-UniversalSovereignNode}"
: "${BREATHLINE_NODE_LOOPBACK_OWNER:?set BREATHLINE_NODE_LOOPBACK_OWNER=<your-principal>}"
HOST="${BREATHLINE_NODE_API_HOST:-127.0.0.1}"; export BREATHLINE_NODE_API_HOST="$HOST"
PORT="${BREATHLINE_NODE_API_PORT:-8421}";      export BREATHLINE_NODE_API_PORT="$PORT"
BASELINE="${D6_BASELINE:-origin/main}"
KEYFILE="$NODE_KEYSTORE_DIR/$BREATHLINE_NODE_NAME.nodekey.json"
NOTE="docs/OPERATE_A_NODE.md"

_fp() { python3 - <<PY
from sovereign_agent.keystore.node_keystore import load_node_keypair
print(load_node_keypair("$NODE_KEYSTORE_DIR", "$BREATHLINE_NODE_NAME").fingerprint)
PY
}
_digest() { sha256sum "$KEYFILE" 2>/dev/null | cut -d' ' -f1; }
_mtime()  { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || true; }
_perms()  { stat -c %A "$1" 2>/dev/null || stat -f %Sp "$1" 2>/dev/null || true; }

# HOME sanity: a poisoned $HOME (e.g. a literal placeholder path) makes ~ unwritable and breaks everything.
case "${HOME:-}" in
  /path/*|""|"/path/to/"*) echo "✗ \$HOME is '$HOME' — that is a placeholder, not a real directory."
                           echo "  fix: export HOME=/home/$(id -un)   (or a real dedicated dir you mkdir first), then re-run."; exit 1;;
esac
[ -d "$HOME" ] || { echo "✗ \$HOME '$HOME' does not exist — export HOME=/home/$(id -un) and re-run."; exit 1; }
_start()  { nohup python3 -m sovereign_agent.node_api.server --host "$HOST" --port "$PORT" >/tmp/d6_node.log 2>&1 &
            echo $!; for _ in $(seq 1 30); do curl -s "http://$HOST:$PORT/api/v1/manifest" >/dev/null 2>&1 && return; sleep 0.5; done; }
_served_fp() { curl -s "http://$HOST:$PORT/api/v1/node" | sed -n 's/.*"fingerprint": *"\([^"]*\)".*/\1/p'; }
_dump_if_down() { if ! curl -s "http://$HOST:$PORT/api/v1/manifest" >/dev/null 2>&1; then
    echo "  ✗ node did NOT bind on $HOST:$PORT — boot failed. Last lines of /tmp/d6_node.log:"
    tail -15 /tmp/d6_node.log 2>/dev/null | sed 's/^/    /'
    echo "    (a ModuleNotFoundError: flask means deps aren't installed — run: pip install -e .)"; fi }

echo "∞Δ∞ D6 NODE DURABILITY + SMOKE — $(date -u +%FT%TZ) — host $(hostname)"
echo "== git =="; echo "HEAD: $(git rev-parse --short HEAD)"; echo "baseline: $BASELINE"
git diff --stat "$BASELINE"..HEAD 2>/dev/null | tail -20 || echo "(baseline not resolvable — set D6_BASELINE)"

echo "== recovery-note mtime (must exist BEFORE the key) =="
echo "  note $NOTE mtime: $(_mtime "$NOTE")  ($(date -u -d @"$(_mtime "$NOTE")" +%FT%TZ 2>/dev/null || echo n/a))"

mkdir -p "$NODE_KEYSTORE_DIR" || { echo "✗ cannot create keystore dir '$NODE_KEYSTORE_DIR' — check \$HOME and permissions."; exit 1; }
chmod 700 "$NODE_KEYSTORE_DIR" 2>/dev/null || true
if [ ! -f "$KEYFILE" ]; then
  python3 - <<PY || { echo "✗ FAIL: could not provision the durable key (see error above)."; exit 1; }
import datetime
from sovereign_agent.keystore.node_keystore import generate_node_key
generate_node_key("$NODE_KEYSTORE_DIR","$BREATHLINE_NODE_NAME",at=datetime.datetime.now(datetime.timezone.utc).isoformat())
PY
fi
[ -f "$KEYFILE" ] || { echo "✗ FAIL: durable key file was not created at $KEYFILE"; exit 1; }
KEYM=$(_mtime "$KEYFILE"); NOTEM=$(_mtime "$NOTE")
echo "  key  $KEYFILE mtime: $KEYM  perms: $(_perms "$KEYFILE")"
if [ -n "${NOTEM:-}" ] && [ -n "${KEYM:-}" ] && [ "$NOTEM" -le "$KEYM" ]; then
  echo "  ✓ recovery note existed before the key was minted"; else echo "  ⚠ note mtime not before key mtime — confirm you read the recovery note first"; fi

echo "== boot 1 =="; PID=$(_start); echo "  pid $PID"; _dump_if_down
echo "  sockets (loopback only):"; { ss -ltnp 2>/dev/null | grep ":$PORT" || lsof -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || echo "(ss/lsof unavailable)"; } | sed 's/^/    /'
F1=$(_fp); D1=$(_digest); SF1=$(_served_fp)
echo "  key fingerprint : $F1"; echo "  keystore digest : $D1"; echo "  /node served fp : $SF1"
echo "== ceremony (sandbox accept — must NOT change the durable key) =="
curl -s -X POST "http://$HOST:$PORT/api/v1/onboard/ceremony" -H 'Content-Type: application/json' -d '{"disposition":"accept","name":"d6"}' | grep -o '"verified": *true' | sed 's/^/  /' || echo "  (ceremony skipped)"

echo "== restart (kill -9 → same recipe) =="; kill -9 "$PID" 2>/dev/null; sleep 1; PID=$(_start); echo "  pid $PID"; _dump_if_down
F2=$(_fp); D2=$(_digest); SF2=$(_served_fp)
echo "  key fingerprint : $F2"; echo "  keystore digest : $D2"; echo "  /node served fp : $SF2"
# require NON-EMPTY values — two empty fingerprints are a FAILURE, not a match
if [ -n "$F1" ] && [ "$F1" = "$F2" ]; then echo "  ✓ FINGERPRINT STABLE across restart"; else echo "  ✗ FINGERPRINT NOT STABLE (or absent): '$F1' → '$F2'"; fi
if [ -n "$D1" ] && [ "$D1" = "$D2" ]; then echo "  ✓ KEYSTORE DIGEST unchanged across restart"; else echo "  ✗ KEYSTORE DIGEST changed or absent"; fi
if [ -n "$F1" ] && [ "$SF1" = "$F1" ] && [ "$SF2" = "$F2" ]; then echo "  ✓ /node served fingerprint == on-disk identity"; else echo "  ⚠ served fp differs from on-disk (or node not up)"; fi

echo "== smoke AFTER restart =="; BREATHLINE_NODE_API_PORT="$PORT" bash scripts/node_smoke.sh 2>&1 | sed 's/^/  /'
kill -9 "$PID" 2>/dev/null
echo "∞Δ∞ D6 END — paste this whole block as the deposit."
