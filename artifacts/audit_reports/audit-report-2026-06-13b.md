# Sovereign Stack Audit — 2026-06-13 (W4 confirming sweep, post-cleanup)

*Seven dimensions assessed — security, performance, code quality, test coverage, dependencies, architecture, constitutional conformance — with every finding adversarially verified against source (false positives already refuted and removed).*

## Executive summary

Overall health: **78/100**. The cryptographic core is genuinely strong — the hash-chained obligation ledger is fenced (flock + fsync), memoized, and fail-closed on material gates; the HTTP auth layer has constant-time token compare, an explicit CORS allowlist, Sec-Fetch CSRF defense, traversal-safe file serving, and `yaml.safe_load` everywhere with no `eval`/`shell=True`/pickle anywhere in the tree. The score is held down because the engine's own proven disciplines — owner-gating, principal-binding, write-fencing, mtime caching, and resolve-or-error — stop at the ledger boundary and were applied **inconsistently** to the sibling route/store/lens layers. There are **7 CRITICAL/HIGH** findings (all rated HIGH; no CRITICAL). The single most important theme: **a defense is implemented correctly in one place and silently omitted on its sibling path** — the owner gate is missing from `/obligations/approve|close`, the ledger's write-fence is missing from `proposals.json`/`relays.json`, the ledger's mtime cache is missing from the polled lens routes, and the new resolve-at-entry `ValueError` is unhandled on three write routes. Almost every fix already exists in-repo as a pattern; this is propagation debt, not design debt.

## Prioritized Findings

### CRITICAL
None.

### HIGH

**1. Authorization — missing owner gate on state-changing obligations routes** · `src/sovereign_agent/node_api/routes/obligations.py:91-113 (approve), 116-153 (close)`
`POST /obligations/<id>/approve` and `/close` carry only `@require_principal`; `require_owner` is not even imported. `approve()` clears KM's constitutional breath-gate and `close()` mints a receipt + credit on the immutable chain. The sibling `/feedback/<id>/disposition` was deliberately owner-gated ("night-watch HIGH 2026-06-12") for the exact same `led.approve()/led.close()`. Any authenticated principal — including a federation peer or loopback caller — can dispose KM's material obligations, recording itself as `approved_by`/`closed_by`. No global before_request owner gate exists (`server.py:98` only short-circuits OPTIONS).
*Fix:* Add `@require_owner` below `@require_principal` on both routes (mirror `feedback_disposition`/`proposals_decide`); or gate by obligation ownership if peers must dispose their own. · **15 min** · *Verifier:* CONFIRMED — could not refute; `require_owner` exists at `auth.py:202-223` and ledger enforces no principal-vs-owner check.

