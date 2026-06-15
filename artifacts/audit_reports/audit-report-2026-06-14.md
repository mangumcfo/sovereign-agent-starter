# Sovereign Stack Audit — 2026-06-14 (post-universalize confirming sweep)

This audit evaluates the sovereign agent stack across 7 dimensions — security, performance, code quality, test coverage, dependencies, architecture, and constitutional conformance — with every finding subjected to adversarial verification (false positives removed before sealing).

## Executive summary

Overall health: **82/100**. The stack is unusually well-hardened — principal binding closes the KM-1176 spoofing vector, state-changing routes are owner-gated, the obligation ledger is hash-chained behind an flock write-fence with append-aware tail-parsing and memoized derived views, and prior audit cycles have already eliminated most dead code and duplication. No CRITICAL findings and no confirmed auth-bypass; the score is held below the 90s by **0 critical / 4 HIGH** issues and a recurring theme: **integrity gaps live at the seams, not in the core engine** — the bell executor (atrium_executor.py) was never hardened to its sibling's standard (false success on failed close, approval-gate bypass), the reproducible dependency lock is wired into no install path, and there is no CI to catch regressions to the load-bearing ledger/auth primitives. Fix the four HIGH items and the stack is in excellent shape.

## Prioritized Findings

### HIGH

**1. Performance · core.py:180-204 (append/get_root)** — `VerifiableMemory.get_root()` rebuilds the ENTIRE Merkle tree from an unbounded in-RAM leaf list on every `append()`, and the write path is not memoized (append sets `_root_cache=None` then immediately calls `get_root()`). Every obligation approve/close drives an append via the wired attestor → `compliance_engine.attest_execution` → `node._self_attest` → `memory.append`, so one close = one full O(n) rebuild over process-lifetime memory; N appends = O(N²) and RAM grows without bound. The docstring's "O(1)-amortized" claim is true only for the NDJSON line, not the Merkle recompute.
- *Fix:* incremental Merkle accumulator (mountain range / streaming root) for O(log n) append; bound/evict resident `self.leaves` (NDJSON is authoritative). Minimal mitigation: don't call `get_root()` inside `append()` — let callers pull the root lazily, collapsing N appends-then-one-read to a single rebuild.
- *Effort:* incremental accumulator ~half a day; lazy-root mitigation <30 min.
- *Verifier:* VERIFIED REAL after refutation. Sealed `MerkleTree.__init__` re-hashes all N leaves then bottom-up rebuilds every construction; `self.leaves` is never evicted; hot engine path traced end-to-end (ledger.close → attestor → _self_attest → append). No mitigation found.

**2. Test Coverage / CI & reproducibility · repo root** — There is NO CI workflow (`.github/workflows` absent) and NO pytest path config anywhere (no conftest.py, no `[tool.pytest.ini_options]`, no pytest.ini/tox.ini/setup.cfg); the package is not installed. Empirically, bare `python -m pytest tests/test_ledger_concurrency.py` fails at collection with `ModuleNotFoundError: No module named 'sovereign_agent'` and passes only under `PYTHONPATH=src`. The 244-test green suite depends on an undocumented manual env var, so a regression to the ledger fence or a route auth gate would not be caught on commit.
- *Fix:* add `[tool.pytest.ini_options]` with `pythonpath = ["src", "scripts"]` to pyproject.toml so bare `pytest` works from repo root, add a minimal GitHub Actions workflow running the suite on push, and document the canonical invocation in README.
- *Effort:* 20-30 min.
- *Verifier:* VERIFIED REAL. No `.github/`, no pytest config, package not installed (both `sovereign-agent` and real name `sovereign-agent-starter`). Bare pytest reproduced the ModuleNotFoundError. A local `.git/hooks/pre-commit` exists but is untracked and runs only `crypto_vector_check.py`, not the suite — does not refute.

**3. Dependencies · Dockerfile:31-33** — `constraints.txt` self-titles as the "Reproducible constraints lock for the Docker/CI path," but no install path applies it. The Dockerfile does `COPY pyproject.toml README.md ./` + `COPY src ./src` + `pip install -e ".[portal]"` — it never COPYs constraints.txt and never passes `-c constraints.txt`. sovereign-install.sh:91 likewise installs with no constraint. requirements.txt (which does defer to the lock) is referenced by no install path. Net: the lock provides zero reproducibility guarantee for the two paths it claims to serve; both resolve freely against pyproject ranges.
- *Fix:* in Dockerfile add `COPY constraints.txt ./` and `pip install --no-cache-dir -e . -c constraints.txt`; add `-c constraints.txt` to sovereign-install.sh. Regenerate the lock's pins first (prior audits flag PyYAML==6.0.1 vs live 6.0.3, pytest==9.0.2 vs live 8.4.2).
- *Effort:* 15 min.
- *Verifier:* CONFIRMED. Constraints never COPYed (not even in build context), no `-c` anywhere; no CI/Makefile/tox wires it. One correction: pyproject already caps `pyyaml<7`/`flask<4`, so those majors can't install regardless — the real loss is minor/patch reproducibility and the air-gapped/SOX story, so the "PyYAML 7 / Flask 4" framing is overstated.

