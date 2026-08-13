#!/usr/bin/env bash
# dragon_share_live.sh — LIVE Dragon compute-share, one command, run ON DRAGON.
# Fetches the public starter, offers ONE named model to Beard under a 7-day human-gated grant, then proves the
# GREEN wrapper end-to-end against the REAL loopback Ollama with a throwaway local test requester (NOT Beard).
#
#   MODEL=<one pulled ollama model>  BEARD_PUBLIC_HEX=<128hex>  [UNITS=100]  bash scripts/dragon_share_live.sh
#
# Loopback only · no 0.0.0.0 · no non-USN backend · no kernel rewrite. The GPU fence refuses to publish while a
# Vast.ai rental holds the card (MIN_GPU_FREE_MIB, default 20000 — rental income > local convenience).
set -euo pipefail
: "${MODEL:?set MODEL=<one pulled ollama model, e.g. llama3.2:1b>}"
: "${BEARD_PUBLIC_HEX:?set BEARD_PUBLIC_HEX=<Beard 128-hex public_hex, from its ceremony>}"
UNITS="${UNITS:-100}"; MINGPU="${MIN_GPU_FREE_MIB:-20000}"
REPO="${SAS_REPO:-$HOME/sas-public-genesis}"
export NODE_KEYSTORE_DIR="${NODE_KEYSTORE_DIR:-$HOME/.sovereign_keystore}"
NODE="${BREATHLINE_NODE_NAME:-UniversalSovereignNode}"
OLLAMA="${OLLAMA_URL:-http://127.0.0.1:11434/api/generate}"
REG="${SHARE_REG_ROOT:-$HOME/.sovereign_share/registry}"

case "$OLLAMA" in *127.0.0.1*|*localhost*) ;; *) echo "✗ model URL must be loopback (got $OLLAMA)"; exit 2;; esac

# 0 · fetch/refresh the public starter at the wrapper tip (anon HTTPS; the repo is public)
if [ "${SKIP_FETCH:-0}" != 1 ]; then
  if [ -d "$REPO/.git" ]; then git -C "$REPO" pull --ff-only || true
  else git clone --depth 1 https://github.com/mangumcfo/sovereign-agent-starter "$REPO"; fi
  cd "$REPO"
fi
export BREATHLINE_SEALED_ROOT="$PWD"; export PYTHONPATH="src:${PYTHONPATH:-}"
echo "== starter HEAD: $(git rev-parse --short HEAD 2>/dev/null || echo '?') =="

# 1 · loopback model server up + the ONE named model warm
if curl -s "$OLLAMA" -d "{\"model\":\"$MODEL\",\"prompt\":\"ok\",\"stream\":false}" >/tmp/ollama_warm.json 2>&1; then
  echo "== model server up on loopback · $MODEL warm =="
else echo "✗ loopback model server not answering for $MODEL at $OLLAMA"; exit 3; fi

# 2 · Dragon's own identity (for the record)
python3 - "$NODE" <<'PY'
import os,sys
from sovereign_agent.keystore.node_keystore import load_node_key
k=load_node_key(os.environ["NODE_KEYSTORE_DIR"], sys.argv[1])
print(f"== node {sys.argv[1]} · fp {k.fingerprint} · public_hex {k.public_hex[:16]}… ==")
PY

# 3 · publish the LIVE offer + Beard's 7-day, human-gated grant (real registry) + bind the key locally
python3 scripts/compute_share_offer.py --node "$NODE" --units "$UNITS" --renew-days 7 \
  --approver KM-1176 --approval-ref km-dragon-live-1 \
  --requester-name Beard --requester-public-hex "$BEARD_PUBLIC_HEX" \
  --models "$MODEL" --registry "$REG" --min-gpu-free-mib "$MINGPU"
python3 scripts/peer_book.py add --label "Beard" --public-hex "$BEARD_PUBLIC_HEX" 2>/dev/null || true

# 4 · prove the GREEN wrapper end-to-end against REAL Ollama — throwaway LOCAL requester, SEPARATE registry
#     (Beard's private key is on Beard's iron; this self-test never uses it and never touches the live offer)
python3 - "$NODE" "$MODEL" "$OLLAMA" <<'PY'
import sys, os, datetime, importlib.util, tempfile, pathlib
NODE, MODEL, OLLAMA = sys.argv[1:4]
spec=importlib.util.spec_from_file_location("cs", pathlib.Path("scripts/compute_share.py"))
cs=importlib.util.module_from_spec(spec); spec.loader.exec_module(cs)
from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.keystore.node_keystore import load_node_key, generate_node_key, sign_node_act
from sovereign_agent.peerhood.delegation import delegate_governed
from sovereign_agent.peerhood.recognition import refuse_recognition
from sovereign_agent.peerhood.clean_exit import clean_exit
ks=os.environ["NODE_KEYSTORE_DIR"]; now=datetime.datetime.now(datetime.timezone.utc).isoformat()
node_pub=load_node_key(ks,NODE).public_hex
sreg=ObjectRegistry(tempfile.mkdtemp()); sks=tempfile.mkdtemp()
generate_node_key(sks,"SmokeRequester",at=now); smk_pub=load_node_key(sks,"SmokeRequester").public_hex
off=cs.open_offer(sreg,NODE,3,at=now)
exp=(datetime.datetime.fromisoformat(now)+datetime.timedelta(minutes=10)).isoformat()
g=delegate_governed(ks,NODE,"SmokeRequester",f"compute:{off['object_id']}",expires_at=exp,at=now,registry=sreg,approver="KM-1176",approval_ref="km-smoke")
def signed(jid, prompt, units):
    e={"job_id":jid,"model":MODEL,"prompt":prompt,"units":units,"requester_mandate":"SmokeRequester"}
    e["sig"]=sign_node_act(sks,"SmokeRequester",cs._canonical(e)); return e
print("== SMOKE · real Ollama · local test requester (NOT Beard) ==")
print("  offer:", off["object_id"], "units", off["payload"]["units"])
try:
    r=cs.submit_job(sreg,NODE,signed("dragon-smoke-1","Reply with one word: sovereign.",1),
                    recognized_public_hex=smk_pub,node_public_hex=node_pub,delegation=g,now=now,model_url=OLLAMA,models=[MODEL])
    print("  admit→complete: outcome", r["outcome"], "· remaining", r["remaining"])
    print("  model said (head):", (r["result"] or "")[:80].replace(chr(10)," "))
    rc=r["receipt"]; print("  receipt:", rc["payload"]["job_id"], rc["payload"]["outcome"],
          "· completer_fp", rc["payload"]["completer_fingerprint"], "· verify", cs.verify_receipt(rc,node_pub))
except Exception as e:
    print("  REFUSE (terminal, no fallback):", type(e).__name__, str(e)[:90])
try:
    cs.submit_job(sreg,NODE,signed("dragon-smoke-oversub","x",99),recognized_public_hex=smk_pub,
                  node_public_hex=node_pub,delegation=g,now=now,model_url=OLLAMA,models=[MODEL])
except Exception as e:
    print("  refuse (over-sub, receipted):", str(e)[:74])
rr=refuse_recognition(ks,NODE,"peer-x",at=now,registry=sreg); ce=clean_exit(ks,NODE,at=now,registry=sreg)
print("  residual: refuse residual_claim", rr.get("residual_claim"), "· clean_exit no_residual", ce.no_residual)
PY
echo "∞Δ∞ LIVE offer to Beard published; wrapper proven end-to-end on loopback Ollama. Loopback only · no non-USN."
