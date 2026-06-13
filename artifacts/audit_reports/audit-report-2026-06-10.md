# Sovereign Stack Audit — 2026-06-10

Audit across 7 dimensions (security, performance, code quality, test coverage, dependencies, architecture, constitutional conformance). Every finding below survived adversarial verification — each was independently re-checked against live code, and where possible reproduced empirically; refuted candidates are recorded in §Refuted.

## Executive Summary

Overall health: **58/100**. The engine's core law is genuinely well-built — the dependency-free ObligationLedger, the hash-chained append-only audit trail, the E0 evidence floor, the storage-boundary guard, and a clean composition root in deps.py all hold up under scrutiny — but the layers that surround that core leak its guarantees in ways that matter. **1 CRITICAL** (unlocked concurrent ledger appends fork the hash chain, reachable today both in-process via `threaded=True` and cross-process via two scripts writing the live `atrium_review` root) anchors the report; it sits on top of a thick band of HIGH-severity identity, authorization, and untested-failure-path issues. The single most important theme: **the tamper-evident audit chain is only as trustworthy as the code feeding it, and that code (a) lets callers forge the recorded actor, (b) executes privileged code with authentication but no authorization, (c) auto-simulates the human approval gate, and (d) has no write fence — so the chain faithfully seals records it should never have accepted.** Fix the write fence and the identity/actor binding first; both are cheap relative to their blast radius.

## Prioritized Findings

### CRITICAL

