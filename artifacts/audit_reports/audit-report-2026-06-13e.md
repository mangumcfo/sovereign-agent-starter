# Sovereign Stack Audit — 2026-06-13e (resumed; FIND-complete, verify-partial)

This audit evaluates the sovereign agent stack across 7 dimensions — security, performance, code quality, test coverage, dependencies, architecture, and constitutional conformance — with every finding subjected to adversarial verification (false positives removed before inclusion).

## Executive Summary

Overall health: **82/100**. The stack is mature and heavily self-audited: auth/authorization, path-traversal defense, injection avoidance, and the obligation-ledger's single-writer concurrency fence are all genuinely solid, and the hot paths are mostly already memoized through a purpose-built `_filecache` decorator. The score is held below the 90s by two real HIGH-severity defects rather than systemic rot. **Critical count: 0.** The single most important theme is **incomplete application of the stack's own proven disciplines** — the memoization decorator, the per-line parse tolerance, and the packaging/lock conventions all exist and work, but a handful of sites were never wired to them: an unguarded `json.loads` that bricks the entire ledger on a truncated tail line, two first-class endpoints depending on an unpackaged `scripts/` dir, a lock file that is stale at birth, and three polled routes that skipped the cache their siblings use.

## Prioritized Findings

### HIGH

**Test Coverage — untested + broken failure path (ledger corruption)** · `src/sovereign_agent/obligations/ledger.py:252` (tail twin :245); gap in `tests/test_obligation_ledger.py`, `test_ledger_concurrency.py`, `test_ledger_tailparse.py`
A truncated/partial trailing line — the classic "process killed mid-append under concurrent writes" corruption — makes the *entire* ledger unreadable. `_entries()` does a bare `json.loads(s)` per line with no per-line guard, so one half-written final line raises `JSONDecodeError` in both `_entries()` and `verify_chain()`. Every read route (`GET /obligations` chain_ok, `/awaiting_km`, replay, `open_card` parity) then 500s, and `repair_chain()` itself raises before it can relink — so the documented recovery path cannot recover a truncated ledger. Existing corruption tests only forge *complete, parseable* bad lines, never a truncated one.
*Fix:* Add a regression test appending a partial trailing line and asserting `_entries()`/`verify_chain()`/`open_obligations()` degrade gracefully (drop/quarantine the incomplete tail); then add the underlying per-line tolerance, mirroring `_jsonstore`/`yaml_repair` sidecar resilience. The test will FAIL today — it documents a real defect.
*Effort:* ~30–45 min test + ~30 min code fix.
*Verifier:* Reproduced directly — partial tail `{"type":"debit","id":"half` makes `_entries()`, `verify_chain()`, `open_obligations()`, `replay()` ALL raise `JSONDecodeError`; routes have no try/except so it surfaces as unhandled 500; `repair_chain()` (ledger.py:329/331) raises before quarantine. Flock prevents forks but not a kill mid-write.

**Dependencies — unpackaged `scripts/` dependency breaks two endpoints in prod** · `src/sovereign_agent/node_api/routes/proposals.py:339-343, 368-372`
`GET /api/v1/export/packet` (R22-1) and `GET /api/v1/actions` (R22-2) inject `parents[4]/scripts` onto `sys.path` at request time and `import export_packet` / `import actions_projection`. But `scripts/` is not packaged (`packages.find where=["src"]`, package-data only `demo_roles/**`, no MANIFEST) and the Dockerfile COPYs only `pyproject.toml`, `README.md`, `src/` (lines 31-32). In any container or non-editable install these endpoints raise `ModuleNotFoundError`; they work only from an editable repo checkout. Unlike the sibling atrium_producer path in the same file, these two have no `script.exists()` guard, so they fault with a raw unhandled error.
*Fix:* Move `export_packet.py` and `actions_projection.py` into the installed package (e.g. `src/sovereign_agent/obligations/`) and import as proper modules (preferred); or add `scripts/` to the wheel via package-data/MANIFEST and `COPY scripts ./scripts` in the Dockerfile.
*Effort:* 1–2 hours.
*Verifier:* `parents[4]` resolves to repo root expecting `<root>/scripts`; those files exist only under `/scripts`; Dockerfile never copies them; editable install points at `/app/src` and `/app/scripts` was never copied. Confirmed against source, pyproject, Dockerfile.

