# Operate a node — durable identity on your own iron, loopback only

How to stand a **durable** sovereign node you operate daily: keys on your iron, a **stable identity across boot**,
and the gate + Port reachable from Node Home on loopback. Same recipe on any machine (Dragon, a laptop, a server).

> Nothing here is a token, a coin, a yield, or a security. No escrow, no second recovery authority — the root of
> your identity is a file on your iron, under your control.

## Stand it up (one command, idempotent)

```bash
# once: install the starter (crypto substrate is vendored — no BREATHLINE_SEALED_ROOT needed)
git clone https://github.com/mangumcfo/sovereign-agent-starter.git && cd sovereign-agent-starter
python3 -m venv --system-site-packages .venv && ./.venv/bin/pip install -e .

# every boot: durable keystore + owner + loopback serve (provisions the key ONCE; never re-mints)
export NODE_KEYSTORE_DIR=~/.sovereign_keystore          # your key lives here, on this iron
export BREATHLINE_NODE_NAME=UniversalSovereignNode      # this node's stable id (key = <name>.nodekey.json)
export BREATHLINE_NODE_LOOPBACK_OWNER=<your-principal>  # owner of the owner-gated routes
./.venv/bin/python scripts/sovereign_node_up.sh         # binds 127.0.0.1:8421 only
```

- **Durable, not ephemeral:** the key is written once to `$NODE_KEYSTORE_DIR/<name>.nodekey.json` (0600). On every
  later boot the node **loads** it — `generate_node_key` refuses to overwrite, so a reboot **never mints a new
  identity**. Your fingerprint is stable across restart.
- **Loopback only:** the API binds `127.0.0.1` by default; an off-loopback dev bind **fails loud**. Nothing
  listens off loopback. No public bind, no wide CORS.
- **Owner aligned:** `BREATHLINE_NODE_LOOPBACK_OWNER` is the principal you call owner-gated routes as (no bearer
  token needed on loopback).

Node Home (the console) points at *this* node only:
```bash
export BREATHLINE_ATRIUM_UI_DIR=<console-dist>   # then open http://127.0.0.1:8421/atrium/
```

## Smoke (operator parity list)

```bash
BREATHLINE_NODE_API_PORT=8421 scripts/node_smoke.sh
```
Checks: node status · onboard **decline → 0 files** · onboard accept → **receipt verifies** · gate **propose →
pending → approve** (`real:true`) · Port **open → sanction** (value-free receipt) · Files **store → verify** ·
Peers **refuse** (`residual_claim=None`) · **no private key** in any response.

## Operator posture — status · propose · gate, under your key, no silent exec

- **status** — `GET /api/v1/manifest`, `/api/v1/node`: the node's identity and state.
- **propose** — the app/agent proposes a governed act (`/onboard/run`, `/storage/datum`, `/port/crossing`); it
  never holds the mandate root and never self-approves.
- **gate** — a gated act is **default-deny** until *you* (the owner) approve it at `/breath_gate/<id>/approve`.
  **No act executes silently.** Reaching anything external is a Port crossing you sanction by hand.
- Your key signs; the node attests; you dispose. That is the whole loop.

## Recovery — where the key lives, and what to do if it's gone

- **Key material:** one file, `$NODE_KEYSTORE_DIR/<name>.nodekey.json`, mode **0600**, on **your iron**. The
  private scalar is written only to that file and is **never returned** by any API response or CLI output.
- **No escrow, no second recovery authority:** no service holds a copy, and no one can reconstruct it for you.
  This is the point — a custodian is the thing the node refuses to be.
- **Backups are yours:** if you want recovery, back up the keystore file yourself, offline, under your own
  custody (an encrypted drive, a paper copy of the file). Restore = put the file back at
  `$NODE_KEYSTORE_DIR/<name>.nodekey.json` (0600) and boot; the identity returns, fingerprint unchanged.
- **Lose the file = lose that identity.** There is no back door. A fresh key is a **new** node, not the old one
  recovered. Family/generational continuity is a governed hand-off (a quorum epoch), not a vendor reset.

## What this node is / is not

- **Is:** a durable self-held identity on your iron; a human gate over acts; offline-verifiable receipts; a
  governed Port for anything external. Loopback-only by default.
- **Is not:** a hosted service, a custodian, or a multi-node federation. **No p2p claim until a second node
  exists** — `mutual_recognition` and inter-node messaging are two-node acts and are not exposed on a single
  process. Single-node acts (`refuse`, `clean_exit`) are present; see `docs/CALLABLE_MAP.md`.
