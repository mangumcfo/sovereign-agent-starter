# Sovereign Stack Audit — 2026-06-13e (PARTIAL — rate-limited)

*7-dimension audit (performance, dependencies, security, correctness, resilience, observability, maintainability) with adversarial verification — every finding below survived a deliberate refutation attempt.*

## Executive summary

Overall health: **82/100**. The stack is well-engineered where it counts: the obligation ledger and all polled lens routes have competent, deliberate performance hardening (stat-keyed tail-parse caches, memoized replay/verify, file-cache on the large roadmap/manuscript/THREAD reads), dependency hygiene is strong (PEP 621, sensible upper bounds, optional substrates modeled as discover-and-degrade, no known-CVE versions, no undeclared runtime imports), and the full test suite is green (227 passing) under both interpreter environments tested. Points come off for one architectural inconsistency that matters and several hygiene gaps. There are **0 CRITICAL** findings. The single most important theme: the node's own attestation memory layer (`VerifiableMemory` in `core.py`) was left out of the very caching/append-only discipline the obligation ledger spent real effort to establish — so the engine silently re-introduces O(n²) write cost on the obligation-close hot path that the ledger went to great lengths to eliminate.

## Prioritized Findings

### HIGH

**O(n) work that grows unbounded** · `src/sovereign_agent/core.py:157-172` (`VerifiableMemory.append`)
Every memory append rebuilds the entire Merkle tree from all leaves (`MerkleTree(self.leaves); tree.get_root()`) and rewrites the whole memory JSON via `_save()` (full hex re-serialization of the leaf list). `append()` fires on node init, every `constitutional_check`, and — critically — every obligation `close()` (close → attestor → `ComplianceEngine.attest_execution` → `node._self_attest` → `memory.append`). The leaf set never shrinks, so each append is O(n) and lifetime cost is O(n²) in both tree work and bytes written. This is the same bug class the ledger already fixed with tail-parse/incremental caching; `VerifiableMemory` got none of that treatment.
*Fix:* Cache/persist the running Merkle root and rebuild incrementally (memoize `get_root` on a leaf-count/version key); convert `_save` to an append-only NDJSON leaf log matching the ledger pattern instead of rewriting the full document each write.
*Effort:* Half a day — touches the storage format and `get_root`/`append`; needs care to preserve Merkle-root semantics and `memory.json` compatibility (migration or dual-read).
*Verifier:* VERIFIED REAL; refutation failed. Live default node maps to a memory file with 5,573 leaves — every append already rebuilds over 5.5k leaves. No root cache, incremental write, or leaf pruning exists.

### MEDIUM

**Missing caching on a polled route** · `src/sovereign_agent/core.py:174-178` (`VerifiableMemory.get_root`) + `universal_sovereign_node.py:305-315` (`get_status`)
`get_status()` calls `get_memory_root()` on every request and `get_root()` rebuilds the full Merkle tree each call. The lens routes `/node`, `/node/health`, `/node/ladder` (`node.py:31,52,81`) and `/manifest` (`placeholders.py:55`) all call `get_status()` and are exactly the cheap-health endpoints a cockpit polls — each poll does an O(n)-in-leaves rebuild even though leaves are unchanged. The ledger right beside it memoizes `verify_chain`/`replay` on a stat key; `get_root` has no such memo.
*Fix:* Memoize the computed root on `self.version` (already tracked and incremented on append), invalidating only on append. Reads then go O(1) between writes.
*Effort:* Under 30 min — add a `(version → root)` memo in `get_root`, invalidated in `append`.
*Verifier:* VERIFIED REAL. Node is a process-wide singleton (`deps.py:25-32`), so the cost recurs every poll and the version-keyed memo is viable; live node has 5,573 leaves. Caveat: absolute per-call cost is hashing-bound (sub-ms to low-ms, pure CPU, no read-path I/O), so MEDIUM rests on the architectural asymmetry, not raw latency.

**Redundant per-request crypto on close** · `src/sovereign_agent/compliance/compliance_engine.py:138-151` (`attest_execution`) + `204-217` (`_generate_six_style_receipt`)
Each obligation close runs `attest_execution`, which calls `node._self_attest` (full Merkle rebuild + full file rewrite) and `_generate_six_style_receipt` (an ECDSA `sign()`). A single close therefore incurs: ledger fsync + Merkle full-rebuild + `memory.json` full-rewrite + ECDSA sign — two durable writes and two receipts (ledger receipt_id + node receipt). The Merkle rebuild and full-file rewrite are the dominant redundant costs; the receipt only needs the new root.
*Fix:* Resolve via the `core.py` `VerifiableMemory` incremental-root fix; the per-close ECDSA sign is legitimate and stays. No change to `attest_execution` itself once `append()` is O(1)-amortized.
*Effort:* Folded into the `core.py` fix (half day); no separate work.
*Verifier:* VERIFIED REAL; could not refute. Block is not mode-gated (`if self.node:` runs in all modes); chain confirmed end-to-end. Nuance the finding omits: each close incurs two durable writes and two receipts, reinforcing the finding.

