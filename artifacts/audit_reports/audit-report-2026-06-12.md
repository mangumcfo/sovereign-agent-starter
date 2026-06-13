# Sovereign Stack Audit — 2026-06-12

Audited across 7 dimensions (security, performance, code quality, test coverage, dependencies, architecture, constitutional conformance), with every finding below passing adversarial verification — false positives were refuted and removed before this report.

## Executive Summary

Overall health: **62/100**. The cryptographic and ledger core is genuinely strong — hash-chained double-entry ledger with a cross-process flock write-fence, constant-time token compare, principal bound from the verified token (never the request body), traversal-safe file serving, no shell=True / pickle / hardcoded secrets, and a well-covered 142-test suite that passes clean. Points are lost at the *edges* of that good core: **1 CRITICAL** (the Propose→Decide→Apply human-gate is not enforceable — undecided or explicitly-rejected diffs can be landed, committed, and sealed) plus a cluster of **HIGH** issues where the local node trusts the browser origin by default (wildcard CORS + default-on loopback-trust = a live CSRF/DNS-rebinding path to owner-level code execution), authorization is applied inconsistently across human-disposition routes, and the entire crypto core hard-imports an undeclared sideloaded package that breaks a clean `import sovereign_agent` and the Docker entrypoint. The single most important theme: **gate and trust boundaries are correct in the ledger but inconsistent and bypassable at the HTTP/apply edge — disposition and execution are sometimes proven, sometimes assumed.**

Critical count: **1**. High count: **9**.

## Prioritized Findings

### CRITICAL

**INTEGRITY — Propose→Approve→Execute gate bypassable** · `scripts/atrium_apply.py:193-198` (with `routes/proposals.py:397-421`)
The documented Propose→Decide→Apply flow is not enforceable in code. In `atrium_apply.main()` the group filter `[g for g in p.get("groups",[]) if (only and g["id"] in only) or (not only and decisions.get(g["id"],"accept")=="accept")]` has two bypasses: (1) when `group_ids` are passed, a group explicitly **rejected** in `/decide` is still applied because the `only` branch never consults `decisions`; (2) when no `group_ids` are passed and the proposal was never decided, `decisions.get(id,"accept")` defaults **every** group to accept. `proposals_apply()` never checks `status=="decided"`. So an undecided or rejected diff is written to disk, committed, and sealed; `@require_owner` gates *who* applies, not *whether* a disposition was recorded.
*Fix:* gate each group on `decisions.get(g["id"]) == "accept"` (drop the default); when `only` is passed, intersect with accepted decisions (`g["id"] in only and decisions.get(g["id"])=="accept"`); in `proposals_apply()` return 409 unless `status=="decided"` with ≥1 accepted group. *Effort:* 20-30 min. *Verifier:* CONFIRMED — both bypasses reproduced; the only spawn caller does no precheck.

### HIGH

**CSRF / DNS-rebinding (browser-origin attack on local node)** · `routes/server.py:79-96` + `auth.py:87-145` + `scripts/run_node_api.sh:14`
Two shipped defaults combine into a live cross-origin attack: `_attach_cors_headers` sets `Access-Control-Allow-Origin: *` on every response and the before_request hook answers OPTIONS preflights with 204 *before* auth; meanwhile loopback-trust authenticates any no-token request on 127.0.0.1 as the configured owner, and `run_node_api.sh` defaults `BREATHLINE_NODE_LOOPBACK_OWNER=KM-1176` with `BREATHLINE_NODE_OWNER` unset (so owner==loopback owner). Any web page open in the operator's browser can drive authenticated, owner-level POSTs (`/obligations`, approve/close, `/feedback/<id>/disposition`, `/produce`, `/apply`, `/recompile`) — igniting the executor and mutating the hash-chained ledger. No Origin/Host/CSRF check exists anywhere; DNS-rebinding works even against a 127.0.0.1 bind.
*Fix:* node-local Origin allowlist (no `*` for state-changing verbs), Host/Origin validation to defeat rebinding, per-session CSRF token or same-origin guarantee for POSTs; make loopback-trust opt-in. *Effort:* 2-4 hours. *Verifier:* CONFIRMED — all three locations verbatim; every refutation hypothesis (global auth hook, dev-mode confound, require_owner stopping it) failed.

**Missing authorization on state-changing routes (privilege gap)** · `routes/obligations.py:91-153`
`POST /obligations/<id>/approve` and `/close` carry only `@require_principal`, not `@require_owner`. They mutate the hash-chained ledger (approve clears the breath-gate; close mints a receipt) and reach the same `led.approve()`/`led.close()` that the sibling `/feedback/<id>/disposition` was deliberately owner-gated to protect. Any authenticated principal — including a verified federation peer — can dispose KM's obligations, recording themselves as approved_by/closed_by on the chain. Inconsistent trust boundary: human-disposition is owner-gated on one path, principal-gated on the other.
*Fix:* add `@require_owner` below `@require_principal` on both handlers (mirror feedback_disposition); if peers must close their own attestations, gate by obligation ownership. *Effort:* 15 min. *Verifier:* CONFIRMED — bounded to credentialed principals (lateral/priv-esc, not anonymous); `proposals_dismiss` is a related pattern worth separate review.

