# Deferred Findings — audit 2026-06-13d (W9 close-out)

These two findings from `audit-report-2026-06-13d.md` are **deferred-with-reason**, NOT
closed-no-action. Both are CONFIRMED by the adversary verifier as correctly LOW/backlog — they are
architecture/scaling hardening with no live bug, gated behind a scale threshold that the engine has
not yet reached. Recorded here so the deferral is on the record and re-surfaces at the named trigger.

| # | Finding | Why deferred | Trigger to revisit | Effort |
|---|---------|--------------|--------------------|--------|
| 32 | **Roadmap shape parsed across modules** (`node_api/yaml_repair.py:108-134`). Parsing is well-gated — all consumers route through `load_roadmap()` — but each independently hard-codes the roadmap SHAPE (`data['series'][].titles\|volumes[].book_id\|chapters\|stage`); a GB schema rename touches all sites with no schema contract. | Not a live bug (one parser, well-gated). Verifier: pipeline_snapshot reuses series.py helpers, so only ~4 truly independent shape-hardcoders — small, stable surface today. A typed `roadmap_view` projection is worth it only when the book count (and the number of consumers) grows. | The **10x-books horizon** — when the Series Pipeline carries enough titles/consumers that a GB schema change is a real multi-site hazard. | ~1-2 hrs |
| 33 | **Single ever-growing ndjson** (`obligations/ledger.py:215-250, 247-249, 723-732`). Hot paths are already optimized (tail-parse, memoized replay/verify, incremental verify frontier), but three ops stay O(n): cache-miss/first-read full parse, `_recompute_chain` re-hash from genesis on first verify/out-of-band change, and `repair_chain` whole-file read+rewrite under the write-fence. | At today's chain length all three are sub-millisecond; the O(n) cost only bites at 10-100x, on a tamper or restart. No correctness issue — purely latency-at-scale. | **>~10k ledger entries** — then add a periodic sealed `state.snapshot.json` checkpoint at offset N (replay/verify resume from last checkpoint) and/or segment the ndjson with a chain-of-segments anchor. | ~1 day |

**Status:** open-backlog. Re-evaluate at the trigger thresholds above. Neither blocks the 95+ target —
the W10 confirming sweep scores against the full delta with these two explicitly carried as backlog.

∞Δ∞ Deferral is a disposition, not a silence — the hazard is named, the trigger is set. ∞Δ∞