**2. Concurrency — unfenced read-modify-write on `proposals.json`** · `src/sovereign_agent/node_api/routes/proposals.py:50-63, 85-104, 466-483, 497-509`
`_read()→mutate→_write()` rewrites the whole file with no flock and no tmp+os.replace, while the node runs `threaded=True` (`run_node_api.sh:19`). Concurrent create/decide/dismiss interleave → last-writer-wins, silently losing a proposal or a decision. This store now holds the Propose→Decide→Execute disposition state the owner-gated `/apply` reads, so a lost write can erase a `reject`. The ledger (`ledger.py:248-278`) and `thread_channel.py` already fixed this exact race; `proposals.json`, colocated beside the ledger, was left unfenced. No chain exists to even detect the loss.
*Fix:* Shared flock(LOCK_EX) read-modify-write helper on a `.lock` sidecar + tmp+os.replace, reusing `ledger._append`; apply to `proposals.py` and `relay.py` (and `atrium_apply.py`'s `_mark_error`, which races cross-process). · **1-2 hr** · *Verifier:* CONFIRMED — Flask `run()` defaults `threaded=True`; cross-process race via the `atrium_apply.py` subprocess.

**3. Concurrency — unfenced RMW on `relays.json`, plus a GET that persists state** · `src/sovereign_agent/node_api/routes/relay.py:48-61, 89-92, 108-132, 141-157`
Same unfenced RMW as proposals, with an extra hazard: `relays_list()` (a **GET**) persists an `answered` status-flip via `_write` inside the GET handler while two POST routes concurrently RMW the same file. A `/relays` poll firing between another request's `_read` and `_write` can clobber a freshly created relay.
*Fix:* Same shared locked RMW helper; additionally, the answered-fold should be computed read-only and persisted through the fenced writer, not inside the GET. · **~30 min once helper exists** · *Verifier:* CONFIRMED — `_fold_reply`/`find_reply` are read-only; GET write at line 128 is the sole extra hazard over proposals.

**4. Performance — no caching on hot lens route `GET /series`** · `src/sovereign_agent/node_api/routes/series.py:270-319 (and 57-196)`
Re-reads and re-parses SIX files on every request with zero caching: a 112KB `series_roadmap.yaml` (full PyYAML `safe_load`, the dominant cost), plus chapter/publishing/channel/stage/review indexes. The ledger right beside it has an mtime/size parse-cache; these lens routes have none (grep confirms only `functools.wraps` in node_api).
*Fix:* mtime+size-keyed memoization mirroring `ledger._entries()`, keyed on `(path, st_mtime_ns, st_size)`, re-parsing only on change. Roadmap is sole-write and changes rarely → ~100% hit rate. · **~30-60 min** · *Verifier:* CONFIRMED — roadmap measured 111,907 bytes. Nuance: precise "polled continuously" cadence is overstated (no live JS consumer found polling `/series`), but the uncached 6-file reparse is fully real.

**5. Performance — full-manuscript re-read per poll on `GET /coherence` + `/rollup`** · `src/sovereign_agent/node_api/routes/coherence.py:36-58, 76-88`
`_compute()` does `passage in open(bf).read()` — a full-file read + substring scan — for every extrusion on every request. Measured: 17 extrusions, ~948KB read+scanned per poll, no streaming/early-out, no cache. `/rollup` adds 3 more uncached `json.loads`. O(n) over extrusions, scaling linearly toward the stated 1M-book goal.
*Fix:* Memoize `_compute` on the registry's `(mtime_ns, size)` + referenced book-file mtimes; early-out the presence check instead of reading the whole file. The exact pattern exists at `ledger.py:209-225`. · **~30-60 min** · *Verifier:* CONFIRMED — 948,034 bytes verified live; blueprint registered at `server.py:67`.

**6. Truth/Error-Voice — unhandled `ValueError` on `hopper_to_packet` open()** · `src/sovereign_agent/node_api/routes/hopper.py:245-253` (root cause `obligations/ledger.py:331-332`, `_assert_source_ref_resolves:151-182`)
The 2026-06-13 resolve-at-entry rule makes `open()` raise `ValueError` on path-like refs that don't resolve. Real GB feed refs are compound and path-like (e.g. `artifacts/...Design Note...md + B51 delta + THREAD[67]`) — **verified to raise** against the actual `GB_Hopper_Feed.ndjson`. `hopper_to_packet` has no try/except, so a legitimate Send-to-Packet returns a bare 500 with no error voice. `server.py` registers only 404/405 handlers.
*Fix:* Wrap `open()` in `except ValueError` returning 422 with what/why/next_step (mirror the insufficient_evidence handler), and/or sanitize the compound ` + ...` suffix before validating. · **~20-30 min** · *Verifier:* CONFIRMED — raise reproduced against the real feed; no global 500 handler.

**7. Truth/Error-Voice — same unhandled `ValueError` on the primary `/obligations` open route** · `src/sovereign_agent/node_api/routes/obligations.py:78-87`
`obligations_open` passes `ref=body.get('ref')` straight into `open()` with no try/except; only `close()` catches `ValueError` (line 141). Any path-like ref to a file outside the known roots → unhandled 500, no code/next_step. `feedback_intake` (`feedback.py:99-110`) has the identical gap, with `ref` settable from `body.get('source')`. Path-like refs are the *normal* file-pointer use, so this is reachable in ordinary operation.
*Fix:* `except ValueError` around `open()` in `obligations_open` and `feedback_intake`, returning 422 with the constitutional what/why/next_step shape. · **~20 min** · *Verifier:* CONFIRMED — reproduced empirically; `server.py` has no generic exception handler.

**8. Integrity — transactional revert leaks newly-created files** · `scripts/atrium_apply.py:137-142 (new-file write), 209-212 & 224-226 (revert)`
The "if red → REVERT all" guarantee uses `git checkout -- <files>`. A group that creates a new (untracked) file never `git add`s it before an abort, and `git checkout -- <untracked>` does not delete it — the file survives the revert. Worse: when a new file is batched in the same per-repo `git checkout --` call as edited tracked files (the normal case), the failed pathspec aborts the *whole* command, so the tracked edits also fail to revert. Partial state lands, contradicting the docstring.
*Fix:* Track created paths in a `created` set and `os.remove()` / `git clean -f --` them on abort, in addition to `git checkout --` for edited files; use per-path checkout to avoid the all-or-nothing pathspec abort. · **~30-45 min** · *Verifier:* CONFIRMED — git behavior reproduced empirically; live path is `proposals.py:447`.

### MEDIUM

**9. Authorization + chain misattribution on `proposals_dismiss`** · `src/sovereign_agent/node_api/routes/proposals.py:461-483`
Gated only by `@require_principal` (unlike sibling `/decide` and `/apply`), so any authenticated principal can close KM's session obligations via dismiss; and it hardcodes `closed_by="tiger"` (line 474) instead of `current_principal()`, violating the 2026-06-10 "bind to authenticated principal, no hardcoded principals (CONSTITUTION §1)" rule. *Fix:* Add `@require_owner`; change `closed_by="tiger"` → `closed_by=current_principal()`. · **10 min** · *Verifier:* CONFIRMED — both sub-claims reproduce.

**10. Hardcoded principal at execute→storage boundary (apply + dismiss)** · `scripts/atrium_apply.py:258`; `proposals.py:474`
The bell path was fixed to propagate `current_principal()` via `BREATHLINE_BELL_PRINCIPAL`, but `proposals_apply` spawns `atrium_apply.py` without propagating the principal, and `atrium_apply` closes the obligation with hardcoded `closed_by="tiger"` (CONSTITUTION §1). Credit, receipt, and actions projection name "tiger" regardless of who clicked Accept. *Fix:* Set `env['BREATHLINE_APPLY_PRINCIPAL']=current_principal()` in `proposals_apply`; have `atrium_apply` read it for `closed_by` (never default "tiger"). · **~30 min** · *Verifier:* CONFIRMED — note: the line-240 git author is a static KM identity, not "tiger" (a separate, lower-severity weakness); the `closed_by` hardcode is the real §1 violation.

**11. Concurrency — unfenced non-atomic decision-state write (proposals.json detail)** · `src/sovereign_agent/node_api/routes/proposals.py:50-63, mutated at 85-103, 497-508, 465-467`
Same unfenced RMW as finding 2, framed as security-relevant decision-state loss/truncation that the constitutional `/apply` gate (`421-444`) and `atrium_apply.py:193-201` depend on; `_read` silently swallows a truncated file to `[]`. *Fix:* covered by finding 2's locked-RMW helper; also cover `atrium_apply.py`'s `_mark_error`. · **25 min** · *Verifier:* CONFIRMED — cross-process race; in-process lock alone insufficient.

**12. Code quality — duplicated THREAD chain math, only one copy locked** · `src/sovereign_agent/node_api/thread_channel.py:32-95` + `scripts/thread.py:29-103`
`_hash`/`load`/`_render`/`append` are duplicated verbatim over the same on-disk record. `thread_channel.append()` fences under flock (2026-06-12 fix); `scripts/thread.py append()` has NO lock. A nightly-cron CLI append racing a node Relay click can read the same `prev_hash` and fork the shared chain. *Fix:* Have `scripts/thread.py` import/call the node's locked `append/load/verify` (single locked writer). · **1-2 hr** · *Verifier:* CONFIRMED — both resolve to the same `THREAD_Tiger_GB.ndjson`; cron caller verified.

**13. Inconsistent pattern — hardcoded vault path bypasses the config seam** · `src/sovereign_agent/node_api/routes/feedback.py:175`
`_doc_roots()` hardcodes `/home/kmangum/work-repos/mangumcfo/breathline-books-vault` for the `/doc` whitelist; every sibling resolves via `config.get_books_kdp_root()`. On any other host, `/doc` cannot resolve vault docs → Awaiting-Me cards 404. *Fix:* Use `config.get_books_kdp_root()` guarding for None (mirror `series.py:438`). · **20 min** · *Verifier:* CONFIRMED — lone bypass; siblings degrade gracefully.

**14. Architecture — `extrusion_validate.py` bypasses the single roadmap-read seam** · `scripts/extrusion_validate.py:141-148`
Calls raw `yaml.safe_load(ROADMAP.read_text())` instead of `yaml_repair.load_roadmap` (used by the other 4 consumers). On a degraded GB-authored YAML the seam exists to tolerate, this validator emits a `⚠ ROADMAP PARSE ERROR` row while every lens renders the file fine — a false alarm and storage-format drift. *Fix:* Route through `load_roadmap` and surface the `degraded` flag (mirror `build_book_code_tree.py:64-65`). · **20 min** · *Verifier:* CONFIRMED — divergence reproduced on the degradation class; latent today (current roadmap parses cleanly).

**15. Performance — per-request reparse of 5 series index files (no memoization)** · `src/sovereign_agent/node_api/routes/series.py:57-196, 283-289`
Same root as finding 4, framed as the codebase's own caching-doctrine inconsistency: the self-described "1M-book foundation" got none of the ledger's mtime/size memoization. *Fix:* mtime/size-keyed memoization on the five index loaders. · **1-2 hr** · *Verifier:* CONFIRMED — scaling risk, not a correctness bug; MEDIUM appropriate at 12-book scale.

**16. Performance — per-request process + whole-log scan on `GET /processing`** · `src/sovereign_agent/node_api/routes/proposals.py:152-197`
Per request: full `proposals.json` parse (only obligation_ids needed), glob over `~/.breathline/runs`, per-run `os.kill(pid,0)`, and `open(lf).read().splitlines()[-14:]` — reads the **whole** (growing) live log to keep 14 lines. *Fix:* Seek-to-end bounded tail read (~8KB); optional mtime-keyed `_read()` cache shared with `/proposals`. · **~20 min** · *Verifier:* CONFIRMED — debunks the 2026-06-10 refutation: `meta["log"]` IS the actively-growing run log.

**17. Test isolation — accept-disposition spawns a real detached process** · `tests/test_node_api_feedback.py:83-93 (and 44-66)`
The ACCEPT path calls `_ring_the_bell()`, which `Popen`-spawns a detached `atrium_executor.py` that mutates the tmp ledger out-of-band. This test file has no `no_spawn`/Popen stub (unlike `test_node_api_security.py:42-52`), so the suite fires real detached processes on every run. *Fix:* Add a `no_spawn` autouse fixture monkeypatching `subprocess.Popen`. · **15 min** · *Verifier:* CONFIRMED — no conftest, no global mitigation.

**18. Test coverage — concurrent double-mint race in `mint_review_packet` untested** · `scripts/review_ready_contract.py:251-282`
Idempotency is check-then-act (scan for existing `review_ready:<book>` ref, then `open()`) with no lock spanning both; `ledger.open()` does no ref-dedup and the flock fence only prevents chain forking, not duplicate same-ref opens. Only sequential idempotency is tested. *Fix:* Add a 2-process concurrent mint test asserting exactly one packet; if it fails, move dedup under the write-lock as atomic check-and-open keyed on ref. · **30 min** · *Verifier:* CONFIRMED — race real; CLI path (needs overlapping invocations).

**19. Test coverage — `/proposals/<id>/dismiss` has zero tests** · `src/sovereign_agent/node_api/routes/proposals.py:461-483`
State-changing (writes store + closes ledger obligation); its degraded `dismissed_proposal_only` branch (close raises → 200 + still-OPEN obligation) is entirely unexercised. *Fix:* Add happy-path + close-raises tests. · **25 min** · *Verifier:* CONFIRMED — only `/dismiss` test is the unrelated relay route.

**20. Dependencies — `cryptography` used but undeclared** · `scripts/crypto_vector_check.py:108-136`
The crypto-assurance gate imports `cryptography` (its central purpose) but it is declared nowhere — works only because 46.0.4 is coincidentally installed. On a clean install the `ImportError` is swallowed by `except Exception` (135) and recorded as `interop_cross_verify: False`, flipping the whole suite RED (exit 1). *Fix:* Declare in an optional extra (`crypto-assurance = ["cryptography>=42,<47"]`) + pin in constraints.txt; emit a distinct WARNING/skip on absence instead of folding into a generic FAIL. · **30 min** · *Verifier:* CONFIRMED — contradicts the repo's own 2026-06-13 audit which wrongly called it a "silent skip"; there is no skip path, it's a hard FAIL.

**21. Dependencies — reproducibility lock not wired into the Docker build** · `Dockerfile:31-33`
`constraints.txt` advertises itself as the "Reproducible constraints lock for the Docker/CI path," but the Dockerfile never COPYs it and runs `pip install -e ".[portal]"` with no `-c constraints.txt` — exact pins resolve live at build time, defeating the SOX/air-gapped reproducibility claim. *Fix:* `COPY pyproject.toml README.md constraints.txt ./` then `RUN pip install --no-cache-dir -e ".[portal]" -c constraints.txt`. · **10 min** · *Verifier:* CONFIRMED — no CI exists; nothing else consumes the lock. (Note: true byte-reproducibility also needs digest-pinning the `python:3.12-slim` base.)

### LOW

**22. Dev-mode principal becomes the chain actor** · `src/sovereign_agent/node_api/auth.py:142-150` — A `dev:<label>` token is bound verbatim to `g.principal_id` and flows into the chain; with no owner gate on obligations approve/close (finding 1), a loopback `dev:<arbitrary>` caller self-assigns the audit actor. Mitigated by the non-loopback dev-start refusal (`server.py:163-176`). *Fix:* covered by finding 1. · **covered by #1** · *Verifier:* CONFIRMED — residual is a local non-owner process forging the actor.

**23. O(n) full-store rewrite grows unbounded** · `src/sovereign_agent/node_api/routes/proposals.py:50-104` — Single JSON blob; every create re-serializes the whole array, list endpoint loads+sorts everything, no pagination/append/prune. *Fix:* migrate to append-only NDJSON (like the ledger) or add a list `limit`. · **~1-2 hr (NDJSON) / 20 min (limit stopgap)** · *Verifier:* CONFIRMED — read side is also on a poll path.

**24. Uncached derived set on `GET /hopper`** · `src/sovereign_agent/node_api/routes/hopper.py:139-163, 166-185` — `_packeted_refs()` rebuilds a set over the full ledger each poll; `_entries()` is cached but the derived set is not. *Fix:* memoize on `_stat_key()` like `replay()`/`verify_chain()`. · **~15-20 min** · *Verifier:* CONFIRMED — feed-branch-only, bounded; LOW appropriate.

**25. Duplicated node-local JSON store trio** · `relay.py:39-61` + `proposals.py:41-63` + `feedback.py:265` — `_store_path/_read/_write` cloned; base derivation repeated a third time. *Fix:* extract `node_api/_jsonstore.py`, preserving per-module env-var/filename/`ensure_ascii` differences. · **45 min** · *Verifier:* CONFIRMED — pure DRY.

**26. Dead/broken config role `compliance_agent_demo`** · `src/sovereign_agent/config.py:34, 42` — Advertised in `FRIENDLY_DEMO_ROLES` and added to the discoverable set, but no `compliance_agent_demo/` dir exists and the alias key is `compliance_agent` (no `_demo`), so it can never load (actually raises an unhandled `FileNotFoundError` → HTTP 500). *Fix:* drop it, or rename to `compliance_agent` to match the alias. · **10 min** · *Verifier:* CONFIRMED — reproduced; impact marginally worse than stated (500, not silent).

**27. `ma_data_room` demo role missing `role_spec.yaml`** · `src/sovereign_agent/demo_roles/ma_data_room` — Ships `role.py`+`__init__.py` but no spec, so `discover_roles()` silently skips it; reachable only via direct test import. *Fix:* add a `role_spec.yaml` or relocate out of `demo_roles`. · **30 min** · *Verifier:* CONFIRMED — convention inconsistency only.

**28. `proposals.py` over the 500-line ceiling** · `src/sovereign_agent/node_api/routes/proposals.py:1-564 (esp. 285-398)` — 564 lines; the self-labeled "KDP Dispatch" artifact-serving block is a clean extraction. *Fix:* extract `routes/book_artifacts.py` (note: `_BOOK_NUM_TO_ID` is also used by `recompile`, so duplicate/import it). · **2-3 hr** · *Verifier:* CONFIRMED — narrower and better-grounded than the prior refuted line-count finding.

**29. Redundant re-slice in `_b51_entries()`** · `src/sovereign_agent/node_api/routes/series.py:378-404` — `raw[-limit:]` re-sliced per iteration purely for its length. *Fix:* `window = raw[-limit:]; start = total - len(window)` before the loop. · **10 min** · *Verifier:* CONFIRMED — readability; negligible perf at limit=12.

**30. Config bound at import time** · `src/sovereign_agent/node_api/routes/series.py:34` — `_PLAYBOOKS_DIR = config.get_playbooks_dir()` frozen at import; the ASIN/CHANNEL overlays then ignore a post-import `BREATHLINE_BOOKS_VAULT` change while everything else honors it. *Fix:* resolve per-call inside `_publishing_index()`/`_channel_index()`. · **15 min** · *Verifier:* CONFIRMED — testability/coupling; LOW.

**31. `/proposals/<id>/recompile` internal branches untested** · `src/sovereign_agent/node_api/routes/proposals.py:200-224` — Only the owner-gate rejection is asserted; `unknown_book` 400, `no_build_script` 500, and the happy 202 are unexercised. *Fix:* add owner_client tests (happy case needs `_VAULT` pointed at a tmp vault with `build_v1.0.py`; stub Popen via `no_spawn`). · **20 min** · *Verifier:* CONFIRMED.

**32. `/processing` route untested** · `src/sovereign_agent/node_api/routes/proposals.py:152-197` — Mutates the filesystem (`jf.unlink`) and classifies live/dead/result-landed with zero tests. *Fix:* seed `~/.breathline/runs` (monkeypatch HOME) and assert classification + unlink (dead-run cleanup needs `started_at` >150s in the past). · **30 min** · *Verifier:* CONFIRMED.

**33. `/coherence/rollup` aggregation math untested** · `src/sovereign_agent/node_api/routes/coherence.py:91-145` — Only a 200/keys smoke test; pct rollup, cap folding, narrative classification unverified. *Fix:* seed registry+capabilities+coverage and assert by_book pct, cap totals, narrative count. · **30 min** · *Verifier:* CONFIRMED.

**34. `GET /obligations/log` untested** · `src/sovereign_agent/node_api/routes/obligations.py:50-64 (route 50-63)` — UI/audit-trail feed has no direct test of its response shape. *Fix:* one test asserting entries in order with expected fields after open+close. · **15 min** · *Verifier:* CONFIRMED — `test_audit_ledger_fixes` hits `full_log()` directly but not the route envelope.

**35. Misleading empty `requirements.txt`** · `requirements.txt:1-2` — Comment-only stub; `pip install -r requirements.txt` yields zero deps, breaking `import yaml` in `playbook_loader.py`/`policy_loader.py`. *Fix:* delete and point docs at `pip install -e ".[portal]"`, or regenerate as a faithful mirror. · **10 min** · *Verifier:* CONFIRMED — still unresolved from prior audits.

**36. `constraints.txt` drift from verified baseline** · `constraints.txt:10-13` — Pins `PyYAML==6.0.1` (env has 6.0.3) and `pytest==8.3.0` (env has 8.4.2; dev floor is `>=7.0`); "suite 160 green" note stale (185 collected). *Fix:* regenerate from the tested env, keep the verified-against note in sync. · **15 min** · *Verifier:* CONFIRMED — hygiene, no CVE.

**37. Stale `pyyaml` import comment** · `src/sovereign_agent/playbook_loader.py:21` — Comment implies pyyaml is optional/unmanaged; it is a declared, version-bounded core dep. *Fix:* update/remove the comment. · **2 min** · *Verifier:* CONFIRMED.

**38. Best-effort close after commit → partial-state divergence** · `scripts/atrium_apply.py:245-264` — After a successful commit + cylinder seal, a failed HTTP `close()` is only logged; the proposal is still marked `applied` while the obligation stays OPEN, so the anti-hiding board re-surfaces it as un-disposed though the work is applied. *Fix:* mark `status='applied_close_pending'` (+oid) on close failure, or close before marking applied. · **~30 min** · *Verifier:* CONFIRMED — recoverable and logged; LOW.

## Quick Wins (<30 min)

- **#1** Owner-gate `/obligations/approve|close` — `obligations.py:91, 116` (15 min)
- **#7** Wrap `open()` in `except ValueError` → 422 — `obligations.py:78`, `feedback.py:99` (20 min)
- **#6** Same try/except (+ ref sanitize) — `hopper.py:245` (20-30 min)
- **#9** Owner-gate + `closed_by=current_principal()` — `proposals.py:462, 474` (10 min)
- **#10** Propagate principal to apply; `closed_by=current_principal()` in dismiss — `atrium_apply.py:258`, `proposals.py:474` (30 min)
- **#13** Replace hardcoded vault path with `config.get_books_kdp_root()` — `feedback.py:175` (20 min)
- **#14** Route through `load_roadmap` — `extrusion_validate.py:141` (20 min)
- **#16** Bounded log-tail read — `proposals.py:191` (20 min)
- **#17** `no_spawn` autouse fixture — `tests/test_node_api_feedback.py` (15 min)
- **#19** dismiss happy + degraded tests — `proposals.py:461` (25 min)
- **#20** Declare `cryptography` extra + WARNING/skip — `crypto_vector_check.py:135`, `pyproject.toml` (30 min)
- **#21** Wire `constraints.txt` into Docker — `Dockerfile:31-33` (10 min)
- **#24** Memoize hopper packeted-refs set — `hopper.py:139` (15-20 min)
- **#26** Drop/rename `compliance_agent_demo` — `config.py:34` (10 min)
- **#29** Hoist the `raw[-limit:]` slice — `series.py:395` (10 min)
- **#30** Resolve playbooks dir per-call — `series.py:90, 133` (15 min)
- **#34** `/obligations/log` shape test (15 min); **#37** fix stale comment — `playbook_loader.py:21` (2 min); **#35** delete `requirements.txt` stub (10 min); **#36** regenerate `constraints.txt` (15 min)

## Refuted (for the record)

- **`ledger.py` over 500-line ceiling** — bare line-count (708) is true, but the "should split" claim does not hold: it's a cohesive append-only engine core with no clean separable concern, unlike `proposals.py`.
- **`atrium_apply.py` replaces only the first occurrence despite an "every instance" contract** — the quoted comment and code are accurate, but the apply semantics are correct as designed; false positive on the "every instance" reading.

## Dimension Summaries

- **Security:** Crypto/auth core is genuinely hardened (constant-time compare, CORS allowlist, CSRF stop, traversal-safe serving, no unsafe deserialization, flock+fsync fences); the residual risk is an inconsistent trust boundary — `/obligations/approve|close` carry only `@require_principal`, the one place the owner-gate fix was never propagated.
- **Performance:** The ledger is well-cached (mtime/size parse-cache + memoized replay/verify); the real hot spots are the uncached cockpit lens routes — `/series` (112KB YAML), `/coherence` (~948KB manuscript scan), `/processing` (whole-log read) — which never received the ledger's caching discipline.
- **Code quality:** Well-documented with no dead hot-path code; debt clusters in duplicated logic (THREAD chain math diverged so only the node copy is locked; the JSON-store trio cloned), inconsistent patterns (hardcoded vault path, dead `compliance_agent_demo`), and two files over the 500-line ceiling.
- **Test coverage:** Strong — 185 tests pass cleanly, with hash-chain break/repair and ledger concurrency well-covered; remaining gaps are a feedback-spawn isolation defect, an unproven concurrent-mint race, and behavior-untested dismiss/recompile/processing/rollup/log routes.
- **Dependencies:** Mostly clean and recently hardened (upper bounds, no CVEs, `pip check` green); the real gaps are an undeclared `cryptography` that silently fails the crypto gate RED and a reproducibility lock the Dockerfile never applies, plus hygiene drift in requirements/constraints.
- **Architecture:** The hash-chained ledger is exemplary (single write-fence, memoized replay, one clean node-coupling seam, no cycles), but its fencing/caching doctrine stops at the ledger boundary — unfenced `proposals.json`/`relays.json` stores, a bypassed roadmap-read seam, and uncached lens loaders are the inverse of the ledger's own discipline.
- **Constitutional:** Hash chain, write-fence, evidence-tier floor, fail-closed material gate, and the Propose→Decide→Execute gate are solid; the issues cluster on the theme the constitution names — pointers/state that don't resolve (unhandled resolve-at-entry `ValueError` on three routes) or don't revert (new-file leak in atrium_apply), plus hardcoded `closed_by='tiger'` at the apply/dismiss execute→storage boundary.

---
*Run wf_153a24f7-e1e · 7 dims · adversarially verified · confirmed by severity: {"HIGH": 8, "MEDIUM": 13, "LOW": 17} (total 38, refuted 2).*
*TRAJECTORY: 58 (06-10) → 62 (06-13 pre-cleanup) → **78** (post-cleanup). CRITICAL 2→**0**. All remaining HIGH = PROPAGATION DEBT (a defense done right in one place, omitted on its sibling) — fixes already exist in-repo as patterns. Not design debt.*
