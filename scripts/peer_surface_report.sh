#!/usr/bin/env bash
# peer_surface_report.sh — script-stdout deposit for AA_PEER_HTTP_SURFACE_BAR (H1–H10).
# Boots a live loopback node, exercises every peer route incl. refusals, the H2 forge check, the H3 tamper pair,
# sockets before/after (H7), re-runs refuse/clean_exit/Port (H8), and fp+digest before/after (H9). Paste stdout.
set -uo pipefail
cd "$(dirname "$0")/.."
KS="${NODE_KEYSTORE_DIR:-/tmp/peer_surface_ks}"; rm -rf "$KS"; mkdir -p "$KS"
export NODE_KEYSTORE_DIR="$KS" BREATHLINE_NODE_NAME=UniversalSovereignNode BREATHLINE_NODE_LOOPBACK_OWNER=owner
export SUBSTRATE_STORAGE_ROOT=/tmp/peer_surface_store OBLIGATION_LEDGER_ROOT=/tmp/peer_surface_obl
rm -rf /tmp/peer_surface_store /tmp/peer_surface_obl
HOST=127.0.0.1; PORT="${PORT:-8461}"; B="http://$HOST:$PORT/api/v1"
j(){ curl -s -H 'Content-Type: application/json' "$@"; }
pyf(){ python3 -c "import sys,json;print(json.load(sys.stdin).get('$1',''))"; }
_dg(){ sha256sum "$KS/UniversalSovereignNode.nodekey.json" 2>/dev/null | cut -d' ' -f1; }
# H7 listener enumeration with fallbacks (AA 5ede8a8 carry).
# THREE distinct outcomes — never share a line between "nothing listening" and "cannot look":
#   • a method enumerated AND matched      -> print the lines
#   • a method enumerated, no match        -> "none listening on :$PORT"   (a real answer)
#   • no method available at all           -> "could not enumerate — NOT a pass"
# Bug fixed: test OUTPUT LENGTH, not grep's exit — grep exits 2 on a missing /proc/net/tcp6
# even when /proc/net/tcp matched, and `&&` would discard the correct out.
_listeners(){
  local out hx
  if command -v ss >/dev/null 2>&1; then
    out=$(ss -ltnp 2>/dev/null | grep ":$PORT")
    [ -n "$out" ] && { echo "$out" | sed 's/^/  /'; return; }
    echo "  (ss: none listening on :$PORT)"; return
  fi
  if command -v netstat >/dev/null 2>&1; then
    out=$(netstat -ltnp 2>/dev/null | grep ":$PORT")
    [ -n "$out" ] && { echo "$out" | sed 's/^/  /'; return; }
    echo "  (netstat: none listening on :$PORT)"; return
  fi
  if [ -r /proc/net/tcp ] || [ -r /proc/net/tcp6 ]; then
    hx=$(printf ':%04X' "$PORT")
    out=$(grep -ih "$hx" /proc/net/tcp /proc/net/tcp6 2>/dev/null)   # -h: no filename prefix -> fields align
    [ -n "$out" ] && {                                               # awk may be absent on the fallback's target hosts too
      echo "  (ss/netstat missing — /proc/net/tcp, local-port hex $hx):"
      while read -r _sl laddr _raddr st _rest; do echo "    $laddr st=$st"; done <<<"$out"; return; }
    echo "  (/proc/net/tcp enumerated — none listening on :$PORT, local-port hex $hx)"; return
  fi
  echo "  (NO ss / netstat / /proc data — could not enumerate — this is NOT a pass)"
}

echo "∞Δ∞ PEER HTTP SURFACE REPORT — $(date -u +%FT%TZ) — host $(hostname)"
echo "git HEAD: $(git rev-parse --short HEAD 2>/dev/null || echo '(not a checkout)')"
FP0=$(python3 - <<PY
import os,datetime
from sovereign_agent.keystore.node_keystore import has_node_key, generate_node_key, load_node_keypair
ks=os.environ["NODE_KEYSTORE_DIR"];nid=os.environ["BREATHLINE_NODE_NAME"]
has_node_key(ks,nid) or generate_node_key(ks,nid,at=datetime.datetime.now(datetime.timezone.utc).isoformat())
print(load_node_keypair(ks,nid).fingerprint)
PY
)
DG0=$(_dg); echo "fp before: $FP0   digest before: ${DG0:0:32}…"
echo "== H7 · sockets BEFORE boot =="; _listeners
nohup python3 -m sovereign_agent.node_api.server --host $HOST --port $PORT >/tmp/peer_node.log 2>&1 &
SV=$!; for _ in $(seq 1 40); do curl -s "$B/manifest" >/dev/null 2>&1 && break; sleep 0.5; done
echo "== H7 · sockets AFTER boot (only the node's own declared bind) =="; _listeners

