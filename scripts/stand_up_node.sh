#!/usr/bin/env bash
# stand_up_node.sh — the ONE command that stands a sovereign node on a cold machine and proves it (P0-1).
#
# Composes the scattered steps (venv+install · durable key · loopback boot · fingerprint · smoke) into a
# single fail-loud entry. Every check reports THREE states — found / checked-and-absent / could-not-check —
# so an empty block is never mistaken for a pass (the H7 lesson). It EXITS NON-ZERO on any silent condition:
# a check that could not run is a failure, not a shrug.
#
#   Flags:
#     --offline      install from vendor/wheels with no pip index (run scripts/vendor_wheels.sh first)
#     --smoke-only   boot, run the smoke, then tear the node down (CI / proof runs). Default leaves it up.
#     --d6           also run scripts/node_d6_report.sh after the smoke
#     --no-smoke     boot + fingerprint only; skip the smoke
#
#   Env (same contract as sovereign_node_up.sh):
#     NODE_KEYSTORE_DIR   durable keystore   (default $HOME/.sovereign_keystore)
#     BREATHLINE_NODE_NAME  stable id        (default UniversalSovereignNode)  — MUST match the key in the dir
#     BREATHLINE_NODE_LOOPBACK_OWNER  your principal (REQUIRED)
#     BREATHLINE_NODE_API_HOST/PORT   default 127.0.0.1 / 8421 (loopback only)
set -uo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"

OFFLINE=0; SMOKE_ONLY=0; RUN_D6=0; DO_SMOKE=1
for a in "$@"; do case "$a" in
  --offline) OFFLINE=1 ;; --smoke-only) SMOKE_ONLY=1 ;; --d6) RUN_D6=1 ;; --no-smoke) DO_SMOKE=0 ;;
  -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
  *) echo "unknown flag: $a" >&2; exit 2 ;;
esac; done

FAIL=0
ok(){   echo "  ✓ $*"; }
absent(){ echo "  ✗ $* — CHECKED, ABSENT"; FAIL=1; }
nocheck(){ echo "  ⚠ $* — COULD NOT CHECK (treated as failure; not a pass)"; FAIL=1; }
die(){ echo; echo "✗ STAND-UP REFUSED: $*"; exit 1; }

HOST="${BREATHLINE_NODE_API_HOST:-127.0.0.1}"
PORT="${BREATHLINE_NODE_API_PORT:-8421}"
export NODE_KEYSTORE_DIR="${NODE_KEYSTORE_DIR:-$HOME/.sovereign_keystore}"
export BREATHLINE_NODE_NAME="${BREATHLINE_NODE_NAME:-UniversalSovereignNode}"

echo "∞Δ∞ STAND-UP — $(date -u +%FT%TZ) — host $(hostname 2>/dev/null || echo '?')"

# ── three-state listener enumeration (ss → netstat → /proc/net/tcp; empty ≠ silent pass) ──
_listeners(){
  local out hx
  if command -v ss >/dev/null 2>&1; then
    out=$(ss -ltnp 2>/dev/null | grep ":$PORT"); [ -n "$out" ] && { echo "$out" | sed 's/^/    /'; return 0; }; return 1
  fi
  if command -v netstat >/dev/null 2>&1; then
    out=$(netstat -ltnp 2>/dev/null | grep ":$PORT"); [ -n "$out" ] && { echo "$out" | sed 's/^/    /'; return 0; }; return 1
  fi
  if [ -r /proc/net/tcp ] || [ -r /proc/net/tcp6 ]; then
    hx=$(printf ':%04X' "$PORT")
    out=$(grep -ih "$hx" /proc/net/tcp /proc/net/tcp6 2>/dev/null)
    [ -n "$out" ] && { while read -r _s l _r st _z; do echo "    $l st=$st"; done <<<"$out"; return 0; }; return 1
  fi
  return 2   # no method available
}

# ── 1 · HOME sanity ───────────────────────────────────────────────────────────
echo "== 1 · HOME + keystore sanity =="
if [ -z "${HOME:-}" ] || [[ "$HOME" == *"/path/to"* ]] || [ "$HOME" = "~" ]; then
  die "\$HOME is unset or a placeholder ($HOME). A durable identity needs a real home — export HOME=/your/home."
