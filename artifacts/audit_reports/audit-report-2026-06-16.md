# Engine 95+ Confirming Sweep — 2026-06-16 (AUTHORITATIVE, Opus 4.8) — post 4-HIGH finish-pass, commit 9708928
*Supersedes the Haiku provisional. Finders+verifiers+synth all Opus 4.8 (KM caught the model error). 7-dim adversarial vs the 82 baseline.*

# Confirming-Sweep Report — sovereign-agent stack, 4-HIGH finish-pass (commit 9708928)

## Health: 85/100 (baseline was 82)
Confirmed (adversarially verified) against live code at 9708928: CRITICAL=0, HIGH=2.
Justification, anchored to the confirmed CRIT/HIGH count:
- 0 CRIT and the two genuinely dangerous baseline HIGH (silent data-integrity/perf failures) are CLOSED and verified in live code — that earns the lift above 82.
- But 2 HIGH remain confirmed-open, both in the CI/dependency supply-chain layer. A stack carrying 2 open HIGH does not belong in the 90s. +3 over baseline for real closure, capped at 85 by the two remaining HIGH. No inflation.

## Verdict on the 82 plateau and partial-completion
- The 82 plateau did NOT break into the 90s. Net HIGH count is unchanged at 2 (four baseline HIGH closed, two new HIGH surfaced in the same finish-pass).
- The finish-pass LEFT one partial-completion: HIGH #3 (constraints lock). Its own stated objective had two halves — (a) wire constraints.txt into all install paths, (b) regenerate the pins from the green env. Half (a) is done and verified; half (b) was not. The commit even asserts in-file that it WAS done, which is false.

## Baseline 4-HIGH closure status (verified in live code)
- HIGH #1 (Merkle O(n^2)): CLOSED. core.py:149 builds MerkleAccumulator.from_leaves once; :196 append() delegates O(log n); :200 get_root() O(1). merkle_accumulator.py present. Genuine, not partial.
- HIGH #2 (no CI / no pytest path): CLOSED for the load-bearing gap. pyproject.toml:90-93 sets pythonpath=[src,scripts]+testpaths; .github/workflows/ci.yml exists (3.10/3.12 matrix, substrate assert, full suite). Caveat: the workflow itself is currently un-green-able — see new HIGH below.
- HIGH #3 (constraints wired into no install path): CLOSED for WIRING ONLY. Dockerfile:33/35, sovereign-install.sh, ci.yml:36 all now apply -c constraints.txt. But the lock pins the WRONG versions — partial-completion (see new HIGH below). Net: the wiring closed, the fix's intent did not.
- HIGH #4 (atrium_executor false-close): CLOSED. atrium_executor.py:85-98 _close_or_residue() honors _close()'s bool; _exec_distribution:107 and _exec_status_confirm:116 both `return 1` on failure before printing success. Genuine, not partial.

## Remaining confirmed HIGH (prioritized)
1. HIGH — constraints.txt pins are stale and the provenance claim is false (constraints.txt:20-26). LIVE-VERIFIED: green env runs PyYAML==6.0.3 and pytest==8.4.2; the lock pins PyYAML==6.0.1 (downgrade) and pytest==9.0.2 (a major-version bump off the validated 8.x runner — note: 9.0.2 DOES exist on PyPI, contrary to an earlier note, so the defect is wrong-version, not non-existent-version). The header (:20-21) claims "re-verified: 270 green... pins recaptured from the green interpreter, unchanged" — contradicted by live importlib.metadata. Now that the lock is load-bearing (HIGH #3 wiring), it forces installs to versions the suite was never proven green on. FIX: regenerate pins from the actual green interpreter (PyYAML 6.0.3 / pytest 8.4.2 / Flask 3.1.3 / cryptography 46.0.4) and correct the provenance block.
2. HIGH — CI zero-skip guard is un-green-able on a clean runner (ci.yml:50-55). The guard greps the pytest summary for "N skipped" and exits RED on any skip. Compounded by finding #1: the install step (ci.yml:36) uses -c constraints.txt, so the stale/wrong pins make the constrained resolve fragile before tests even run. Net effect is a structural false-RED, and the standing pressure to "make CI green" pushes a future maintainer toward loosening the guard (a path to a future false-GREEN). FIX: land finding #1 first (correct pins), then confirm the guard passes on a fresh runner with the substrate present; consider scoping the skip-grep to the final summary line to avoid matching skip-reason text.

## Remaining MED (noted, not in the confirmed-HIGH set)
- MED (dependencies/CVE floor) — constraints.txt:24 pins cryptography==46.0.4 and pyproject.toml:53 allows cryptography>=42,<47; the baseline-#12 CVE-safe floor (>=46.0.7) was never raised. The now-load-bearing lock makes the sub-floor pin authoritative. Raise the floor to >=46.0.7 when regenerating pins for finding #1.

## Sweep notes
- Verified live: PyYAML 6.0.3, Flask 3.1.3, cryptography 46.0.4, pytest 8.4.2 on Python 3.12.3 — matches the divergence claim exactly.
- Files of record (absolute): /home/kmangum/work-repos/sovereign-agent-starter/constraints.txt; /home/kmangum/work-repos/sovereign-agent-starter/.github/workflows/ci.yml; /home/kmangum/work-repos/sovereign-agent-starter/src/sovereign_agent/core.py; /home/kmangum/work-repos/sovereign-agent-starter/scripts/atrium_executor.py; /home/kmangum/work-repos/sovereign-agent-starter/pyproject.toml; /home/kmangum/work-repos/sovereign-agent-starter/src/sovereign_agent/merkle_accumulator.py

---
*Run wf_43b7cb0e-d1b (Opus 4.8) · health 85 (vs 82) · 0 CRIT / 2 HIGH · 4 baseline HIGH ALL CLOSED (completion-verified, root-equivalence brute-forced n=1..259) · Opus REFUTED 2 of Haiku's 4 new-HIGH (more rigorous). TRAJECTORY 58→62→78→82→82→82→**85**. Plateau HELD — 4 baseline closed (+3) but 2 confirmed new HIGH remain.*