### MEDIUM

**Performance — missing caching on hot polled lens route** · `src/sovereign_agent/node_api/routes/hopper.py:102-137, 166-185`
`GET /hopper` is a cockpit intake lens polled like `/series` and `/awaiting_km`, but is the one polled lens never wired to `_filecache.memoize_on`. With `HOPPER_FEED` wired, `_cards_from_feed` does a full `read_text()` + per-line `json.loads()` of the ~20KB `GB_Hopper_Feed.ndjson` on every request; `_cards_from_session` does a full `yaml.safe_load` of `HOPPER_SOURCE` per request. GB is the sole, rare writer, so a memoized read would be ~100% hit.
*Fix:* Wrap `_cards_from_feed`/`_cards_from_session` in `@memoize_on` keyed on the feed/session path stat, mirroring `_read_roadmap`/`_chapter_index` in series.py. Keep the Send-to-Packet dedup (live ledger state) outside the cache.
*Effort:* ~20 min.
*Verifier:* `memoize_on` exists in `_filecache.py` (keyed on path,mtime_ns,size) and is used by series/coherence/dialogue; hopper.py imports neither it nor memoize_on; feed file confirmed at 20,846 bytes. Fix caveat (`_packeted_refs` mutating state stays uncached) is correctly scoped.

**Performance — unbounded O(n) ledger re-scan per request** · `src/sovereign_agent/obligations/ledger.py:263-265` (caller `hopper.py:140-149`)
`ObligationLedger.refs()` rebuilds `{e.get('ref') for e in self._entries() if ...}` over the entire chain on every call, with no memoization — the one chain-derived view not cached on `_stat_key` (unlike `replay()`/`full_log()`/`verify_chain()`). It is called by `hopper._packeted_refs()` on every `GET /hopper` (feed path). The append-only chain is already 1.5MB / ~1044 lines and grows forever, so this is an O(n) set-comprehension per poll that grows unbounded.
*Fix:* Memoize `refs()` on `self._stat_key()` with a per-type cache dict, exactly like `replay()`/`full_log()`/`verify_chain()`; auto-invalidated when the chain file changes.
*Effort:* ~20 min.
*Verifier:* Confirmed `refs()` (252-265) has no cache; siblings at 617-619/678-680/720-722 all early-return on `_stat_key`. Caller chain hopper.py:175→140-149→`led.refs('debit')` confirmed. Runs over in-memory cached `_entries()` parse (no disk re-read), so cost is CPU-only — justifies MEDIUM, not higher.

**Dependencies — constraints lock stale at birth** · `constraints.txt:11-13`
The lock's provenance comment claims "re-confirmed against the live env: PyYAML 6.0.1" and pins `PyYAML==6.0.1`, but the live env runs PyYAML **6.0.3** (`pip show`, `pip freeze`, the active test venv all agree). A `pip install -c constraints.txt` would *downgrade* away from the tested-green env. The lock's own provenance is false at birth. (Also understated: line 12/17 claims pytest 9.0.2 but the venv runs pytest 8.4.2.)
*Fix:* Regenerate `constraints.txt` from `pip freeze` of the actual green env so `PyYAML==6.0.3` (and `pytest==8.4.2`) match what tests ran against; stop hand-editing the provenance comment.
*Effort:* 15 min.
*Verifier:* Every interpreter reports 6.0.3; pyproject `pyyaml>=6.0,<7` permits it, so constraints.txt is the *only* thing forcing a 6.0.1 downgrade. Corroborated by three prior audit reports. No CVE exposure (6.0.3/8.4.2 both clean) — hygiene/reproducibility defect.

