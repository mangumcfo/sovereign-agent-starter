# Sovereign Stack Audit — 2026-06-19

*Seven dimensions audited — security, performance, code quality, test coverage, dependencies, architecture, constitutional conformance — with every finding adversarially verified (false positives removed before this report).*

## Executive Summary

Overall health: **78/100**. The engine core is genuinely hardened — the obligation ledger (hash-chained, flock-fenced, fail-closed on material self-approval, append-aware O(delta) tail-parse with disciplined mtime/size memoization), the Propose→Decide→Execute gate, and principal-binding to `current_principal()` on every write path are all verified-correct, and the classic vectors (injection, unsafe deserialization, path traversal, secrets-in-code) are closed. That said, **zero CRITICAL** and **four HIGH** findings cluster around one dominant theme: *the single-writer hash-chain fence is only half-installed and the test suite that should catch it is currently red.* The Tiger↔GB coordination THREAD has a real cross-process chain-fork race (the documented-primary CLI writer `scripts/thread.py` takes no lock while the node side fences), and three tests are failing on this branch — two on the R1 ship gate that decides whether a book reaches KM's review queue — so CI is broken and the highest-leverage gates are effectively untested right now. The remaining findings are mostly sub-30-minute quick wins.

## Prioritized Findings

### HIGH

**Architecture / Constitutional — INTEGRITY · `scripts/thread.py:58-68` (vs `node_api/thread_channel.py:72-90`)**
The hash-chained Tiger↔GB THREAD (`memory/coordination/THREAD_Tiger_GB.ndjson`) has two cross-process writers with identical chain math, but only one fences. The node relay route flocks `<file>.lock` around its read-prev→hash→append section; the CLI `scripts/thread.py:append()` takes no lock at all (zero `flock`/`fcntl` in the file). The cron night-watch prompt and module docstring name the CLI as the *primary* append path, so a CLI append racing a node `/relay/<id>/relay` append can both read the same `prev` and permanently fork the GENESIS-anchored chain (TOCTOU); `verify()` then reports BROKEN. The node's flock is unilateral — the counterparty never participates.
*Fix:* give `scripts/thread.py:append()` the same `<file>.lock` flock around load→prev→hash→write, or (cleaner) delegate to `thread_channel.append()` to eliminate the divergent unlocked copy. *Effort:* 20-30 min. *Verifier:* CONFIRMED — both paths resolve to the identical file (proven programmatically), chain math identical, no mitigation anywhere; corroborated as still-open in `audit-report-2026-06-13b.md:60`.

**Test coverage — stale ship-gate tests · `tests/test_review_ready_contract.py:53,138`**
Two tests in the R1 review-ready suite are FAILING (confirmed: pytest red). The fixture writes the old `📦` Receipt-box marker, but the production detector `_check_gate6_renderability` was changed *today* (commit `cbe4f23`) to count the letters-only `**RECEIPT —` header (`scripts/review_ready_contract.py:95`). Result: `test_all_gates_green_is_review_ready` sees gate6 RED → `review_ready=False` → FAIL, and `test_gate6_renderability_red_paths` gets `no-receipt-boxes` where it asserts `partial` → FAIL. The gate deciding whether a book reaches KM's queue (and its Gate-6 branch) is effectively untested while these are red — a false-green could ship an un-reviewed book.
*Fix:* update the fixture (line 53) and red-path manuscript (line 138) to emit the `**RECEIPT —` header the detector now matches; keep the partial-path box count below the section count to land on `partial(1/2)`. *Effort:* ~15 min. *Verifier:* CONFIRMED — both failures reproduced directly; no skip/xfail markers, tests are hard red.

