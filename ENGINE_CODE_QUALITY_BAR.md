# Engine Code-Quality Bar (M2) — sovereign-agent-starter

*One page. The engine's analog to the S2 Visual Standard: "built right" made explicit. This writes down the
bar this engine **already meets** — it is not a wall of new rules. KM-1176 ratifies changes. (audit 2026-06-16)*

## Structural (Constitution §5)
- **File ceiling ≤ 500 lines** — re-seed by **extraction, not abstraction** when a module grows past it
  (exemplar: `obligations/ledger.py` 790 → 499 via `_util`/`_locking`/`evidence`/`roots`/`provenance`/
  `projection` siblings; the class kept its I/O + lifecycle and delegated reads).
- **Function complexity ≤ 10** — enforced by `ruff` `C90` (`[tool.ruff.lint.mccabe] max-complexity = 10`),
  set to the §5 number, not an arbitrary one. New code stays ≤10; existing >10 is tracked, not grandfathered.
- **No duplication tail** — lift repeated blocks into one helper (exemplars: `_write_fence()` context manager,
  `_require()` existence guard). Code you don't write can't break.

## Testing
- **Suite green in the canonical env:** `pip install -c constraints.txt -e ".[dev,crypto-assurance]"` then
  `pytest` → all pass / **0 skipped** (CI asserts zero-skip via the JUnit count, no silent false-green).
- **Load-bearing code carries a full-chain test** (completion-verified, not attempt-verified): the Merkle
  accumulator (root-equivalence across boundaries + O(log n) proof), the atrium_executor (false-close →
  non-zero + OPEN), the ledger (byte-identical equivalence snapshot pre/post any refactor).
- **A refactor of `obligations/` must pass the ledger equivalence snapshot** (get_ledger_root + replay +
  verify_chain + full_log + manifest, byte-identical on the live + a synthetic chain).

## Static analysis (standing tool — the loop can SEE dead code + complexity)
- **`scripts/static_scan.sh`** = `ruff` (dead F + complexity C90≤10 + bare-except E722) + `vulture` (dead
  symbols @80, whitelisted) + `coverage` (use-evidence). Reproducible; **report-only**.
- **Candidates-not-delete:** findings are triaged into REMOVE-recommended / KEEP-with-reason / REVIEW; **no
  symbol is removed without KM's gate** + the suite staying green. A wrong delete is worse than dead code.
- House style (line length, multi-statement) is **not** enforced — only correctness/complexity/dead-code.

## Supply chain & provenance
- **Reproducible install:** `constraints.txt` pins the runtime/test surface, regenerated from a green venv via
  `pip freeze` (never a hand-edit) and self-checked by `tests/test_constraints_lock.py` (pins == installed).
- **CVE floor:** `cryptography >= 46.0.7`; `setuptools` upper-bounded; `pip-audit` CI step (M3) scans for CVEs.
- **Evidence/receipt discipline:** material changes are gated; each close carries E1+ evidence; refactors carry
  a byte-identical equivalence receipt. The map (`GB_Engine_Gap_to_100_LIVING.md`) is the living debt register.

## Maturity tail (tracked, not required for the 95 claim)
M4 threat model · M5 SLSA build provenance · M6 OpenSSF Scorecard · M7 mutation testing on the load-bearing
three · M8 ADRs. Explicit + small, sequenced — recorded in the map so they're tracked, not re-discovered.

∞Δ∞ Built right = ≤500-line modules, ≤10-complexity functions, no duplication, full-chain tests on the
load-bearing code, a reproducible static pass, a reproducible install, and a human gate on every removal. ∞Δ∞
