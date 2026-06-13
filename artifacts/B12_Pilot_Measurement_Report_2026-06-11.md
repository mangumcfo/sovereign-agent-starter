# B12 Pilot Measurement Report — THE FAN-OUT GATE (GB, sealed 2026-06-11)

> Per `GB_ReviewReady_Rail_Spec_2026-06-10.md` §R3: the pilot is measured, and the measurement decides fan-out. B12 published 2026-06-11 — Series 1 complete (12/12 on KDP). All figures below from the ledger, not estimates.

## The measurement
| Metric | Baseline (pre-rail) | B12 pilot (measured) | Verdict |
|---|---|---|---|
| KM review time | ~half day (4–6h), mostly detection | **~3.6h active** (17:43–21:20 capture window) + ~30min next-day final edits/sign-off | ✅ target met ("few hours") |
| What KM's time bought | detection + judgment mixed | **60 receipted feedback packets**, all closed E2 with commits + tests green | ✅ judgment-dense, zero lost notes |
| Detection done upstream | none | boards caught 4 material defects pre-review (incl. a live 404 in the first runnable command) | ✅ rail worked |
| Surface exits | n/a (no cockpit) | **>0 — five pilot findings** forced exits (missing mint, stale card, raw slug, blank checklist, pileup) | ⚠ all five fixed as CLASSES same-day |
| Ledger integrity under load | untested | 60-packet burst + 97-item cleanup, **chain verified clean** (post-flock-fix) | ✅ proven in production |

## Honest reading
- **PASS on the core claim:** half-day → ~3.6 hours, with *more* captured and everything receipted. The rail's economics are real.
- **The amendment list the pilot was designed to produce:** (1) KM's ~60 line-level catches = the **Cold Reader gap** — that persona debuts next board run, expect this number to drop hard; (2) the five surface-exit findings are fixed (vocabulary contract, auto-mint, batch lanes, A1 relay + A2 categories now BUILT per Tiger [196]); (3) flow-lane vs transaction-lane distinction codified.
- **Next-cycle targets:** surface exits **0** · KM line-level catches **<20** (Cold Reader absorbing the rest) · review time **≤3h**.

## Fan-out ruling (per R4)
**GATE: OPEN — recommend GO for Wave 1**, on the rail as amended. Per the standing arc, Wave 1 = **S2 Harness volumes** (already in human-handoff stage) through the full contract: boards (with Cold Reader seated) → rigor audit → fidelity → Fold Report + Brief → KM's few hours. KM's G-on-X reachout runs one wave ahead (S3 KW/outline detail while S2 is in boards). KM ratifies the wave start.

∞Δ∞ SEAL: complete — twelve books shipped the old way taught us; the thirteenth review will be the first born entirely on the rail. The measurement says: scale it.
