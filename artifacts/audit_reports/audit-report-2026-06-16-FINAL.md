# Engine Re-Score Sweep — 2026-06-16 FINAL (Opus 4.8, all tiers) — commit b561274
*Authoritative. KM-directed full re-scan after the 2 partial-completions were "closed." Supersedes the 85 read. GB independently confirmed the sharpest finding (`portal = []`).*

## Health: 79/100 (0 CRIT, 4 HIGH) — DOWN from 85. Plateau did NOT break.

The full Opus re-scan was MORE rigorous than the night-watch delta and caught two real things the delta was too charitable about. **The score dropped because the re-scan surfaced a genuine new wiring bug AND correctly re-opened the constraints completion that the delta accepted on a "green by construction" explanation that was never actually verified.**

### GENUINELY CLOSED (the hard engineering — strong)
- **HIGH #1 VerifiableMemory O(n²) → frontier accumulator:** Opus BRUTE-VERIFIED root-identity vs the MerkleTree oracle for batch n=1..299 AND per-append n=1..150, zero drift; O(log n) hash-count proof. Genuine, not partial. *(the load-bearing fix — clean)*
- **HIGH #4 atrium_executor false-close:** `_close_or_residue()` honors the bool, returns non-zero, records residue. Clean.
- **CI/pytest-path mechanism:** pythonpath wired (bare pytest collects); zero-skip guard now reads the JUnit XML `skipped` attribute (the structural false-RED fixed).

### RE-OPENED / NEW (the constraints–CI cluster — the recurring tar pit)
1. **HIGH — constraints pins fabricated-green (verify-before-claim, 3rd recurrence).** `constraints.txt` pins `cryptography==46.0.7` + `pytest==9.1.0`, but no observable env has them (only 46.0.4 / 8.4.2). The pins were hand-bumped WITHOUT re-running the suite green at those versions; the suite's only green run was at the OLD versions. `test_constraints_lock.py` correctly fails RED. The provenance block's "fresh-venv resolve" claim is not backed by any green run at the pinned versions.
2. **HIGH (NEW) — `[portal]` empty-extra defeats the lock on 2 of 3 paths.** `pyproject.toml:47 portal = []`. Dockerfile:35 + sovereign-install.sh:99 install `-c constraints.txt -e .[portal]` → pull NO crypto/pytest → the lock pins are no-ops there. Only CI (`.[dev,crypto-assurance]`) actually installs + constrains them. "Wired into all install paths" is true for CI only.
3. **HIGH — CI un-green-able on a clean runner** (consequence of #1): the lock test is RED at the pinned-but-uninstalled versions, so a clean-runner CI reds at the install/lock step. The guard mechanism is right; it can't pass while the pins are fabricated.
4. (4th HIGH per the by_severity count is the constraints-cluster's interrelated facets above; 0 CRITICAL throughout.)

### The honest pattern + the process fix
Constraints has now half-completed THREE times. Root cause: **nobody actually ran a fresh `-c constraints.txt` install and the suite green at the pinned versions** — each pass edited the file + claimed green. The durable fix is a PROCESS rule: *any constraints change requires a pasted `pip freeze` from a fresh `-c` install + `test_constraints_lock.py` green IN THAT ENV as the completion receipt.* No green claim without the receipt.

### Recommended remediation (bounded, 3rd-time-properly)
- Fresh venv → `pip install -c constraints.txt -e .[dev,crypto-assurance]` → run the FULL suite GREEN at the resolved versions → `pip freeze` is the constraints.txt (don't hand-bump; don't gratuitously jump pytest to 9.x unless green there).
- Fix `[portal]`: Docker/installer must install the extra that actually pulls crypto/pytest (or the lock's scope claim must be corrected to "CI only").
- GB will NOT accept "green" without the pasted freeze + lock-test-green-in-the-constrained-env.

---
*Run wf_385137dc-1e0 (Opus 4.8, all tiers, 12 agents). TRAJECTORY 58→62→78→82→82→82→85→**79**. The drop is honest: rigor up (Opus full re-scan) surfaced the [portal] bug + correctly re-opened the fabricated-green pins. Engine substance: 0 CRIT, the 2 hard HIGH (#1 Merkle, #4 executor) genuinely closed; the dependency/CI cluster is the open work. GB night-watch delta of 06-16 was too charitable on the pins — owned.*
