# Live Node Runbook — wire the Atrium to a real node (`?api=live`)

**What this gives you:** the Atrium stops reading mock data and reads/writes the **real obligation
ledger** over HTTP — the Obligations lens, the FEC card's ledger state, and book-review feedback all
become live. Proven 2026-06-02: served the real coordination ledger (5 open / 24 closed / 29) with
auth + CORS to a file:// Atrium.

## Architecture (already built — this is just turning it on)
- **Node API:** Flask app on `http://127.0.0.1:8421/api/v1` (`sovereign_agent/node_api/server.py`). CORS open for local dev; serves `/obligations` (GET list, POST open/approve/close) from a real `ObligationLedger`.
- **Atrium:** `api.js` `LIVE_BASE` already = `http://127.0.0.1:8421/api/v1`. In `?api=live` it sends `Authorization: Bearer <principal_id>:<secret>` from `localStorage.breathline_atrium_token`.
- **Auth (CONSTITUTION §1):** every call carries a principal token; verified against `~/.breathline/credentials/<principal_id>.token` (0600). No hardcoded principals.

## Steps (3)

**1. Mint your token** (once):
```
cd ~/work-repos/sovereign-agent-starter
scripts/mint_node_token.sh KM-1176
# prints:  Atrium token (...): KM-1176:<secret>   ← copy this
```

**2. Start the node** (leave it running; serves the real coordination ledger by default):
```
scripts/run_node_api.sh
# Node API -> http://127.0.0.1:8421/api/v1  (ledger: .../memory/obligations/tiger_coordination)
```
*(To serve a different/scratch ledger: `OBLIGATION_LEDGER_ROOT=/path scripts/run_node_api.sh`.)*

**3. Point the Atrium at it.** Open `atrium-standalone.html`, then in the browser console (F12):
```
localStorage.setItem('breathline_atrium_token','KM-1176:<secret>');   // from step 1
location.search = '?api=live';                                        // reloads in live mode
```
Now **Work → Obligations** (and the FEC card's "Packet ledger state", and the Series lens) render from the **live ledger**. The top banner flips from MOCK to live. Switch back any time with `?api=mock`.

## Verify (optional)
```
curl -s -H "Authorization: Bearer KM-1176:<secret>" http://127.0.0.1:8421/api/v1/obligations | python3 -m json.tool | head
```

## Honest edges
- This is the **dev** Flask server (single host, permissive CORS) — production tightens CORS to a node-local allowlist + TLS.
- Writes from the Atrium (e.g. book-feedback → `POST /obligations`) land on whatever ledger you pointed at — point it at a scratch root if you don't want to add to the coordination ledger while testing.
- Material obligations still can't close without the breath-gate (BG-1/2) — the live node wires the real `HumanApprovalGate` + `ComplianceEngine` attestor.

∞Δ∞ The lens now reads the real chain. Mock → live, one flag. ∞Δ∞
