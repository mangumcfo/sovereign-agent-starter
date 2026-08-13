#!/usr/bin/env bash
# node_smoke.sh — the operator smoke against a running loopback node (Beard / Dragon parity list).
# Usage: BREATHLINE_NODE_API_PORT=8421 scripts/node_smoke.sh   (node must be up via sovereign_node_up.sh)
# Loopback owner needs no bearer token. Asserts: no private key in any response.
set -euo pipefail
HOST="${BREATHLINE_NODE_API_HOST:-127.0.0.1}"
PORT="${BREATHLINE_NODE_API_PORT:-8421}"
B="http://$HOST:$PORT/api/v1"
j() { curl -s -H 'Content-Type: application/json' "$@"; }

echo "== 1 · node status =="
j "$B/../healthz" >/dev/null 2>&1 || true
j "$B/manifest" | head -c 200; echo

echo "== 2 · onboard decline → 0 files =="
j -X POST "$B/onboard/ceremony" -d '{"disposition":"decline"}'; echo

echo "== 3 · onboard accept → receipt verifies (sandbox) =="
j -X POST "$B/onboard/ceremony" -d '{"disposition":"accept","name":"smoke"}' | tr ',' '\n' | grep -E 'verified|fingerprint'

echo "== 4 · gate: propose → pending → approve =="
RID=$(j -X POST "$B/onboard/run" -d '{"rationale":"smoke gated act"}' | sed -n 's/.*"req_id": *"\([^"]*\)".*/\1/p')
echo "  req_id=$RID"; j "$B/breath_gate/pending" | grep -o '"count": *[0-9]*'
j -X POST "$B/breath_gate/$RID/approve" | grep -o '"real": *true' || echo "  approve FAILED"

echo "== 5 · Port open → sanction (value-free receipt) =="
CID=$(j -X POST "$B/port/crossing" -d '{"target":"example.com","instruction":{"send":"ref://m1"}}' | sed -n 's/.*"crossing_id": *"\([^"]*\)".*/\1/p')
j -X POST "$B/port/crossing/$CID/sanction" -d '{"approval_ref":"smoke #1"}' | grep -o '"crossed": *true' || echo "  sanction FAILED"

echo "== 6 · Files store → verify (integrity) =="
OID=$(j -X POST "$B/storage/datum" -d '{"chunks":["a","b"],"visibility":"private"}' | sed -n 's/.*"object_id": *"\([^"]*\)".*/\1/p')
j -X POST "$B/storage/datum/$OID/verify" -d '{"chunks":["a","b"]}' | grep -o '"integrity": *"verified"' || echo "  verify FAILED"

echo "== 7 · Peers refuse (residual_claim=None) =="
j -X POST "$B/peers/refuse" -d '{"other":"peer-x"}' | grep -o '"residual_claim": *null' || echo "  refuse: residual_claim NOT null"

echo "== 8 · no private key leaked in any surface =="
if j "$B/manifest" "$B/node" | grep -iqE 'private_key|secret_key|"d":'; then echo "  LEAK DETECTED"; exit 1; else echo "  clean (no private key in responses)"; fi
echo "SMOKE COMPLETE"
