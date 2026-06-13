# Sovereign Stack Audit — 2026-06-13 (full sweep)

This audit assesses the sovereign agent stack across **7 dimensions** — security, performance, code quality, test coverage, dependencies, architecture, and constitutional conformance — with every finding subjected to **adversarial verification** (false positives were challenged and removed before this report; only reproduced, code-confirmed findings remain).

## Executive Summary

**Overall health: 62/100.** The engine's load-bearing core is genuinely strong — the hash-chained obligation ledger writes under an exclusive `flock`, HTTP writes bind to the authenticated principal (no body-spoofing), `yaml.safe_load` and arg-list subprocess calls are used throughout, and path-serving routes are traversal-guarded. The score is held down by **2 CRITICAL** and **9 HIGH** findings that cluster on one theme, plus a hard packaging defect. **Critical count: 2.** The single most important theme: **the governed loop is hardened at the HTTP boundary but leaks at every seam that steps outside it.** The Propose→Decide→Execute gate is bypassable (`/apply` never checks a decision exists), the bell executor writes the chain directly with a hardcoded `'tiger'` principal against a divergent ledger root, the loopback-trust + permissive-CORS posture forms a drive-by CSRF-to-code-execution chain, and the storage root resolves three incompatible ways across the codebase. Fix the seams (one shared ledger-root resolver, a decision guard on apply, principal propagation into the executor, CORS/CSRF hardening) and this stack moves from "strong core, leaky edges" to genuinely sound.

## Prioritized Findings

### CRITICAL

**Propose/Approve/Execute gate bypassable** · `src/sovereign_agent/node_api/routes/proposals.py:397-421` (+ `scripts/atrium_apply.py:194-198`)
The `/apply` route executes code (lands diffs, commits, seals) but never checks `prop['status'] == 'decided'`. In `atrium_apply.py` the group filter collapses two ways: (1) if `group_ids` are passed, every named group applies regardless of any decision; (2) if none are passed, undecided groups default to `'accept'` via `decisions.get(g['id'], 'accept')`. So a proposal never run through `/decide` can be landed, committed, and sealed — the constitution's Propose→Decide(Accept)→Execute reduces to Propose→Execute. `require_owner` gates *who* fires it, not *whether* a decision exists.
*Fix:* Reject in `proposals_apply()` if status is not `decided`/`partially decided`; require ≥1 explicitly-accepted group. In `atrium_apply.py`, drop the `'accept'` fallback (undecided → reject) and intersect any passed `group_ids` with explicitly-accepted ids. *Effort:* ~30-45 min. *Verifier:* CONFIRMED; proposal object is never even loaded in the route, so status is never verified. Distinct from the 2026-06-10 authorization hardening, which added *who* not *whether*.

**Undeclared hard runtime dependency `breathline_primitives`** · `pyproject.toml:28-30`
`breathline_primitives` is an unconditional top-level import in the core (`universal_sovereign_node.py:26-27`, `core.py`, `playbook_loader.py`, `compliance/policy_loader.py`) and loads at package import via `__init__.py`, yet it is declared nowhere — `pyproject` lists only `pyyaml>=6.0` and `requirements.txt` is empty comments. A clean `pip install` cannot `import sovereign_agent`; it only works because `activate-breathline.sh`/`bootstrap.py` inject a sibling sealed checkout onto `sys.path`, and that bootstrap failure is silently swallowed in `__init__.py:18-23`.
*Fix:* Declare `breathline_primitives` in `pyproject` dependencies (pinned VCS URL if not on PyPI), OR make the core imports lazy/guarded like `inference/primitives.py`'s `_bp()` helper. At minimum, stop swallowing the bootstrap failure so users get an actionable message. *Effort:* 1-3h (declare + install path) or 30-60m (lazy imports). *Verifier:* CONFIRMED; `python3 -c 'import breathline_primitives'` fails on this machine; package is not installable from a package index as-is.

### HIGH