PEERPUB=$(python3 -c "print('ab'*64)")
echo "== H1 · /peers/recognize returns a HALF (states what's missing + who supplies it) =="
REC=$(j -X POST "$B/peers/recognize" -d "{\"peer_public_hex\":\"$PEERPUB\",\"peer_name\":\"beard\"}")
echo "  request : {\"peer_public_hex\":\"ab…(128)\",\"peer_name\":\"beard\"}"
echo "  response: $REC"
OBJH=$(echo "$REC" | pyf obj_hash); MYSIG=$(echo "$REC" | pyf my_half_sig); MYPUB=$(echo "$REC" | pyf my_public_hex)

echo "== H2 · ⛔ returned sig verifies as THIS node, NOT the peer (name-independent) =="
echo -n "  verify(my_half_sig, my_public_hex)  -> "; j -X POST "$B/peers/verify/message" -d "{\"hash\":\"$OBJH\",\"sig\":\"$MYSIG\",\"sender_public_hex\":\"$MYPUB\"}"; echo
echo -n "  verify(my_half_sig, PEER_public_hex)-> "; j -X POST "$B/peers/verify/message" -d "{\"hash\":\"$OBJH\",\"sig\":\"$MYSIG\",\"sender_public_hex\":\"$PEERPUB\"}"; echo
echo "== H4 · peer key is an INPUT — recognize with none → refuse (no lookup/default) =="
echo -n "  "; j -X POST "$B/peers/recognize" -d '{}'; echo

echo "== H3 · message sign → verify genuine True, one-byte-flip False (protection, not error) =="
MSG=$(j -X POST "$B/peers/message" -d '{"text":"hello, peer"}')
MH=$(echo "$MSG" | pyf hash); MSIG=$(echo "$MSG" | pyf sig)
TSIG=$(python3 -c "s='$MSIG';print(s[:-2]+('00' if s[-2:]!='00' else '11'))")
echo -n "  genuine     -> "; j -X POST "$B/peers/verify/message" -d "{\"hash\":\"$MH\",\"sig\":\"$MSIG\",\"sender_public_hex\":\"$MYPUB\"}"; echo
echo -n "  tampered sig-> "; j -X POST "$B/peers/verify/message" -d "{\"hash\":\"$MH\",\"sig\":\"$TSIG\",\"sender_public_hex\":\"$MYPUB\"}"; echo

echo "== H8 · already-GREEN rows unchanged =="
echo -n "  refuse     -> "; j -X POST "$B/peers/refuse" -d '{"other":"peer-x"}'; echo
echo -n "  clean_exit -> "; j -X POST "$B/peers/clean_exit" -d '{}'; echo
CID=$(j -X POST "$B/port/crossing" -d '{"target":"example.com","instruction":{"send":"ref://m1"}}' | pyf crossing_id)
echo -n "  port sanction (value-free) -> "; j -X POST "$B/port/crossing/$CID/sanction" -d '{"approval_ref":"h8"}'; echo

echo "== H6 · no private material in any response (incl. errors) =="
if { echo "$REC$MSG"; j "$B/node"; j -X POST "$B/peers/recognize" -d '{}'; } | grep -iqE 'private_key|secret_key|"d":[0-9]'; then
  echo "  ✗ LEAK DETECTED"; else echo "  ✓ clean — no private key in any body"; fi

echo "== H7 · sockets AFTER (no new listener beyond the node's bind) =="; _listeners
kill "$SV" 2>/dev/null
FP1=$(python3 -c "import os;from sovereign_agent.keystore.node_keystore import load_node_keypair;print(load_node_keypair(os.environ['NODE_KEYSTORE_DIR'],os.environ['BREATHLINE_NODE_NAME']).fingerprint)")
DG1=$(_dg)
echo "== H9 · identity unchanged across the whole run =="
echo "  fp     : $FP0 == $FP1  -> $([ "$FP0" = "$FP1" ] && echo UNCHANGED || echo CHANGED)"
echo "  digest : $([ "$DG0" = "$DG1" ] && echo UNCHANGED || echo CHANGED)"
echo "∞Δ∞ PEER SURFACE REPORT END — pair with git diff --stat + suite count for the deposit."