fi
case "$NODE_KEYSTORE_DIR" in
  /var/www/*|*/public_html/*|/usr/share/nginx/*|/srv/www/*|*/htdocs/*)
    die "NODE_KEYSTORE_DIR ($NODE_KEYSTORE_DIR) is inside a WEB-SERVED dir — a private key there can be served to the internet. Move HOME/NODE_KEYSTORE_DIR outside any web root." ;;
esac
: "${BREATHLINE_NODE_LOOPBACK_OWNER:?set BREATHLINE_NODE_LOOPBACK_OWNER=<your-principal> (owner of the owner-gated routes)}"
mkdir -p "$NODE_KEYSTORE_DIR" && chmod 700 "$NODE_KEYSTORE_DIR" 2>/dev/null || true
ok "HOME=$HOME · keystore=$NODE_KEYSTORE_DIR · name=$BREATHLINE_NODE_NAME · owner=$BREATHLINE_NODE_LOOPBACK_OWNER"

# keystore/name MATCH — booting a name with no key, or a dir already holding a DIFFERENT identity, is the
# scar that mints a second identity or fails 500. Fail loud BEFORE boot.
shopt -s nullglob
KEYS=("$NODE_KEYSTORE_DIR"/*.nodekey.json)
shopt -u nullglob
if [ "${#KEYS[@]}" -eq 0 ]; then
  ok "keystore empty — will provision the durable identity '$BREATHLINE_NODE_NAME' once (first run)"
else
  MATCH=0; NAMES=()
  for k in "${KEYS[@]}"; do n=$(basename "$k" .nodekey.json); NAMES+=("$n"); [ "$n" = "$BREATHLINE_NODE_NAME" ] && MATCH=1; done
  if [ "$MATCH" -eq 1 ]; then
    ok "keystore holds '$BREATHLINE_NODE_NAME' — reusing the durable identity (no re-mint)"
    [ "${#KEYS[@]}" -gt 1 ] && echo "    (note: other identities also present here: ${NAMES[*]})"
  else
    die "keystore holds [${NAMES[*]}] but BREATHLINE_NODE_NAME='$BREATHLINE_NODE_NAME' matches none of them.
     Booting '$BREATHLINE_NODE_NAME' would MINT A SECOND identity in this dir and orphan the first.
     Fix: export BREATHLINE_NODE_NAME=${NAMES[0]}   (or point NODE_KEYSTORE_DIR at a different dir)."
  fi
fi

# ── 2 · venv + install (offline-aware) ────────────────────────────────────────
echo "== 2 · runtime (venv + install) =="
PYBIN="python3"
if python3 -c "import sovereign_agent, flask, yaml" 2>/dev/null; then
  ok "sovereign_agent + flask + pyyaml already importable in the active interpreter"
else
  if [ ! -d "$REPO/.venv" ]; then
    echo "  creating .venv …"; python3 -m venv "$REPO/.venv" || die "python3 -m venv failed — is python3-venv installed?"
  fi
  PYBIN="$REPO/.venv/bin/python"
  if [ "$OFFLINE" -eq 1 ] || [ -n "$(echo "$REPO"/vendor/wheels/*.whl 2>/dev/null | grep -v '\*')" ]; then
    echo "  installing OFFLINE from vendor/wheels (no pip index) …"
    PIP_NO_INDEX=1 "$PYBIN" -m pip install --no-index --find-links "$REPO/vendor/wheels" -e "$REPO" >/tmp/standup_pip.log 2>&1 \
      || { tail -15 /tmp/standup_pip.log; die "offline install failed — run scripts/vendor_wheels.sh on a networked machine first."; }
  else
    echo "  installing from index (pip install -e .) …"
    "$PYBIN" -m pip install -e "$REPO" >/tmp/standup_pip.log 2>&1 \
      || { tail -15 /tmp/standup_pip.log; die "pip install failed — see /tmp/standup_pip.log (offline? use --offline after vendor_wheels.sh)."; }
  fi
  "$PYBIN" -c "import sovereign_agent, flask, yaml" 2>/dev/null && ok "installed — sovereign_agent + flask + pyyaml importable" \
    || die "install completed but sovereign_agent still won't import — see /tmp/standup_pip.log"
fi

# ── 3 · durable identity (provision-once, never re-mint) + fingerprint ─────────
echo "== 3 · durable self-held identity =="
FP_KS=$("$PYBIN" - <<'PY' 2>/tmp/standup_key.err
import os, datetime
from sovereign_agent.keystore.node_keystore import has_node_key, generate_node_key, load_node_key
ks=os.environ["NODE_KEYSTORE_DIR"]; nid=os.environ["BREATHLINE_NODE_NAME"]
if not has_node_key(ks,nid):
    generate_node_key(ks,nid,at=datetime.datetime.now(datetime.timezone.utc).isoformat())
print(load_node_key(ks,nid).fingerprint)
PY
)
if [ -n "$FP_KS" ]; then ok "keystore fingerprint: $FP_KS  (key file 0600, on this iron; no escrow)"
else nocheck "could not read a fingerprint from the keystore"; cat /tmp/standup_key.err 2>/dev/null | sed 's/^/    /'; fi

# ── 4 · port free (three-state) ───────────────────────────────────────────────
echo "== 4 · port $PORT before boot =="
if _listeners; then echo "  ✗ port :$PORT is OCCUPIED — a listener is already bound (stop it, or set BREATHLINE_NODE_API_PORT)"; FAIL=1
else case $? in
  1) ok "port :$PORT is free" ;;
  2) nocheck "no ss / netstat / /proc — cannot confirm :$PORT is free" ;;
esac; fi

[ "$FAIL" -ne 0 ] && die "a preflight check failed or could not run (see ✗/⚠ above) — refusing to boot on unproven ground."

# ── 5 · boot loopback node (background) ───────────────────────────────────────
echo "== 5 · boot node on http://$HOST:$PORT (loopback only) =="
BREATHLINE_SEALED_ROOT="${BREATHLINE_SEALED_ROOT:-$REPO}" \
  "$PYBIN" -m sovereign_agent.node_api.server --host "$HOST" --port "$PORT" >/tmp/standup_node.log 2>&1 &
SV=$!
B="http://$HOST:$PORT/api/v1"
UP=0
for _ in $(seq 1 40); do curl -s "$B/manifest" >/dev/null 2>&1 && { UP=1; break; }; kill -0 "$SV" 2>/dev/null || break; sleep 0.5; done
if [ "$UP" -eq 1 ]; then ok "node up — /manifest responding (pid $SV)"
else
  echo "  ✗ node did not come up. boot log:"; tail -20 /tmp/standup_node.log | sed 's/^/    /'
  kill "$SV" 2>/dev/null; die "node failed to answer /manifest on :$PORT."
fi

echo "== 6 · what the node serves (fingerprint to compare BY HAND) =="
FP_SVC=$(curl -s "$B/node" | sed -n 's/.*"fingerprint": *"\([^"]*\)".*/\1/p')
if [ -n "$FP_SVC" ]; then
  if [ "$FP_SVC" = "$FP_KS" ]; then ok "served fingerprint $FP_SVC == keystore $FP_KS  (the human is the checker)"
  else absent "served fingerprint ($FP_SVC) != keystore ($FP_KS) — DO NOT trust this node until it matches"; fi