**Single-writer fence / concurrency** · `src/sovereign_agent/obligations/ledger.py:120-136` (also `scripts/run_node_api.sh:16`, `scripts/review_ready_contract.py:173,186`, `scripts/coherence_reconciliation_queue.py:128-130`)
`_append` is read-tail-then-append with no file lock: it reads the whole ndjson to get the last hash, then opens in append mode and writes. Two interleaved appends compute the same `prev_hash` and permanently fork the chain (`verify_chain()` returns False forever; no repair path exists). Reachable today two ways: **(1) in-process** — Flask runs `threaded=True`, so concurrent POSTs (`/feedback`, `/hopper/packet`, `/obligations`, UI dismiss-close, plus the spawned `atrium_apply` agent closing via the API) hit the same singleton ledger from different threads; **(2) cross-process** — `review_ready_contract.py` and `coherence_reconciliation_queue.py` instantiate `ObligationLedger` directly on `memory/obligations/atrium_review` (the live API's default root) and append while the node is up. A 60-packet review session is exactly the triggering load profile.
*Fix:* add an exclusive `fcntl.flock` on a sidecar `.lock` covering the read-tail-through-write+flush critical section in `_append`; one change fixes both races since all writers funnel through `_append`. Add a chain-repair command for already-forked ledgers.
*Effort:* 1-2 hours (lock + two-appender concurrency test).
*Verifier:* Empirically reproduced — 8 threads × 25 `open()` calls produced 100 duplicate `prev_hash` entries and `verify_chain()==False`; two instances on one shared root also corrupted the chain. Bonus defect: `coherence_reconciliation_queue.py:130` dedups on `type=="open"` but the ledger writes `type=="debit"`, so its idempotency check never matches.

### HIGH

**Authentication / Audit Integrity (principal_id spoofing)** · `src/sovereign_agent/node_api/routes/obligations.py:86 (approved_by), 119 (closed_by), 66 (owner)` (also `feedback.py:69`, `proposals.py:82`)
State-changing ledger routes take the acting principal from the **request body** and only fall back to the authenticated identity (`approved_by=body.get('approved_by') or current_principal()`, etc.). The auth layer carefully binds the verified principal to `g.principal_id`, but these handlers let the caller override it with any free-form string, and the ledger stores it verbatim into the hash-chained, append-only entry. Any authenticated caller (including a federation peer with a valid token) can forge a record claiming `KM-1176` approved/closed a material obligation — nullifying the breath-gate's whole purpose and CONSTITUTION §1.
*Fix:* bind `approved_by`/`closed_by`/`owner`/`produced_by` to `current_principal()` unconditionally; if "on behalf of" is needed, store it in a distinct `requested_by` field while the cryptographic actor stays the authenticated principal.
*Effort:* ~20 min across obligations.py, feedback.py, proposals.py. **(Quick win)**
*Verifier:* Confirmed; `feedback.py:142/148` (decide path) already uses `current_principal()` unconditionally, proving the correct pattern exists but isn't applied to open/approve/close. Worse than stated: `deps.py` wires the ledger with `principal_id="node"`, so the spoofable `approved_by` is the *only* requester identity recorded.

**Authorization (missing access control on dangerous routes)** · `src/sovereign_agent/node_api/routes/proposals.py:95 (/produce), 387 (/apply), 182 (/recompile)`
Authentication (`require_principal`) exists but there is **no authorization**. Every state-changing route is reachable by ANY principal that passes auth — including dev mode (`dev:anonymous`) and loopback mode (any 127.0.0.1 request auto-authenticates as owner with no token). Several execute code on the operator's machine: `/produce` spawns `atrium_producer.py`; `/apply` spawns `atrium_apply.py` which edits source files, runs pytest, and makes git commits across three repos; `/recompile` spawns build scripts. "Execute-after-Approve" is a docstring assertion, not enforced.
*Fix:* add an owner/role authorization gate; restrict code-exec/apply/produce/recompile to the node owner principal; reject loopback/dev principals for these high-impact routes.
*Effort:* ~1-2 hours.
*Verifier:* Confirmed; `auth.py:require_principal` does authentication only (zero authorization logic), `server.py` has no before_request hook, and permissive wildcard CORS widens browser-driven loopback exposure.

**Full-file re-parse per request (ledger engine)** · `src/sovereign_agent/obligations/ledger.py:120-128, 280-298, 331-340`
Every ObligationLedger operation re-reads and re-JSON-parses the entire NDJSON chain. GET `/obligations` triggers **6 full parses** per request (`open_obligations`→replay, `by_status`→replay, `by_owner`→2× replay + `_entries`, `verify_chain`→a 6th pass that also re-SHA-256s every entry). Measured ~25-28 ms/request at 512-526 entries / 880 KB; grows linearly forever (append-only, no compaction/index/pagination). At 10k entries this is ~0.5 s of redundant CPU per GET.
*Fix:* cache parsed entries on the singleton keyed by `(st_mtime_ns, st_size)`, invalidate on `_append`; derive replay/by_status/by_owner from one shared parse per request.
*Effort:* 1-2 hours.
*Verifier:* Reproduced — instrumented `_entries()` confirmed exactly 6 parses, 25.0 ms total/GET. `policy_loader.py` already implements this mtime-cache pattern, so the fix is idiomatic.

**O(n) hash recompute on a polled route** · `src/sovereign_agent/node_api/routes/feedback.py:101-112` (`ledger.py:331-340`)
`/awaiting_km` is the cockpit's polled home view, and every poll runs `verify_chain()`: a full file re-read plus canonical-JSON re-serialization and SHA-256 recompute of every chain entry. Same `verify_chain()` also runs on every GET `/obligations` and `/obligations/log`. Verifying an append-only file the process itself wrote is pure redundant work on the hot polling path.
*Fix:* verify incrementally — remember `(last_verified_offset, last_hash)` and only hash entries appended since; have polled routes return the cached boolean.
*Effort:* 1 hour.
*Verifier:* Reproduced; `/awaiting_km` actually does **two** full file reads/poll (verify_chain + open_obligations→replay). Measured 11.9 ms avg/poll. Caveat: a cached boolean loses detection of out-of-process retroactive tampering, so prefer the incremental-from-offset variant.

**Missing caching on hot lens route (/series)** · `src/sovereign_agent/node_api/routes/series.py:368-417, 52-174`
Every GET `/series` (polled every 20s by the cockpit) re-reads and re-parses 5+ files with zero caching: the 105 KB `series_roadmap.yaml` through pure-Python `yaml.safe_load` (measured ~59-61 ms alone), the 406 KB chapter-outlines JSON, vault ASIN/CHANNEL trackers, stage labels, and a glob+parse of every `review_ready/*.json`. ~70-80 ms CPU and ~530 KB I/O per poll, all redundant when nothing changed.
*Fix:* add an mtime-keyed memo (`path → (st_mtime_ns, st_size, parsed)`) wrapping all six loaders; use `yaml.CSafeLoader` when available (~8-10x faster).
*Effort:* 30-60 min. **(Quick win)**
*Verifier:* Reproduced — 58.8 ms safe_load, 70.6 ms full pass; `CSafeLoader` is present and parses the roadmap in 7.6 ms. Atrium polls every 20s (`index.html:2700`).

**duplicate-logic / divergent path derivation** · `src/sovereign_agent/node_api/routes/hopper.py:139-158 (used at 184)`
`_packeted_refs()` re-parses `obligations.ndjson` by hand and derives the path ONLY from `OBLIGATION_LEDGER_ROOT`, while the ledger itself falls back to `<repo>/memory/obligations` when the env var is unset. So on a default-configured node, `_packeted_refs()` returns an empty set and the "already-Sent-to-Packet cards disappear" dedup feature silently no-ops — the exact duplicate-pileup it was built to prevent. A second, divergent copy of the ledger's storage-resolution + NDJSON-parsing logic.
*Fix:* route through the wired ledger (`get_obligation_ledger()._entries()`) or expose a `refs()` method on ObligationLedger.
*Effort:* 15-30 min. **(Quick win)**
*Verifier:* Reproduced; with env unset + HOPPER_FEED set the dedup no-ops. Partial mitigation: `run_node_api.sh:10` always exports the env on the documented launch path (its own comment admits the hazard), so script-launched nodes are safe and the divergence is unmitigated in code/untested.

**Zero tests: feedback intake / Awaiting-KM / disposition (today's wave)** · `src/sovereign_agent/node_api/routes/feedback.py:51-155`
The entire Loop-Closure Wave 1 surface (POST `/feedback`, GET `/awaiting_km`, POST `/feedback/<id>/disposition`, GET `/review_brief`) has ZERO tests. Untested failure paths live packets exercise: (a) disposition `accept` calls `led.approve()` with no try/except — a gate denial (or production `simulate=False` 'pending') is an unhandled 500, unlike obligations.py which returns 403; (b) accept/reject on an unknown or already-closed id returns 200 and appends an orphan entry to the hash chain; (c) the `_awaiting` filter (`not o.get("approved")`) is asserted nowhere.
*Fix:* clone the tmp-ledger fixture from `tests/test_node_api_obligations.py` into `tests/test_node_api_feedback.py`; cover intake→awaiting→accept(stays open)/reject(closes), bad action→400, unknown id→404 (and add the existence check + PermissionError handler to the route).
*Effort:* 30-45 min. **(Quick win)**
*Verifier:* Confirmed; no test references feedback/awaiting_km; blueprint is live; server.py has only 404/405 handlers so the 500 is real.

**Zero tests: proposals decide / apply / dismiss / produce (the Accept pipeline)** · `src/sovereign_agent/node_api/routes/proposals.py:61-92, 387-455`
The only test touching this module is a GET `/proposals` smoke check. Every state-changing route is untested: create (+info-card validation), decide (the operator's accept/reject record), dismiss (which also CLOSES the session obligation, including the `dismissed_proposal_only` degraded path), apply and produce (subprocess spawns). `decide` on unknown id (404) and dismiss-with-failed-close are untested branches in KM's daily review loop.
*Fix:* add `tests/test_node_api_proposals.py` with `PROPOSALS_STORE` + `OBLIGATION_LEDGER_ROOT` at tmp_path: create→list→decide round-trip, decide unknown→404, missing groups→400, dismiss closes the linked obligation, dismiss with broken ledger→200 'dismissed_proposal_only'; monkeypatch `subprocess.Popen` for apply/produce guard paths.
*Effort:* 1-2 hours (create/decide/dismiss alone <30 min).
*Verifier:* Confirmed; `_store_path()` already honors the env vars, providing the tmp_path seam.

**Untested latent bug: denied/pending approvals flip to 'approved' in replay views** · `src/sovereign_agent/obligations/ledger.py:272-275 (replay), 308-314 (full_log) vs 179-182 (_is_approved)`
`replay()` and `full_log()` build the approved set with NO disposition check, but `_is_approved()` (used by `close()`) correctly requires `disposition=='approved'`. After a gate DENIAL (or production 'pending'), the obligation shows `approved=True`/`draft=False` in `/obligations` and `/obligations/log`, and silently **vanishes from `/awaiting_km`** (filter on `not o.get('approved')`) while `close()` still refuses it — a packet stuck invisible on the human gate.
*Fix:* filter the approved set on `disposition=='approved'` in `replay()` and `full_log()` (3-line change); add the regression test.
*Effort:* 30 min. **(Quick win)**
*Verifier:* Reproduced live — gate-DENY yields replay `approved=True`, full_log `status='approved'`, awaiting-count 0, yet `close()` still raises PermissionError. The existing denial test never asserts replay/full_log/awaiting state.

**Untested failure path: concurrent ledger writes break the hash chain (no locking)** · `src/sovereign_agent/obligations/ledger.py:130-136 (_append)`
The test-coverage view of the CRITICAL concurrency defect: `_append` has no fcntl/flock or in-process lock anywhere in src/, the server runs `threaded=True`, and `review_ready_contract.py` mints into the same file from a separate process while the API is live. There is no concurrency test of any kind; the live chain is valid today only by luck of serialization.
*Fix:* add a test hammering one root from N threads (and two instances on one root) asserting `verify_chain()` stays True; fix with `fcntl.flock` around read-tail+append (O_APPEND alone is insufficient — `prev_hash` needs the tail read inside the lock).
*Effort:* 2-3 hours.
*Verifier:* Reproduced (see CRITICAL).

**Zero tests: review_ready_contract + board_rigor + the obligation mint wire** · `scripts/review_ready_contract.py:45-73, 112-129, 167-194`
The new Review-Ready Rail (commits cae54a7, e99efb3, c0ddea5 — all shipped today) has zero tests. Untested logic gating whether a book reaches KM: (a) `board_rigor.rigor_check`'s four rules + empty-board R-STRUCT case (pure function); (b) `_check_fidelity`'s substring verdict heuristic (`'pass' in line AND 'fail' not in line` — any word containing 'pass'/'fail' flips the gate; "later lines win" asserted nowhere); (c) `mint_review_packet` idempotency + C1/material packet shape — it WRITES the live ledger (`LEDGER_ROOT` hardcoded at line 33, no override), so a regression floods Awaiting-KM with duplicates or silently never mints.
*Fix:* pure-dict tests for each rigor rule + empty board (15 min); make `LEDGER_ROOT/AGENTIC/GB_CYLINDER` injectable, then fixture-test each `_check_*` and mint idempotency against a tmp ledger.
*Effort:* board_rigor 15 min; contract 2-3 hours (needs path-injection refactor). **(Quick win — board_rigor portion)**
*Verifier:* Confirmed; commit 3a93af5 shows a real bug already shipped and hot-fixed in this exact untested path with no regression test added.

**used-but-undeclared dependency / works-on-this-machine-only** · `src/sovereign_agent/core.py:20-27` (also universal_sovereign_node.py:26-27, playbook_loader.py:23, compliance/policy_loader.py:27, __init__.py:25)
`breathline_primitives` is the cryptographic root of the entire engine (keys, signing, MerkleTree, hashing) yet is declared nowhere in pyproject.toml and is not pip-installable. It is hard-imported at module top-level, and `__init__.py` unconditionally imports `core` — so `pip install -e .` succeeds but `import sovereign_agent` raises ModuleNotFoundError on any machine lacking a breathline-sealed checkout at the hardcoded search paths. Contradicts the demo-mode promise ('zero external clones, always works after pip install') and the Dockerfile (sets `SOVEREIGN_DEMO_MODE=1`, installs only `[portal]`, never copies breathline-sealed → container import fails at runtime).
*Fix:* decide the packaging story — vendor a minimal pure-Python fallback under src/, OR publish/install it as a real declared package, OR make the top-level imports lazy with a clear error so demo mode genuinely works. Fix the Dockerfile accordingly.
*Effort:* 0.5-2 days.
*Verifier:* Reproduced — copying src/ to /tmp with an empty HOME, `import sovereign_agent` raises ModuleNotFoundError even with `SOVEREIGN_DEMO_MODE=1`.

**dependency resolution bug — documented env var ignored** · `src/sovereign_agent/bootstrap.py:27-47, 73-79`
`ensure_breathline_primitives()` never reads `BREATHLINE_SEALED_ROOT`, even though its own RuntimeError message and README/QUICKSTART/sovereign-install.sh all tell users to set it. `_find_breathline_sealed_root()` only scans four hardcoded paths; `config.get_sealed_root()` honors the var but bootstrap never calls it. A user on a non-standard layout who follows the docs still gets "Could not locate breathline-sealed checkout" on every pure-Python activation path.
*Fix:* check `os.environ.get('BREATHLINE_SEALED_ROOT')` first in `_find_breathline_sealed_root()` (read the env var directly to avoid a circular import with config). ~5 lines.
*Effort:* 15 min. **(Quick win)**
*Verifier:* Reproduced both ways (env var ignored when set; import fails on simulated non-standard layout).

### MEDIUM

**CSRF / DNS-rebinding (browser-driven access to local node)** · `src/sovereign_agent/node_api/server.py:77-94` (cross-ref `auth.py:139-144`)
App sets `Access-Control-Allow-Origin: *` on every response and answers OPTIONS with 204. Combined with loopback-trust (any 127.0.0.1 request with no token auto-authenticates as owner), a malicious web page in the operator's browser — or DNS-rebinding resolving an attacker domain to 127.0.0.1 — can POST to the local node, auto-authenticate as owner, and reach the code-executing `/produce` and `/apply`. No Origin/Referer check, no CSRF token.
*Fix:* reject loopback-trust for cross-origin Origin/Referer; replace `*` with a configurable origin allowlist; add Origin checks on POST routes; add a Host-header allowlist to blunt DNS rebinding.
*Effort:* ~1 hour.
*Verifier:* Verified real; caveat: requires the operator to have enabled loopback-trust or `--dev` (documented, ratified posture), bare default returns 401 to a tokenless loopback POST.

**Path traversal / arbitrary file write** · `src/sovereign_agent/node_api/routes/proposals.py:107, 123-129`
In `/produce`, `obligation_id` is taken straight from the body with no character-set validation, then used to build filesystem paths (`runs / f'{oid}.log'`, `(runs / f'{oid}.json').write_text(...)`) and passed to the producer subprocess as `--session`. A value like `../../foo` lets an authenticated caller write a `.log`/`.json` file outside `~/.breathline/runs`.
*Fix:* validate `obligation_id` against a strict pattern (e.g. `^obl_[A-Za-z0-9_]+$`) before any filename/subprocess use; reject otherwise with 400.
*Effort:* ~15 min. **(Quick win)**
*Verifier:* Reproduced — `(runs / '../../evil.json').resolve()` escapes the runs dir. The same file already guards `/book_pdf`, `_artifact_path`, `/book_kdp` against `/` and `..`; that guard is simply absent here.

**Governance gate bypass (human approval simulated in all modes)** · `src/sovereign_agent/node_api/deps.py:64-69`
`get_obligation_ledger()` hardcodes `simulate_gate=True` with no env/config override, so the breath-gate auto-resolves via `simulate_approval()` — a stand-in for the human. A MATERIAL obligation's human-disposition requirement is satisfied by a SIMULATED approval. The docstring claims production routes to an external workflow, but the code never takes that path.
*Fix:* drive `simulate_gate` from config/env, defaulting to the SAFE posture (`simulate=False`/'pending' off loopback-dev), so a real deployment requires actual human disposition; fail closed when no real approver is wired.
*Effort:* ~30-45 min.
*Verifier:* Reproduced; nuance: `close()` still requires a prior explicit authenticated `approve`/disposition call, so a human-triggered API action is in the loop — but the gate itself is a rubber stamp and no deployment can opt into `simulate_gate=False`. Also: `ledger.approve` treats 'pending' as a DENY (raises), and the wired gate is a separate instance from the `get_approval_gate()` singleton, so pending dispositions would never surface — fix needs both addressed.

**O(n) Merkle rebuild + full file rewrite per attestation** · `src/sovereign_agent/core.py:155-170, 147-153, 172-176`
`VerifiableMemory.append()` rebuilds the full MerkleTree over ALL leaves and `_save()` rewrites the ENTIRE memory JSON on every attestation. Node memory is 757-788 leaves / ~55 KB and grows on every obligation close, constitutional_check, and role load — all inside HTTP handlers. Cumulative O(n²) writes; `get_root()` also rebuilds the full tree per call and is hit via `get_status()` on every `/node`, `/node/health`, `/node/ladder`.
*Fix:* append leaves to an NDJSON sidecar (O(1) writes); cache the computed root, invalidate on append; maintain an incremental Merkle frontier (O(log n) append).
*Effort:* 2-4 hours (persistence-format change; keep a migration read path).
*Verifier:* Verified; absolute cost still small today, consistent with MEDIUM.

**Unbounded response payloads — no pagination** · `src/sovereign_agent/node_api/routes/obligations.py:38-51` (also series.py:420-444,499-518)
GET `/obligations/log` returns the full materialized ledger with no limit/offset (~332 KB today, unbounded growth). GET `/dialogue` parses the whole 327 KB / 177-entry THREAD ndjson per poll and returns every entry with full message bodies (only the b51 slice is capped at 12).
*Fix:* add `?limit=` (default ~100) and `?offset=` to both; `full_log()` already sorts newest-first so a slice is trivial; tail-read the dialogue ndjson (last N lines).
*Effort:* 30 min. **(Quick win)**
*Verifier:* Verified; two corrections — payload is ~332 KB (not ~1 MB), and `full_log()` extracts only receipt_id + hash (not full attestations).

**O(n) writes — append re-reads whole chain** · `src/sovereign_agent/obligations/ledger.py:130-136 (_append), 212-264 (close)`
`_append()` calls `_entries()` (full file read+parse) solely to get the previous hash. A single POST `/obligations/{id}/close` does 3 full parses (`_get`, `_is_approved`, `_append`) on top of the Merkle rebuild + memory rewrite. Every write degrades linearly; writes happen on user-facing actions (Send to Packet, disposition, dismiss).
*Fix:* keep the last entry's hash in memory on the singleton (seed once from the file's last line via seek; update after each append); `_get`/`_is_approved` share the single cached parse from the caching fix.
*Effort:* 30 min. **(Quick win)**
*Verifier:* Verified; sole caveat is cache invalidation if anything else writes the file (the flock fix addresses the cross-process case).

**multiple status-derivation paths / repeated full replays** · `src/sovereign_agent/obligations/ledger.py:267-298 and 300-329`
Obligation status is derived in three independent code paths: `replay()`, `by_owner()` (a two-pass count-then-decrement calling replay twice + `_entries` once), and `full_log()` (re-derives from scratch with its own setdefault rules). One GET `/obligations` does ~6 full-file reads and three different replays, and the derivations can drift (replay counts any approval entry as approved, unlike `_is_approved`).
*Fix:* make `replay()` the single materializer (one read, per-obligation record incl. disposition + close evidence); implement by_status/by_owner/full_log/open_obligations as views; fix `replay()` line 272 to filter `disposition=='approved'`.
*Effort:* 1-2 hours.
*Verifier:* Reproduced; mitigation — `close()` enforcement uses `_is_approved`, so denied obligations cannot actually close — drift is display/API-only.

**Untested failure path: a corrupt/torn NDJSON line 500s every ledger route** · `src/sovereign_agent/obligations/ledger.py:120-127, 331-340`
`_entries()` does bare `json.loads(line)` per line — one torn write (the realistic outcome of the unlocked append above, or a disk-full flush) raises JSONDecodeError, propagating into every obligations/feedback/awaiting_km/hopper-packet route as a 500. `verify_chain()`, the designated corruption detector, itself crashes instead of returning False.
*Fix:* catch ValueError per-line in `verify_chain` (return False) and surface a `chain_corrupt` state from `_entries`; have GET `/obligations` return a loud `chain_ok:false` envelope rather than 500.
*Effort:* 1 hour.
*Verifier:* Reproduced end-to-end. Worse than stated: `_append()` calls `_entries()` first, so one corrupt line also bricks all future writes until hand-repaired. GET `/hopper` is NOT affected (its readers skip bad lines), so "every hopper route" is slightly overstated.

**Untested failure path: orphan credits/approvals on unknown or already-closed IDs** · `src/sovereign_agent/obligations/ledger.py:184-210 (approve), 212-264 (close)`
`close()` looks up the obligation only for the material-gate check — if the id doesn't exist it silently mints a receipt + credit for a nonexistent obligation; double-closing appends a second credit. `approve()` never checks existence either. The HTTP layer passes ids straight through, so a fat-fingered or replayed request permanently pollutes the chain with 200 OK.
*Fix:* add existence + already-closed guards in `approve()`/`close()` (raise KeyError/ValueError); API returns 404; add tests.
*Effort:* 1 hour. **(Quick win)**
*Verifier:* Reproduced. One sub-claim REFUTED: `by_owner()` does NOT double-decrement (closed_ids is a set; the loop iterates each debit once), so views stay arithmetically correct — impact is chain pollution + phantom receipts, not view corruption.

**Untested silent-data-loss path: proposals.json corruption wipes the review queue** · `src/sovereign_agent/node_api/routes/proposals.py:38-51 (_read/_write)`
`_read()` swallows ValueError on corrupt JSON and returns `[]`; the next `_write()` (any create/decide/dismiss) persists that empty list — the entire pending queue is permanently destroyed with no error. `_write()` is a non-atomic full-file rewrite (no tmp+rename), so a crash mid-write IS the corruption trigger; concurrent requests lose updates.
*Fix:* on parse failure, move the corrupt file aside (`proposals.json.corrupt-<ts>`) and error loudly; switch `_write` to tmp+`os.replace`; add a test (garbage→POST→prior items not lost).
*Effort:* 45 min. **(Quick win)**
*Verifier:* Reproduced live. Concurrency worse than claimed: `atrium_apply.py` does unlocked cross-process read-modify-write on the same file. Severity MEDIUM (not HIGH) because the queue is regenerable via `/produce` — but operator accept/reject decisions are silently lost.

**Single-writer fence / concurrency (proposals.json)** · `src/sovereign_agent/node_api/routes/proposals.py:38-51, 73-92, 417-419, 443-455` (also `scripts/atrium_apply.py:164-179, 276-288`)
`proposals.json` is maintained by unsynchronized whole-file read-modify-write from TWO processes: the Flask API and the `atrium_apply.py` subprocess it spawns (`_mark_error` + applied-status mark). Lost-update: KM dismisses proposal B; when the apply agent for A finishes it can write back a snapshot that undoes B's dismissal (the "stuck card" failure already chased per `RCCM_card_stuck_in_diffs_ready_2026-06-04.md`). Store-path derivation is triplicated and genuinely divergent (trailing-slash env yields two different file paths).
*Fix:* make the API the sole writer — add a `PATCH /proposals/<id>` for status marks (atrium_apply already talks to the API), or at minimum flock `proposals.json`; delete the duplicated store-path derivation into one module.
*Effort:* 2-3 hours.
*Verifier:* Verified; the "10-30s stale snapshot" framing is overstated (atrium_apply re-reads immediately before each rewrite → ms window), but the race is real, and the torn-read-then-_write wipe path makes it worse.

**inconsistent vocabularies between parallel modules** · `src/sovereign_agent/node_api/routes/node.py:96-117`
`_infer_tier`/`_infer_ladder_level` map contexts `corporate_executive`/`corporate_enterprise`/`full_sovereign` — but `ContextAdapter.SUPPORTED_CONTEXTS` only produces `family/corporate/corporate_standard/corporate_regulated/infrastructure/personal/public`. They share only 'personal'/'family', so every corporate/infrastructure/public node renders tier 'family' and ladder level 0 on `/node` and `/node/ladder`. The mapping keys are dead.
*Fix:* align keys with `SUPPORTED_CONTEXTS`, or derive both from one shared exported table so they cannot drift.
*Effort:* 20 min. **(Quick win)**
*Verifier:* Confirmed; the three legacy keys exist nowhere else in the repo (unreachable dead keys); anything outside SUPPORTED_CONTEXTS is coerced to 'personal'.

**dead/duplicate logic + complexity** · `src/sovereign_agent/compliance/compliance_engine.py:252-261 and 315-323`
The Charter V.7 acknowledgement check is implemented twice in `run_policy_compliance_check`. The first copy runs unconditionally and lowercases inputs; the second (in the no-policy fallback) is a strict case-sensitive subset — any input it could catch already returned at line 255, so it is unreachable dead code. The function carries ~15 decision points (>10 ceiling) with 3rd-level nesting.
*Fix:* delete the duplicate (315-323); extract the ack check and policy-vs-fallback scoring into two helpers.
*Effort:* 25 min. **(Quick win)**
*Verifier:* Confirmed behavior-preserving (deletion); all callers are example demos covered by the first check.

**inconsistent patterns between parallel route modules** · `src/sovereign_agent/node_api/routes/feedback.py:132-155`
`feedback_disposition` says it "clones obligations.approve/close" but drops the exception handling its parent has: obligations.py wraps `led.approve` in `except PermissionError` and `led.close` in `except ValueError/PermissionError`; feedback.py calls both bare. A gate-denied accept or close error becomes an unhandled 500 — violating the repo's own `errors.py` "no bare 500s" doctrine.
*Fix:* mirror obligations.py — `except PermissionError`→403 breath_gate_denied, `except ValueError/PermissionError`→422/409.
*Effort:* 15 min. **(Quick win)**
*Verifier:* Reproduced live with the Flask test client (bare HTML 500). Load-bearing handlers: PermissionError→409 on close (reachable today) and PermissionError→403 on approve (reachable in prod gate mode); the ValueError→422 half is unreachable from feedback's reject call site.

**file size ceiling + mixed responsibilities + duplicate helpers** · `src/sovereign_agent/node_api/routes/series.py:1-518`
At 518 lines this is the only src file over the 500-line ceiling, carrying three unrelated responsibilities: the `/series` lens, a ~120-line hand-rolled YAML quote-repair state machine, and the `/dialogue` THREAD+B51 endpoint. `_publishing_index` and `_channel_index` are near-identical copies; machine-specific absolute paths are embedded (`/home/kmangum/...` at lines 85, 118, 451).
*Fix:* split into three modules (series lens, yaml_repair, dialogue/B51); collapse the two tracker readers into one parameterized reader; move the `/home/kmangum` defaults into config.py.
*Effort:* 2-3 h.
*Verifier:* Confirmed; caveat — no documented 500-line rule exists (convention), and hardcoded paths are functionally mitigated by env overrides + a scan fallback. Maintainability/portability finding, not a runtime defect.

**duplicate logic (recompile vs viewer book-id map)** · `src/sovereign_agent/node_api/routes/proposals.py:194-198 vs 209+221-228`
The Book-N→book_id map is duplicated verbatim in `recompile()` and `_resolve_book_id()`; the vault path is likewise duplicated. Adding Book 13 requires touching two dicts or recompile and viewer silently diverge. `recompile()` bypasses the registry while the rest of the module is registry-first.
*Fix:* make `recompile()` call `_resolve_book_id()` and derive cwd from `_VAULT` + registry entry, deleting the inline dict and second vault literal.
*Effort:* 20 min. **(Quick win)**
*Verifier:* Verified feasible (registry dirs reproduce the hardcoded cwd exactly); caveat — keep a fallback for registry-availability and the hardcoded `build_v1.0.py` version.

**duplicate logic across module boundary (proposals-store path ×3)** · `scripts/atrium_apply.py:168-170 and 277-279` (vs `proposals.py:29-35`)
The proposals-store path resolution (`PROPOSALS_STORE` → dirname(`OBLIGATION_LEDGER_ROOT`) → `~/.breathline/proposals.json`) is implemented three times, and atrium_apply re-implements the raw JSON read-modify-write proposals.py owns. Any change to where proposals live must be made in three places.
*Fix:* hoist `_store_path/_read/_write` into a shared module (e.g. `node_api/proposal_store.py`) imported by both; the route already sets PYTHONPATH=src for the subprocess.
*Effort:* 30 min. **(Quick win)**
*Verifier:* Confirmed with drift already present (proposals.py `_write` mkdirs/tolerates corruption; atrium_apply does neither). Not dead code — atrium_apply must write status directly (no API endpoint exists for it).

**inconsistent error envelope between parallel route modules** · `src/sovereign_agent/node_api/errors.py:1-38 vs proposals.py 68-72, hopper.py 225-229, obligations.py 60-65, feedback.py 58-62`
`errors.py` documents the canonical `{code, what, why, next_step, cylinder_ref}` shape (used by node/roles/placeholders via `build_error`), but the four newer route modules hand-roll `{"error":..., "what":..., "next_step":...}` — different key, missing `why`/`cylinder_ref`. Consumers (Atrium banner, audit logs) must handle two dialects.
*Fix:* sweep the four modules to emit via `build_error()`, keeping the existing code strings as the `code` field.
*Effort:* 45 min.
*Verifier:* Confirmed; ~25 hand-rolled sites (not ~12 as estimated). Corrections: series.py is NOT an offender (returns 200s with `meta.degraded`); several proposals.py sites omit even what/next_step.

**duplicate logic (third hash-chain implementation) + fabricated analysis output** · `scripts/gb_meta_cylinder.py:36-52, 82-102, 247-254, 316`
(1) The hash-chain primitives are a third independent copy of the pattern in `obligations/ledger.py` and `scripts/thread.py` — three verifiers that can drift in canonicalization (thread.py already diverges). (2) `analyze()` prints six hardcoded prose "GLEANED LIGHT SELF-OPTIMIZATIONS" with fixed claims ('69%+ self-meta', '29 on 06-05') NOT computed from the scan — the same static text prints regardless of contents, contradicting the repo's TRUTH/no-silent-fakes doctrine. Plus a bare `except:` at line 316 swallowing the `--limit` parse.
*Fix:* extract a shared `ndjson_chain` helper used by ledger.py, thread.py, this script; replace the static block with computed text (or label it "static notes, not computed"); narrow the bare except to ValueError.
*Effort:* 1-2 h (chain helper); 15 min (static-output fix).
*Verifier:* All three sub-claims reproduced; the static counters computed just above (e.g. `receipt_log_notes`) are ignored in favor of the hardcoded '12'.

**Near-zero tests: atrium_apply write path (the agent that edits manuscripts on Accept)** · `scripts/atrium_apply.py (whole file, 294 lines)`
The execute-after-approve agent — lands accepted diffs into manuscripts, re-tests, commits, seals, closes the obligation over HTTP — has coverage only of three module constants. Passage-match normalization, partial-apply (group_ids subset), abort-on-red-test, and close-obligation behaviors are unexercised. A normalization regression silently corrupts a manuscript on Accept.
*Fix:* unit-test the pure pieces first (passage normalization/matching against curly-quote/em-dash fixtures; group_ids filtering); cover the git/seal/HTTP tail later with a fake NODE endpoint.
*Effort:* 2 hours.
*Verifier:* Verified; aggravator — the post-apply pytest gate only triggers for code groups, so book-manuscript edits get zero post-apply checks before auto-commit.

**Zero tests: series stage-vocabulary contract + review-ready overlay (shipped today)** · `src/sovereign_agent/node_api/routes/series.py:145-172, 331-339`
Commit 7e97413 (HEAD) added `_stage_labels()`, unknown-slug handling, and `_review_ready_overlay()` (the wire making the contract checker's verdict visible to KM). The existing series test predates this and references none of it.
*Fix:* extend the series fixture — drop a tmp `pipeline_stage_labels.yaml` + `artifacts/review_ready/<book>.json` (needs monkeypatch-able path resolution) and assert `stage_label`, `stage_step`, and the review_ready flag land on the card; assert unknown slug yields the fallback.
*Effort:* 45-60 min. **(Quick win)**
*Verifier:* Verified; understated — `_stage_labels()`/`_review_index()` have no env override, so the existing "hermetic" fixture silently reads the real artifacts on every test run.

**Missing abstraction seam / silent drift between lens and snapshot** · `scripts/pipeline_snapshot.py:24, 31`
`pipeline_snapshot.py` imports private functions from the Flask route module and calls `_series_card(s, idx)` with only the chapter index. The lens has since grown four more merge inputs (publishing/channel/stage/review), so the snapshot silently omits publishing_state/asin/channels/stage_label/review_contract while its header claims it captures "exactly what the lens renders". The drift the snapshot exists to detect has happened to the snapshot itself.
*Fix:* move the projection into a shared module with one `build_projection()` entry point both route and snapshot call; interim — pass the four indexes in `build_snapshot()`.
*Effort:* 20 min. **(Quick win)**
*Verifier:* Reproduced; the content_hash is computed over the impoverished cards, so the omission is invisible to the snapshot's own drift detection.

**Scaling: O(n) full-file replay per operation** · `src/sovereign_agent/obligations/ledger.py:120-128, 280-298, 331-340`
The architecture-dimension view of the ledger replay cost: at 10x scale (~5k entries) with the Atrium polling several lenses, each board refresh becomes tens of thousands of line parses plus full chain re-verification, and every `_append` is O(n) → O(n²) cumulative.
*Fix:* cache parsed entries keyed on `(st_mtime_ns, st_size)` invalidated by `_append`; verify incrementally (new tail only) and cache last verified state.
*Effort:* 2-3 hours.
*Verifier:* Reproduced (6 parses + full re-hash, 27.5 ms at 527 entries); `policy_loader.py` already uses the proposed mtime-cache pattern.

**console script depends on optional extra** · `pyproject.toml:51 vs 28-30 and 33-35` (`src/sovereign_agent/node_api/server.py:30`)
The `breathline-node-api` console script is registered unconditionally but points at `server:cli_serve`, whose module hard-imports flask, and flask is only in the optional `[portal]` extra. A plain `pip install` ships a broken command that dies with `ModuleNotFoundError: No module named 'flask'`. This Node API is the primary HTTP surface.
*Fix:* add flask to a dedicated `node-api` extra (with portal including it), or promote flask to base deps, or wrap the import with a clear `pip install "...[portal]"` error.
*Effort:* 15-20 min. **(Quick win)**
*Verifier:* Reproduced; failure is loud at runtime, hence MEDIUM.

**broken build — invalid Dockerfile syntax** · `Dockerfile:33, 36`
Lines 33/36 use shell redirection in COPY: `COPY six-sov-portal /app/six-sov-portal 2>/dev/null || true`. COPY is not a shell command — Docker parses `2>/dev/null`, `||`, `true` as additional source paths, so the build fails. The image as committed cannot be built, masking the deeper missing-breathline_primitives problem.
*Fix:* remove the shell suffixes; for optional copies use the wildcard trick (`COPY six-sov-porta[l] ...`) or multi-stage builds.
*Effort:* 10 min (syntax). **(Quick win)**
*Verifier:* Reproduced with Docker 29.1.5 (fails under both BuildKit and legacy builder). Bonus: line 27 also fails from the documented repo-root context.

**bootstrap script imports nonexistent module** · `activate-breathline.sh:41 (also 38-43)`
The fallback branch runs `from breathline_bootstrap import ensure_breathline_primitives`, but no module `breathline_bootstrap` exists (it lives at `sovereign_agent.bootstrap`). The `python3 -c` block always raises ModuleNotFoundError; with `set -e` the script aborts (and since it must be sourced, can terminate the user's interactive shell). The fallback activation path has never worked.
*Fix:* change line 41 to `from sovereign_agent.bootstrap import ensure_breathline_primitives` (a string arg works fine), or drop the verification block since line 37 already exports PYTHONPATH.
*Effort:* 10 min. **(Quick win)**
*Verifier:* Confirmed; reachable (line 18 accepts roots lacking `scripts/`); masked locally only because both checkouts have `scripts/breathline-sealed-env.sh`.

### LOW

**Cryptographic / token handling (non-constant-time compare)** · `src/sovereign_agent/node_api/auth.py:76`
Bearer-token verification compares secrets with plain inequality (`if stored != secret`) — not constant-time, theoretically vulnerable to timing analysis. Low practical risk on a loopback node, but trivial to harden and on the security-critical path (~50 routes).
*Fix:* use `hmac.compare_digest(stored, secret)`.
*Effort:* ~5 min. **(Quick win)**
*Verifier:* Confirmed; zero uses of compare_digest and no rate limiting anywhere. Adjacent (out of scope): differing 401 reason strings leak whether a principal exists.

**Transport security / configuration** · `src/sovereign_agent/node_api/server.py:145-161` (`auth.py:82-83`)
(1) TLS is not implemented — `principal:secret` bearer tokens travel cleartext, so any non-loopback bind exposes credentials. (2) Dev mode (`BREATHLINE_NODE_API_DEV=1`) disables the bearer check entirely; if left set on a non-dev deployment, every state-changing route becomes unauthenticated, with no loopback check on the dev path.
*Fix:* refuse to start (or loudly degrade) when dev mode is combined with a non-loopback bind; land self-signed TLS before allowing non-loopback binds; warn-and-block `0.0.0.0` without TLS.
*Effort:* ~1 hour.
*Verifier:* Confirmed both prongs; defaults are safe (127.0.0.1, dev off), exploitation requires operator misconfiguration — hence LOW.

**Full ledger re-read per /hopper poll** · `src/sovereign_agent/node_api/routes/hopper.py:139-158 (used at 184)`
When the iron-clad feed is wired, every GET `/hopper` reads and parses the entire `obligations.ndjson` (880 KB / 512 entries) just to build the packeted-refs set, bypassing the ledger object (so no ledger-level cache helps) and duplicating the parse the obligations routes do.
*Fix:* apply an `(mtime,size)`-keyed memo to the refs set (routing through the ledger singleton alone won't help — `_entries()` re-reads per call).
*Effort:* 20 min. **(Quick win)**
*Verifier:* Confirmed; the env default in `run_node_api.sh:10` makes the feed live.

**Unbounded in-process memory growth** · `src/sovereign_agent/compliance/compliance_engine.py:93 (_audit_trail), 147`
`_audit_trail` is a plain list that grows by one AuditRecord (with embedded receipt + attestation) on every obligation close for the life of the process; nothing trims it. Process-local state that vanishes on restart anyway (the durable record is the ledger + memory file).
*Fix:* prefer persist-to-disk-with-bounded-window over `deque(maxlen=N)` — a deque would silently truncate `export_evidence_bundle` and the audit endpoints that request limit=500/10000.
*Effort:* 15 min. **(Quick win)**
*Verifier:* Confirmed; per-record size is small (summaries truncated to 200 chars), hence LOW.

**dead code (unused imports)** · `src/sovereign_agent/universal_sovereign_node.py:21, 26-27, 30, 32`
AST-verified unused imports: `json`, the entire crypto block (`generate_keypair/sign/verify/MerkleTree/hash_function`, `secp256k1_curve`), `ConstitutionalGovernor/VerifiableMemory`, and `BoundRole` (only in quoted annotations). Same pattern: `placeholders.py:29` (uuid), `compliance_engine.py` (sys, Path), `pipeline_snapshot.py:19` (os).
*Fix:* delete the unused imports (keep `BoundRole` behind `if TYPE_CHECKING:`); one pyflakes pass catches all.
*Effort:* 15 min. **(Quick win)**
*Verifier:* AST-confirmed; nuance — removing USN's crypto imports won't drop the import-time `breathline_primitives` dependency (line 30 imports `.core` which imports it anyway).

**dead code (superseded placeholder machinery)** · `src/sovereign_agent/node_api/errors.py:68-77` (server.py:61, placeholders.py)
`not_implemented()` has zero callers — `placeholders.py` was rewritten into real thin handlers, but the stale naming layer remains (module still named placeholders.py, `server.py:61` comment, blueprint `sections_bdef`). Future readers will assume those 16 routes are stubs.
*Fix:* delete `not_implemented()`, fix the server.py/`__init__.py`/pyproject.toml stale comments; rename is optional.
*Effort:* 20 min. **(Quick win)**
*Verifier:* Confirmed (undercounts — `__init__.py:24-26` and `pyproject.toml:49` also claim 501 placeholders); caveat — `README.md:25` documents the filename is retained deliberately for blueprint-registration stability, so the rename part contradicts documented intent.

**latent bug (missing imports masked by PEP 563)** · `src/sovereign_agent/bootstrap.py:23 vs 114, 191`
`bootstrap.py` imports only `Optional` from typing but annotates `-> Dict[str, Any]`. Works only because `from __future__ import annotations` defers evaluation; any `typing.get_type_hints()`/runtime introspection raises `NameError: Dict`.
*Fix:* `from typing import Any, Dict, Optional`.
*Effort:* 5 min. **(Quick win)**
*Verifier:* Reproduced (NameError on get_type_hints); latent — no get_type_hints/pydantic usage in the repo.

**parallel-path drift + dead locals** · `scripts/pipeline_snapshot.py:31, 74, 88`
(Same root as the lens/snapshot drift finding, plus dead locals.) `build_snapshot()` omits the four overlay indexes; `prev = _coverage_of(out)` at line 74 is never used; `cov = meta["coverage"]` at line 88 re-assigns the identical value from line 80.
*Fix:* pass all five overlay indexes into `_series_card`; delete the unused `prev` and duplicate `cov`.
*Effort:* 20 min. **(Quick win)**
*Verifier:* All three reproduced.

**dead conditionals + hardcoded machine paths** · `src/sovereign_agent/config.py:86-90, 118-123, 127`
In `get_sealed_root()` and `get_federation_root()` both branches of the env-validation conditional return `p` — the `is_dir()`/`exists()` checks are dead code doing pointless filesystem stats. Line 127 keeps the hardcoded `/home/kmangum/work-repos/mangumcfo/breathline-federation` (self-annotated "will be removed"), redundant with the Path.home() candidate. Related hardcoded defaults in `playbook_loader.py:38`, `policy_loader.py:58`, `kernel_integration.py:39`.
*Fix:* collapse each if/else to `return p`; delete line-127 candidate; route the three modules' hardcoded defaults through config.py env-resolvable helpers.
*Effort:* 30 min. **(Quick win)**
*Verifier:* Reproduced; LOW — no functional bug.

**hardcoded machine-specific dependency paths (kernel can never load elsewhere)** · `src/sovereign_agent/config.py:127; kernel_integration.py:38-41`
`kernel_integration`'s candidate list is ONLY the kmangum layout (literal + same path via Path.home()); it never reads `BREATHLINE_FEDERATION_ROOT`. So a non-kmangum install gets federation roles but the kernel Governor/Critic/Auditor primitives never load — silently (all exceptions swallowed, returning None), degrading constitutional enforcement without notice.
*Fix:* derive kernel candidates from `config.get_federation_root()` (which honors the env var) + `/platform`; drop the literals.
*Effort:* 20 min. **(Quick win)**
*Verifier:* Reproduced; LOW because the kernel gate is an explicitly optional additive layer over the authoritative LGP heuristic.

**import name collision with ubiquitous PyPI package** · `src/sovereign_agent/compliance/compliance_engine.py:32-39, 94, 162`
The optional SIX backend is `from six import six_attestation, ...` — `six` collides with the ubiquitous PyPI `six` shim (installed in the active venv). Whenever PyPI six shadows the real package, the import fails, is swallowed by bare `except Exception`, and `_SIX_AVAILABLE` silently stays False — so `"sixon_backed"` permanently reports False even when the real SIX stack is present.
*Fix:* import SIX under a non-colliding package path/name; at minimum verify the imported module exposes the expected attributes and warn when shadowed/absent.
*Effort:* 30-60 min.
*Verifier:* Reproduced; worse than stated — `services/six` is a PEP 420 namespace package (no `__init__.py`), so the regular PyPI module wins regardless of sys.path order; renaming/adding `__init__.py` alone won't fix it.

**Python version assumption above declared floor** · `tools/create-sovereign-bundle.sh:20-25`
The bundle script uses `import tomllib` (3.11+) while pyproject declares `requires-python >=3.10`. On 3.10 the inline python fails and `|| echo "0.3.0"` silently substitutes a hardcoded version — so once pyproject is bumped past 0.3.0, a 3.10 host produces a bundle labeled with the wrong version, no warning.
*Fix:* hard-fail instead of the silent fallback, OR parse the version 3.10-compatibly (grep/sed), OR raise the floor to 3.11.
*Effort:* 10 min. **(Quick win)**
*Verifier:* Verified; latent today only because the fallback coincidentally matches the current version.

**no reproducibility pinning; vestigial requirements.txt** · `requirements.txt:1-2; pyproject.toml:28-41`
All deps are floor-only with no lockfile, and `requirements.txt` is an empty placeholder that contradicts pyproject (`pip install -r requirements.txt` yields an env missing pyyaml). For regulated/SOX/air-gapped positioning there is no way to reproduce a known-good dependency set; the bundle tool only zips source (no vendored wheels), and the Dockerfile uses unpinned `python:3.12-slim`.
*Fix:* delete requirements.txt and document `pip install -e ".[portal,dev]"`, OR make it a checked-in generated lock (pip-compile/uv lock) for the air-gapped story; add conservative upper bounds (e.g. `flask>=3.0,<4`).
*Effort:* 30-45 min. **(Quick win)**
*Verifier:* Confirmed; reproducibility gap, not a vulnerability today (Flask 3.1.3 / PyYAML 6.0.3, no CVEs).

**Test hygiene: module-level env mutation leaks across files** · `tests/test_node_api.py:27-31` (also test_extrusion_anchors.py:54, 68)
A module-scoped fixture sets `os.environ['BREATHLINE_NODE_API_DEV']='1'` directly (not via monkeypatch) and never restores it, so the dev-auth bypass leaks into every later-collected module; the suite's auth posture depends on collection order. No conftest.py; the sys.path hack is duplicated per-file; tests never set `OBLIGATION_LEDGER_ROOT` or call `deps.reset_node()`, so the ledger root is collection-order-dependent.
*Fix:* add `tests/conftest.py` with the sys.path insert + an autouse fixture that monkeypatches the env to a tmp root and calls `deps.reset_node()` around each test; convert the two direct `os.environ` writes to `monkeypatch.setenv`.
*Effort:* 30 min. **(Quick win)**
*Verifier:* Verified; suite currently passes 77/77 in ~1.26s — latent order-dependence hazard, not a live failure.

**Dead configuration seam (BREATHLINE_SEALED_ROOT, LOW dup)** · `src/sovereign_agent/bootstrap.py:73-79, 27-47`
The architecture-dimension restatement of the bootstrap env-var bug: the documented escape hatch (`BREATHLINE_SEALED_ROOT`) is dead in the activation path.
*Fix:* check `os.environ.get('BREATHLINE_SEALED_ROOT')` first in `_find_breathline_sealed_root`.
*Effort:* 15 min. **(Quick win)**
*Verifier:* Reproduced; masked on the dev machine only because `DEFAULT_SEARCH_PATHS[0]` exists.

## Quick Wins (<30 min)

- Bind ledger actor to the authenticated principal (drop body-supplied `approved_by`/`closed_by`/`owner`/`produced_by`) — `obligations.py:66/86/119`, `feedback.py:69`, `proposals.py:82` (~20 min)
- Validate `obligation_id` against a strict pattern before filesystem/subprocess use — `proposals.py:107` (~15 min)
- `hmac.compare_digest` for bearer-token compare — `auth.py:76` (~5 min)
- Filter `replay()`/`full_log()` approved-set on `disposition=='approved'` + regression test — `ledger.py:272/308-314` (30 min)
- Add `?limit=`/`?offset=` to `/obligations/log` and tail-read `/dialogue` — `obligations.py:38-51`, `series.py:420-444` (30 min)
- Cache last-entry hash on the ledger singleton to drop `_append`'s full re-read — `ledger.py:130-136` (30 min)
- Add existence + already-closed guards in `approve()`/`close()`, API 404 — `ledger.py:184-264` (≤30 min for the guards)
- Route hopper `_packeted_refs` through the ledger / add mtime memo — `hopper.py:139-158` (15-30 min)
- Mirror obligations.py exception handling in `feedback_disposition` — `feedback.py:132-155` (15 min)
- Align node.py tier/ladder keys with `SUPPORTED_CONTEXTS` — `node.py:96-117` (20 min)
- Delete duplicate Charter V.7 ack block — `compliance_engine.py:315-323` (25 min)
- Collapse recompile/viewer book-id map; hoist proposals-store path into a shared module — `proposals.py:194-228`, `atrium_apply.py:168-179` (20-30 min each)
- `mtime`-keyed memo + `CSafeLoader` on `/series` loaders — `series.py:52-174` (best <30 min for the memo)
- Per-request file memo in `/coherence` `_compute` (eliminates 9× re-reads) — `coherence.py:45-47` (15 min)
- Move corrupt `proposals.json` aside + tmp-write atomicity — `proposals.py:38-51` (≤30 min for the write fix)
- Read `BREATHLINE_SEALED_ROOT` in `_find_breathline_sealed_root` — `bootstrap.py:35-47` (15 min)
- Fix `activate-breathline.sh:41` import name; remove Dockerfile COPY shell suffixes — (10 min each)
- `from typing import Any, Dict, Optional` — `bootstrap.py:23` (5 min)
- Delete AST-confirmed unused imports + dead locals (pyflakes pass) — multiple files (15 min)
- `breathline-node-api` flask-extra guard; `tomllib` 3.10 fallback in bundle script — `pyproject.toml:51`, `create-sovereign-bundle.sh:20` (15-20 min each)
- `deque`/bounded window for `_audit_trail` — `compliance_engine.py:93` (15 min)
- Collapse dead `if/else return p` + drop hardcoded `/home/kmangum` paths; derive kernel candidates from config — `config.py:86-127`, `kernel_integration.py:38-41` (20-30 min)
- `tests/conftest.py` with autouse env+reset fixture — `tests/` (30 min)

## Refuted (for the record)

- **Whole-file read to tail a growing log** (`proposals.py` /processing) — the whole-file read at line 173 exists, but the finding misidentified the file: `/processing` reads `meta["log"]`, not the live run log being appended; the premise (reading the actively-written log) is false.
- **Resource leak in request handler** (`proposals.py` /produce, `stdout=open(logf,"w")` to Popen) — the code pattern exists but the claimed leak does not reproduce; the file object's lifetime is bound to the spawned process, not leaked in the request handler.

## Dimension Summaries

- **Security:** Two HIGH issues dominate — request-body principal spoofing forges the hash-chained actor, and authentication-without-authorization leaves code-executing routes (`/produce`, `/apply`, `/recompile`) open to any authenticated/loopback/dev caller; MEDIUM CSRF/DNS-rebinding, `/produce` path traversal, and an all-modes simulated approval gate compound it; positives verified (no eval/exec/shell=True, list-arg subprocess, PDF-route id guards, ledger boundary guard).
- **Performance:** Systemic and verified — every read endpoint reconstructs all state from disk per request on unbounded, cockpit-polled stores (6 ledger re-parses + full re-hash per GET /obligations, 61 ms YAML on /series, 946 KB manuscript reads on /coherence, O(n²) Merkle/memory rewrites), all fixable with mtime-keyed caches since the singleton process is the sole writer.
- **Code Quality:** Root pattern is copy-then-diverge between parallel modules rather than shared extraction — a no-op hopper dedup, a dead context vocabulary, dropped exception handling, three hash-chain copies, three status-derivation paths, a 518-line multi-responsibility file, and AST-confirmed dead code; 11 of 16 are quick wins.
- **Test Coverage:** 77 tests pass in ~1.25s with solid happy-path/Phase-1-3 coverage, but everything shipped today (feedback/awaiting_km, Review-Ready Rail, series overlay) and the entire Accept pipeline are untested, and the ledger's failure modes hide real latent bugs (chain-fork, torn-line 500s, orphan entries, denied→approved flip).
- **Dependencies:** Tiny declared surface with safe YAML and no CVEs, but the undeclared layer is broken — `breathline_primitives` (the crypto root) is hard-imported yet undeclared/un-pip-installable, the documented `BREATHLINE_SEALED_ROOT` is ignored, the node-api console script and Dockerfile and activate script are each independently broken, and the SIX backend silently dies on a name collision.
- **Architecture:** Layering intent is genuinely good (dependency-free ledger, clean adapter and composition root, no circular imports), but the single-writer fence is doctrine-only (unlocked appends fork the chain from threads AND scripts — already broken once on the THREAD chain), gateway bypasses cause two silent dedup failures, and the canonical roadmap projection lives in a Flask route module that the snapshot tool has already drifted from.
- **Constitutional:** The pure engine conforms (draft→approve gate, E0 floor, boundary guard, verifiable chain, honest principal flow), but the EXECUTE half breaks it — undecided proposal groups default-to-accept (Execute with no human Approve), abort/revert is non-transactional (new files survive), and two close paths hardcode `closed_by="tiger"` / pin every entry's principal_id to a literal `node`, so the requesting actor never reaches the audit chain.

---
*Run wf_60017456-927 · 7 dimensions · adversarially verified · confirmed by severity: {"HIGH": 14, "MEDIUM": 26, "LOW": 16, "CRITICAL": 1} (total 57, refuted 2) · NOTE: 17 verifier agents (mostly constitutional dimension) starved on spend limit at the tail — their candidate findings are NOT in this report; they re-run in the first nightly delta.*