**4. Integrity / Error Voice · scripts/atrium_executor.py:76-101 (_close, _exec_distribution, _exec_status_confirm)** — The bell's scriptable executors call `_close(...)`, DISCARD its boolean return, then unconditionally print 'executed'/'confirmed+closed' and `return 0`. `_close` wraps `led.close()` in a bare `except Exception` that swallows EVERY failure (PermissionError on un-approved material packet, AlreadyClosedError, ValueError E0, forked/locked chain), prints a one-line note, returns False. Because handlers ignore that False, the executor reports the packet executed while the obligation stays OPEN on the chain — seal/cockpit state and ledger diverge, reported as success. Sibling atrium_apply.py was hardened (status='apply_close_failed'); the executor was not.
- *Fix:* honor the `_close` result: `if not _close(...): _handshake(... status='close_failed'); return non-zero` (or raise). Mirror atrium_apply.py's apply_close_failed discipline so a failed close can never read as 'executed'.
- *Effort:* ~20 min.
- *Verifier:* VERIFIED REAL. Bare except confirmed at 76-82; swallowed exceptions match ledger.close raise sites (KeyError, AlreadyClosedError, ValueError E0, 3x PermissionError); both handlers discard the bool and return 0; no upstream re-check. Sibling atrium_apply.py is hardened (returns 4, marks apply_close_failed) — contrast confirmed.

### MEDIUM

**5. Integrity · src/sovereign_agent/node_api/routes/placeholders.py:210-249** — The live `POST /breath_gate/<id>/approve` and `/deny` routes call `gate.simulate_approval()`/`simulate_denial()`, which human_approval_gate.py:86 explicitly documents as "TEST-ONLY stand-ins ... never used in the live wiring." They emit `{"timestamp": "simulated"}` instead of the real authenticated `record_disposition()` (used by node_integration.py:47), so the session-scoped breath-gate records a fabricated disposition, contradicting the `real_gates_every_mode` invariant. Routes are `@require_owner` (not an auth bypass); the ledger-backed `/obligations/<id>/approve` path is unaffected.
- *Fix:* switch the two routes to `gate.record_disposition(gate_id, status=..., approver=current_principal(), reason=...)`. Keep `simulate_*` for tests only.
- *Effort:* <30 min (two call sites).
- *Verifier:* VERIFIED REAL (could not refute). Self-contradiction confirmed verbatim; simulate_* emit "simulated" and lack `"real": True`; grep shows simulate_* invoked ONLY from these two live routes; no wrapping layer overrides the timestamp.

**6. Code quality / Constitution ceiling · src/sovereign_agent/obligations/ledger.py:1-790** — ledger.py is 790 lines, breaching the constitution's 500-line ceiling (CONSTITUTION §5) by 290 and growing (632→708→713→790). It bundles five separable concerns: flock helpers, EvidenceTier/classify_evidence, root resolution + boundary guards, chain primitives/caching, and the dr/cr lifecycle + replay.
- *Fix:* extract the side-effect-free groups (flock helpers + EvidenceTier → obligations/_chain_io.py; root resolution → obligations/roots.py), dropping ~180 lines and leaving ledger.py under the ceiling. Cross-check importers of `get_ledger_root`.
- *Effort:* 2-4 hours.
- *Verifier:* Ceiling breach VERIFIED HIGH-confidence (wc -l = 790; §5 is a genuine rule). CAVEAT, disclosed by the finding itself: three prior in-repo audits (06-12, 06-13b, 06-13c) REFUTED the "split it" remedy as not actionable, calling ledger.py a cohesive engine core. So the breach is real; the fix's actionability is the contested point.

**7. Code quality · src/sovereign_agent/node_api/routes/placeholders.py:35,95,129,186,224,242,283** — placeholders.py is the only one of the route modules still emitting error bodies via `build_error()` instead of `route_error()`. The other seven use `route_error()`, which adds the `error` slug field the Atrium banner + back-compat tests read; build_error omits it. So 404/400 bodies from placeholders carry `code` but no `error` slug, rendering the cockpit banner inconsistently.
- *Fix:* import `route_error`; convert the 6 route-handler error sites from `build_error(code=...)` to `route_error(error=...)` (mechanical keyword rename). Leave `kernel_exception` and server.py's framework 404/405 handlers untouched.
- *Effort:* 15-20 min.
- *Verifier:* VERIFIED REAL. Sibling tests assert `["error"]==slug`; placeholders' tests assert only `["code"]`. Minor caveat: roles.py also lacks the slug via dedicated helpers if full consistency is wanted; the proposed placeholders fix is correct.