**CSRF / auth bypass: loopback-trust + permissive CORS → local code execution** · `src/sovereign_agent/node_api/server.py:79-87` (+ `auth.py:140-145,166-193`)
`after_request` unconditionally sets `Access-Control-Allow-Origin: '*'` while `auth.py` grants token-less owner-level access on loopback (which *also* satisfies `require_owner` via the `_node_owner()` fallback). Under the documented loopback-owner posture (`Dockerfile:42`), any web page the operator visits can issue a simple cross-origin POST to `http://127.0.0.1:8421/api/v1/proposals/<id>/apply` (no Authorization header, `text/plain` body → `{}`), spawning `atrium_apply.py` to write files and git-commit. A drive-by CSRF-to-local-code-execution chain; the browser is the confused deputy the loopback-trust design ignores.
*Fix:* Drop `ACAO '*'` for an explicit node-local allowlist; require an unguessable CSRF token (or a custom header simple requests can't set) before the loopback shortcut on state-changing routes; ideally require the owner bearer token even on loopback for code-executing routes. *Effort:* 2-4h. *Verifier:* CONFIRMED; the clean drive-by primitive is `POST /proposals/<id>/apply` (no existence check before `Popen`). No CSRF token / Origin / SameSite / Sec-Fetch check exists anywhere in `src/`.

**Missing authorization on the human-disposition gate** · `src/sovereign_agent/node_api/routes/proposals.py:449-466`
`POST /proposals/<id>/decide` records the operator's accept/reject decisions but is decorated only with `@require_principal`, not `@require_owner`. Its siblings (`apply`, `produce`, `recompile`, and `feedback_disposition`) are all owner-gated. `atrium_apply.py` then applies the groups whose decision == `'accept'` (absent → accept). So any authenticated federation peer or dev/loopback caller can set the accept decisions that the owner-gated apply executes — the accept disposition *is* the human gate and must carry the same authority.
*Fix:* Add `@require_owner` below `@require_principal` on `proposals_decide`, mirroring `proposals_apply`/`feedback_disposition`. *Effort:* <15 min. *Verifier:* CONFIRMED; `require_principal` admits dev/loopback/federation peers that `require_owner` rejects, so `/decide` is reachable by callers who couldn't pass `/apply`'s gate.

**Hardcoded principal writes the governed chain (bell executor)** · `scripts/atrium_executor.py:40,69`
The HTTP layer binds every ledger write to `current_principal()`, but the bell path bypasses HTTP: `feedback_disposition` accept → `_ring_the_bell` → `atrium_executor.py`, which constructs `ObligationLedger(principal_id='tiger')` and closes with `closed_by='tiger'`. The credit entry, its receipt principal, and the actions projection therefore attribute the close to a constant string, not the operator who clicked Accept — re-opening the exact SOURCE hole the HTTP audit closed. (`atrium_apply.py`'s `'tiger'` is inert — the HTTP layer overrides it; the executor's direct file write is not.)
*Fix:* Propagate `current_principal()` from `_ring_the_bell` into the executor (argv/env) and use it for `ObligationLedger(principal_id=...)` and `close(closed_by=...)`. If a true system actor is intended, name it explicitly (e.g. `system:bell`). *Effort:* ~30 min. *Verifier:* CONFIRMED; real chain writes occur for scriptable classes (distribution/b12/editorial_r1). Auth doctrine (`auth.py:9-10,93`) explicitly forbids hardcoded principals (CONSTITUTION §1).

**Split-brain ledger root between API and bell executor** · `scripts/atrium_executor.py:33-34` vs `deps.py:66` / `ledger.py:81-84`
When `OBLIGATION_LEDGER_ROOT` is unset the two writers resolve different roots: the API default is `<repo>/memory/obligations` while the executor defaults to `<repo>/memory/obligations/atrium_review`. On disk all 995 entries live in `atrium_review` and the API default path does not exist — so an env-unset API serves an empty queue while the executor writes the real chain (and `execute()` silently returns 1 on a missing id). Approve lands in one chain, close in another.
*Fix:* One shared resolver whose default equals `ledger._default_root()` exactly; route `atrium_executor` and the API through it. *Effort:* ~20 min. *Verifier:* CONFIRMED, but **latent**: `scripts/run_node_api.sh:10` exports `OBLIGATION_LEDGER_ROOT=…/atrium_review` so the documented launch path agrees; the defect manifests only when the API is booted bypassing the launcher (IDE/tests) or in the container.

**Storage-root coupling / no single source of truth** · `deps.py:85` vs `proposals.py:497-498,515-516` vs `review_ready_contract.py:34`
The ledger root resolves three incompatible ways: the live API defaults to `memory/obligations`; `/export/packet`, `/actions`, and `atrium_executor` default to `atrium_review`; and five seal/crypto/review scripts hardcode `atrium_review` and ignore the env var entirely (`ledger_manifest.py:24` adds a *fourth* default, `tiger_coordination`). The Dockerfile sets `/data/obligations`, honored by half the code and ignored by the rest. `_assert_root_not_starved` exists to catch the silent-empty-queue but only `log.error()`s.
*Fix:* One `get_ledger_root()` helper resolving env-or-single-canonical-default, routed through every site; pick one default (`atrium_review` has the data); escalate the starvation guard from log-only to a boot refusal. *Effort:* 30-60 min. *Verifier:* CONFIRMED with two corrections — `ledger_manifest.py` defaults to `tiger_coordination` not `atrium_review` (worse, a 4th default); `run_node_api.sh:10` is a real mitigation on the launcher path.

**Test coverage: review-ready rail gate untested** · `scripts/review_ready_contract.py:246-323`
`review_ready_contract.py` is the R1 gate deciding whether a book reaches KM's review queue, and `mint_review_packet()` opens a real material C1 human-gate obligation on the live ledger — with ZERO tests (named only in a comment). Every gate (`_check_boards`, `_check_obligations`, `_check_fidelity`, `_check_review_brief`), `evaluate()`, and mint idempotency are unverified; a bug flips review-ready true/false silently — a false-green ships an un-reviewed book.
*Fix:* `tests/test_review_ready_contract.py` driving `evaluate()` against a tmp book dir + tmp ledger root, asserting each gate flips and `mint_review_packet` opens exactly one packet and is idempotent. *Effort:* 2-3h. *Verifier:* CONFIRMED; the node consumer only reads the pre-written overlay, so no transitive coverage. Implementer note: module-level constants resolved at import need monkeypatching.

**Test coverage: rigor gate untested** · `scripts/board_rigor.py:70-106`
`board_rigor.py` enforces the "no rubber stamps" gate wired directly into `review_ready_contract._check_boards` (a rigor-fail means a board does not count as executed). `rigor_check()`/`rigor_check_md()` and all four rule checks (R-LGP, R-OBL, R-DEPTH, R-HUMAN) plus the empty-board R-STRUCT minimum have ZERO tests. A too-lax regex/threshold is exactly the failure the gate exists to prevent, with nothing to catch it.
*Fix:* `tests/test_board_rigor.py`: one passing findings dict + one violating each rule, plus `rigor_check_md` cases for valid block / missing block / invalid JSON. *Effort:* 1-2h. *Verifier:* CONFIRMED; also note the try/except import degrades silently to status "present", strengthening the case.

**Test coverage: accept→execution wire untested** · `src/sovereign_agent/node_api/routes/feedback.py:230-249,298`
The accept path calls `_ring_the_bell()` → spawns `atrium_executor.py` (the ledger-mutating ignition). The one test that hits accept never asserts the spawn — `"executor":"spawned"` is returned unconditionally and the best-effort exception swallow (line 248) makes a real spawn failure invisible. The heart of the loop-closure is unverified.
*Fix:* A test monkeypatching `subprocess.Popen`/`_ring_the_bell` to a recording stub asserting invocation with `obligation_id` + `PYTHONPATH`; a second asserting a spawn exception is logged but disposition still returns 200 ("bell must never break the gate"). *Effort:* 45 min. *Verifier:* CONFIRMED; violates the file's own `every_gate_earns_a_test` doctrine.

**Pointers written at `open()` are never validated; resolve roots hardcoded** · `src/sovereign_agent/obligations/ledger.py:102-128,258-302`
The "a pointer is never written false" rule is enforced only for `close(source_ref=...)`. The obligation's own `ref`, hopper `intent`/`Target:`/`Page:` strings, and feedback `ref` are sealed into the hash chain at `open()` with no resolve-at-entry validation. Separately, `_assert_source_ref_resolves` hardcodes operator-specific vault roots (`/home/kmangum/…/breathline-books-vault`), so on any other host a genuinely-resolvable passage fails resolution — contradicting the `config.get_books_kdp_root()` runs-anywhere posture used by the routes.
*Fix:* (1) Validate path-like refs at `open()` the same resolve-or-symbolic-or-raise way `close()` does. (2) Replace hardcoded vault literals with `config.get_books_kdp_root()`/`get_playbooks_dir()` plus cwd/repo-root. *Effort:* ~30-45 min. *Verifier:* CONFIRMED; both real callers (`hopper.py:245`, `feedback.py:99`) seal unvalidated pointers; `_assert_source_ref_resolves` has exactly one call site (close).

### MEDIUM

**Fully anonymous principal in dev mode** · `src/sovereign_agent/node_api/auth.py:125-135` (+ `server.py:141-143,151-152`)
With `BREATHLINE_NODE_API_DEV` truthy (`--dev`), a no-Authorization request is accepted as `dev:anonymous` and any `dev:<label>` token is accepted verbatim. `require_owner` blocks code-executing routes, but all read+write principal routes accept unauthenticated callers who self-assign any principal label — which becomes the audit actor (owner, `decided_by`, `closed_by`). `obligations.close` even reads `evidence_tier`/`require_e1` from the body. *Fix:* Never enable dev implicitly; hard-abort startup if dev mode AND host != loopback; document dev principals are never audit-trustworthy. *Effort:* 1-2h. *Verifier:* CONFIRMED; no host/dev guard exists today.

**Plaintext bearer secret read from file; no TLS** · `src/sovereign_agent/node_api/auth.py:47-80` (+ `server.py:14-21,158`)
The stored credential is the raw shared secret, not a hash (the `compare_digest` use is correct); the `0600` expectation is a comment, never enforced. The server binds plain HTTP with TLS deferred, so federation-peer tokens (the remote case the loopback exemption does *not* cover) travel in cleartext and are replayable when bound to `0.0.0.0`. *Fix:* Store/verify a hash; actively verify cred file mode 0600; gate non-loopback binds behind a TLS requirement or refuse to start. *Effort:* 2-4h. *Verifier:* CONFIRMED across `auth.py`, `server.py`, `mint_node_token.sh`, `Dockerfile`.

**Material breath-gate is a no-op when ledger gate is None** · `src/sovereign_agent/obligations/ledger.py:381-386`
`close()`'s material-execution guard is conditioned on `self.gate is not None`. The API wires a real gate, but `atrium_executor.py` builds a raw `ObligationLedger` with no gate, so a material obligation can be closed with the human-primacy gate fully skipped. *Fix:* Make the guard fail-closed — a `None` gate should mean "cannot self-approve," not "no gate to satisfy" (or route the executor through `wire_node_ledger`). *Effort:* ~30 min. *Verifier:* CONFIRMED as a missing defense-in-depth layer; currently backstopped because the API approves on the gated ledger *before* spawning the executor, so realized paths are safe — but a direct CLI invocation on an un-approved material packet would skip the gate.

**Missing caching on hot lens route** · `src/sovereign_agent/node_api/routes/series.py:383-392`
`GET /series` (a polled cockpit lens) re-reads and re-parses SIX files every request with zero caching, including a glob-and-parse of every file in `review_ready/` and an expensive `_repair_unquoted_colons` fallback on degraded YAML. *Fix:* Memoize each loader on its file's `(mtime_ns, size)` — the pattern `obligations/ledger.py:_entries()` already uses. *Effort:* <1h. *Verifier:* CONFIRMED; no memoization anywhere in `routes/`.

**Redundant in-process recomputation (replay amplification)** · `src/sovereign_agent/obligations/ledger.py:534-552`
`GET /obligations` triggers four `replay()` runs (`by_owner()` calls it twice plus a redundant `_entries()` closed-ids scan) — ~24 linear chain passes per request. The parse is cached and `verify_chain` is memoized, but `replay()` is not. *Fix:* Call `replay()` once and derive open/status/by_owner from it; optionally memoize on `_stat_key` like `verify_chain`. *Effort:* <1h. *Verifier:* CONFIRMED; output identical, pure scaling concern. (Same scaling theme also tracked under ARCHITECTURE.)

**Files exceeding 500-line ceiling** · `src/sovereign_agent/node_api/routes/series.py:594`
`series.py` is 594 lines; ~123 of them (182-304) are a self-contained YAML quote-repair sub-system unrelated to HTTP routing. *Fix:* Extract `_load`/`_repair_unquoted_colons`/scanners into `node_api/yaml_repair.py`; that alone drops `series.py` to ~472 lines and makes the salvage logic reusable/testable. *Effort:* 1h. *Verifier:* CONFIRMED (`wc -l` = 594); ceiling is the audit's house standard, not a lint rule — consistent with MEDIUM.

**Duplicate Charter-V.7 ack guard with case-sensitivity divergence** · `src/sovereign_agent/compliance/compliance_engine.py:253-261,315-323`
The same Charter-V.7-ack guard appears twice; the first lowercases `action_class`+`materiality`, the second does not — a latent inconsistency. *Fix:* Hoist `_charter_v7_ack_required(action_class, context)` and call it once at the top. *Effort:* 30-45 min. *Verifier:* CONFIRMED; Guard 1's trigger set is a strict superset, so Guard 2 is effectively unreachable dead code — strengthens the finding.

**Broken caller after refactor (gate demo)** · `examples/fec_gate_demo.py:22,54`
Calls `wire_node_ledger(..., simulate_gate=True, simulate_deny=True, ...)`; those params were removed in the `real_gates_every_mode` audit, so the documented breath-gate demo raises `TypeError` on first call and misrepresents the current gate contract. *Fix:* Use `gate_mode='sovereign'` and demonstrate DENY via a real disposition, or remove the example. *Effort:* 20 min. *Verifier:* CONFIRMED; ran the example — crashes at line 22, exit 1.

**Robust-parse logic not shared (lens vs derivers)** · `scripts/build_book_code_tree.py:60-61`, `extrusion_validate.py:142-145`, `gen_outline_digest.py:40`
The lens (`series.py:_load`) hardens degraded-roadmap parsing; three derivers consuming the same `series_roadmap.yaml` call raw `yaml.safe_load` with no fallback — two crash outright, and `extrusion_validate.distribution()` swallows the error and returns `[]` (a silent empty table that can still report GATE: PASS). *Fix:* Extract the lens `_load` into a shared `roadmap_read.py`; at minimum stop `distribution()` swallowing the parse error. *Effort:* 45-60 min. *Verifier:* CONFIRMED; the live roadmap carries the exact `gb_notes:`/`references:` tail blocks the fallback targets.

**Missing read-gateway / private-internals coupling** · `routes/hopper.py:149`, `atrium_executor.py:143`, `ledger_manifest.py:42`, `coherence_reconciliation_queue.py:130`
Four sites reach into the private `ObligationLedger._entries()` and three more hand-parse `obligations.ndjson`, each encoding the entry schema independently — the chain format is coupled to ~7 modules rather than fenced behind the class (a past `'open'→'debit'` rename had to be hand-chased). *Fix:* Public accessors (`debit_refs()`, `iter_entries()`) + a shared `read_chain(root)` classmethod so the NDJSON format has one parser. *Effort:* 1-2h. *Verifier:* CONFIRMED; hand readers also parse outside the flock/parse-cache (read-only, low blast radius).

**Scaling: O(n) re-replay per request** · `src/sovereign_agent/obligations/ledger.py:509-552` (+ `routes/obligations.py:39-47`)
`replay()` is not memoized, so `GET /obligations` re-materializes full chain state ~4× per request — cheap at 995 entries, linear at the 10x target. *Fix:* Memoize `replay()` on `_stat_key` (invalidate on append); single-pass `by_owner()`; longer-term a materialized-state snapshot. *Effort:* 1-2h. *Verifier:* CONFIRMED (architectural framing of the replay-amplification finding above).

**Test coverage: proposals apply/dismiss bodies** · `src/sovereign_agent/node_api/routes/proposals.py:397-446`
`/apply` is covered only for the 403 gate; `/dismiss` (clears a proposal AND closes its linked obligation, with a deliberate resurface-on-failure branch) is fully untested. *Fix:* Owner-client tests for dismiss-closes-obligation, dismiss-on-close-failure returns `dismissed_proposal_only`+warning with the obligation still open, and apply spawns `atrium_apply.py` with the proposal_id. *Effort:* 1h. *Verifier:* CONFIRMED; the only "dismiss" test targets a different relay route.

**Test coverage: cross-process ledger race** · `tests/test_ledger_concurrency.py:43-65`
The flock fix is justified by a cross-PROCESS race but tested only with threads in one process; `fcntl.flock` semantics differ across separate OS processes. *Fix:* A `multiprocessing`/subprocess test launching 2+ processes appending to a shared root, asserting entry count == sum, unique `prev_hash`, `verify_chain()` True. *Effort:* 1-1.5h. *Verifier:* CONFIRMED as a coverage gap; the implementation itself looks sound (fresh fd + `LOCK_EX` per append).

**`fcntl` import breaks Windows** · `pyproject.toml:10,22-24` (+ `obligations/ledger.py:16`)
`ledger.py` does an unconditional top-level `import fcntl` (POSIX-only) and is imported at package load, while `pyproject` declares `requires-python>=3.10` with no OS restriction — the ledger fails to import on a claimed-supported platform. *Fix:* Add a POSIX-only OS classifier / document Windows-unsupported, OR guard the import with a no-op fallback (as `thread_channel.py` partially does). *Effort:* 30-60m. *Verifier:* CONFIRMED.

**Unbounded dependency ranges, no lockfile** · `pyproject.toml:28-41`
All deps are lower-bound-only with no upper bounds and no lockfile; a future Flask 4.x / PyYAML 7.x could silently install and break the JSON provider / yaml lenses — a reproducibility/supply-chain weakness for an attestation-oriented package. *Fix:* Add upper bounds (`flask>=3.0,<4`, `pyyaml>=6.0,<7`) and ship a pinned constraints file for the Docker/CI path. *Effort:* 30-60m. *Verifier:* CONFIRMED; the `[portal]` Docker install has no `-c` constraints.

### LOW

**Decorator ordering: authorization without prior authentication** · `proposals.py:484-485` — `export_packet_route` has `@require_owner` but is missing `@require_principal`; fails closed (403) so no bypass, but the route is unreachable even by the owner and is a latent footgun. *Fix:* add `@require_principal` above. *Effort:* <10 min. *Verifier:* CONFIRMED.

**Hardcoded operator paths/identities + credential-less internal calls** · `scripts/atrium_apply.py:25-36,242-255` — hardcoded `SEAL` path, repo roots, committer identity, and a credential-less `http://127.0.0.1:8421` call that only works via the loopback bypass. *Fix:* drive NODE URL, roots, identity, SEAL from config/env; authenticate with the owner token. *Effort:* 1-2h. *Verifier:* CONFIRMED; no shell-string injection (arg-list subprocess).

**Per-request `sys.path` growth** · `proposals.py:490-518` — `/export/packet` and `/actions` insert `repo/scripts` into `sys.path` every request with no dedup; slow unbounded list growth. *Fix:* guard with `if p not in sys.path`, or hoist to module load. *Effort:* <15 min. *Verifier:* CONFIRMED.

**Duplicate Book-num→book_id dict** · `proposals.py:207-208,236-237` — same mapping duplicated in `recompile()` and `_resolve_book_id()`; adding Book 13 means two edits. *Fix:* module-level `_BOOK_NUM_TO_ID` constant. *Effort:* 10 min. *Verifier:* CONFIRMED (caveat: don't naively delegate `recompile()` to `_resolve_book_id()` — the fallbacks differ).

**Duplicate JSON-store trio** · `relay.py:39-61` — `_store_path/_read/_write` cloned across `relay.py`, `proposals.py`, `feedback.py`, with an `ensure_ascii` divergence (`relay` uses `ensure_ascii=False`, `proposals` doesn't). *Fix:* extract `node_api/jsonstore.py`, standardize `ensure_ascii`. *Effort:* 45-60 min. *Verifier:* CONFIRMED; `relay.py:14` docstring self-admits the clone.

**Undefined type annotations** · `bootstrap.py:114,191` — `Dict[str, Any]` used but only `Optional` imported; saved from crashing only by `from __future__ import annotations`, but `get_type_hints()` raises `NameError`. *Fix:* `from typing import Any, Dict, Optional`. *Effort:* 5 min. *Verifier:* CONFIRMED.

**High complexity: `atrium_apply.main()`** · `scripts/atrium_apply.py:182-290` — ~110 lines, CC ~43, ten serial try/except stages; highest-complexity function in scope. *Fix:* decompose into named stages (`_apply_all_groups`, `_retest_or_revert`, `_commit_per_repo`, `_seal`, `_close_obligation`, `_recompile_books`, `_mark_applied`). *Effort:* 2-3h. *Verifier:* CONFIRMED.

**High complexity: `ledger.close()`** · `ledger.py:348-437` — ~90 lines, CC ~23, four gates + receipt minting + attestor wiring in one method; correct but reorder-fragile. *Fix:* extract ordered private guards + `_mint_receipt()`. *Effort:* 1-2h. *Verifier:* CONFIRMED.

**High complexity: `_title_card()`** · `series.py:307-353` — CC ~21, five overlays threaded as five positional Optionals through three call layers. *Fix:* per-overlay helpers and/or an indexes bundle. *Effort:* 1-2h. *Verifier:* CONFIRMED (pure readability refactor).

**High complexity / lane→ref drift: `hopper_to_packet()`** · `hopper.py:209-255` — CC ~22; the lane→ref convention is duplicated in `_card_packeted()` with already-present divergences (tooling `or "hopper"` fallback) that can silently break dedup. *Fix:* extract a shared `_packet_title_ref(...)` used by both writer and predictor. *Effort:* 45-60 min. *Verifier:* CONFIRMED; drift is untested.

**`utcnow()` deprecation** · `core.py:92,151,159,226` — four `datetime.utcnow()` sites, scheduled for removal; `ledger.py` already uses `datetime.now(timezone.utc)`. *Fix:* swap the four sites; add `filterwarnings=error` for `DeprecationWarning`. *Effort:* 20 min. *Verifier:* CONFIRMED, but the audit's "174 warnings, all utcnow" is wrong — actual run: 82 warnings total, only 4 from utcnow (the rest are unclosed-file `ResourceWarning`s).

**Unguarded top-level `import yaml`** · `routes/placeholders.py:1-3` — breaks the module's own yaml-optional/lazy-import discipline (`series.py`, `hopper.py` import yaml lazily). Inert today (pyyaml is core), latent if pyyaml moves to an extra. *Fix:* lazy import inside `specs_validate`. *Effort:* <30m. *Verifier:* CONFIRMED.

**Test coverage: export/actions route layer** · `proposals.py:484-519` — engines tested, route layer (owner gate, 400/404, comma-split, led_root resolution) untested. *Fix:* thin route tests with owner_client/dev fixtures + tmp ledger. *Effort:* 45 min. *Verifier:* CONFIRMED.

**Test coverage: coherence route content** · `coherence.py:1-145` — only a shape smoke test; summary counts and by_book rollup unverified. *Fix:* seed a known extrusion fixture and assert counts/rollup. *Effort:* 1h. *Verifier:* CONFIRMED (caveat: the proposed `/feedback`-emission test targets client behavior, not this route — drop that half).

**Undeclared `cryptography` import (guarded)** · `scripts/crypto_vector_check.py` — uses undeclared third-party `cryptography`; guarded, so the interop assurance check silently skips. *Fix:* declare it as an extra and surface a warning when absent. *Effort:* 30m. *Verifier:* CONFIRMED as under-declaration (severity downgraded from the original framing).

**Error voice: dispatch-gate drops unknown channel states** · `series.py:138-147,91-92` — `_dispatch_gate_summary` counts only `state=='staged'`; `_publishing_index` `continue`s past unmapped KDP statuses — both vanish silently instead of screaming, unlike the already-fixed stage map. *Fix:* surface an `other`/`unmapped` bucket and a loud `⚠ UNMAPPED STATUS` sentinel. *Effort:* ~25 min. *Verifier:* CONFIRMED; read-only projection, so visibility/honesty impact only.

## Quick Wins (<30 min)

- **Add `@require_owner` to `/decide`** — `proposals.py:449-466` (closes a HIGH auth gap, <15 min)
- **Add `@require_principal` to `export_packet_route`** — `proposals.py:484-485`
- **Guard the `sys.path` insert** — `proposals.py:490-518`
- **Module-level `_BOOK_NUM_TO_ID` constant** — `proposals.py:207-208,236-237`
- **Fix the typing import** — `bootstrap.py:23` (`from typing import Any, Dict, Optional`)
- **Swap `utcnow()` → `datetime.now(timezone.utc)`** — `core.py:92,151,159,226`
- **Lazy `import yaml`** — `routes/placeholders.py`
- **Align executor ledger-root default** — `atrium_executor.py:33-34` (closes the HIGH split-brain, ~20 min)
- **Loud sentinels for unknown channel/publishing states** — `series.py:138-147,91-92`
- **Coherence per-call file cache + `with open(...)`** — `coherence.py:44-47` (and `board_rigor` unit tests are the highest value/effort test quick win)

## Refuted (for the record)

- **`ledger.py` over 500-line ceiling** — REFUTED: line count is accurate but the file is cohesive engine core with no cleanly separable sub-concern; not the same as the `series.py` YAML-repair case.
- **`proposals.py` over 500-line ceiling** — REFUTED: 519 lines, but the load-bearing "three accreted concerns should be split" claim does not hold up as framed.
- **`crypto_vector_check.py` undeclared `cryptography` (CRITICAL framing)** — REFUTED as framed: the "silently passing / coverage silently disappears with no warning" severity claim is false; downgraded and retained as a LOW under-declaration finding.
- **proposals.json path coupled to ledger-root layout** — REFUTED: the claimed divergent-`proposals.json` failure mode is not reproducible; only a weaker DRY concern survives.

## Dimension Summaries

- **Security:** Data layer is solid (flock'd hash chain, principal binding, safe_load, traversal guards); the real risk is the loopback/CORS auth posture — a drive-by CSRF-to-code-execution chain, an un-owner-gated `/decide`, anonymous dev principals, and plaintext-secret/no-TLS federation.
- **Performance:** The ledger is already cache-aware; remaining debt is in uncached read lenses — `GET /series` (6 files/request), `/coherence` (most-cited manuscript read 9×/request), and 4× un-memoized `replay()` on `/obligations`.
- **Code quality:** Well-documented and correct, with no true dead code; debt is three files over the 500-line ceiling, a case-divergent duplicated compliance guard, a cloned JSON-store trio, and several high-complexity orchestrators.
- **Test coverage:** 142 tests pass cleanly with strong ledger/gate coverage, but the new review-ready rail (`review_ready_contract`, `board_rigor`) and the accept→execution bell wire are essentially untested, and the cross-process race is only simulated with threads.
- **Dependencies:** Declarations are dangerously incomplete — undeclared `breathline_primitives` (CRITICAL, breaks clean install), POSIX-only `fcntl` on a Windows-claimed package, and unbounded version ranges with no lockfile.
- **Architecture:** The chain primitives and single-writer fence are sound; the debt is in resolution/access layers — three (really four) incompatible ledger-root defaults, no single read-gateway over the chain, and duplicated robust-parse logic, all converging on one fix: a single `get_ledger_root()`/roadmap-read seam.
- **Constitutional:** The HTTP layer is genuinely hardened, but the governed loop leaks at every non-HTTP seam — a bypassable Propose→Execute gate, a hardcoded-`tiger` direct chain writer, a split-brain ledger root, a gate-skipping material close, and two silent-blank Error Voice regressions.

---
*Run wf_714a2b75-f63 · 7 dims · adversarially verified · confirmed by severity: {"HIGH": 8, "LOW": 16, "MEDIUM": 17, "CRITICAL": 2} (total 43, refuted 4).*
*vs BASELINE audit-report-2026-06-10 (58/100, 57 confirmed: 1 CRIT/14 HIGH/26 MED/16 LOW): health 58→62. CRITICAL 1→2 (write-fence CLOSED; 2 new seam-CRITs surfaced). HIGH 14→8. Theme shift: baseline=core leaks; now=core hardened, SEAMS leak (gate bypass on /apply, bell hardcoded-principal, split-brain root, CSRF chain).*