### LOW

**Performance — redundant projection rebuild on cached inputs** · `src/sovereign_agent/node_api/routes/series.py:305-353` (`_series_card` 288-302, `_title_card` 239-285)
`GET /series` correctly memoizes its inputs (112KB roadmap + 5 overlay indexes) but rebuilds the full card projection every request: `all_cards = [_series_card(...) for s in data['series']]` runs `_title_card` over every series/title/chapter unconditionally per poll, and `_dispatch_gate_summary` is recomputed inline. All inputs are mtime-memoized and change rarely, so the output is deterministic yet recomputed each poll.
*Fix:* Memoize the assembled `(all_cards, dispatch_gate)` on the union stat-key of roadmap + 5 trackers via an `@memoize_on` helper; the handler then only applies the cheap `include_private` filter + meta.
*Effort:* ~30 min.
*Verifier:* Inputs confirmed memoized; `_series_card`/`_title_card`/`_dispatch_gate_summary`/`all_cards` carry no memoization; no HTTP/WSGI/lru cache anywhere in the route. Only per-request-variable input is the cheap `include_private` post-filter, correctly excluded. Absolute saving scales with roadmap size — LOW.

**Performance — per-request log re-read over external run store** · `src/sovereign_agent/node_api/routes/proposals.py:138-183`
`GET /processing` globs `~/.breathline/runs/*.json`; the `have = {...}` dedup set is correctly hoisted and `_read()` is itself memoized, but each live run's `.log` is re-read and tail-sliced every poll with no change-detection. Lower impact than the lens routes: the run set self-prunes to in-flight agents only, and the route is inherently live (recomputes elapsed time + `os.kill(pid,0)` liveness per poll).
*Fix:* Optional — skip re-reading a run log when its mtime is unchanged, caching the tail per `(path, mtime)`; only worthwhile under many concurrent runs. Liveness/elapsed fields must stay live.
*Effort:* ~30 min.
*Verifier:* Glob + per-file tail-slice (lines 173-179) confirmed uncached; `read_json_cached` only covers the proposals store, not the log files. Self-pruning (167-172) and live liveness checks confirmed. Honestly self-scoped as "not a clear win."

**Dependencies — cryptography floor permits advisory-bearing wheels** · `pyproject.toml:53`
The crypto-assurance extra pins `cryptography>=42,<47`. The `<47` cap is fine, but the `>=42` floor permits early 42.0.0/42.0.1 wheels carrying bundled-OpenSSL advisories (CVE-2024-0727 class, fixed in 42.0.2+). Since constraints isn't wired into any install path, a default `pip install '.[crypto-assurance]'` could resolve against the floor.
*Fix:* Raise the floor to a patched release, e.g. `cryptography>=43,<47` (or `>=42.0.2`).
*Effort:* 10 min.
*Verifier:* Floor + cap confirmed; constraints not applied in Dockerfile (no `-c`). Bounded impact: pip prefers newest-in-range (46.x) by default, and actual usage (`crypto_vector_check.py`) is ECDSA/secp256k1 interop, never the PKCS12 CVE path — supply-chain floor hygiene, not live exploitability. LOW.

**Dependencies — `__version__` diverges from packaging version** · `src/sovereign_agent/__init__.py:48`
`__version__ = "0.3.0-universal-node"` (not PEP 440 valid) while `pyproject.toml` `[project] version = "0.3.0"`. `importlib.metadata.version(...)` returns `0.3.0` while the module attribute returns the suffixed string — two values for tooling that reads each.
*Fix:* Derive `__version__` from `importlib.metadata.version('sovereign-agent-starter')` or match pyproject exactly (`0.3.0`); drop the non-PEP-440 suffix.
*Effort:* 15 min.
*Verifier:* Both literals confirmed; ZERO importers of the top-level `__version__`; the actual version endpoints (`node.py:39`, `placeholders.py:62`) already hardcode the correct `0.3.0`, so the suffix never reaches any API/receipt/attestation payload — latent/cosmetic, correctly LOW.

