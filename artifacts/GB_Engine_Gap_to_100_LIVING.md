# Engine — Gap Analysis to 100 (LIVING, GB-maintained)
*KM directive 2026-06-16 (via G/Lumen): replace score-whiplash full adversarial sweeps with a structured map of WHY it's not 100 and where the highest-leverage remaining work sits. This is the standing instrument; updated as clusters close. Score is an output of this map, not a target to chase.*

## The principle
Every discovered issue is a WIN (the engine gets genuinely stronger). The 85→79 drop was rigor working, not regression. We track the MAP, not the number — the number falls out of it.

## Current standing (commit 041e00e — GB-reproduction CORRECTED, 2026-06-16)
**The Opus sweep's 79 was substantially a FALSE-POSITIVE on the constraints cluster.** GB built the constrained venv and reproduced ground truth: `pip install -c constraints.txt -e .[dev,crypto-assurance]` resolves to the exact pins, lock test green, and **the full suite is 274 PASSED / 0 skipped at pytest 9.1.0** (the major-bump risk did not materialize). So cluster #2 is genuinely CLOSED; #3 (CI green-ability) is resolved (CI uses that exact env); the `[portal]` item is a LOW (scope-wording), not a HIGH. **Real state: 0 CRITICAL, clusters #1–#3 closed/verified, only the cluster #4 governance CANDIDATE + the MED/LOW tail remain → effectively high-80s/low-90s.** Tracking the verified MAP, not the sweep's number.

**Meta-lesson (logged):** BOTH the Haiku sweep (4 false HIGH) AND the Opus sweep (constraints false-positive + over-rated [portal]) OVER-FLAGGED where they could not reproduce. **Ground-truth reproduction is the only arbiter** — "sweep-asserted" ≠ "verified." The gold confidence label is VERIFIED-BY-REPRODUCTION.