else nocheck "GET /node returned no fingerprint"; fi
CONSOLE="http://$HOST:$PORT/atrium/"
if [ -n "${BREATHLINE_ATRIUM_UI_DIR:-}" ] && [ -d "${BREATHLINE_ATRIUM_UI_DIR/#\~/$HOME}" ]; then
  echo "  Console (Node Home): $CONSOLE   (UI dir: $BREATHLINE_ATRIUM_UI_DIR)"
else
  echo "  Console dir not set/found — API is live at $B ; set BREATHLINE_ATRIUM_UI_DIR=<console-dist> for the panel at $CONSOLE"
fi

# ── 7 · smoke / D6 ────────────────────────────────────────────────────────────
if [ "$DO_SMOKE" -eq 1 ]; then
  echo "== 7 · operator smoke =="
  BREATHLINE_NODE_API_HOST="$HOST" BREATHLINE_NODE_API_PORT="$PORT" bash "$REPO/scripts/node_smoke.sh" 2>&1 | sed 's/^/    /' \
    || { FAIL=1; echo "  ✗ smoke reported a failure"; }
fi
if [ "$RUN_D6" -eq 1 ]; then
  echo "== 8 · D6 durability report =="
  BREATHLINE_NODE_API_PORT="$PORT" bash "$REPO/scripts/node_d6_report.sh" 2>&1 | sed 's/^/    /' || FAIL=1
fi

# ── teardown / hand-off ───────────────────────────────────────────────────────
if [ "$SMOKE_ONLY" -eq 1 ]; then
  echo "== teardown (--smoke-only) =="; kill "$SV" 2>/dev/null; wait "$SV" 2>/dev/null
  [ "$FAIL" -eq 0 ] && { echo "∞Δ∞ STAND-UP OK (proved, then torn down)."; exit 0; } || die "one or more checks failed above."
else
  if [ "$FAIL" -ne 0 ]; then kill "$SV" 2>/dev/null; die "one or more checks failed above — node stopped."; fi
  echo "∞Δ∞ STAND-UP OK — node LEFT RUNNING on http://$HOST:$PORT (pid $SV)."
  echo "   compare the fingerprint above to your D6 record by hand · stop with:  kill $SV"
  exit 0
fi