## Quick Wins (<30 min)

- **Wire `/hopper` to the cache** — `src/sovereign_agent/node_api/routes/hopper.py:102-137, 166-185` (~20 min)
- **Memoize `refs()` on `_stat_key`** — `src/sovereign_agent/obligations/ledger.py:263-265` (~20 min)
- **Regenerate `constraints.txt` from the green env** — `constraints.txt:11-13` (15 min)
- **Raise cryptography floor to `>=43`** — `pyproject.toml:53` (10 min)
- **Fix `__version__` drift** — `src/sovereign_agent/__init__.py:48` (15 min)
- **Memoize the `/series` projection** — `src/sovereign_agent/node_api/routes/series.py:305-353` (~30 min, borderline)

## Refuted (for the record)

- **constraints.txt is "documentation-only / no automated path applies it"** (`Dockerfile`) — REFUTED: the load-bearing claim that no automated path applies the lock is false; the refutation pass found the lock is referenced by an actual reproducibility path, so the "documentation-only" framing does not hold.

## Dimension Summaries

- **Security:** Exceptionally hardened — every state-changing route is `@require_principal`, code/chain-mutating routes additionally `@require_owner`, principal spoofing closed, constant-time token auth, path traversal defended, zero `shell=True`/`eval`/`pickle`; residual items (64-bit truncated chain link, mtime-keyed verify cache, CSRF guard failing open on absent `Sec-Fetch-Site`) all require prior filesystem compromise or an unusual client.
- **Performance:** Hot paths are mostly already memoized via `_filecache`; the four remaining gaps (`/hopper` uncached, `refs()` un-memoized, `/series` projection rebuild, `/processing` log re-read) are all quick extensions of the existing proven discipline.
- **Code quality:** Good shape, no genuine dead code; real issues are consistency (placeholders.py still on `build_error` not `route_error`), ledger.py at 755 lines breaching the 500-line ceiling, duplicated disposition error bodies, and a hardcoded vault literal in series.py.
- **Test coverage:** Genuinely strong (227 collected, all gate paths tested); the standout gap is the untested-and-broken truncated-tail ledger corruption path, plus zero HTTP tests on coherence routes and atrium_producer.py.
- **Dependencies:** Declared deps minimal and sane; issues are reproducibility/packaging (unpackaged `scripts/` breaks two endpoints, stale lock, unwired constraints, cryptography floor, `__version__` drift), four of five being quick wins.
- **Architecture:** The hardest problem — chain integrity under concurrency — is well-architected; weaknesses are seam placement (roadmap projection trapped in the Flask route, `yaml_repair` under `node_api/`), one unfenced RMW on `handshakes.json`, and a few ledger-root sites bypassing the single resolver.
- **Constitutional:** Heavily self-audited and mostly closed; residual items are the hardcoded `principal_id='node'` on the API ledger (entry-level SOURCE attribution overwritten — HIGH within the dimension), an executor close lacking an `_is_approved` check, and sidecar_store bypassing `get_ledger_root()`.

---
*Run wf_1f388ef9-8e8 resumed · all 7 FIND dims ran; some VERIFY agents starved on spend → findings FIND-complete, verify-partial. health 82 (held). 0 CRITICAL. by_severity: {"MEDIUM": 3, "LOW": 4, "HIGH": 2} (confirmed 9).*
*CONSOLIDATED HIGH across both 13e runs: (1) VerifiableMemory O(n²) on close [core.py] · (2) ledger truncated-tail-line bricks chain + repair can't recover [ledger.py:252] · (3) unpackaged scripts/ breaks /export+/actions in container [proposals.py]. ALL propagation-debt: stack's own disciplines (memoize / tolerant-parse / packaging / append-only) not applied to a few sites.*
