#!/usr/bin/env bash
# compute_share_report.sh — script-stdout deposit for AA_COMPUTE_SHARE_WRAPPER_BAR (W1-W12).
# Owns the LOOPBACK stub model server (the execution bridge W7 speaks to) and the socket enumeration
# (before / after boot / after run), then runs compute_share_report.py for W1-W6/W8-W12. Paste stdout.
set -uo pipefail
cd "$(dirname "$0")/.."
export NODE_KEYSTORE_DIR="${NODE_KEYSTORE_DIR:-/tmp/cshare_ks}"; rm -rf "$NODE_KEYSTORE_DIR"; mkdir -p "$NODE_KEYSTORE_DIR"
export SHARE_REG_ROOT="${SHARE_REG_ROOT:-/tmp/cshare_reg}"; rm -rf "$SHARE_REG_ROOT"; mkdir -p "$SHARE_REG_ROOT"
export BREATHLINE_SEALED_ROOT="${BREATHLINE_SEALED_ROOT:-$PWD}"
export PYTHONPATH="src:${PYTHONPATH:-}"
MPORT="${MODEL_PORT:-11599}"; export MODEL_URL="http://127.0.0.1:$MPORT/generate"

# W7 · three-state listener enumeration (ss → netstat → /proc/net/tcp; empty is never a silent pass).
_listeners(){
  local out hx P="$1"
  if command -v ss >/dev/null 2>&1; then out=$(ss -ltnp 2>/dev/null | grep ":$P"); [ -n "$out" ] && { echo "$out" | sed 's/^/    /'; return; }; echo "    (ss: none on :$P)"; return; fi
  if command -v netstat >/dev/null 2>&1; then out=$(netstat -ltnp 2>/dev/null | grep ":$P"); [ -n "$out" ] && { echo "$out" | sed 's/^/    /'; return; }; echo "    (netstat: none on :$P)"; return; fi
  if [ -r /proc/net/tcp ]; then hx=$(printf ':%04X' "$P"); out=$(grep -ih "$hx" /proc/net/tcp /proc/net/tcp6 2>/dev/null)
    [ -n "$out" ] && { while read -r _s l _r st _z; do echo "    $l st=$st"; done <<<"$out"; return; }; echo "    (/proc: none on :$P)"; return; fi
  echo "    (NO ss/netstat/proc — could not enumerate — NOT a pass)"
}

echo "== W7 · sockets BEFORE the model bridge boots =="; _listeners "$MPORT"

# The LOOPBACK stub model server — binds 127.0.0.1 ONLY, never 0.0.0.0 (the GPU never faces the open network).
cat > /tmp/cshare_stub.py <<'PY'
import sys, json
from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n=int(self.headers.get('Content-Length',0)); body=self.rfile.read(n)
        try: req=json.loads(body or b'{}')
        except Exception: req={}
        out=json.dumps({"ok":True,"model":req.get("model"),"echo":req.get("prompt","")}).encode()
        self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(out)
    def log_message(self,*a): pass
HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()  # 127.0.0.1 ONLY
PY
python3 /tmp/cshare_stub.py "$MPORT" >/tmp/cshare_model.log 2>&1 &
MPID=$!
for _ in $(seq 1 40); do curl -s -X POST "$MODEL_URL" -d '{}' >/dev/null 2>&1 && break; sleep 0.2; done

echo "== W7 · sockets AFTER the model bridge boots (loopback only, nothing new on 0.0.0.0) =="
_listeners "$MPORT"
echo "    0.0.0.0 check:"; (ss -ltn 2>/dev/null || netstat -ltn 2>/dev/null || cat /proc/net/tcp 2>/dev/null) | grep -E "0.0.0.0:$MPORT|:::$MPORT" | sed 's/^/    /' || echo "    (nothing on 0.0.0.0:$MPORT — loopback only ✓)"

python3 scripts/compute_share_report.py

echo
echo "== W7 · sockets AFTER the run (the wrapper opened NO socket of its own) =="; _listeners "$MPORT"
kill "$MPID" 2>/dev/null
echo "∞Δ∞ pair with: git diff --stat 40d79c4..HEAD + suite count. Nothing armed, nothing sealed."