**Test Coverage — untested owner gate on disposition** · `routes/feedback.py:273-283`
`feedback_disposition` gained `@require_owner` on 2026-06-12 (Accept ignites `_ring_the_bell` → spawns executor + mutates the ledger), but `test_node_api_feedback.py` has only an owner_client fixture and ZERO negative test proving a non-owner gets 403 — violating the project's own `every_gate_earns_a_test` doctrine that `test_node_api_proposals.py` enforces for `/produce`/`/apply`/`/recompile`. A regression dropping the gate passes the suite green.
*Fix:* add a dev_client fixture (mirror proposals lines 27-39) and assert `POST /feedback/<id>/disposition` → 403 error=forbidden for a non-owner. *Effort:* 20 min. *Verifier:* CONFIRMED — coverage not provided anywhere else; gate is live in code, risk is regression-silence.

**Test Coverage — zero tests on board_rigor gate** · `scripts/board_rigor.py:70-106`
The "NO RUBBER STAMPS" enforcer wired into the Review-Ready Rail has zero tests. `rigor_check()` (R-LGP/R-OBL/R-DEPTH/R-HUMAN) and `rigor_check_md()` (parses the embedded ```rigor``` block the ratified GB rail mapping depends on) are unverified; `review_ready_contract._check_boards` depends entirely on this returning correct pass/fail. The regex boundaries (LGP_TERMS, BOILERPLATE, block extraction, malformed-JSON handling) silently drift.
*Fix:* add `tests/test_board_rigor.py` — a passing fixture plus one per failing rule (thin detail, boilerplate, missing LGP, material-without-obligation_id, empty board → R-STRUCT), and rigor_check_md valid/missing-block/invalid-JSON cases. *Effort:* 45 min. *Verifier:* CONFIRMED — `_BOILERPLATE` is anchored via `.match()`, so the boilerplate fixture must be short and exact.

**Test Coverage — zero tests on the readiness contract** · `scripts/review_ready_contract.py:246-294`
The machine-checkable gate deciding "no book reaches KM's queue unless ALL gates pass" has zero direct tests. `evaluate()` (4-gate AND), `mint_review_packet()` (mints a C1 material packet onto the live atrium_review ledger, idempotency keyed on `ref=review_ready:<book>`), and the per-gate checks (`_check_obligations` self-exclusion at line 171, `_check_fidelity` later-lines-win, `_check_gate6_renderability` receipt-box count) are unverified. This is an obligation-mint WIRE to the real hash-chained ledger; if the idempotency guard or self-exclusion breaks it either floods Awaiting-KM with duplicates or flips a not-ready book green.
*Fix:* `tests/test_review_ready_contract.py` on a tmp ledger — evaluate not-ready/ready, mint writes exactly one packet and is idempotent on second call, `_check_obligations` excludes its own `review_ready:` packet. *Effort:* 1-2 hours. *Verifier:* CONFIRMED — node consumer only reads the pre-written overlay, so no indirect coverage exists.