**8. Code quality / config discipline · src/sovereign_agent/node_api/routes/series.py:396,404** — `book_docs()` makes paths vault-relative by splitting on the hardcoded literal `'/breathline-books-vault/'`. On a host where the vault is named differently or `BREATHLINE_BOOKS_VAULT` points elsewhere (config.py supports both), the split returns the full absolute path. This is the lone remaining hardcoded vault literal; siblings were already migrated to `config.get_books_kdp_root()`. `book_docs` already holds `kdp = config.get_books_kdp_root()` at line 369.
- *Fix:* replace both sites with `str(p.relative_to(kdp.parent))` guarded by try/except.
- *Effort:* 20-30 min.
- *Verifier:* Literal + portability gap VERIFIED HIGH-confidence (lone remaining occurrence; siblings migrated). REFUTATION of the stated harm: the finding claims /doc "cannot resolve" the absolute path so docs silently fail — this is FALSE; /doc explicitly accepts absolute paths (feedback.py:219-220) and its root-containment guard passes. So the MEDIUM severity is overstated — it's a real discipline/maintainability defect, not broken docs.

**9. Performance · src/sovereign_agent/node_api/routes/book_artifacts.py:58-93,224-269** — `GET /book_kdp` calls `_artifact_path()` five times per request; the cover_paperback/cover_hardcover variants have no registry key, so execution always falls through to `glob.glob(..., recursive=True)` walking the entire books vault (~13 recursive globs/request just for covers, ~20ms measured). Nothing on this path is memoized. `/book_pdf` and `/book_cover` share the same recursive-glob-on-miss pattern.
- *Fix:* memoize resolved paths on the vault dir's (mtime,size) via the existing `_filecache.memoize_on`, or short-circuit registry-absent kinds and drop the recursive vault-wide globs for bounded `{bid}/v*/final` globs.
- *Effort:* ~30-45 min.
- *Verifier:* VERIFIED REAL. Inspected the actual registry (24 entries, no cover_ebook/paperback/hardcover keys) → cover kinds always glob. `_filecache.memoize_on` exists with the exact (mtime_ns,size) semantics. Finding is slightly conservative (pdf/epem short-circuit on a healthy vault) but cover globs alone substantiate MEDIUM.

**10. Test Coverage · src/sovereign_agent/node_api/routes/book_artifacts.py:96-125** — The owner-gated, code-executing `/recompile` route (subprocess.Popen at line 122) has only one auth-rejection test row. Untested: unknown_book→400, no_build_script→500, and the success 202 spawn path. A regression in the `Book <N>` regex parse or `_BOOK_NUM_TO_ID` mapping would ship silently. Sibling `/apply` has a `no_spawn` fixture asserting ignition.
- *Fix:* mirror the /produce pattern — owner posts unknown book→400, known book with absent build script→500, success with a no_spawn Popen monkeypatch→202 + exactly one spawn.
- *Effort:* 20-30 min.
- *Verifier:* CONFIRMED. grep finds recompile/unknown_book/no_build_script only in one parametrize row + docstring; require_owner rejects before the body so no handler branch is exercised; the shared regex+mapping helpers also have no direct tests, so the risk is unmitigated.

**11. Test Coverage · src/sovereign_agent/node_api/routes/proposals.py:120-135** — The `/produce` success path is untested: it spawns the producer subprocess and writes two side-effect files to `~/.breathline/runs/` (a `.log` and a `.json` run-status manifest the cockpit reads). A break in the run-status JSON shape would surface only as a silent black-box cockpit.
- *Fix:* add a success test — monkeypatch Popen (fake `.pid`), redirect the runs dir to tmp_path, post a well-shaped obligation_id, assert 202 + status 'processing' + the `{oid}.json` manifest with session_id/started_at/pid/log keys.
- *Effort:* 20-30 min.
- *Verifier:* CONFIRMED. /produce tested only on failure/gate branches; `/processing` reads the same manifest keys so shape drift silently blinds the cockpit. Checked both plausible hidden-coverage candidates — neither covers the route side effects.