**Dependencies — used-but-undeclared Pillow · `scripts/dist_generators/gen_linkedin_carousel.py:19`**
`from PIL import Image, ImageDraw, ImageFont` at module top with no try/except. Pillow is declared nowhere (pyproject, requirements, constraints, Dockerfile, install script all grep-clean). `generate_all.py:8` imports the carousel module unconditionally, so a clean install hard-fails with `ModuleNotFoundError: No module named 'PIL'` (reproduced for both the carousel module and `generate_all`). CI installs only `.[dev,crypto-assurance]` and the generators have no tests, so CI misses it. This is the exact defect class the project already fixed for flask (audit 2026-06-13c #4).
*Fix:* add a `distribution` optional-dependencies extra declaring `pillow>=10,<13`, pin in `constraints.txt`, require `.[distribution]` in the generator docs; optionally wrap the import with a loud actionable error. *Effort:* <30 min. *Verifier:* CONFIRMED — clean-install hard-fail reproduced; ambient Pillow 12.2.0 is the only reason it works today. (Severity bounded: generators are dev tooling, not packaged console scripts, so `pip install .` of the core is unaffected.)

**Constitutional — INTEGRITY (hash-chain fork race) · `scripts/thread.py:58-68`**
Same defect as the architecture HIGH above, viewed through the constitutional lens: the receipted coordination THREAD's documented-primary writer is unlocked while only the node side fences, and the node comment *falsely claims* cross-process coverage. The nightly delta-audit cron explicitly instructs agents to append via `scripts/thread.py append`, firing the unlocked writer automatically exactly when a Relay click could race it.
*Fix:* identical to the architecture finding — same `<file>.lock` flock, or delegate to the package's `thread_channel.append`. *Effort:* 20 min. *Verifier:* CONFIRMED — same-file resolution, identical chain math, and cron invocation path all verified; route store lock guards only the relay JSON, not the THREAD ndjson.

### MEDIUM

**Security — auth bypass / deployment misconfig · `node_api/server.py:182-198 (cli_serve) vs 49 (create_app)`**
The dev-mode guard that refuses to start with bearer-check disabled off-loopback lives only in `cli_serve()`. The importable `create_app()` WSGI entrypoint — which its own docstring invites ("Importable for tests + WSGI hosts") — performs no such check. A direct-WSGI host (gunicorn/uwsgi) with `BREATHLINE_NODE_API_DEV=1` bound off-loopback bypasses the guard; dev mode then accepts a no-Authorization request as `dev:anonymous` and any `dev:<label>` token verbatim, letting an unauthenticated caller self-assign the audit actor. The shipped Dockerfile uses the console script (`cli_serve`), so the documented path is safe.
*Fix:* move the dev-mode + non-loopback refusal into `create_app()`, gated by an explicit `BREATHLINE_NODE_API_DEV_ALLOW_NONLOOPBACK` opt-in or a bind-host check via `BREATHLINE_NODE_API_HOST` at factory time. *Effort:* <30 min. *Verifier:* CONFIRMED — guard absent from `create_app` and module scope; no wsgi wrapper or gunicorn config re-adds it.

**Security — principal spoofing / audit-actor integrity · `node_api/auth.py:168-171`**
In dev mode any `dev:<label>` token is accepted verbatim and bound to `g.principal_id`, then stamped as the audit actor (owner/decided_by/closed_by/produced_by) across the hash-chained ledger. A dev caller can mint chain entries attributed to any label, including a real operator id. `require_owner` blocks dev principals from owner-only routes, but the non-owner ledger-writing routes (`/obligations` open, `/feedback`, `/hopper/packet`, `/relay`) accept the spoofed principal. Dev-only (loopback-constrained via the cli_serve guard, modulo the WSGI gap above).
*Fix:* reject a dev label that collides with a configured real owner id, and/or tag every dev-mode entry `dev_mode=True` so downstream audit never trusts the actor. *Effort:* <30 min. *Verifier:* CONFIRMED — no `dev_mode`/`auth_dev_mode` flag propagates into persisted entries; stored actor retains the `dev:` prefix but is still attacker-controlled.

**Performance — unmemoized per-title FS walk on hottest route · `node_api/routes/series.py:245-261`**
`_latest_manuscript_version` is called per-title inside `_title_card` on the cockpit's most-polled route (`/series`), yet — uniquely among the disk/index functions in this file — it carries no `@memoize_on`. Each call sweeps `get_books_kdp_root()` (4-candidate `.exists()`) then globs ~7 roots × version dirs; with ~96 book_id occurrences in the roadmap, one GET drives ~600+ glob syscalls plus ~90 redundant root sweeps. Added 2026-06-19 (`b0e4099`), it bypasses the very memoization discipline the adjacent roadmap parse documents as "the dominant /series cost."
*Fix:* build one `{book_id: (ver, path)}` map per request (single tree pass) and pass it to `_title_card` for O(1) lookup; or `memoize_on` keyed by dir mtime/size and hoist `get_books_kdp_root()` out of the loop. *Effort:* 20-30 min. *Verifier:* CONFIRMED — function un-memoized, called only at line 272, no mitigation; syscall figure is a hedged estimate (true root count is host-vault-dependent).

**Code quality — correctness / duplicate dict key · `scripts/outline_lock_lint.py:198,202`**
The `--json` dict literal sets `"undercounted"` twice — line 198 to the count (`len(under)`), line 202 to the list of rows. Python keeps the last, silently dropping the count; a consumer expecting an int (matching sibling `phantom_locks`/`thin_locks` counts) gets a list. ruff F601.
*Fix:* rename the list key (e.g. `"undercounted_rows"`) so both the count and detail survive, mirroring the phantom/thin pairs. *Effort:* 5 min. *Verifier:* CONFIRMED three ways (AST, runtime, real `--json` run); latent today (no automated consumer parses it as a count) but a genuine silent data-loss in the JSON contract.

**Code quality / Architecture — locking primitive ×3, already drifted · `node_api/thread_channel.py:72-90` (also `obligations/_locking.py:8-34`, `node_api/_jsonstore.py:35-101`)**
The POSIX-advisory write-fence is implemented three times. Two guard `import fcntl` with try/except and degrade to a no-op (runs-anywhere posture). `thread_channel.py:72` does a bare `import fcntl`, so `append()` — the receipted relay THREAD writer reached via owner-gated `POST /relay/<id>/relay` — hard-fails on any non-POSIX host while its siblings degrade. Violates the quality bar's "no duplication tail" rule whose named exemplar is a write-fence context manager.
*Fix:* extract one shared fcntl-guarded fence both `_jsonstore.locked()` and `thread_channel.append()` call; at minimum guard the bare import to match siblings. *Effort:* 45 min (10 min for just the guard). *Verifier:* CONFIRMED — exactly three `import fcntl` sites, only thread_channel unguarded; tracked OPEN in `GB_Engine_Gap_to_100_LIVING.md` (#6).

**Architecture / Missing platform guard · `node_api/thread_channel.py:72`**
The same bare `import fcntl` viewed as a portability defect: `thread_channel.append()` is the lone un-guarded fence in an otherwise platform-guarded codebase. On non-POSIX the A1 Relay/append path raises `ImportError` at first-call instead of degrading like `_locking.py`/`_jsonstore.py`.
*Fix:* mirror `obligations/_locking.py` — guard the import, degrade to a no-op with a one-time `RuntimeWarning` (single-process safe), or reuse `_flock_ex/_flock_un`. *Effort:* 15 min. *Verifier:* CONFIRMED — reachable via `routes/relay.py:157`; not caught or guarded anywhere. (Same root cause as the duplication finding above.)

**Test coverage — stale guard test (raw ndjson parse) · `tests/test_universalize_guards.py:45`**
`test_no_raw_perline_ndjson_parse_outside_gateway` is FAILING: `scripts/distribution_contract.py:253` now does a raw per-line `json.loads(line)` loop, bypassing the tolerant ndjson gateway. The red guard means the invariant it protects is no longer enforced, and that path also silently `except Exception: continue`s malformed lines instead of degrading through the gateway that distinguishes a truncated tail from a corrupt middle.
*Fix:* route lines 250-257 through the shared `read_ndjson` reader, or allowlist with a comment. *Effort:* ~20 min. *Verifier:* CONFIRMED — failure reproduced; the file imports no `read_ndjson`, and `distribution_contract.py` is not on the ledger fast-path allowlist.

**Test coverage — untested GB-routing branch · `node_api/routes/feedback.py:335-341`**
`_owner_agent()`'s `tiger` default is tested, but the `gb` branch (ref starts `relay`, or blob contains `gb_`/`re-read`/`board re-stamp`) has zero coverage. A regression in that string-match would silently misroute GB-owned reject-with-note feedback to Tiger — exactly the capture-reliability bug the fix closes — with no failing test.
*Fix:* mint a card whose ref/title triggers `gb` (e.g. `ref='relay:...'`), reject with a note, assert `routed_to=='gb'`. *Effort:* ~15 min. *Verifier:* CONFIRMED — repo-wide grep finds no GB-branch assertion; only the tiger-default test exercises `routed_to`.

**Test coverage — real unmocked subprocess + leak · `tests/test_node_api_feedback.py:92`**
The feedback `accept` disposition fires `_ring_the_bell` → a real detached `subprocess.Popen(atrium_executor.py)`. The proposals tests mock Popen via a `no_spawn` fixture; the feedback tests do not (no `conftest.py` shares it). So `test_awaiting_km_lists_then_drops_on_accept` leaks a real background process (`start_new_session=True`) that races `tmp_path` teardown, and the bell-ignition path is asserted nowhere — it could silently stop igniting and tests stay green.
*Fix:* clone the proposals `no_spawn` recording fixture; assert exactly one spawn carrying the obligation id and that no real subprocess runs. *Effort:* ~25 min. *Verifier:* CONFIRMED — single real Popen observed; the named test is the leak site (the two other examples in the finding's prose do not actually spawn).

**Test coverage — missing regression guard (prefix match) · `node_api/routes/feedback.py:160-163`**
`_awaiting()` uses `startswith(HUMAN_GATE)` — a documented fix for an exact-`==` regression that "silently hid" suffixed gates like `Human disposition (Atrium Review)` from KM's "waiting on me" view. Real hopper cards (`hopper.py:255`) carry exactly that suffix, but no test mints a suffixed gate and asserts it appears in `/awaiting_km`; the one existing test uses the non-suffixed value and would pass even under the regression.
*Fix:* add a test opening an obligation with `next_gate='Human disposition (Atrium Review)'`, GET `/awaiting_km`, assert it's listed. *Effort:* ~15 min. *Verifier:* CONFIRMED — no test in tests/ covers the suffix case.

**Dependencies — unpinned tooling in CI · `.github/workflows/ci.yml:72`**
The CVE-scan step runs `pip install pip-audit` unpinned and outside `constraints.txt`, even though pip-audit is already declared (`pip-audit>=2.7`) in the `analysis` extra — inconsistent with the repo's reproducibility discipline. Bounded by `continue-on-error: true`.
*Fix:* `pip install -c constraints.txt -e '.[analysis]'` then `pip-audit --desc`; optionally add a pip-audit pin to constraints. *Effort:* <15 min. *Verifier:* CONFIRMED — line 72 unpinned, pip-audit absent from constraints, step is advisory-only.

**Architecture / Constitutional — series_roadmap parse seam · `scripts/roadmap_sealed_guard.py:57-58`**
A shared resilient loader (`yaml_repair.load_roadmap`) auto-repairs GB's known-degraded YAML, and three derivers use it. But `roadmap_sealed_guard.py:58`, `outline_lock_lint.py:168`, and `scout_run.py:58` still raw `yaml.safe_load` the same degradation-prone file — most painfully the seal/CI guard, which crashes (unhandled `YAMLError`, nonzero exit) where the `/series` lens beside it degrades gracefully.
*Fix:* route all three through `yaml_repair.load_roadmap(text)` and surface `degraded` honestly. *Effort:* 20-30 min. *Verifier:* CONFIRMED in code; LATENT — current committed roadmap parses clean, so the crash is conditional on the degradation recurring (documented as a recurring real event in `extrusion_validate.py` audit note 2026-06-13c #16).

**Constitutional — INTEGRITY / transactional safety · `scripts/atrium_apply.py:297-318`**
The apply agent advertises "if red → REVERT all" / "Reversible (git)", but the multi-repo commit loop is not transactional. If repo #1 commits and repo #2's commit fails, `_revert` only does `git checkout -- <file>` (a no-op against the now-committed HEAD) — there is no `git reset` of the landed commit. Result: repo #1 keeps a committed change while the proposal is marked `apply_failed` and the obligation never closes — a partial, non-reversible state contradicting the docstring.
*Fix:* capture each repo's `head_before` and on any commit failure `git reset --hard` every advanced HEAD; or stage+commit all repos only after all groups + re-test pass. *Effort:* 45 min. *Verifier:* CONFIRMED — no `git reset` anywhere; the spawning route fire-and-forgets, so nothing resets committed repos. (The finding's secondary claim about the `changed and not commits` branch is overstated — that path is harmless.)

**Constitutional — TRUTH / snapshot diverges from live lens · `scripts/pipeline_snapshot.py:24,31`**
The drop-off guard claims it "reuses the lens merge … so the snapshot never drifts from the live view," but it calls `_series_card(s, idx)` with a stale 2-arg signature, silently dropping `publishing_index`, `channel_index`, `stage_labels`, `review_index`. The snapshot body omits each title's stage/publishing/channel/review overlays — exactly what live `/series` renders — so a regression in those fields is invisible to a snapshot diff. (Numeric drop counts still work.)
*Fix:* import and thread all four overlays as `series_list()` does: `_series_card(s, idx, _publishing_index(), _channel_index(), _stage_labels(), _review_index())`. *Effort:* 20 min. *Verifier:* CONFIRMED — empirically, the latest snapshot has zero stage/publishing/channel/review fields. (Path label "routes/series.py" is the real `node_api.routes.series` import.)

### LOW

**Security — non-owner ledger writes · `routes/obligations.py:72-101` (also feedback.py:97, hopper.py:209, relay.py:54)**
The create routes that mint hash-chained entries are `@require_principal`-only, not `@require_owner`, so any authenticated principal (incl. a federation peer) can open obligations/feedback/relay cards on the operator's chain. All dispose/execute routes are correctly owner-gated, so impact is bounded to draft/ledger-noise, not escalation. *Fix:* decide whether federated intake is intended; add `@require_owner`/a known-principal allowlist, or a per-principal quota + cockpit segregation. *Effort:* design decision first; decorator change <30 min. *Verifier:* CONFIRMED — also `POST /proposals` is the same class (finding under-counts by one).

**Performance — uncached root sweep · `config.py:142-162`**
`get_books_kdp_root()` re-runs an env lookup + up-to-4 `.exists()`/`.resolve()` sweep on every call, compounding the per-title hot loop above (~90 extra sweeps per `/series`). The resolved root is process-static. *Fix:* `lru_cache` or an env-keyed module cache (mirroring `book_artifacts.py:32`). *Effort:* 10-15 min. *Verifier:* CONFIRMED — uncached; secondary to the series.py finding.

**Code quality — dead function parameter · `compliance/compliance_engine.py:222`**
`_generate_six_style_receipt(self, record, original_payload)` never reads `original_payload`; line 238 stubs `payload_hash: None`. *Fix:* drop the param and update the line-190 call site, or wire `payload_hash` from it. *Effort:* 10 min. *Verifier:* CONFIRMED (vulture 100%); zero body references.

**Code quality — file over 500-line ceiling · `scripts/review_ready_contract.py:1-665`**
665 lines, over the §5 ceiling — but a cohesive CLI script (~15 `_check_*` gates + `evaluate()`/`main()`), not an engine primary (ledger.py is exactly 499). *Fix:* extract `_check_*` into a sibling `review_ready_checks.py`, mirroring the ledger.py→projection.py exemplar. *Effort:* 1-2 hr. *Verifier:* CONFIRMED — 665 even discounting blanks/comments; no CLI exemption exists.

**Code quality — complexity >10 tail · `node_api/yaml_repair.py:64` (+7 others)**
8 engine functions exceed the C901 ceiling (yaml_repair 16, series._title_card 15, json_provider 16, etc.). The quality bar tracks rather than grandfathers these, and `static_scan.sh` is report-only / not in CI, so this is tracked-debt by design, not a broken gate. *Fix:* extract `_apply_*_overlay` helpers from `_title_card`; leave the yaml line-state machine with a tracking note. *Effort:* 2-3 hr. *Verifier:* CONFIRMED — counts reproduced under project ruff config; CI runs only pytest + pip-audit.

**Code quality — duplicated id-minting idiom · `routes/proposals.py:70` (and relay.py:75)**
Both mint ids via `"<prefix>_" + str(int(time.time()*1000))` with no collision guard under the threaded server; a same-ms double-create collides on a primary lookup key. *Fix:* shared `_mint_id(prefix)` in `_jsonstore.py` with a short random suffix. *Effort:* 15 min. *Verifier:* CONFIRMED — and the finding's "dedup-by-content" mitigation rationale is inaccurate (no such dedup exists), so impact is marginally higher than stated.

**Code quality — misleading module name · `routes/placeholders.py:1` (and server.py:65)**
The file is named `placeholders.py` and `server.py:65` comments "B/D/E/F placeholders," but the routes are live, wired handlers (some do real ledger-backed dispositions). *Fix:* rename to `routes/contract_sections.py` (the blueprint is already `sections_bdef`); update the import and comment. *Effort:* 10 min. *Verifier:* CONFIRMED — `README.md:25` already documents the truth, lowering impact, but the in-code name still misleads.

**Dependencies — unused-import idiom · `scripts/gen_outline_digest.py:16`**
`import yaml` is F401-flagged but sits in a try/except fail-fast availability check — intentional, not dead. *Fix:* add `# noqa: F401` with rationale, or switch to `importlib.util.find_spec`. *Effort:* 5 min. *Verifier:* CONFIRMED — the only F401 in the scanned tree; documented-noqa discipline exists elsewhere.

**Dependencies — undeclared system fonts · `scripts/dist_generators/gen_linkedin_carousel.py:29-30`**
Hardcoded absolute Liberation TTF paths loaded via `ImageFont.truetype` with no `load_default()` fallback; `fonts-liberation` is in neither the Dockerfile nor the installer. On the project's own `python:3.12-slim` image `_font()` raises `OSError` and the generator crashes. *Fix:* add `fonts-liberation` to the Dockerfile apt line AND wrap the load in a `load_default()` fallback. *Effort:* <30 min. *Verifier:* CONFIRMED — no fallback; fonts present on this host but absent on slim.

**Test coverage — route-level error-translation gap · `routes/obligations.py:137`**
Joint-attestation/veto refusal (`close()` → `PermissionError`) is tested at the ledger unit level but not through the HTTP close route's error translation. *Fix:* set `requires_attestation` via deps, drive close over HTTP, assert a contextual 4xx with the canonical shape. *Effort:* ~25 min. *Verifier:* CONFIRMED route-level gap, but partly mitigated — a broad `except PermissionError` already returns 409 (no 500 leak); residual is an error-voice mismatch, and the attestation path is not reachable by pure HTTP today (no open-route forwarding, no /attest route).

**Test coverage — /coherence degraded-path gap · `routes/coherence.py:90,105`**
The read-only `/coherence` routes lack a malformed-registry degradation test; a wrong-shape registry yields a 500 (reproduced) where sibling lenses degrade to 200. *Fix:* add `test_node_api_coherence.py` asserting missing/malformed registry → 200. *Effort:* ~30 min. *Verifier:* CONFIRMED gap, but the "zero HTTP tests" headline is FALSE — `test_extrusion_anchors.py` HTTP-tests both routes (happy-path only); fix needs `monkeypatch` of `_registry_path` (no env override).

**Architecture — O(n) chain replay on every change · `obligations/ledger.py:434-499`**
`replay()`/`full_log()` re-walk the whole chain from genesis on every append (stat-key invalidation), unlike the incremental `_entries()`. Under sustained write+poll load, per-poll cost grows with chain length. Bounded (node-local, in-memory). *Fix:* make replay/full_log incremental via `_entries()`'s grow-detection. *Effort:* 2-4 hr. *Verifier:* CONFIRMED, with one correction — `verify_chain()` IS already incremental (its frontier advances in-lock on append), so only replay/full_log re-walk under write load.

**Architecture — shared-mutable singleton under threaded server · `node_api/deps.py:55-77`**
The process-wide ledger singleton's in-process caches are read/written from concurrent request threads with no lock; under CPython's GIL each wholesale tuple reassignment is atomic, so the worst case is a stale read or redundant recompute, never a torn read. *Fix:* document the GIL assumption, or add a `threading.Lock` if free-threaded/parallel execution is ever targeted. *Effort:* 30 min if pursued. *Verifier:* CONFIRMED — threaded serving verified (Flask `run` sets `threaded=True`); no in-process lock; safe under current CPython.

**Constitutional — INTEGRITY / unlocked cylinder append · `scripts/gb_meta_cylinder.py:51-57`**
`_append()` does read-last→prev_hash→hash→`open('a')`+write with no fence; `generate_receipt()` appends the same unlocked way. Effectively single-writer (GB's own meta-log), so a fork is unlikely — but an overlapping cron + manual `log` run could fork the chain. *Fix:* flock a sidecar `<cylinder>.lock` (mirror `_locking`/`thread_channel`). *Effort:* 15 min. *Verifier:* CONFIRMED — no lock; governance designates GB sole-writer, bounding risk to LOW.

## Quick Wins (<30 min)

- `scripts/outline_lock_lint.py:202` — rename the duplicate `"undercounted"` key (5 min).
- `scripts/gen_outline_digest.py:16` — `# noqa: F401` or `find_spec` (5 min).
- `compliance/compliance_engine.py:222` — drop the dead `original_payload` param (10 min).
- `node_api/server.py:65` + `routes/placeholders.py` — rename module / fix stale comment (10 min).
- `node_api/thread_channel.py:72` — guard the bare `import fcntl` (10 min).
- `scripts/thread.py:58-68` — add the `<file>.lock` flock or delegate to `thread_channel.append` (HIGH, ~20 min).
- `tests/test_review_ready_contract.py:53,138` — update fixtures to `**RECEIPT —` (HIGH, ~15 min).
- `routes/feedback.py:335-341` — add the GB-branch routing test (~15 min).
- `routes/feedback.py:160-163` — add the suffixed-gate `/awaiting_km` regression test (~15 min).
- `.github/workflows/ci.yml:72` — pin pip-audit via `-c constraints.txt -e '.[analysis]'` (<15 min).
- `config.py:142-162` — memoize `get_books_kdp_root()` (10-15 min).
- `scripts/gb_meta_cylinder.py:51-57` — flock the append fence (15 min).
- `node_api/server.py:49` — lift the dev-mode/non-loopback guard into `create_app()` (<30 min).
- `node_api/auth.py:168-171` — reject colliding dev labels / tag `dev_mode=True` (<30 min).
- `scripts/pipeline_snapshot.py:24,31` — thread the four missing overlays (20 min).

## Refuted (for the record)

*No findings were refuted — the supplied data contained no entries in the refuted set (false positives had already been removed adversarially before this report; e.g. demo_roles dead-code, `placeholders.py` "dead routes," the `six` import as PyPI six, and `/coherence` "zero HTTP tests" were all ruled out during verification).*

## Dimension Summaries

- **Security:** Unusually well-hardened — injection, unsafe deserialization, path traversal, and secrets-in-code are all closed; the three residuals are dev/deployment-surface gaps (unguarded `create_app` WSGI entry, verbatim `dev:` actor spoofing, non-owner create routes), no CRITICAL or HIGH.
- **Performance:** The ledger's mtime/size-keyed append-aware caching is exemplary; the one real regression is a 2026-06-19 feature that runs an uncached per-title filesystem walk (~600+ glob syscalls) on the cockpit's most-polled `/series` route.
- **Code quality:** Primary engine is exceptionally clean (extraction-not-abstraction, ledger.py at 499, unified error shapes); real issues are a duplicate-key correctness bug and a thrice-implemented, already-drifted locking primitive, the rest being a tracked complexity/ceiling tail in secondary scripts.
- **Test coverage:** Breadth is genuinely strong but the suite is currently RED (3 failing, incl. two on the R1 ship gate), and the highest-risk live-concurrency and capture-routing paths (real unmocked subprocess, GB-routing branch, suffixed-gate guard) are thin or missing.
- **Dependencies:** Primary-scope hygiene is excellent and pins are CVE-clean; all real findings are in `scripts/dist_generators` — used-but-undeclared Pillow (the strongest), undeclared Liberation fonts, and an unpinned pip-audit in CI.
- **Architecture:** The obligation ledger's single-fenced-writer model is the stack's strongest part; the weak point is the Tiger↔GB THREAD where the fence is only half-installed (unlocked CLI twin → chain-fork race) plus storage-format coupling on `series_roadmap.yaml`.
- **Constitutional conformance:** SOURCE/INTEGRITY/TRUTH/ERROR-VOICE are largely enforced in code (principal-binding, Propose→Decide→Execute, fail-closed material gate, loud error voice); residuals are concurrency/transactional — the THREAD fork race (HIGH), non-atomic multi-repo commit, and a drifted snapshot guard.

---
## Run footer — confirmed-count comparison

**This run (full, 2026-06-19):** health 78/100 · confirmed 32 (refuted 0) · CRITICAL 0 / HIGH 3 / MEDIUM 14 / LOW 15
**Previous full report (`audit-report-2026-06-16-FINAL.md`):** health 79/100 · 0 CRITICAL / 4 HIGH (the constraints–CI supply-chain cluster; MED/LOW not tabulated that run)

**Delta:**
- CRITICAL: 0 → 0 (held clean)
- HIGH: 4 → 3. The 06-16 cluster was a single recurring theme (constraints pins fabricated-green + `[portal]` empty-extra + CI un-green-able). This run's 3 HIGH are a *different* theme: (1) `scripts/thread.py` hash-chain fork race — single-writer fence only half-installed (counted twice in the prose under architecture + constitutional lenses → 1 in by_severity), (2) stale R1 ship-gate tests RED on this branch (commit `cbe4f23` today), (3) Pillow used-but-undeclared in the carousel generator. **The 06-16 constraints–CI HIGH cluster no longer surfaces as HIGH** — treat as resolved/de-escalated pending one-line confirmation.
- Health: 79 → 78 (−1). Honest: rigor surfaced a fresh fork-race + a red CI suite on this branch; offset by the constraints cluster clearing.
- Verifier discipline: 0 refuted as false-positive this run (every finding adversarially verified before report).

*Full re-run, fresh date — no stale cache. Run `wf_d734acc3-193` · 40 agents · 0 spend-starvation.*
