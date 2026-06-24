# Night-Watch Delta Audit — 2026-06-16 (commit b561274 vs baseline 9708928)
*Token-light delta: ONE Opus read-only finder, scope = only the 4 files changed by the 2-HIGH close.*

## Verdict: both partial-completion HIGH genuinely CLOSED (mechanical, not cosmetic). 0 new CRIT/HIGH, no regressions.

**HIGH-a (stale constraints pins + false provenance) — CLOSED.**
- Pins regenerated to live: `constraints.txt` PyYAML==6.0.3 / Flask==3.1.3 / cryptography==46.0.7 / pytest==9.1.0 (stale 46.0.4 / 9.0.2 / never-installed 6.0.1 corrected).
- Crypto floor raised `pyproject.toml:55` → `cryptography>=46.0.7,<47` (also closes baseline MED-#12 CVE floor).
- Provenance header now truthful — false "re-verified…unchanged" gone, replaced by honest "pip freeze of a fresh venv" + history recording the prior pins were WRONG.
- `tests/test_constraints_lock.py` is NON-tautological: finder RAN it → it correctly FAILED RED on drift (`cryptography pinned 46.0.7 but installed 46.0.4`; `pytest 9.1.0 vs 8.4.2`). Reads installed versions via importlib.metadata, asserts == pins. The verify-before-claim gap is now mechanically enforced.

**HIGH-b (un-green-able CI zero-skip guard) — CLOSED.**
- `ci.yml` now emits `--junitxml` and reads the authoritative `skipped` XML attribute (not text-grep). Old bug reproduced (grep matched literal "0 skipped" → false-RED). New guard verified both ways: 0 skips → GREEN; injected real skip → RED. Immune to skip-reason text; zero-silent-skip intent preserved.

## 2 LOW (no action required)
- `ci.yml` guard sums `skipped` but not `errors` — but pytest's own exit code reds the run first (covered). Cosmetic.
- `test_constraints_lock.py` makes the suite env-coupled by design: any interpreter NOT installed `-c constraints.txt` fails the lock test. Intended (it's the guard).

## ⚠ Operational note (LOW, surfaced to Tiger)
The ambient dev venv on this box (`~/.breathline-tools-venv`) still carries the OLD packages (cryptography 46.0.4 / pytest 8.4.2) — so local `pytest` now RED-fails the lock test there. Tiger's "274 green / 0 skipped" holds only in the canonical `-c constraints.txt` venv (not reproducible from the ambient interpreter). ACTION: `pip install -c constraints.txt` the ambient dev venv so local runs are green, not just CI/container.

## Fixed-since-baseline
HIGH-a, HIGH-b, and baseline MED-#12 (CVE floor) all closed.

---
*ONE Opus read-only finder (34k tokens). No new CRITICAL/HIGH → no urgent Tiger escalation; env-sync LOW noted. The full Opus re-score confirming sweep is the remaining step for the official ~88-90 number.*