**12. Dependencies · pyproject.toml:52-54 (cryptography>=42,<47)** — The crypto-assurance extra permits the entire 42.x–46.0.6 sub-range, which carries known CVEs (CVE-2024-26130 fixed 42.0.4; CVE-2026-26007 fixed 46.0.5; CVE-2026-39892 fixed 46.0.7). Since the install paths don't apply constraints.txt (finding #3), an unconstrained resolve is governed only by this range.
- *Fix:* raise the floor to `cryptography>=46.0.7,<47`.
- *Effort:* 5 min.
- *Verifier:* VERIFIED REAL; CVE IDs web-confirmed. Worse than stated: constraints.txt pins `cryptography==46.0.4`, itself below both fix lines. CAVEAT: the only consumer (scripts/crypto_vector_check.py) uses SECP256K1 contiguous-bytes ECDSA — neither CVE is exploitable on this path — so a prior verifier graded it LOW; MEDIUM is arguably overstated, but the fix is correct and would force regenerating the vulnerable pin.

**13. Coupling · scripts/pipeline_snapshot.py:24** — `pipeline_snapshot.py` (an audit/snapshot script, no HTTP role) imports projection logic directly from the Flask route module `routes.series` (which imports flask at module top and instantiates a Blueprint at import time), so running it requires Flask and loads the entire HTTP blueprint. Same coupling already fixed for ndjson.py and yaml_repair.py but never finished for series-card shaping.
- *Fix:* extract the pure shaping functions (`_series_card`, `_title_card`, `_chapter_index`, `_roadmap_path`) into a Flask-free `src/sovereign_agent/series_projection.py`; have routes/series.py and the script import from there.
- *Effort:* 1-2 hours.
- *Verifier:* CONFIRMED via import-hook (blocking `flask` makes the script import raise ImportError). `_load` is already a re-export of the Flask-free yaml_repair loader (extraction started), but the shaping fns were never moved — matches the finding exactly.

**14. Missing abstraction seam · src/sovereign_agent/config.py (absence; callers e.g. routes/coherence.py:29-35, series.py:53-204, proposals.py:112-324)** — No `get_repo_root()`/`get_artifacts_dir()`/`get_memory_dir()` helper. `Path(__file__).resolve().parents[N]` is recomputed at 72 sites across 52 files with the depth index hardcoded per directory level (parents[4] routes, parents[3] obligations, parents[1] scripts); 'artifacts'/'memory' literals at 66 sites. Any file move silently resolves to a real-but-wrong directory instead of erroring.
- *Fix:* add repo-root/artifacts/memory helpers to config.py (anchor repo root once from package location), route callers through them. Repo-root helper alone removes the depth-index fragility.
- *Effort:* 2-4 hours full sweep; <30 min for helper + hottest callers.
- *Verifier:* VERIFIED REAL. Counts confirmed higher than the finding stated (72 parents[] sites / 66 literal sites). config.py already uses the candidate-sweep pattern, so it's the natural home. Latent maintainability defect, not an active bug.

**15. Diverging resolvers · src/sovereign_agent/node_api/_jsonstore.py:31-33** — `sidecar_store()` resolves proposals.json/relays.json from `OBLIGATION_LEDGER_ROOT`'s PARENT (fallback `~/.breathline`), while the ledger resolves via `get_ledger_root()` (fallback `<repo>/memory/obligations/atrium_review`). With the env unset (the default the API boots fine under), the ledger and sidecars land in two unrelated directories; they co-locate only when the env is set — yet sidecar_store's comment claims the node and subprocesses "can never disagree about where the store lives."
- *Fix:* have `sidecar_store()` derive its base from `get_ledger_root()` (the one resolver) so ledger and sidecars share one fallback and always co-locate.
- *Effort:* 30-45 min.
- *Verifier:* VERIFIED REAL, empirically reproduced (env unset → split dirs; env set → co-located). Nuance confirmed: subprocess inherits env so node/child never disagree with each other — this is SSOT drift vs the ledger, not data loss; MEDIUM appropriate. Fix must place sidecars in `get_ledger_root().parent` to preserve env-set behavior.

**16. Integrity · scripts/atrium_executor.py:129-146 (execute)** — `execute(oid)` checks only existence and `_is_closed`, never `_is_approved`. A direct `atrium_executor.py <oid>` on a non-material scriptable packet (distribution:/b12:/editorial_r1:) runs the handler and closes it with E2 evidence with no approval check — `ledger.close()` enforces the breath-gate only for `material=True`. The HTTP route enforces approve-first; the CLI executor relies on the caller, so the Execute-after-Approve gate is defense-in-depth-only at this boundary.
- *Fix:* in execute(), refuse unless approved (or an explicitly born-approved batch/mechanical lane): `if not led._is_approved(oid) and o.get('lane') != 'batch': record handshake + return`.
- *Effort:* ~25 min.
- *Verifier:* CONFIRMED. Trace verified: scriptable classes created non-material (feedback.py 54-57, hopper.py 249), close()'s gate fires only for material (ledger.py:511). Exploiting requires local shell (operator-equivalent trust), so integrity/defense-in-depth, not remote escalation — MEDIUM appropriate.