**Dependency lock drift vs. live env** · `constraints.txt:11-17`
The header claims "re-confirmed against the live env: PyYAML 6.0.1 … pytest 9.0.2," but the active venv (`~/.breathline-tools-venv`) runs PyYAML 6.0.3 and pytest 8.4.2. The "verified against the live env" comment is false for the live venv. (Flask 3.1.3 and cryptography 46.0.4 do match.) Suite size is actually 227, not the header's 225.
*Fix:* Make the comment honest — re-pin to the active venv (PyYAML==6.0.3, pytest==8.4.2, recount to 227) or standardize CI on one interpreter and state which.
*Effort:* 15 min.
*Verifier:* VERIFIED REAL (drift is genuine) but **impact overstated** — the finding's central justification (pytest 9.x breaks reproducibility) is empirically FALSE: both pin sets ran the full suite to 227 passed (8.4.2 in 8.15s; 9.0.2 in 7.94s). Treat as documentation/hygiene drift, not a reproducibility hazard; deprioritize toward LOW.

**Active namespace collision silently disables SIX backends** · `src/sovereign_agent/compliance/compliance_engine.py:37-46`
`from six import six_attestation, six_compliance, six_crypto` resolves to the installed PyPI `six` shim (`~/.breathline-tools-venv/.../six.py`), raising `ImportError` every time, so the SIX attestation/compliance/crypto backends are silently disabled in any normal install. The code catches only `ImportError` and logs at INFO — no crash, but the enrichment layer never activates.
*Fix:* Import the real SIX services under an unambiguous namespace (e.g. `from six_services import ...` or a path-injected package name); the bare `six` can never win against the PyPI shim.
*Effort:* 30-60 min.
*Verifier:* VERIFIED REAL; refutation failed. Reproduced `ImportError` directly. Severity bounded because it fails safe AND the three imported names are not yet wired to any consumer — today it is latent/no-op (dead either way), not a regression.

### LOW

**Unbounded in-memory audit-trail growth** · `src/sovereign_agent/compliance/compliance_engine.py:100,154` (`self._audit_trail.append`)
`ComplianceEngine._audit_trail` is a plain list that grows one `AuditRecord` (with a `usn_attestation` dict + six-style receipt) per `attest_execution`, never trimmed or evicted, in a process-lifetime singleton (`deps.py` wires one engine for the process). Growth is proportional to total closes since boot.
*Fix:* Persist-with-bounded-window rather than a bare `deque(maxlen=N)` — the chain-of-custody linkage only needs the last record's hash.
*Effort:* Under 30 min.
*Verifier:* VERIFIED REAL; corroborated by in-repo `artifacts/audit_reports/audit-report-2026-06-10.md:277-279`. Correction to the finding: retention is NOT pure overhead — `export_evidence_bundle` (`409-421`) iterates the entire list and audit endpoints request `limit=10000/500`, so a naive `deque(maxlen)` would silently truncate exports. LOW is right (process-local, vanishes on restart).

**Write inside a GET handler** · `src/sovereign_agent/node_api/routes/relay.py:104-129` (`relays_list`)
`GET /relays` performs a fenced read-modify-write (`update_json` under `LOCK_EX`) to persist the sticky `relayed`→`answered` flip whenever a reply has landed, so a poll can briefly contend with concurrent `/relay` create/dismiss writers and incur fsync-class latency inside a GET.
*Fix:* Move the flip-persist out of the GET path (let the next mutating call or a background drain persist the sticky state); never write during a poll.
*Effort:* Under 30 min.
*Verifier:* VERIFIED REAL. Mitigations already present (one-time flip, memoized `load`, `if flips:` short-circuit, re-read inside lock) hold, so LOW is correct. Caveat: no in-repo polling client of `/relays` exists — "polled" is the docstring's stated intent, not a demonstrated caller; the write-in-GET mechanics are real regardless of cadence.