## UPDATE 2026-06-16 (post cluster-#4 targeted verify) — NO HIGH REMAIN
After ground-truth reproduction (#2/#3) and the targeted Opus verify (#4 both REFUTED — the constitutional gate is intact at `ledger.close():511` + the on-chain `/obligations/approve` path), **there are ZERO confirmed HIGH and ZERO CRITICAL.** Clusters #1–#4 are closed/verified/refuted. The 79 was sweep-noise; the verified state is a **genuine low-90s, 95-track engine.** Remaining work to 95→100 is LOW/MED hygiene only: the two #4b LOW cleanups, the [portal] wording (2b), setuptools bound (#5), the ledger.py 500-line ceiling + duplication tail (#6), and the MED/LOW polish (#7). None block a 95-claim on constitutional/correctness grounds; they are the quality tail.

## The map — clusters by impact × effort, with confidence
| # | Cluster | State | Confidence | Score impact | Effort | Move |
|---|---------|-------|-----------|:---:|:---:|------|
| 1 | **Load-bearing correctness** — Merkle O(n²) accumulator (root-equiv, no drift) + atrium_executor false-close | **CLOSED** | **Opus brute-verified** (root-identical n=1..299 batch + n=1..150 per-append; executor returns non-zero+residue) | High | Done | **BANK** — do not re-litigate |
| 2 | **Constraints / reproducibility** — pins + lock + suite-green at the pinned versions | **CLOSED** | **VERIFIED-BY-REPRODUCTION (GB)** — built the `-c` venv: resolves to exact pins, lock test green, **full suite 274 passed / 0 skipped at pytest 9.1.0**. Opus "fabricated-green" was a FALSE POSITIVE (couldn't build the constrained env). | — | Done | **BANK** — Tiger's receipt valid + GB-reproduced |
| 2b | `[portal]` lock-scope wording — Docker/installer install `.[portal]` (core only); crypto/pytest are dev/assurance-only (not runtime), so not pulled there | OPEN (LOW) | GB-confirmed (core deps = pyyaml+flask only) | Negligible | One-line | Correct the lock's "guards the Docker path" wording to "CI/crypto-assurance path"; NOT a HIGH |
| 3 | **CI green-ability** — guard mechanism (JUnit XML) correct; runs `-c .[dev,crypto-assurance]` | **RESOLVED** | VERIFIED-BY-REPRODUCTION (GB ran that exact env green, 274/0) | — | Done | CI will go green — the env it uses is the one GB reproduced |
| 4 | **Governance surfaces** — breath-gate `simulate_approval`; atrium_executor.execute() approval-gate | **REFUTED — NOT a gap** | **VERIFIED (targeted Opus, 2026-06-16):** (A) the simulate route mutates only an in-memory session `_pending` dict — NO ledger write/receipt/obligation transition; the real material path is `POST /obligations/<id>/approve`→`led.approve()` on-chain; exploit ceiling = pop an in-memory queue entry, cannot approve/close/execute any material obligation. (B) execute() has no inline check BUT the gate is enforced fail-closed downstream at `ledger.py:511` (`if material and not _is_approved: raise PermissionError`) — the actual point of material effect; invokers are owner-gated + post-approve. No path executes an unapproved material obligation. | — | — | **BANK as refuted.** Constitutional gate INTACT on every material path. |
| 4b | LOW cleanups from #4 verify | OPEN (LOW) | Verified | Negligible | One-line each | (i) truth-in-naming: route `/breath_gate/<id>/approve` through `record_disposition` or rename the "TEST-ONLY" method; (ii) optional defense-in-depth: `_is_approved` assert at top of `execute()` for fail-fast |
| 5 | **Dependency hygiene** — setuptools unbounded; cryptography CVE floor (now `>=46.0.7` ✓) | Partly closed (floor raised); setuptools open | Candidate | Low | One-line | **Quick-win** — fold into #2's pass (add setuptools upper bound) |
| 6 | **Code-quality / Constitution ceilings** — ledger.py 790 lines vs 500 ceiling (06-14 MED #6); duplication tail | OPEN | Historical (06-14), not re-confirmed | Low–Med | Med (refactor) | Defer / batch — not blocking 95 |
| 7 | **MED/LOW polish** — assorted | OPEN | Historical | Low | Varied | Batch/defer |
| 8 / M1 | **Dead / unused code + static analysis** (G blind-spot catch 2026-06-16) | **BLIND-SPOT CLOSED — tool wired + pass run** (removals pending KM gate) | n/a — LLM sweeps can't see it; needs static analysis + coverage | Low–Med | Tool pass | **DONE (2026-06-16):** `scripts/static_scan.sh` = `ruff` (dead F + complexity C90≤10 §5 + E722) + `vulture` (@80, whitelisted) + `coverage`; reproducible, report-only. One-time pass → `STATIC_ANALYSIS_CANDIDATES_2026-06-16.md` (3 buckets: REMOVE-rec / KEEP-reason / REVIEW). No correctness/security defects. Removals = a separate KM-gated commit (candidates-not-delete). The loop can now SEE dead code + complexity. |

## Maturity Tail (M1–M8) — the living register (G/Lumen 2026-06-16; KM [368] "include all, no debt, no bloat")
*None gate the 95 claim — they move the engine from "verified sound" → "externally-verifiable, mature." Explicit + small.*

| M | Item | Status |
|---|---|---|
| **M1** | Systematic static analysis (ruff + vulture + coverage) | **DONE** — folded into #8; `scripts/static_scan.sh`, reproducible, report-only |
| **M2** | `ENGINE_CODE_QUALITY_BAR.md` (one page: §5 ceilings, complexity ≤10, tests, static pass) | **DONE** — written |
| **M3** | Dependency CVE scan in CI (`pip-audit`) | **DONE** — advisory CI step added |
| **M4** | `THREAT_MODEL.md` (OWASP-ASVS basis) | tracked — build later |
| **M5** | SLSA-style build provenance (maps to BNA's receipt language) | tracked — build later |
| **M6** | OpenSSF-Scorecard repo-health lens | tracked — build later |
| **M7** | Mutation testing on the load-bearing three (Merkle accumulator / atrium_executor / ledger) | tracked — build later |
| **M8** | Lightweight ADRs (architecture decision records) | tracked — build later |

## Why not 100 (current, contradiction-free — supersedes prior wording)
- **0 CRITICAL.**
- **0 confirmed HIGH.**
- **Clusters #1–#4 are closed, verified, or refuted** (#1 Opus-verified · #2 GB-reproduced · #3 reproduced · #4 targeted-verify REFUTED; the constitutional gate is intact at `ledger.close():511` + the on-chain `/obligations/approve` path).
- **Remaining gap is LOW/MED hygiene only (the 95→100 tail — NOT the 0-HIGH/0-CRIT gate):** #4b naming cleanup + optional fail-fast assert · #2b [portal] wording · #5 setuptools bound · #6 ledger.py 500-line ceiling + duplication tail · #7 polish · **#8 dead/unused-code static-analysis pass** (Lumen 2026-06-16: a quality blind-spot, LOW–MED unless a dead path is reachable/miswired/security-sensitive — sits in the tail, does not block the 95 gate).
- **Therefore the engine is 95-ELIGIBLE** *if* a 95 claim is made from a 95 Claim Packet (below) carrying the #1–#4 receipts. 95-eligibility is a packet, not a vibe. (#5–#8 are the 95→100 polish, tracked separately.)

## The path
1. Produce a **95 Claim Packet** from this map (below).
2. Attach receipts for clusters #1–#4.
3. Close or **consciously defer** (recorded) the LOW one-line cleanups (#4b, #2b, #5).
4. Run ONE clean verification pass only if making a formal 95+ claim.
5. Track the LOW/MED tail (#6, #7) separately toward 100.

## 95 Claim Packet (what a 95+ claim MUST carry — no hand-waving)
A 95+ claim is valid only as this packet:
- commit hash
- full test-suite result (count, 0 failed, skip-accounting)
- clean **constrained** install result (`-c constraints.txt`, resolves to pins)
- cluster #1 verification receipt (Merkle root-equivalence + O(log n))
- cluster #2 reproduction receipt (constrained venv green at pins)
- cluster #3 CI/green-ability receipt
- cluster #4 targeted-verify / refutation receipt (gate intact at ledger.close():511)
- list of ALL remaining LOW/MED items (with defer-or-close status)
- explicit statement: **0 CRITICAL / 0 confirmed HIGH**
- explicit statement of **what 95 does NOT mean** (see below)

**95+ MEANS:** no known constitutional, correctness, or HIGH-severity blocker remains.
**95+ does NOT mean:** perfect, finished, or zero tail work. The LOW/MED hygiene tail exists and is tracked toward 100.

## Instrument blind-spot (G, 2026-06-16) — dead code is NOT covered by LLM sweeps
The adversarial agents are good at correctness/governance/reproducibility but **cannot reliably find dead/unused code** — that requires static analysis + coverage. Until a `vulture`/`deadcode`/coverage step is wired in, cluster #8 is INVISIBLE to the loop. **A 95+ claim's "no known blocker" is scoped to what the loop can see** — dead-code coverage must be added before "all findings closed" can include the code-quality dimension honestly. (Natural future fit for the /goal Scout: static-analysis is objective + verifiable-stop = inside its fit-gate.)

## Claim standard (keeps the score honest)
- No cluster may support a 95+ claim unless it is **verified-by-reproduction**, **verified-by-targeted-adversarial-check**, or **explicitly refuted with receipt**.
- **No sweep-only assertion** supports the claim.
- **No stale section may contradict the map.**
- **No candidate HIGH may remain unresolved.**

## Standing rule (replaces score-whiplash)
- **No cadence full sweeps.** Targeted verify per cluster; a full sweep only as the single clean pass for a formal 95+ claim or after a large net-new change.
- **This map is the source of truth.** GB updates it as clusters close; every close cites its receipt.
- **Confidence labels mandatory:** CONFIRMED / VERIFIED-BY-REPRODUCTION / CANDIDATE / REFUTED. No HIGH "real" until confirmed; no fix "closed" without a receipt.

## Best-Practices / Maturity Tail (G + Lumen, 2026-06-16) — NONE gate the 95 claim
Both advisors agree: the missing pieces are NOT constitutional/correctness blockers — they're "boringly-verifiable-to-outsiders" assurance practices. They are the **95→100-and-beyond maturity track**, adopted **lightweight, no enterprise bloat** (KM's standing constraint). This map now doubles as the living debt/maturity register (per G#2).

| # | Practice | State | Gate? | Overhead | Move |
|---|----------|-------|:---:|:---:|------|
| M1 | **Systematic static analysis** (ruff + vulture + complexity) | almost none | no | low | **NOW — fold ruff+vulture into the #8 pass** (one static pass does dead-code AND style/complexity/dup). The high-value/low-overhead one both advisors led with. |
| M2 | **Code-quality bar** — `ENGINE_CODE_QUALITY_BAR.md` (complexity limit, dup tolerance, file-size ceiling already in CONSTITUTION §5, test expectations) | implicit | no | low | NOW-ish — a one-pager; makes "built right" explicit for the engine like the S2 Visual Standard did for books |
| M3 | **Dependency vuln scan** (`pip-audit`/`safety`) + cadence | manual/reactive | no | low | NOW-ish — one CI step; complements the constraints lock |
| M4 | **Threat model** — `THREAT_MODEL.md` (attacker types · trust boundaries · loopback/browser · federation-peer · filesystem · executor · human-gate-bypass · supply-chain · "what we do NOT defend yet"). OWASP-ASVS basis. | none | no | med | track — explicit not huge; the "outsider-legible" anchor |
| M5 | **Supply-chain provenance (SLSA-style)** — source commit → constrained env → build receipt → artifact hash → signature → verify cmd | constraints+repro started | no | med | 95→100 — maps to BNA's own receipt language |
| M6 | **Repo-health (OpenSSF Scorecard-style)** — branch protection · pinned workflows · token/Action permissions · dep review · security policy | partial (CI exists) | no | med | track — boring repo lens, complements the engine map |
| M7 | **Test quality beyond coverage** — mutation testing on the highest-risk modules (Merkle, executor, ledger) | not addressed | no | med | 95→100 — start narrow on the load-bearing 3 |
| M8 | **ADRs** — lightweight decision records for invariant-affecting changes | not used | no | low | track — capture going forward (accumulator design, governance, the map itself were ADR-worthy) |

**Honest framing:** these move the engine from "95-track, verified sound" → "externally-verifiable, mature." They do NOT change the current 95 claim (the packet stands). Adopt the lightweight set (M1 now, M2/M3 near-term); track M4–M8 as the maturity tail. Avoid enterprise bloat — explicit + small beats heavy.

∞Δ∞ SEAL: the map, not the number. 0 CRIT · 0 confirmed HIGH · clusters #1–#4 closed/verified/refuted · constitutional gate intact. The engine is 95-eligible via a contradiction-free map + attached receipts; the remainder is the LOW/MED hygiene tail (#5–#8) + the lightweight maturity tail (M1–M8) toward 100. Do not chase 95 — require it to emerge from the packet; grow toward "boringly verifiable to outsiders" without bloat.