**17. Truth · src/sovereign_agent/obligations/ledger.py:67-79 (classify_evidence)** — `classify_evidence` grades any string with a 16-64 hex run, path-like substring, http(s)://, rcpt_/msg_ token as E1/E2 by pure SYNTAX — nothing verifies the pointer resolves. So evidence like `'see /tmp/nonexistent'` or a fabricated 40-hex sha CLOSES a material obligation, writing a non-resolving pointer onto the immutable chain. This contradicts the resolve-at-entry discipline `_assert_source_ref_resolves` enforces for `ref`/`source_ref`; `evidence` — the field authorizing the credit — gets no such check.
- *Fix:* apply resolve-at-entry to the evidence pointer (run `_assert_source_ref_resolves` or a lighter is_file check on path-like tokens; demote/raise on miss). At minimum document classify_evidence as syntactic-only and require require_e1 callers to pass a verified pointer.
- *Effort:* ~40 min.
- *Verifier:* CONFIRMED. The asymmetry is real and load-bearing — ref/source_ref resolve-checked, evidence never (grep confirms no evidence resolve call site). Real callers pass evidence unverified; some pass explicit tiers bypassing classify entirely — an even more direct form of the defect.

**18. Integrity / Error Voice · src/sovereign_agent/obligations/ledger.py:42-53,307-337** — On any platform without fcntl (Windows), `_flock_ex` degrades to a no-op with a ONE-TIME `warnings.warn`, then `_append` proceeds read-tail-compute-prev_hash-write with NO cross-process exclusion — the docstring calls this lock 'CRITICAL' because without it two appenders fork the chain permanently. The warning is suppressible/easily missed and the append still happens unfenced, so on a non-POSIX multi-writer host (threaded server + apply/executor subprocesses on the shared root) writers can silently fork the chain, which verify_chain() then reports False forever.
- *Fix:* on a fcntl-less platform, either refuse multi-process append (raise unless explicit single-process opt-in env) or fall back to an atomic O_CREAT|O_EXCL lockfile so the fence holds; if keeping the warning, emit via logging.warning on every append, not once.
- *Effort:* ~1-2 hrs.
- *Verifier:* CONFIRMED. No-op fence + unfenced critical section verified; _append is the sole write funnel for all 8 mutating sites; the only sibling lock (_jsonstore.locked) has the identical degradation. Exposure bounded to Windows / multi-writer, so MEDIUM (not HIGH) is appropriate.

### LOW

**19. Access control / confidentiality · src/sovereign_agent/node_api/routes/feedback.py:203-260 (/doc) + book_artifacts.py book endpoints + /review_brief** — The document/book-serving routes are gated only by `@require_principal`, not `@require_owner`. auth.py:47 accepts any holder of a valid `<principal_id>.token` (by design includes federation peers), so any non-owner authenticated principal can read full vault contents — unpublished manuscripts, board reviews, Review Briefs, KDP metadata — plus any .md/.txt/.yaml under artifacts/ and scripts/ via /doc. Path traversal itself is correctly defended; this is a coarse authorization gap vs the deliberately owner-gated write routes.
- *Fix:* decide the intended read audience; if peers shouldn't read pre-publication content, add `@require_owner`/read-scope to the serving routes; otherwise document the intent so the asymmetry is deliberate.
- *Effort:* ~30-60 min.
- *Verifier:* VERIFIED REAL. Auth asymmetry confirmed (read=require_principal, write=require_owner); require_owner's docstring explicitly names peers as rejected. Mitigation supporting LOW: default single-operator loopback-owner trust + typically no peer token files; real exposure needs a provisioned peer .token.

**20. CSRF · src/sovereign_agent/node_api/auth.py:131-207** — The loopback-owner token-less shortcut defends drive-by CSRF only via `_is_cross_site_browser_write()`, which blocks ONLY when `Sec-Fetch-Site` is present and cross-site/same-site. A request OMITTING the header is treated as a trusted CLI client and granted owner authority — fail-open for older/embedded browsers, WebView/extension contexts, or a header-stripping intermediary, reaching code-executing owner routes (/produce, /apply, /recompile).
- *Fix:* fail-closed for unsafe methods — require an affirmative same-origin signal (Sec-Fetch-Site==same-origin or a cockpit-set CSRF/custom header) before granting owner authority to a token-less unsafe-method request; have CLI/agents present the owner bearer token instead.
- *Effort:* ~1-2 hours.
- *Verifier:* VERIFIED REAL. Header-absent → site=="" → not blocked → granted loop_owner, which equals owner when BREATHLINE_NODE_OWNER unset; reaches require_owner routes. CORS does not mitigate (governs read-ability, not whether the POST fires). Modern browsers stamp the header on form/fetch POSTs, so common drive-by IS covered — LOW.

