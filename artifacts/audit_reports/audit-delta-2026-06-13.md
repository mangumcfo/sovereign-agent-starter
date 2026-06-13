# Night Watch — Delta Audit — 2026-06-13 (degraded: spend-limit honest run)

**Baseline:** `artifacts/audit_reports/audit-report-2026-06-12.md` (delta) + `audit-report-2026-06-10.md` (last full sweep, 58/100, 57 confirmed).

## Operational note (no silent cap)
- **Friday full sweep STARVED** — `wf_c18e7914-483`: all 7 finders hit the **monthly spend limit** in 24s, 0 confirmed, report null. **Deferred to spend-limit reset** (resume from `wf_c18e7914-483`, do NOT restart — same workflow, cached prefix). Not retried tonight: re-throwing agents at a confirmed-hit limit burns nothing useful (the no-vigilance-theater rule).
- **Nightly delta adversarial pass (Opus subagent) also deferred** — same limit. Instead: the deterministic half ran free (below), and the genuinely-new code already carries GB fidelity traces from this session (not the workflow, but adversarial-grade).

## Deterministic delta (git, free)
- **Committed changes since baseline: ZERO commits.** By the delta's own "zero changes → skip" rule, there is nothing new in *committed* code to audit.
- **BUT large uncommitted surface** — 33 working-tree code changes + new files this session: the 5 R-22 builds (`export_packet.py`, `actions_projection.py`, `qualification_gate.py`, `gate_tiers.yaml`, `ledger.py` lineage/reopen), `thread_channel.py`, `feedback.py` (bell + authz fix), the sittings/parity prep.

## The real finding (NIGHT-WATCH BLIND SPOT — HIGH, process not code)
**The night watch's git-based delta cannot see uncommitted work.** A full session of verified, live R-22 + parity + sittings code is running but uncommitted — which means: (1) a crash loses it; (2) the night watch is blind to it; (3) the next full sweep won't audit it until it's committed. The code itself is **not** unreviewed — GB fidelity-traced all 5 R-22 builds this session (THREAD [262]/[267], full suite **142 green**) + the night-watch [237] caught+fixed the bell authz HIGH. But *verified-and-uncommitted* is its own risk class.
**Fix (Tiger):** commit the session's GB-verified work (R-22 + ledger reopen/lineage + bell authz fix + tests), so it survives, the watch can see it, and the deferred full sweep audits it on resume.

## New CRITICAL/HIGH from code: NONE surfaced
No committed code changed; the live new code carries GB traces (142 green). The one new-surface HIGH this week (bell `@require_owner` gap) was already caught by the [237] delta and fixed. No regressions detectable without the adversarial pass — flagged as deferred, not clean.

## Counts vs baseline
Cannot compute confirmed-vs-baseline this run (sweep starved). Carry-forward: last full = 58/100 / 57 confirmed; the week's fixes (CRITICAL write-fence, 5 HIGHs, 5 R-22) await the resumed sweep to re-score.

∞Δ∞ The watch ran honestly into a wall: it named the wall, named the blind spot behind it, and deferred — rather than pretend a clean night. Commit the verified work; resume the sweep on reset.

---
## UPDATE — targeted delta ran (spend allowed a focused probe, 61k tokens)
A targeted Opus delta on the new surface succeeded (the 84-agent full sweep still re-starves; deferred). Findings, all in this session's new code:
- **MED · correctness · ledger.py:547** — `by_owner()` not order-aware: after the new `reopen()`, a reopened-not-reclosed obligation counts as `closed`; GET `/obligations` per-owner counts lie after any reopen. (The Open Card Parity disease in miniature — a view out-truthing the ledger; the parity harness will guard this class.) Fix: derive `by_owner` from order-aware `replay()`.
- **LOW · tests · ledger.py:439-457** — `reopen()`/order-aware replay untested (the 42-card correction rides on it).
- **LOW · tests · feedback.py:273-275** — bell-route `@require_owner` has no negative (non-owner→403) test.
- **CLEAN** — thread_channel flock-fenced; export_packet/actions_projection Merkle agree; qualification_gate fails-closed (unwired/standalone); R22-3 fails-closed; `_append` write-fence intact; principal-binding holds; deps root-starve guard sound. **No CRITICAL/HIGH; gates + default-deny + Propose→Approve→Execute hold in new code.**
Full 7-dimension sweep still deferred → resume `wf_c18e7914-483` on spend reset.