**portability-hardcoded-path** · `routes/feedback.py:175`
`_doc_roots()` hardcodes the vault as `_P("/home/kmangum/work-repos/mangumcfo/breathline-books-vault")` instead of `config.get_books_kdp_root()`. `config.py:145-148` documents this exact path was removed elsewhere for portability (BREATHLINE_BOOKS_VAULT). On any non-KM host the `/doc` route 404s on vault docs (the kdp root won't resolve and the traversal allow-check never matches the configured vault); `proposals.py`/`series.py` already use the config getter, so feedback.py is the lone holdout. series.py emits vault-relative paths intended to be served by this route.
*Fix:* replace the literal with `config.get_books_kdp_root()` (returns the kdp child — use directly), guard None like proposals.py's empty-string fallback. *Effort:* <30 min. *Verifier:* CONFIRMED — repo/artifacts and repo/scripts roots still work; only the vault branch breaks off KM's host.

**DEPENDENCIES — used-but-undeclared crypto core** · `universal_sovereign_node.py:26-27` (+ `core.py:20-27`, `playbook_loader.py:23`, `compliance/policy_loader.py:27`)
`breathline_primitives` (the entire crypto root: generate_keypair/sign/verify/MerkleTree/hash_function) is imported at module top level but is NOT in pyproject.toml or requirements.txt, not bundled, not pip-installable, and not installed (ModuleNotFoundError reproduced). It only works via sideloading the `~/work-repos/breathline-sealed` sibling onto sys.path. Because `__init__.py` eagerly imports `.core`, even `import sovereign_agent` fails on a clean machine, and the Docker `pip install -e ".[portal]"` doesn't provide it, so `CMD breathline-node-api` ImportErrors at startup despite the "runs anywhere" claim.
*Fix:* declare/vendor `breathline_primitives` (pyproject dependency or pip URL/path) or make core imports lazy with an actionable failure that doesn't break `import sovereign_agent`; fix requirements.txt + Dockerfile; apply the `inference/primitives.py:_bp()` graceful-fallback pattern. *Effort:* 1-3 hours (publishing as an installable artifact is larger). *Verifier:* CONFIRMED & reproduced both ways; minor: two enumerated locations (`compliance_engine.py:199` lazy, `json_provider.py` comment-only) are not top-level offenders — the four above are.

**ARCHITECTURE — divergent closed-ness in one /obligations response** · `ledger.py:542-552 (by_owner) vs 509-532 (replay/by_status)`
`GET /obligations` returns `by_status()` and `by_owner()` side-by-side, but they compute closed-ness differently: `replay()`/`by_status()` are reopen-aware; `by_owner()` derives `closed_ids` purely from credit events (line 547), ignoring the 42 reopen events in the live chain. A reopened-and-not-re-closed obligation would count OPEN in the rollup but CLOSED per-owner — the exact "one truth" failure reopen was built to prevent; the fix landed in `replay()` but not `by_owner()`.
*Fix:* derive `by_owner()`'s open/closed from `replay()['open']`/`['closed']` instead of recomputing — removes the divergence and the triple replay. *Effort:* 20 min. *Verifier:* CONFIRMED as a latent code defect; **currently dormant** — all 42 reopens were subsequently re-closed, so divergent count is 0 today. The finding overstates present observable impact; the next un-re-closed reopen triggers it.

**ARCHITECTURE — single-writer fence violation on proposals.json** · `routes/proposals.py:44-57, 79-95, 430, 454-465`
`proposals.json` is mutated by an unfenced, non-atomic read-modify-write (`_read()` → mutate → `_write()` with no flock, no tmp+rename). Three endpoints (create/decide/dismiss) race it; Flask serves threaded by default, so concurrent requests lose updates (last write wins), and a crash mid-write truncates the store to garbage which `_read` silently swallows to `[]`. This is the exact race the ledger closes with flock and that `thread_channel.py` fixed on 2026-06-12 — proposals.json (same directory) was left unfenced. A 60-packet review session is the live trigger.
*Fix:* wrap read+mutate+write under `fcntl.flock(LOCK_EX)` over a sibling `proposals.lock` and write atomically (tmp + `os.replace`) — the pattern already proven in `ledger._append`. *Effort:* 25 min. *Verifier:* CONFIRMED — Flask 3.1.3 `run()` defaults `threaded=True`; proposals.json is the only one of the three colocated stores with no lock and no atomic write.

### MEDIUM

**ARCHITECTURE — single-writer fence violation (cross-process)** · `scripts/atrium_executor.py:52-64`
`handshakes.json` gets the same unfenced read-modify-write, but runs as a **detached subprocess** spawned by `_ring_the_bell` on every Accept (`start_new_session=True`). Multiple Accepts spawn concurrent executors racing the file *and* the API's `GET /handshakes` reader; a mid-truncation read returns `[]`, so the A3 "never silently stuck" row shows empty under exactly the concurrency it's meant to surface.
*Fix:* give `_handshake` the same flock + atomic-write (tmp + `os.replace`) treatment via a `handshakes.lock` sibling. *Effort:* 20 min. *Verifier:* CONFIRMED — the hash-chained ledger the executor also writes is safe; the residue store is not.

**Broken auth/authz decorator ordering** · `routes/proposals.py:484-503`
`GET /export/packet` is `@require_owner` but MISSING the `@require_principal` above it, violating auth.py's documented "require_principal must run FIRST" contract. `g.principal_id` is never set, so `p != owner` is `None != "KM-1176"` → True → the route returns 403 for everyone (dead route, correctness bug). Latent risk: any reorder or change to require_owner's None-handling flips it from fail-closed to exposed, and the packet assembles owner-sensitive receipts + Merkle proofs.
*Fix:* add `@require_principal` between the route decorator and `@require_owner`. *Effort:* 5 min. *Verifier:* CONFIRMED — always-403 traced; no HTTP-layer test covers the route.

**Arbitrary file write via accepted proposal (path traversal)** · `scripts/atrium_apply.py:69-104,129-161`
`_resolve()` returns an absolute path AS-IS for a non-existent file (line 88) and `_apply_group` then `os.makedirs` + `open(path,"w")` writes it (137-140). A proposal group with `file="/home/kmangum/.breathline/credentials/KM-1176.token"` (or `~/.bashrc`) and empty `before` would be written with attacker-chosen contents. The producer authoring proposals is itself an LLM reading captured sessions (path is not purely operator-authored), and there's no allowlist confining writes to repo/book roots — gated only by the operator's diff-review Accept.
*Fix:* after `.resolve()`, require the target under `REPOS[*]['root']`/`BOOK_DIRS`; refuse off-root paths and credential/dotfile targets. *Effort:* 1-2 hours. *Verifier:* CONFIRMED & reproduced (created a nested dotfile); exploitation needs a poisoned producer group + an unnoticed Accept, so MEDIUM is fair.

**PERFORMANCE — replay() not memoized** · `ledger.py:509-552, 534-540, 542-552`
`replay()` is rebuilt from scratch and called 4× per `GET /obligations` (open_obligations + by_status + by_owner's 2 + an extra _entries scan); each replay is ~7 O(n) passes, so the primary list endpoint does ~28 full passes over the 995-entry chain per poll. The parse cache fixed disk re-reads but not the reconstruction cost; `verify_chain` is correctly memoized, `replay` is not.
*Fix:* memoize `replay()` on the same `_stat_key()` (mtime_ns, size) the parse/verify caches trust; reuse one reconstruction across the rollups. *Effort:* 20-30 min. *Verifier:* CONFIRMED — singleton ledger, key is no weaker than existing caches; drops to 1 replay/~7 passes, O(1) on repeated polls.

**PERFORMANCE — uncached /series loaders** · `routes/series.py:375-422, 57-179`
The cockpit's primary pipeline lens re-does ~8 filesystem ops per poll with zero caching: parse the 786-line roadmap plus 5 overlay files (chapter outlines — a 736 KB JSON, ASIN/channel trackers, stage labels, review_ready/*.json). All re-read and re-parsed each request though they mutate rarely.
*Fix:* mtime-keyed per-file cache (same `(path, mtime, parsed)` pattern as the ledger's `_entries`); a real edit bumps mtime and re-parses, keeping labels honest. *Effort:* 25-40 min. *Verifier:* CONFIRMED — no cache/ETag anywhere; the 736 KB JSON re-parse is the heaviest cost.

**PERFORMANCE — uncached /coherence manuscript scans** · `routes/coherence.py:36-58, 76-88, 91-145`
`_compute(reg, repo)` reads each cited manuscript full-file and substring-scans per extrusion, per request, duplicated across `/coherence` and `/coherence/rollup` with no shared/cached result.
*Fix:* cache `_compute` keyed on registry mtime + digest of cited book_file mtimes; at minimum memoize reads by path within a request. *Effort:* 30-45 min. *Verifier:* CONFIRMED mechanism; but the finding's magnitude is INFLATED — today's registry has 17 extrusions / 6 distinct files / ~560 KB (not 34 / ~17 large manuscripts), so present cost is sub-ms-to-low-ms — a latent scaling concern, not a current hotspot.

**PERFORMANCE — unbounded O(n) ledger reads, no pagination/index** · `ledger.py:37-47, 554-584, 304-309, 311-314, 174-183, 460-506`
`full_log()` folds and sorts all entries per call; `/obligations` returns all open with no limit; `_get`/`_is_approved`/`_is_closed`/`attestation_status` each scan the whole chain (close() invokes several per write); `classify_evidence` runs 5 regex scans. Fine at 995 entries; a scaling cliff given the stated 1M-book target.
*Fix:* pagination (limit/offset/cursor) on `/obligations` and `/obligations/log`; in-memory id→entry and id→state index rebuilt on the parse-cache mtime key, keeping the append-only chain as source of truth. *Effort:* half a day. *Verifier:* CONFIRMED — parse/verify caches spare re-parse/re-hash but not the per-entry folds; two docstring phrases are slightly misattributed (cosmetic).

**duplicate-logic — Book-number→id mapping ×3** · `routes/proposals.py:206-238`
The `{"10":"10_scaling_enterprise",...}` map + `re.search(r"Book (\d+)")` is duplicated verbatim in `recompile()` and `_resolve_book_id()` (same file), and a third time in `scripts/atrium_producer.py`.
*Fix:* have `recompile()` call `_resolve_book_id()`; extract a module-level `BOOK_NUM_TO_ID`. *Effort:* <30 min. *Verifier:* CONFIRMED — caveat: `_resolve_book_id`'s broader fallback changes the error path for non-10/11/12 titles, so whitelist-check the resolved id.

**duplicate-logic — four hash-chained-NDJSON implementations** · `thread_channel.py:7-86`
ObligationLedger, `gb_meta_cylinder.py`, `scripts/thread.py`, and `thread_channel.py` each carry their own `_hash`/append/verify; thread_channel's docstring admits it "mirrors scripts/thread.py exactly." The danger already materialized: the flock TOCTOU fix was applied to ledger.py and re-applied to thread_channel.py but **missed** in `scripts/thread.py`, which writes the same shared file.
*Fix:* extract THREAD primitives (`_hash`/load/append/`_render_md`) into one shared module imported by both thread.py and thread_channel.py. *Effort:* 1-2 hours. *Verifier:* CONFIRMED — both write `THREAD_Tiger_GB.ndjson`, so format/receipt drift is a real correctness risk.

**duplicate-logic — duplicated Charter V.7 ack check** · `compliance/compliance_engine.py:252-323`
The charter_v7_ack fail-closed guard is duplicated near-verbatim at lines 252-261 and 315-323; the second copy is unreachable (Block 1 returns before the policy branch, and its trigger set is a strict superset).
*Fix:* hoist into one guard/helper at the top and delete the duplicate. *Effort:* <30 min. *Verifier:* CONFIRMED dead via ordering + subset proof; no test asserts the second copy's rationale.

**high-complexity-function — run_policy_compliance_check** · `compliance/compliance_engine.py:217-333`
117-line central authorization decision, CC in the low-mid 20s: 5 terminal verdict exits, policy-present/absent split, nested classification/charter/approval/risk branches plus a parallel fallback set (incl. the duplicated charter check). ZERO dedicated unit tests — only exercised indirectly via demo scripts.
*Fix:* decompose into `_check_allowed_envelope` / `_check_charter_v7_ack` / `_apply_policy_rules` / `_apply_fallback_rules`; collapses the L254/L316 duplication. *Effort:* 2-4 hours. *Verifier:* CONFIRMED (CC computed manually, radon unavailable).

**TRUTH — provenance guard resolves only against one operator's vault** · `ledger.py:113-124`
`_assert_source_ref_resolves()` (the R22-3 "a citation is never written false" guard) hardcodes `/home/kmangum/.../breathline-books-vault` + its kdp child as resolution roots. On other hosts a genuine vault-relative `source_ref` fails to resolve and `close()` raises ValueError (blocks a legitimate close), while giving false assurance since it can't see the configured vault. `config.get_books_kdp_root()` exists precisely for this.
*Fix:* derive roots from `config.get_books_kdp_root()` / vault root (as proposals.py/series.py do), falling back to cwd + repo root when None. *Effort:* 15-20 min. *Verifier:* CONFIRMED — cwd/repo-root probes can incidentally succeed but don't cover the env/home-configured vault; only path_parts with both `/` and `.` are treated as file claims.

**ERROR VOICE — crypto signing failure degrades to a string** · `compliance/compliance_engine.py:209-210`
In `_generate_six_style_receipt()`, node-identity signing is wrapped in `except Exception: receipt['signatures']['node_identity']='signing_failed'` — no log, no raise, no metric — in a layer whose docstring promises "never silent degradation." `attest_execution()` still returns success with receipt_hash populated, so an unsigned receipt looks materially like a signed one to callers that don't deep-inspect signatures.
*Fix:* log loudly with `exc_info=True`, record a structured `{status:SIGNING_FAILED, error}` marker, and surface `signed: False` on the return. *Effort:* 15 min. *Verifier:* CONFIRMED — module imports no logging at all; both real callers ignore `signatures`. The USN self-attestation still runs, justifying MEDIUM not HIGH.

**duplicate-logic — three ledger-root defaults** (overlaps with the architecture seam below) · `routes/proposals.py:497-498, 515-516`
The `OBLIGATION_LEDGER_ROOT` fallback to `memory/obligations/atrium_review` is duplicated inline in `export_packet_route`/`actions_route` and hardcoded again in `scripts/review_ready_contract.py`, while `deps.py` defaults to `memory/obligations` (a *different* directory) and proposals/feedback derive yet another base from `.parent`.
*Fix:* one `get_ledger_root()` helper in deps.py; reconcile the atrium_review vs memory/obligations defaults. *Effort:* 30-60 min. *Verifier:* CONFIRMED — the default-path divergence borders on a latent correctness bug (silent empty queue), exactly what `_assert_root_not_starved` exists to scream about (but only logs).

**ARCHITECTURE — three ledger-root defaults, no single resolver** · `deps.py:66 + ledger.py:81-84 vs proposals.py:497-516 + feedback.py:258-259`
With `OBLIGATION_LEDGER_ROOT` unset, `deps.get_obligation_ledger()` falls back to `memory/obligations` (empty on disk) while export/actions read the real 995-entry `atrium_review` chain — same server, two ledgers. Alignment is guaranteed only by `run_node_api.sh` exporting the var; the starvation guard only logs.
*Fix:* one `deps.get_obligation_ledger_root()` called by proposals/feedback/relay, default matching `ledger._default_root()` exactly. *Effort:* 30 min. *Verifier:* CONFIRMED & reproduced (empty root, 995-line atrium_review); the disposition route + all of obligations.py via the deps singleton are the surfaces that actually split.

**ARCHITECTURE — robust roadmap parser trapped in an HTTP route** · `routes/series.py:234-304`
Only series.py has the resilient roadmap reader (`_load` + `_repair_unquoted_colons` + degraded flag), built because GB's hand-authored file recurs with strict-YAML-breaking scalars. Other scripts call `yaml.safe_load` directly and will crash on the malformation the lens survives — file-format resilience lives inside a Flask blueprint.
*Fix:* extract `_load` + repair family + `_roadmap_path` into `src/sovereign_agent/roadmap.py`; import everywhere. *Effort:* 45 min. *Verifier:* CONFIRMED for `build_book_code_tree.py:61` and `gen_outline_digest.py:40` (hard-crash). **Corrected:** `qualification_gate.py` does NOT parse the roadmap (false victim), and `extrusion_validate.py:143` is wrapped in try/except → silently returns `[]` (degrades, not crashes). Currently latent — the roadmap parses clean today.

**Test Coverage — proposals_dismiss partial-failure branch** · `routes/proposals.py:424-446`
The honest-failure branch (close raises → `status=dismissed_proposal_only`, warning, 200, proposal gone but obligation stays OPEN and resurfaces) is uncovered; `/dismiss` is never called by any test.
*Fix:* two tests — happy path (dismiss + obligation closed, closed_by=tiger/E1) and close-failed branch (status + warning present). *Effort:* 25 min. *Verifier:* CONFIRMED — repo-wide grep finds no test or caller.

**Test Coverage — ledger rejection exemptions (human "no" path)** · `ledger.py:379-400`
Two human-primacy exemptions in `close()` lack ledger-direct tests: (1) a MATERIAL obligation may be rejected without a prior approve() (breath-gate bypass for refusal); (2) a vetoed/missing-attestation obligation raises PermissionError on execute but a `rejected=True` close is exempt. The first is exercised only indirectly via HTTP; the second has no test at all.
*Fix:* two ledger tests for the reject-without-approve and reject-under-veto exemptions. *Effort:* 30 min. *Verifier:* CONFIRMED — no ledger test passes `rejected=`; invariant #2 has zero coverage; current behavior is correct (gap is regression-silence).

**Test Coverage — untested gb_meta_cylinder / pipeline_snapshot scripts** · `scripts/gb_meta_cylinder.py`, `scripts/pipeline_snapshot.py`
Both in-scope and dirty in git status, with zero test references. The cylinder feeds `review_ready_contract._check_fidelity`'s brittle substring verdict parser; a writer schema change silently flips the gate to non-PASS.
*Fix:* a smoke test each (cylinder writes an NDJSON line `_check_fidelity` reads as PASS; snapshot emits the expected JSON shape). *Effort:* 45 min. *Verifier:* CONFIRMED — the fidelity parser is brittle substring matching on lowercased lines; coupling makes the risk concrete.

### LOW

**Unauthenticated internal HTTP write relies on loopback-trust** · `scripts/atrium_apply.py:25,51-53,251-255`
The apply agent POSTs `/obligations/<id>/close` with no Authorization header, succeeding only via loopback-trust; the route overrides the body's `closed_by:"tiger"` with `current_principal()` (the loopback owner), so the receipt mis-attributes the close to KM. Widens the loopback-trust blast radius and muddies principal attribution.
*Fix:* give internal agents their own credential file + principal_id and send Authorization. *Effort:* 1 hour. *Verifier:* CONFIRMED.

**SOURCE — hardcoded principal violates CONSTITUTION §1** · `routes/proposals.py:437`
`proposals_dismiss()` closes with `closed_by="tiger"` — a fabricated actor written to the receipt's principal_id, the attestation, and the credit entry — though the route is `@require_principal` and `current_principal()` is imported and used at line 459. Contradicts the module's own "No hardcoded principals" docstring; every sibling write was fixed to bind the authenticated principal (audit 2026-06-10).
*Fix:* replace `closed_by="tiger"` with `closed_by=current_principal()`. *Effort:* 5 min. *Verifier:* CONFIRMED — script hardcodes (atrium_executor.py:69, atrium_apply.py:252) are honest (Tiger is the runner); only the API route is the violation.

**PERFORMANCE — proposals store full-rewrite per mutation** · `routes/proposals.py:44-57, 60-64, 449-466, 424-446`
Single JSON blob; `_read()` parses all and `_write()` serializes+rewrites all on every mutation; `/proposals` re-reads and full-sorts each request. O(n) per read/write, unbounded, and not concurrency-safe (no lock, unlike the ledger's flock).
*Fix:* mtime cache on `_read()` now; NDJSON + compaction if it grows; add a write-lock. *Effort:* 20 min for read cache. *Verifier:* CONFIRMED — bounded today since dismissed items are pruned.

**PERFORMANCE — by_owner two-pass + extra scan** · `ledger.py:542-552`
`by_owner()` replays once to seed open, scans `_entries()` for closed_ids, then replays again to decrement/increment — three reconstructions for a per-owner rollup one pass could compute.
*Fix:* count per-owner from a single `replay()` iterating `['open']` and `['closed']`. *Effort:* 15 min. *Verifier:* CONFIRMED — bonus correctness: deriving from `replay()['closed']` is reopen-aware, fixing a latent miscount; "three full reconstructions" slightly overstates I/O (one physical read).

**PERFORMANCE — ~4–5 replays per /obligations (scaling)** · `ledger.py:534-552, obligations.py:42-47`
Redundant uncached `replay()` rebuilds per request on the documented 1M-book scaling path; invisible at 995 entries.
*Fix:* compute replay once per request or memoize on `_stat_key`; fixing by_owner collapses most of them. *Effort:* 30 min. *Verifier:* CONFIRMED — count corrected to **4**, not 5 (the finding double-counts the cached `_entries()` scan as a replay).

**Test Coverage — BELL ignition + read routes** · `routes/feedback.py:230-270`
`_ring_the_bell()` best-effort failure tolerance, `/handshakes` (status!=done filter + newest-first sort), and `/review_brief` are untested net-new surface.
*Fix:* a 200-on-missing-atrium_executor.py test + a tmp HANDSHAKES_STORE test for the filter/sort. *Effort:* 25 min. *Verifier:* CONFIRMED — and thinner than stated: no test even asserts `executor=="spawned"`.

**duplicate-logic — ledger error-voice duplicated** · `routes/feedback.py:294-314`
The 404/409/403 ledger error responses are implemented twice — `obligations.py` helpers vs `feedback_disposition`'s inline re-implementation (commented "Mirror obligations.py error voice"). Bodies have already diverged in next_step text.
*Fix:* shared importable `_not_found`/`_already_closed`/`_breath_gate_denied` helpers, optionally parameterized for per-route next_step. *Effort:* 30-60 min. *Verifier:* CONFIRMED.

**duplicate-logic — ledger-root fallback ×3 (LOW slice)** · `routes/proposals.py:497-498`
(See the MEDIUM architecture/duplicate seam findings above.) *Fix:* single `get_ledger_root()` helper. *Effort:* 30-60 min. *Verifier:* CONFIRMED.

**portability — ledger provenance roots hardcoded** · `ledger.py:113-118`
`_assert_source_ref_resolves` hardcodes KM's vault + kdp child as resolution roots; on other hosts a valid vault-resident `source_ref` fails R22-3 and blocks `close()`. (TRUTH-dimension twin of the MEDIUM provenance finding.)
*Fix:* use `config.get_books_kdp_root()` + parent, fall back gracefully when None. *Effort:* <30 min. *Verifier:* CONFIRMED — identical on KM's host; strictly a cross-host gap.

**high-complexity-function — doc() route handler** · `routes/feedback.py:179-227`
~49 lines, three resolution strategies, 3rd-level nesting, security-sensitive (traversal guard).
*Fix:* split into `_resolve_doc_candidate` and `_resolve_bare_filename`; route becomes a short dispatcher. *Effort:* 1-2 hours. *Verifier:* CONFIRMED — traversal tested only end-to-end, never in isolation; guard logic appears sound.

**misleading-naming — placeholders.py** · `routes/placeholders.py:1-38`
Module named `placeholders` and registered as "(A+C real, B/D/E/F placeholders)" but the handlers wrap real primitives and the docstring calls them "real thin handlers." Misleads triage of shippable vs stubbed.
*Fix:* rename to `sections_bdef.py` (matching the Blueprint name) and fix the server.py import/comment; also amend the stale `__init__.py:24-26` "501 placeholders" docstring. *Effort:* <30 min. *Verifier:* CONFIRMED — note only `/federation/shards`/`/propagation` are genuine (honest) stubs; `/federation/peers` is real.

**DEPENDENCIES — fcntl is Unix-only** · `ledger.py:16`
Top-level `import fcntl` (used for the flock write-lock) makes the core engine unimportable on Windows; no OS classifier set despite "local-first" marketing.
*Fix:* add `Operating System :: POSIX` classifier + document Unix-only, or guard the import with a portable lock fallback (portalocker/filelock). *Effort:* 10 min (docs) / 30-45 min (fallback). *Verifier:* CONFIRMED — Linux Docker unaffected; the sibling thread_channel.py imports fcntl inside its function (fails later), showing the codebase knows it's POSIX-specific.

**DEPENDENCIES — unpinned Flask upper bound** · `pyproject.toml:33-35`
`flask>=3.0` with no cap; node_api relies on `flask.json.provider.DefaultJSONProvider`, and Flask 3.1.3 already emits a `__version__`-removal DeprecationWarning (3.x churn). A future `pip install` could pull 3.2+ and break the JSON provider silently.
*Fix:* `flask>=3.0,<3.2` and a lockfile. *Effort:* 5 min. *Verifier:* CONFIRMED — no lockfile/constraints anywhere; stability risk, not security.

**DEPENDENCIES — floor-only dev tooling** · `pyproject.toml:37-41`
`pytest>=7.0`, `build>=1.0`, `twine>=4.0` are floor-only with no caps and no lockfile/CI pinning, making the publish toolchain non-reproducible.
*Fix:* raise floors to known-good versions and/or add a dev lockfile; bump twine floor. *Effort:* 5 min. *Verifier:* CONFIRMED — no CI exists, slightly reducing urgency.

**DEPENDENCIES — misleading requirements.txt** · `requirements.txt:1-2`
Comment-only stub with zero entries while real deps live in pyproject; `pip install -r requirements.txt` yields a non-functional env, reinforcing the undeclared-primitives problem. Stale `playbook_loader.py:21` "may need pyyaml" comment confirms doc drift.
*Fix:* delete requirements.txt (point to `pip install -e ".[portal]"`) or generate from pyproject; remove the stale comment. *Effort:* 10 min. *Verifier:* CONFIRMED — supported path uses the extra, so harm only reaches readers who ignore docs; independently logged in the repo's own 2026-06-10 audit.

**ERROR VOICE — kernel-primitive load failures swallowed** · `kernel_integration.py:73, 85, 99, 131`
`get_kernel_critic/governor/auditor` and `record_kernel_usage` each `except Exception: return None` with no logging. Since `_ensure_kernel_primitives()` already handles the expected-absent case before the try, any exception there is unexpected (broken-but-present tree) yet silently no-ops the constitutional Governor/Auditor/Critic.
*Fix:* log at warning/error with `exc_info` inside each try before returning None. *Effort:* 10-15 min. *Verifier:* CONFIRMED — module imports no logging; core.py constructs with None gates inside its own bare except, compounding the silence. Behavior (graceful degrade) is correct; only visibility is lost.

**INTEGRITY — atrium_apply revert is best-effort, not guaranteed** · `scripts/atrium_apply.py:201-222`
The "if red → REVERT all changes" guarantee is unenforced: (1) `git checkout -- <newfile>` cannot delete an untracked new file (and a mix of new+modified files in one checkout aborts the *entire* revert, leaving the full diff); (2) the revert's return code is never inspected, so on a held index.lock the code proceeds to `_mark_error` believing it reverted while the tree still carries the landed diff.
*Fix:* track new-file creations and `os.remove()` them on abort; never pass untracked files into `git checkout --`; inspect every revert return code and set a distinct `apply_failed_dirty` status. *Effort:* 30-45 min. *Verifier:* CONFIRMED & reproduced (untracked file survives; mixed list reverts nothing); sole caller does no pre-stash or post-verify.

**TRUTH — produce/apply spawn without verifying the proposal exists/state** · `routes/proposals.py:397-421`
`proposals_apply()` validates only that the script exists, then spawns detached with the raw URL id, never checking the proposal resolves or its status; returns 202 "applying" regardless. A nonexistent/already-applied id yields a green response with nothing happening (stderr→DEVNULL), contrasting `produce()` which strictly regex-validates first.
*Fix:* mirror produce() — load via `_read()`, 404 if missing, 409 if already applied, or at minimum validate the `prop_<digits>` shape before spawning. *Effort:* 15 min. *Verifier:* CONFIRMED — `_log` also persists to `~/.breathline/atrium_apply.log` (recoverable), but the API surface is a false-positive success.

## Quick Wins (<30 min)

- **Owner-gate obligation disposition** — add `@require_owner` to approve/close · `routes/obligations.py:91-153` (15 min)
- **Fix export/packet decorator order** — add `@require_principal` above `@require_owner` · `routes/proposals.py:484-486` (5 min)
- **Bind the real principal on dismiss** — `closed_by=current_principal()` · `routes/proposals.py:437` (5 min)
- **Close the Decide-gate bypass** — drop the `,"accept"` default + intersect `only` with accepted decisions · `scripts/atrium_apply.py:194-195` (20-30 min)
- **Fence proposals.json** — flock + atomic write · `routes/proposals.py:44-57` (25 min)
- **Fence handshakes.json** — flock + atomic write · `scripts/atrium_executor.py:52-64` (20 min)
- **Fix by_owner reopen divergence** — derive from `replay()` · `ledger.py:542-552` (20 min)
- **Memoize replay()** on `_stat_key` · `ledger.py:509-532` (20-30 min)
- **Portable /doc vault path** — `config.get_books_kdp_root()` · `routes/feedback.py:175` (<30 min)
- **Portable provenance roots** — `config.get_books_kdp_root()` · `ledger.py:113-118` (<30 min)
- **Dedup Book-number→id map** — reuse `_resolve_book_id` · `routes/proposals.py:206-238` (<30 min)
- **Delete the dead charter check** · `compliance/compliance_engine.py:316-323` (<30 min)
- **Loud signing-failure surface** — log + `signed:False` · `compliance/compliance_engine.py:209-210` (15 min)
- **Log kernel-primitive failures** — `exc_info` in each except · `kernel_integration.py:73,85,99,131` (10-15 min)
- **Rename placeholders.py → sections_bdef.py** + fix server.py/__init__.py comments (<30 min)
- **Add disposition 403 test** — dev_client + forbidden assertion · `tests/test_node_api_feedback.py` (20 min)
- **Add /dismiss tests** (both branches) · `tests/test_node_api_proposals.py` (25 min)
- **Pin Flask `<3.2`** and bump dev-tool floors · `pyproject.toml:33-41` (5-10 min)
- **Fix requirements.txt + stale pyyaml comment** · `requirements.txt`, `playbook_loader.py:21` (10 min)

## Refuted (for the record)

- **Missing owner gate on breath_gate disposition + role invoke** (`placeholders.py:210-240`, `roles.py:111-170`) — REFUTED: the cited gating posture did not hold up as a real owner-gap on verification.
- **constitution-ceiling: ledger.py (632 lines)** — REFUTED as framed: line count is accurate but the "constitution ceiling violation" framing is false (the asserted ceiling does not bind this core engine file as claimed).
- **constitution-ceiling: series.py (594 lines)** — REFUTED as a MEDIUM ceiling finding: structural facts accurate, but the ceiling-violation conclusion is a false positive.
- **Cross-process cache soundness (`_entries`/`verify_chain` keyed on mtime+size)** — REFUTED: the (st_mtime_ns, st_size) key under the append fence is sound; no real cache-invalidation defect exists.

## Dimension Summaries

- **Security:** auth core is well-built (constant-time compare, principal-from-token, hash-chained flocked ledger, traversal-safe /doc), but human-disposition and execution acts are gated inconsistently and the local node trusts the browser origin by default — wildcard CORS + default loopback-trust is the single most serious exposure.
- **Performance:** the two worst I/O hotspots (parse cache, incremental verify_chain) are already fixed; remaining costs are the layers on top — unmemoized `replay()` (~4× per /obligations), uncached /series and /coherence loaders, and an unindexed/unpaginated ledger that is a scaling cliff, not a current outage.
- **Code quality:** two files over the 500-line ceiling and pervasive duplicate logic (book-id map ×3, four hash-chain implementations, duplicated charter/error-voice/ledger-root paths) plus hardcoded /home/kmangum vault paths bypassing the existing config seam; no genuinely dead code.
- **Test coverage:** 142 tests pass clean and the ledger engine is strongly defended, but coverage debt sits squarely on the newest Review-Ready Rail gate-scripts (board_rigor, review_ready_contract — zero tests) and one shipped-without-its-test owner gate (feedback disposition).
- **Dependencies:** declared deps are minimal and clean, but the entire crypto core hard-imports an undeclared, sideloaded `breathline_primitives` that breaks `import sovereign_agent` and the Docker entrypoint on any clean machine — plus Unix-only fcntl, an unpinned Flask, and a misleading empty requirements.txt.
- **Architecture:** the pure ledger is well-layered with a genuine flock write-fence, but the edges leak — a live reopen-divergence in one /obligations response, the single-writer discipline not applied to proposals.json/handshakes.json, no single ledger-root resolver, and a robust roadmap parser trapped inside a Flask blueprint.
- **Constitutional:** the ledger enforces principal-flow, provenance, and material/veto gates with loud errors, but the Propose→Decide→Apply human gate is not enforceable (CRITICAL), one fabricated principal still writes to the chain, the provenance guard is host-locked, and crypto/kernel failures degrade silently against an explicit "never silent" contract.

---

## Audit Footer — Full-Report Comparison (KM night watch)

**This run:** 2026-06-12 (full re-run, fresh cache) · Run ID `wf_cd950e14-cb3` · 58 agents · 7 dimensions · adversarially verified · no spend starvation.
**Previous full report:** 2026-06-10 (`audit-report-2026-06-10.md`, run `wf_60017456-927`).

| Severity | 2026-06-10 | 2026-06-12 | Δ |
|---|---:|---:|---:|
| CRITICAL | 1 | 1 | 0 |
| HIGH | 14 | 9 | **−5** |
| MEDIUM | 26 | 19 | **−7** |
| LOW | 16 | 18 | +2 |
| **Total confirmed** | **57** | **47** | **−10** |
| Refuted | 2 | 4 | +2 |
| **Overall health** | 58/100 | **62/100** | **+4** |

**Net:** −10 confirmed findings, +4 health. Material hardening landed since 06-10.

**The CRITICAL moved (not lingered):**
- *Fixed (was 06-10 CRITICAL):* unlocked concurrent ledger appends forking the hash chain — a cross-process `fcntl.flock` write-fence is now in place on `_append`.
- *New (06-12 CRITICAL):* the Propose→Decide→Apply human-gate is not enforceable — undecided/rejected diffs can be applied, committed, and sealed (`scripts/atrium_apply.py:193-198`). `@require_owner` gates *who* applies, not *whether* a disposition was recorded.

**Other fixes corroborated by this run's positives** (each was a confirmed 06-10 finding):
- Request-body principal spoofing → principal now bound from the verified token, never the request body.
- Non-constant-time bearer-token compare (06-10 LOW) → constant-time compare now in place.
- Traversal-safe file serving confirmed; no `shell=True` / `pickle` / hardcoded secrets.

**Still open / themes carried forward:** wildcard CORS + default-on loopback-trust = live CSRF/DNS-rebinding path to owner-level code exec (HIGH); inconsistent authorization across human-disposition routes (`/obligations` approve/close still only `@require_principal`); crypto core hard-imports undeclared sideloaded `breathline_primitives` (breaks clean `import sovereign_agent` + Docker); coverage debt on the newest Review-Ready Rail gate-scripts (`board_rigor`, `review_ready_contract` — zero tests).