**21. Performance · src/sovereign_agent/evidence/actions_projection.py:27-37,58-71** — `GET /actions` rebuilds the full Merkle layer pyramid on every chain change and reads with the UNCACHED `read_ndjson`; its single-entry `_CACHE` does an unconditional `clear()`, so two different ledger roots thrash each other. Duplicates parse work the ledger's own incremental `_entries()` already does.
- *Fix:* read via `read_ndjson_cached`; drop the unconditional `_CACHE.clear()` (LRU/size cap) so multiple roots don't thrash. The layer rebuild is acceptable given the inclusion-proof contract.
- *Effort:* ~20-30 min.
- *Verifier:* VERIFIED REAL. read_ndjson_cached exists and is keyed by path (never cleared) — the fix would eliminate the thrash. query_actions takes a Path not a Ledger so it can't trivially reuse `_entries()`, but the parse is genuinely redundant. LOW appropriate (single-key thrash only bites with >1 root/process).

**22. Code quality / duplication · src/sovereign_agent/node_api/routes/feedback.py:343-359** — `feedback_disposition()` inlines the same obligation 404/409/403 error bodies obligations.py factored into module-private helpers (`_not_found`, `_already_closed`); because they're private, feedback.py can't import them, so they were copy-pasted and must be hand-synced.
- *Fix:* promote the obligation disposition error bodies to shared builders in errors.py and call them from both modules.
- *Effort:* 30-45 min.
- *Verifier:* VERIFIED REAL with a correction: the bodies are NOT identical — they've already diverged (404/409 wording differs; the permission handler differs in BOTH code and status: feedback `breath_gate_denied`/403 vs obligations `approval_required`/409). The already-drifted state strengthens the consolidation case. LOW.

**23. Code quality / duplication · src/sovereign_agent/node_api/routes/hopper.py:149-160,234-241** — The lane→ref derivation is implemented twice (`hopper_to_packet` and `_card_packeted`, whose docstring admits "Mirrors hopper_to_packet's ref derivation") and already structurally diverges (explicit `coordination` branch vs folded-into-else). They align only because card.id==ref for current feed cards; a future lane or src_ref change would silently break dedup and re-surface packeted cards.
- *Fix:* extract one `_lane_ref(lane, card_id, series_ref, src_ref)` helper used by both paths; reconcile the missing coordination case and the fallback-default divergence.
- *Effort:* 30-45 min.
- *Verifier:* VERIFIED REAL. Both divergences confirmed; no shared helper, no other callers. No active bug today (aligns for all real feed cards) — pure future-drift risk. LOW.

**24. Code quality / duplication · src/sovereign_agent/obligations/ledger.py:32-58** — The POSIX-advisory-flock guard is implemented twice with different semantics: ledger.py warns once (loud RuntimeWarning) when fcntl is absent, _jsonstore.py:35-101 degrades SILENTLY — inconsistent operator signal for the identical degraded condition, plus two import-guards to maintain.
- *Fix:* factor one shared flock utility (a `locked(path)` context manager + one-time-warn) used by both ledger and _jsonstore.
- *Effort:* 45-60 min.
- *Verifier:* CONFIRMED. _jsonstore says "mirroring the ledger's guard" verbatim; no shared util exists. Bonus: a THIRD copy in thread_channel.py:72-90 uses a hard `import fcntl` with no guard at all — consolidation would unify three sites. LOW (POSIX-only deployment makes it cosmetic in practice).

**25. Code quality / naming · src/sovereign_agent/node_api/routes/placeholders.py:1-38** — The module is named placeholders.py / blueprint `sections_bdef`, but its own docstring says these are "real thin handlers" wrapping live core; all routes are registered live in server.py:76 and not superseded by any module. NOT dead code, but the filename invites accidental deletion / under-maintenance.
- *Fix:* rename to reflect reality (e.g. routes/sections_bdef.py); update the import alias at server.py:36/76. Pure rename, no behavior change.
- *Effort:* 15 min.
- *Verifier:* VERIFIED REAL. grep shows zero duplicate registrations of these contract-B/D/E/F sections; genuine stubs are honestly `note`-labelled. Minor: the file actually defines ~17 handlers (not "12"); does not affect validity.

**26. Dependencies · pyproject.toml:2 (setuptools>=68.0)** — The build-system requires `setuptools>=68.0` with no upper bound, the one dependency exempt from the project's own bound-the-major policy (used explicitly for pyyaml<7/flask<4). A future setuptools major with breaking PEP 517/discovery changes could break `pip install .` reproducibility while runtime deps stay locked.
- *Fix:* add an upper bound consistent with policy, e.g. `setuptools>=68.0,<82`.
- *Effort:* 5 min.
- *Verifier:* CONFIRMED. Unbounded, not pinned in constraints (PEP 517 isolated builds ignore runtime constraints anyway). Minor finding error: the `pip install --upgrade ... setuptools` lives in sovereign-install.sh:82, not the Dockerfile — does not falsify.

