# Sovereign Stack — Delta Audit — 2026-06-12 (night watch)

**Baseline:** `artifacts/audit_reports/audit-report-2026-06-10.md` (cutoff = 2026-06-11 04:27:39, the report's mtime).
**Delta scope:** 44 changed code/script/test files since baseline — 20 commits (`10644ba..HEAD`, last `aeeffe5`) plus working-tree edits. Pure data/memory/artifact JSON & NDJSON were excluded from code-dimension review.
**Method:** ONE read-only Opus finder, 7 dimensions (security, performance, code quality, test coverage, dependencies, architecture, constitutional conformance). Every surfaced finding was cross-verified against live code at the cited `file:line`; only NEW findings, regressions, and fixed-since-baseline items are reported.

## Headline

The audit-lane work since baseline **resolved the anchor CRITICAL** (unlocked concurrent ledger appends) **and 5 HIGHs** (principal spoofing, missing authorization, simulated approval gate, denied→approved replay flip, orphan-id crediting), plus several performance / path-traversal / crypto items — 11 baseline items fixed and verified. The one material new issue is a **partial-fix gap**: the `require_owner` authorization gate added to `/produce`, `/apply`, `/recompile` was *not* applied to the new Accept→executor route `/feedback/<id>/disposition`, which spawns a subprocess and mutates the hash chain. No regressions.

## NEW findings

### HIGH

**Authorization gap on the new Accept→execute path (`/feedback/<id>/disposition`)** · security / constitutional · `src/sovereign_agent/node_api/routes/feedback.py:273-274, 286, 215-233`
The commits that added `@require_owner` to `/produce`, `/apply`, `/recompile` (fixing the baseline missing-authorization HIGH) also introduced a NEW code-executing route gated by `@require_principal` **only** — no `@require_owner`. On `action=="accept"`, `feedback_disposition` calls `_ring_the_bell(obligation_id)` (feedback.py:286), which spawns `scripts/atrium_executor.py` as a detached subprocess (feedback.py:226-231). That executor closes/credits obligations in the hash-chained ledger and, when `BREATHLINE_EXECUTOR_AGENT` is configured, spawns that arbitrary binary (`atrium_executor.py:99-104`). So any authenticated non-owner — a federation peer with a valid token, or a loopback/`dev:anonymous` caller — can trigger execution + chain mutation via Accept, the very privilege the baseline fix walled off on the sibling routes.
*Fix:* add `@require_owner` below `@require_principal` on `feedback_disposition` (at minimum gate the accept/`_ring_the_bell` branch to the node owner), mirroring `proposals.py:100-102 / 195-196 / 396-398`.
*Verified:* feedback.py:273-274 (decorators show only `@require_principal`), :286 (`_ring_the_bell` in accept branch), :215-233 (spawn); atrium_executor.py:99-104 (spawns `BREATHLINE_EXECUTOR_AGENT`), :67-73 (closes obligations). `require_owner` exists/works at auth.py:172-188 but is absent from this route.

### LOW

**New unlocked hash-chain appender reachable from the threaded API (`thread_channel.append`)** · concurrency / architecture · `src/sovereign_agent/node_api/thread_channel.py:59-71`
`thread_channel.append()` is read-tail-then-append with no flock: it `load()`s the whole THREAD ndjson for `entries[-1]["hash"]`, then opens in append mode — the fork pattern the baseline CRITICAL described for the ledger. It writes the live `memory/coordination/THREAD_Tiger_GB.ndjson` and is now reachable from `threaded=True` Flask via `POST /relay/<id>/relay` (relay.py:148), concurrently with the separate-process `scripts/thread.py` writer. Kept LOW: writes are human-gated (one KM Relay click at a time), so concurrent same-process appends are unlikely; the baseline already owns the underlying un-fenced-THREAD issue. What is NEW is wiring it behind a concurrent HTTP route.
*Fix:* route `thread_channel.append` through an `fcntl.flock` over read-tail-through-write (reuse the ledger pattern), or funnel both writers through one fenced module.
*Verified:* thread_channel.py:59-71 (no lock; reads tail then `p.open("a")`); relay.py:135-148 (API call site).

## Regressions

**None.** No baseline finding was worsened and no baseline fix was broken. (The CORS wildcard + loopback-trust MEDIUM at `server.py:80-86` is unchanged and still permissive, but it is a baseline-known item with an explicit "tighten in a follow-up" note — not a regression.)

## Fixed since baseline (verified in live code)

1. **CRITICAL — ledger write-fence / unlocked concurrent appends** · `ledger.py:131-176`. `_append` now wraps read-tail→write→`flush`→`os.fsync` in an exclusive `fcntl.flock` on sidecar `obligations.lock` (:138-141, 162-166); `import fcntl` :16. All writers funnel through `_append`, closing both in-process and cross-process races. `repair_chain()` added (:178-209) with backup. `tests/test_ledger_concurrency.py` (8 threads × 25 opens; two instances/one root) asserts `verify_chain()` stays True.
2. **HIGH — principal_id / actor spoofing from request body** · `obligations.py:80,100,135`; `feedback.py:101,283`; `proposals.py:88`. Actor now bound unconditionally to `current_principal()` (owner/approved_by/closed_by/produced_by); the `body.get(...) or current_principal()` override is gone.
3. **HIGH — missing authorization on dangerous routes** · `auth.py:172-188`; `proposals.py:100-102,195-196,396-398`. Real `require_owner` decorator (rejects no-owner / dev-mode / `dev:*` / principal≠owner) applied to `/produce`, `/recompile`, `/apply`. `g.auth_dev_mode` set on every auth branch. *(See NEW HIGH for the one route this gate missed.)*
4. **HIGH — simulated approval gate in all modes** · `deps.py:59-71`; `node_integration.py:17-52`; `human_approval_gate.py:82-96`. `simulate_gate=True` removed; `gate_mode` from env (default `sovereign`); `sovereign` records a real disposition via `record_disposition()`, `external` returns `pending`. Approver is a verified human (must pass `require_principal`).
5. **HIGH — denied/pending approvals flip to 'approved' in replay/full_log** · `ledger.py:377-378, 417-419`. Approved set built only from `disposition=='approved'`, mirroring `_is_approved`.
6. **HIGH/MEDIUM — orphan credits/approvals on unknown / already-closed IDs** · `ledger.py:279-281, 313-318, 54`. `approve()`/`close()` raise `KeyError` / new `AlreadyClosedError`; routes map to 404 / 409 (obligations.py:101-105,135-139; feedback.py:286-303).
7. **HIGH — feedback disposition bare 500s** · `feedback.py:285-303`. `approve`/`close` wrapped in try/except → 404 / 409 / 403; bad action → 400 before the try.
8. **Perf HIGH/MEDIUM — full-file re-parse per request + O(n) verify on hot routes** · `ledger.py:124-141, 438-465`. `_entries()` memoized on `(st_mtime_ns, st_size)`; `verify_chain()` memoized on the same key with in-lock frontier advance; `replay()`/`full_log()` copy inner dicts so the cache can't alias-corrupt.
9. **LOW — non-constant-time token compare** · `auth.py:77,24`. Now `hmac.compare_digest`.
10. **MEDIUM — `/produce` path traversal via obligation_id** · `proposals.py:116-124`. `oid` validated against `re.fullmatch(r"obl_[0-9]{8,}_[0-9a-f]{4,}", oid)` → 400 otherwise.
11. **MEDIUM/LOW — hardcoded `/home/kmangum` vault path in recompile** · `proposals.py:30, 211-212`. Duplicated `_VAULT` literal replaced by `config.get_books_kdp_root()`.

## Still baseline-open (unchanged — not re-reported as new)

- Corrupt/torn NDJSON line still 500s every ledger route — `ledger.py:134` bare `json.loads`; `_recompute_chain` (:456-464) raises rather than returning False. (baseline MEDIUM)
- CORS wildcard + loopback-trust — `server.py:80-86`. (baseline MEDIUM)
- `closed_by="tiger"` hardcoded in the executor (`atrium_executor.py:69`) and `principal_id` literals — consistent with baseline's constitutional note; not newly introduced beyond the new executor file.

## Summary counts

| Category | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---|---|---|---|
| NEW findings | 0 | 1 | 0 | 1 | 2 |
| Regressions | 0 | 0 | 0 | 0 | 0 |
| Fixed since baseline | 1 | 5 | 3 | 2 | 11 |

**Net:** the engine's trust layer materially improved — the anchor CRITICAL and the identity/authorization/gate band are closed and tested. One partial-fix authorization gap (NEW HIGH) is escalated to Tiger; one new un-fenced THREAD appender (LOW) is logged for follow-up.