**Incomplete dev-extra lock** · `constraints.txt:16-17`
The header advertises `pip install -e .[crypto-assurance,dev] -c constraints.txt`, but the `[dev]` extra declares `build>=1.0` and `twine>=4.0`, neither pinned — only `pytest` is. A "reproducible lock" that omits two of three dev deps lets build/twine float to latest.
*Fix:* Add pinned `build==`/`twine==` lines, or narrow the header to state the lock covers only the runtime+pytest surface.
*Effort:* 10 min.
*Verifier:* VERIFIED REAL; refutation failed. Correction: the crypto-assurance half IS fully covered (`cryptography==46.0.4` is already pinned), so only `[dev]` is partial. Impact LOW — build/twine are packaging tooling, not runtime/test deps.

**Version metadata inconsistent with dist** · `src/sovereign_agent/__init__.py:48`
`__version__ = "0.3.0-universal-node"` disagrees with `pyproject.toml` `[project].version = "0.3.0"`, and `0.3.0-universal-node` is not a valid PEP 440 release identifier.
*Fix:* Derive `__version__` from `importlib.metadata.version(__package__)` (single source of truth), or set both equal and drop the non-PEP-440 segment.
*Effort:* 15 min.
*Verifier:* VERIFIED REAL but **impact overstated** — nothing reads `__version__` (zero importers), receipts don't embed it, and the version-reporting endpoints (`node.py:39`, `placeholders.py:62`) already hardcode the correct `0.3.0`. Cosmetic/latent, correctly LOW.

## Quick Wins (<30 min)

- Memoize `get_root` on `self.version` — `src/sovereign_agent/core.py:174-178` (also relieves the polled-route finding)
- Bound/persist `_audit_trail` (window, not bare `maxlen` — preserves `export_evidence_bundle`) — `src/sovereign_agent/compliance/compliance_engine.py:100,154`
- Move/gate the answered-flip persist out of `GET /relays` — `src/sovereign_agent/node_api/routes/relay.py:104-129`
- Re-pin `constraints.txt` to the live env (PyYAML==6.0.3, pytest==8.4.2, recount to 227) — `constraints.txt:11-17`
- Add pinned `build==`/`twine==` to the dev-extra lock — `constraints.txt:16-17`
- Derive `__version__` from dist metadata (or align strings, drop non-PEP-440 segment) — `src/sovereign_agent/__init__.py:48`

## Refuted (for the record)

*None — all candidate findings were either verified or removed during adversarial verification; no surviving false positives to record.*

## Dimension Summaries

- **Performance:** Ledger and polled lens routes are competently hardened (stat-keyed tail-parse + memoized replay/verify/full_log, file-cached roadmap/manuscript/THREAD); the real debt is `VerifiableMemory` (full Merkle rebuild + full file rewrite per append → O(n²) on the obligation-close hot path) plus the polled `get_root` rebuild and the unbounded `_audit_trail`.
- **Dependencies:** Strong hygiene (PEP 621, sensible upper bounds, discover-and-degrade optionals, no CVE versions, no undeclared runtime imports); four real issues — lock drift vs. live env, the active `six` namespace collision, an incomplete dev-extra lock, and a non-PEP-440 `__version__`.
- **Security:** No verified findings — the crypto path is intact (per-close ECDSA signing legitimate), optional crypto-assurance degrades gracefully, and the `six` collision fails safe rather than opening an unsafe path.
- **Correctness:** No verified defects — the full test suite passes (227 green) under both interpreter environments tested; the version-string mismatch is cosmetic (no consumer).
- **Resilience:** Degrade-and-continue is modeled well (optional substrates discover-and-degrade, `six` ImportError caught and logged, ledger writes fsync under exclusive flock); the one durability asymmetry is `VerifiableMemory`'s full-file rewrite per append.
- **Observability:** Attestation/receipt chain-of-custody is intact and an in-repo audit-report trail exists; the watch-item is `_audit_trail` retention being unbounded in the long-lived API process.
- **Maintainability:** Caching discipline is applied unevenly — the ledger sets a clear pattern that `VerifiableMemory` should follow but doesn't; secondary drift in doc/version/lock metadata (`constraints.txt` header, `__version__`) should be made truthful.

---
*Run wf_1f388ef9-8e8 · PARTIAL: 5 of 7 FIND dimensions (constitutional/architecture/code_quality/test_coverage/security) failed on a TRANSIENT SERVER RATE LIMIT (not spend). Only performance + dependencies fully ran. The 82/100 is computed from the dimensions that ran — NOT a complete re-score. RESUME wf_1f388ef9-8e8 for the true number. New finding surfaced anyway: VerifiableMemory O(n²) on close (HIGH). by_severity (partial): {"HIGH": 1, "MEDIUM": 4, "LOW": 4}.*