**27. Abstraction leak · src/sovereign_agent/obligations/ledger.py:176-183** — Both ledger.py and node_integration.py document the ledger as having "no node dependency," but `_assert_source_ref_resolves()` does `from .. import config` and calls config.get_books_kdp_root()/get_playbooks_dir(). The lazy function-local import (noqa PLC0415) avoids an import cycle but signals the latent cycle; the "pure ledger" invariant is not actually held. On the live write path (open/close).
- *Fix:* inject the resolution roots into ObligationLedger (constructor arg/callable) so the ledger stays config-free and node_integration supplies vault roots at the seam; or soften the docstrings.
- *Effort:* 1 hour.
- *Verifier:* VERIFIED REAL. Lazy import + config calls confirmed on the live write path; constructor takes no root injection. Matches the existing thin-waist injection pattern (gate/attestor). node_integration.py:5's categorical "no node dependency" is the claim most directly falsified.

**28. Latent split-gate · src/sovereign_agent/obligations/node_integration.py:107** — `wire_node_ledger()` constructs a fresh `HumanApprovalGate()` rather than the deps singleton the /breath_gate endpoints use. Harmless in default 'sovereign' mode (synchronous request+record in one gate() call), but in `gate_mode='external'` the pending req_id registers only on the ledger's private instance, so the /breath_gate endpoints would never see it — an externally-gated obligation couldn't be dispositioned through the API surface.
- *Fix:* inject the deps singleton gate into wire_node_ledger so the pending request is visible to /breath_gate; or gate external mode behind a clear 'not yet wired' guard.
- *Effort:* 1-2 hours.
- *Verifier:* Largely REAL as a latent gap, framing partly mis-stated. Confirmed two distinct instances; external mode reachable. BUT the deeper blocker is that nothing writes a resolved breath-gate disposition back into the ledger chain (close() raises PermissionError in external mode by design, tested) — so the proposed fix is necessary-but-not-sufficient. External mode is intentionally inert/tested-as-blocked; default sovereign is harmless. LOW.

