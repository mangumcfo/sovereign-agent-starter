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
export BREATHLINE_NODE_NAME=UniversalSovereignNode      # this node's stable id (key = NODENAME.nodekey.json)
export BREATHLINE_NODE_LOOPBACK_OWNER=owner             # your principal id — any label; do NOT use angle brackets
bash scripts/sovereign_node_up.sh                       # binds 127.0.0.1:8421 only
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
export BREATHLINE_ATRIUM_UI_DIR=/path/to/console-dist   # then open http://127.0.0.1:8421/atrium/
```

## Stop / restart

The API (and the compute-share puller, if you run one) are ordinary processes. Start them detached so
they survive closing your shell; stop them by name.
```bash
# start detached (survives ssh close):  setsid keeps it in its own session
setsid bash scripts/sovereign_node_up.sh </dev/null >/tmp/nodeapi.log 2>&1 &
# stop:
pkill -f sovereign_agent.node_api.server
pkill -f compute_share_pull            # if the puller is running
```

## Persistence across reboot (optional)

`setsid` survives an ssh close, **not** a reboot. To bring the node back after a power cycle, add a
`@reboot` line to your own crontab (user cron — no root, no systemd needed). Back up first.
```bash
crontab -l > /tmp/crontab.bak.$(date +%F) 2>/dev/null
( crontab -l 2>/dev/null; \
  echo '@reboot sleep 30; setsid bash ~/sovereign-agent-starter/scripts/sovereign_node_up.sh </dev/null >/tmp/nodeapi.log 2>&1 &' \
) | crontab -
```
The keystore is durable (§ stand-up), so a reboot returns the **same** identity — the `@reboot` line
only restarts the *process*, never re-mints the key.

## Smoke (operator parity list)

```bash
BREATHLINE_NODE_API_PORT=8421 scripts/node_smoke.sh
```
Checks: node status · onboard **decline → 0 files** · onboard accept → **receipt verifies** · gate **propose →
pending → approve** (`real:true`) · Port **open → sanction** (value-free receipt) · Files **store → verify** ·
Peers **refuse** (`residual_claim=None`) · **no private key** in any response.

## D6 durability report (one command → pasteable deposit)

Proves identity is stable across a restart, keystore digest unchanged, loopback-only, and the smoke passes
**after** a restart — all in one block you paste back as the deposit. **Use plain values, never angle brackets**
(a `<` is a shell redirect and will error).

```bash
export NODE_KEYSTORE_DIR=~/.sovereign_keystore
export BREATHLINE_NODE_NAME=UniversalSovereignNode
export BREATHLINE_NODE_LOOPBACK_OWNER=owner    # your principal id (plain text, no < >)
export PYTHONPATH=src                          # only if you did not `pip install -e .`
bash scripts/node_d6_report.sh                 # prints the whole deposit; paste it verbatim
```

## Report — one status document

The node's state has a **single source**: `sovereign_agent.agent.local_mind.facts()`. The CLI, the API,
and the console all read that one function — they cannot disagree.
```bash
python3 scripts/node_agent.py status          # CLI
curl -s http://127.0.0.1:8421/api/v1/status   # API — byte-for-byte the same facts
# console: http://127.0.0.1:8421/atrium/ → Home "Node Status · live" card, or type /status in Chat
```
One document reports: node fingerprint · GPU three-state (free/total/util, or "no-check"/"error") ·
peers · grants + units offered · puller up/down · model up/down.

## Talk — the node's local mind (loopback only)

An optional local mind reads node state and **proposes** — it never executes. It calls a loopback model
(Ollama/vLLM); a non-loopback model URL is refused, not tried. With no model up it still returns facts +
exact proposals from the read tools.
```bash
python3 scripts/node_agent.py ask  "what expires soon and what should I do?"   # needs --model or a default
python3 scripts/node_agent.py chat                                             # REPL
```
Console Chat builtins (local, no model, nothing executed): `/status` (facts) · `/propose` (the exact
renew/revoke commands for each grant, copy-to-keyboard) · `/help`.

## Capacity ops — earn: offer · renew · revoke · puller

Offering compute is **human-gated, time-bound, deny-by-default**. The node reports and proposes; **you**
issue. (If the iron rents its GPU elsewhere, `--min-gpu-free-mib` makes the offer *refuse to publish*
while the card is busy — rental income first.)
```bash
# OFFER / RENEW (re-issue with a fresh window; requires an --approver — a human):
NODE_KEYSTORE_DIR=~/.sovereign_keystore python3 scripts/compute_share_offer.py \
  --node UniversalSovereignNode --units 100 --renew-days 7 --approver <you> \
  --approval-ref <ref> --requester-name <peer> --requester-public-hex <128hex> \
  --models <model...> --registry ~/.sovereign_share/registry \
  --emit-grant ~/.sovereign_share/grant_<peer>.json --min-gpu-free-mib 20000
# REVOKE (live — the puller reloads the grant each poll and denies the next job ~5s later):
rm ~/.sovereign_share/grant_<peer>.json
# PULLER (the outbound worker that services a peer's jobs): start / stop
setsid python3 scripts/compute_share_pull.py --node UniversalSovereignNode \
  --registry ~/.sovereign_share/registry --grant-file ~/.sovereign_share/grant_<peer>.json \
  --beard-host <peer_host> --beard-port <port> --model-url http://127.0.0.1:11434/api/generate \
  --min-gpu-free-mib 20000 --poll-seconds 5 </dev/null >/tmp/puller.log 2>&1 &
pkill -f compute_share_pull
```
Every step moves the one status document (§ Report). The node **never** issues, renews, or revokes on its
own — `/status` and `/propose` only *hand you* the exact command.

## Operator posture — status · propose · gate, under your key, no silent exec

- **status** — `GET /api/v1/status` (the one doc), `/api/v1/manifest`, `/api/v1/node`: identity + state.
- **propose** — the app/agent proposes a governed act (`/onboard/run`, `/storage/datum`, `/port/crossing`); it
  never holds the mandate root and never self-approves.
- **gate** — a gated act is **default-deny** until *you* (the owner) dispose it. Raise → dispose:
  ```bash
  curl -s -X POST http://127.0.0.1:8421/api/v1/port/crossing \
    -H 'Content-Type: application/json' -d '{"target":"<t>","instruction":{"send":"ref://…"}}'
  curl -s http://127.0.0.1:8421/api/v1/breath_gate/pending                       # it's waiting
  curl -s -X POST http://127.0.0.1:8421/api/v1/breath_gate/<id>/deny  -d '{}'     # or …/approve
  # a Port crossing you approve via …/port/crossing/<id>/sanction (owner-only)
  ```
  A **non-owner** principal is refused at the owner gate (`403`); a **disposed or unknown** gate is `404`.
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
