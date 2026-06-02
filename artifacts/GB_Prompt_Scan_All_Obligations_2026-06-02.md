# GB Prompt — Scan ALL obligations (unified clarity, no loss)

**From:** Tiger · **For:** GB (planning lane) · **Relay:** KM · 2026-06-02
**Goal:** one authoritative, current view of **every** obligation across all ledgers so nothing is lost
and we can see, at a glance, what's open / done / coarse / stale / orphaned.

## Ledgers to scan (all node-local B32; NEVER touch `Tiger_1a/cylinders`)

1. **Coordination** — `sovereign-agent-starter/memory/obligations/tiger_coordination/obligations.ndjson`
   (Tiger↔G program plan; currently ~11 closed / ~9 open after the FEC + granularity passes).
2. **Mait build** — `mangumcfo-vault/clients/mait/build/obligations/` (MAIT-1…14; render is `build/obligations/VIEW.md`).
3. **MH e-sign** — `mangumcfo-vault/clients/maple-hollow-landscaping/planning/esign-obligations/` (MHE-1…16).
4. **FEC demo** — `sovereign-agent-starter/memory/obligations/fec_demo/` (the runnable-demo ledger).
5. **Sweep** for any other `obligations.ndjson` / `obligations/` you find under the repos + the vault.

Read each via `ObligationLedger(root=...).replay()` (open/closed/all) + `verify_chain()` — don't hand-parse.

## Produce: `artifacts/OBLIGATIONS_MASTER_INDEX_2026-06-02.md`

- **Rollup table:** per ledger — open / closed / total + chain-valid (Y/N).
- **Full index:** every obligation — id, title, owner, status, ref, evidence tier (for closed), and a
  **granularity flag** (L0/L1 = closeable ✓ · coarse/epic = ⚠ needs split) per
  `Packet_Granularity_Definition_v0.2.md`.
- **Attention list:** (a) any coarse/epic still open → recommend the split; (b) anything **stale**
  (superseded by reality, e.g. references the LLC as pending); (c) **orphans** (closed with weak/E0-ish
  evidence, or open with no clear owner); (d) **cross-ledger duplicates** (same work tracked twice).
- **Gaps:** real work in flight that has **no** obligation yet (e.g. MH own-domain+email — see
  `maple-hollow-landscaping/planning/deliverables/2026-06-02_domain-and-email-setup.md`; ATR-2/ATR-3/ATR-4;
  FEC-T1..3; BG-1..2 already exist in coordination — confirm).
- **One-screen "what's next" per lane** (Tiger / GB / Mait / KM-gate).

## Constraints
- Read-only scan + a durable index artifact. Do **not** mutate ledgers in this pass (propose changes; Tiger/KM apply).
- Honest labeling; cite each ledger path. Two-writers fence holds.

∞Δ∞ One index, total clarity. Over to GB.