**29. Truth / Source · scripts/atrium_executor.py:40-51,76-82** — When `BREATHLINE_BELL_PRINCIPAL` is unset (--drain at session start, or a manual execute), `_principal()` returns literal `'system:bell'`, which becomes both ledger principal_id and `closed_by` on the credit + receipt. On the drain path, a credit closing a real human-owned obligation is attributed to 'system:bell' rather than the original approver whose identity is on the chain (approval entry's approved_by).
- *Fix:* on the drain/standalone path, derive `closed_by` from the obligation's recorded approver; keep 'system:bell' only for genuinely system-initiated closes.
- *Effort:* ~30 min.
- *Verifier:* CONFIRMED. Live accept path sets the env correctly (feedback.py:284); the drain/standalone path does not and is unmitigated. Honest explicit system actor (not the old hardcoded 'tiger'), no security break — attribution fidelity only. LOW.

**30. Truth · scripts/atrium_apply.py:283-293,319-330** — The re-test-or-revert safety net fires only for code groups (`has_code`). A prose/manuscript-only apply is committed, sealed, and closed with E2 evidence whose string says "tests green" even though no test ran (line 362's `; tests green.` is an unconditional literal). A small TRUTH gap between receipted evidence and what actually happened.
- *Fix:* only assert 'tests green' when has_code and pytest ran green; for prose-only say 'prose apply (no code tests)'. Optionally add a lightweight manuscript sanity check before sealing.
- *Effort:* ~30 min.
- *Verifier:* VERIFIED REAL. Re-test block skipped when has_code False; the evidence string's "tests green" is ungated (whereas the SEAL portion IS conditionalized — proving the author knows how). Prose-only apply is a reachable path. Evidence-accuracy gap, not data loss. LOW.

## Quick Wins (<30 min)

- **Wire the dependency lock** — Dockerfile:31-33 (+ sovereign-install.sh:91): add `COPY constraints.txt ./` and `-c constraints.txt`. (15 min) [#3]
- **Add pytest path config** — pyproject.toml: `[tool.pytest.ini_options] pythonpath = ["src","scripts"]` so bare `pytest` works; add a minimal CI workflow. (20-30 min) [#2]
- **Fix false-success on failed close** — scripts/atrium_executor.py:76-101: honor `_close`'s bool, handshake status='close_failed' + non-zero exit. (~20 min) [#4]
- **Real breath-gate disposition** — placeholders.py:210-249: swap `simulate_*` → `record_disposition`. (<30 min) [#5]
- **route_error in placeholders** — placeholders.py:35,95,129,186,224,242,283: import route_error, rename `code=`→`error=` at 6 sites. (15-20 min) [#7]
- **Drop hardcoded vault literal** — series.py:396,404: use `p.relative_to(kdp.parent)`. (20-30 min) [#8]
- **Raise cryptography floor** — pyproject.toml:53: `cryptography>=46.0.7,<47`. (5 min) [#12]
- **Bound setuptools** — pyproject.toml:2: `setuptools>=68.0,<82`. (5 min) [#26]
- **Test /recompile branches** — book_artifacts.py:96-125: unknown_book/no_build_script/success. (20-30 min) [#10]
- **Test /produce success path** — proposals.py:120-135: spawn + manifest-shape assertions. (20-30 min) [#11]
- **Cache /actions reader** — actions_projection.py:58-71: read_ndjson_cached + drop unconditional `_CACHE.clear()`. (20-30 min) [#21]
- **Smoke-test dialogue/crypto_assurance** — routes/dialogue.py:117-160: 200 + envelope keys incl. empty-state. (15-20 min) [read-only route gap]
- **Rename placeholders.py** — + server.py:36/76 alias. (15 min) [#25]
- **Enforce executor approval gate** — atrium_executor.py:129-146: `_is_approved` check. (~25 min) [#16]
- **Honest prose-apply evidence** — atrium_apply.py:362: stop asserting 'tests green' for prose-only. (~30 min) [#30]

## Refuted (for the record)

- **constraints.txt — "known CVE in pinned cryptography==46.0.4"** — pin and code line exist, but the live consumer (crypto_vector_check.py, SECP256K1 contiguous-bytes ECDSA) is not exploitable by either CVE; false positive as written (folded into the version-floor finding #12 instead).
- **constraints.txt — "stale/inaccurate provenance claim in lock"** — claim that the pins can't have come from the live green env was itself unsupported; refuted as a false positive.
- **pyproject.toml — "loose range permits Flask CVE"** — Flask is correctly pinned to the fixed 3.1.3 and the range is `>=3.0,<4`; the asserted security impact does not hold; false positive on impact.

## Dimension Summaries

- **Security:** Unusually well-hardened — principal binding (KM-1176 closed), owner-gated writes, flock+hash-chain ledger, allowlist CORS, no injection/eval/unsafe-yaml, traversal-defended file serving; only lower-tier residuals (simulated breath-gate disposition, peer-readable pre-pub content, header-absent CSRF fail-open). No CRITICAL/HIGH security issues.
- **Performance:** ndjson engine perf hygiene is excellent (tail-parse, memoized views, singleton caches); the one real hot-path defect is VerifiableMemory rebuilding the whole Merkle tree from an unbounded leaf list on every append — the engine's true scaling ceiling.
- **Code quality:** Actively maintained, most dead code/duplication already removed; real issues are the 790-line ledger.py ceiling breach, placeholders.py's lone build_error drift, the hardcoded vault literal, and hand-synced duplication (disposition errors, lane→ref, flock guard).
- **Test coverage:** Broad and disciplined on CRITICAL paths (hash-chain fork/repair, concurrent appends, gates); the gaps are no CI / no pytest path config (biggest risk), untested /recompile + /produce success paths, route-level concurrency, and the read-only dialogue route.
- **Dependencies:** Disciplined hygiene (minimal, guarded, bounded majors); the failures are the reproducible lock wired into no install path, version floors permitting CVE-bearing cryptography, and an unbounded setuptools — all sub-30-min fixes.
- **Architecture:** Strong ledger core (one root resolver, singleton, fenced sidecars, no load-time cycles); debt is at the seams — Flask coupling in a standalone script, no repo-root abstraction (~72 recomputed paths), and diverging sidecar-vs-ledger root resolvers.
- **Constitutional:** Disciplined four-fold conformance (principal flow, enforceable Propose→Decide→Execute, resolve-at-entry, loud unmapped sentinels); gaps cluster in the un-hardened bell executor (false success, approval bypass) plus syntactic-only evidence grading and the degradable write-fence.

---
*Run wf_9fda7b13-d86 · by_severity {"MEDIUM": 14, "LOW": 15, "HIGH": 4} (confirmed 33, refuted 3). suite 244.*
*TRAJECTORY: 58→62→78→82→82→**82**. Plateau HELD post-universalize. KEY: 3 of 4 HIGH are PARTIAL-COMPLETIONS of the wave's own fixes (Merkle-recompute not made incremental · constraints regenerated-not-wired · executor false-close not hardened like apply), +1 genuinely new (no CI/pytest-path). NOT an endless sibling tail — a bounded set of finish-the-job items. #1 (VerifiableMemory O(n²)) is ALSO the #1 scaling wall.*
