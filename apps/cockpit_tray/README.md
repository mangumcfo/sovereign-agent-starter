# Cockpit Tray — six desks, one gate

∞Δ∞ Desks = lanes · belt = the board · center = the human gate. ∞Δ∞

One local page that shows, at a glance, who last moved on the coordination board
(AA / Tiger / GB / No1), how many gated acts await the human hand (KM), what the
node's receipt tail is, and — just as loudly — what is **not** live.

## What honest means here

- **Every tile is bound or marked.** A tile either executes a live read during
  the page render, or carries a painted OUT mark in the visible UI. There is no
  third kind of tile.
- **Every probe can fail, visibly.** Nothing is cached between renders. Kill a
  tile's source and the next paint (auto-refresh, 5s) shows `SOURCE DEAD` with
  the failing URL or path — never a stale number.
- **No tile claims more certainty than its source.** Node API answering 401
  paints `AUTH-REQUIRED` with the fix, not a fake zero. The sources-answering
  count is derived from this render's probes and cannot read full unless every
  probed source answered.
- **The OUT strip is past tense on purpose.** Its six lines are facts as they
  stood at the P0 inventory (2026-08-29), not live claims.

## Launch

```bash
cd /path/to/sovereign-agent-starter
python3 -m venv --system-site-packages .venv && ./.venv/bin/pip install -e .

./apps/cockpit_tray/launch.sh                # → http://127.0.0.1:8479
```

To let the node-fed tiles authenticate (contract auth model
`principal_id-bearer`):

```bash
NODE_API_BEARER='<principal_id>:<secret>' ./apps/cockpit_tray/launch.sh
```

The secret lives in `~/.breathline/credentials/<principal_id>.token` on the
node's own iron. Without the variable the tray still runs — the node tiles
paint `AUTH-REQUIRED` and say exactly that.

Binds loopback only and refuses any other host. Reach from another machine is a
Port-governed crossing, not a bind flag.

## Sources (all read per render)

| Tile | Source |
|---|---|
| AA / Tiger / GB / No1 desks | `coordination/TURN_BOARD.md` — last row per seat, zoom expands the full row |
| KM desk + center gate tile | `GET :8421/api/v1/breath_gate/pending` (bearer) |
| Center receipt tail | `GET :8421/api/v1/inference/receipts` — tail record's own hash field, named |
| Grok Bot desk | nothing — painted OUT mark; no Bot process runs on this iron |
| Zoom strip | board path · v1.1 surface `:8477` liveness · both suite locations by name, existence-checked |

It holds no state, no store, no history. It is a lens; the node is the truth.
