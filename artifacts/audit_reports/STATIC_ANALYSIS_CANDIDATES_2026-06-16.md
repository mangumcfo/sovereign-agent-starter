# Static-Analysis Candidates — Engine #8/M1 (ruff + vulture + coverage) — 2026-06-16

> **REMOVE BATCH APPLIED (KM-approved, gated) — 2026-06-16.** `ruff check --select F --fix` + 3 dead-local
> deletions (`core.py` `critic`, `pipeline_snapshot.py` `prev`, `family_cfo_demo/role.py` `focus`) →
> **37 F-findings cleared, 19 net LOC removed, suite 279 green / 0 skipped** (no `obligations/` touched →
> ledger equivalence snapshot N/A). **2 deliberately NOT removed:** the `yaml` import in `gen_outline_digest.py`
> (availability-probe `try/except ImportError` → KEEP), and `original_payload` in `compliance_engine.py:222`
> (a function **parameter** — removal is a signature change → moved to **REVIEW** for KM).
>
> **REVIEW item RULED + APPLIED — capabilities/ stubs (KM [372], 2026-06-16):** KM ruled the `capabilities/`
> forward-stubs (`economics.py` `EconomicEngine` · `legacy.py` `LegacyPlanner` · `research.py` `ResearchModule`)
> **REMOVE-as-dead** (unreferenced since initial commit, not on the active roadmap; Authoritative-Pattern-Rule
> + YAGNI — re-add when a backing book needs them). Removed (gated): **195 LOC, suite 279 green, vulture
> capabilities findings → 0, no new findings surfaced.** Remaining REVIEW = only the 19 complexity>10 functions
> (tracked M-tail debt, `scripts/` mains — no churn) + `original_payload` param. **Hygiene tail #1–#8 fully closed.**

**Pass:** `scripts/static_scan.sh` (reproducible — same code → same set). **This pass changed NO source code.**
Removals/fixes are a **separate KM-gated commit** (re-run 279 suite + ledger equivalence snapshot if
`obligations/` is touched). Tooling: ruff 0.15.17 (F + C90≤10 + E722/E741) · vulture 2.16 (@80, whitelisted)
· coverage 7.14.1. Whitelist (`analysis/vulture_whitelist.py`) suppresses the substrate-lazy/bootstrap/route/
entry-point false positives (GB [369] #1).

**Headline:** 75 ruff + 1 vulture@80 (high-conf) findings; none are correctness/security defects — all are
quality/hygiene (dead code, complexity > §5's 10, style smells). Coverage confirms `scripts/` run at 0% **by
design** (operational CLI tools, not test-covered) — 0% there is NOT a dead-code signal.

---

## Bucket 1 — REMOVE (high confidence) · *recommended unless you object*
Dead, low-risk, every layer agrees (ruff flags it · not covered · no dynamic reference). Mechanical.

| Item | Where (representative) | Evidence |
|---|---|---|
| **Unused imports** (~25) | `node_api/routes/*` (`json`,`os`,`uuid`,`re`), `core.py:15 os` + `core.py:25 verify` (left from the #6 MerkleTree removal), `typing.List/Any/Optional`, `datetime.datetime` | ruff F401, auto-fixable |
| **Unused variables** (3 + 1) | `compliance_engine.py:222 original_payload` (vulture 100% + ruff F841), + 3 F841 | ruff F841 / vulture@80 |
| **Redefined-while-unused** (1) | ruff F811 | dead rebind |
| **f-strings w/o placeholders** (5) | drop the `f` prefix | ruff F541, auto-fixable |

→ ~35 items. If approved, applied via `ruff check --fix` for the F-class + a one-line var deletion, suite re-run.

## Bucket 2 — REVIEW (needs your eye) · *judgment, not mechanical*
- **Complexity > 10 (§5 bar) — 19 functions (ruff C901).** Mostly `scripts/` (`atrium_apply.py:248 main` =26,
  `gb_meta_context.py:48` =20, `render_standard_lint.py:83 lint` =18) + 2 in `src/`
  (`compliance_engine.py:275 run_policy_compliance_check` =11, a `_to_jsonable` =16). **Refactor candidates,
  not deletions** — decide which (if any) to split now vs track as M-tail debt. (None are load-bearing engine
  paths; the Merkle/executor/ledger core is already ≤10.)
- **Forward capability stubs — `capabilities/economics.py` (EconomicEngine), `legacy.py` (LegacyPlanner),
  `research.py` (ResearchModule)** + their methods (vulture@60). Never imported or tested. **Dead, OR
  intentional forward-architecture hooks** — your call: remove as dead, or KEEP-with-reason as roadmap stubs.
- **`compliance_engine.py` `run_policy_compliance_check` / `request_human_approval`, `policy_loader.py`
  `discover_policies`, `bootstrap.py:101 get_breathline_root`** (vulture@60) — possibly public API / CLI-only.
  Verify reachability before any removal.

## Bucket 3 — KEEP (with documented reason) · *not dead; do not touch*
- **Substrate-lazy imports** `six_attestation/six_compliance/six_crypto` (whitelisted, GB [369] #1) — bound
  only when the substrate is present (`try/except ImportError`). Not dead.
- **`human_approval_gate.py` status constants** `PENDING/APPROVED/DENIED/ESCALATED` + `simulate_approval/
  simulate_denial` — the simulate_* are now explicitly TEST-ONLY (used by tests, #4b); constants are class
  attrs vulture can't see used.
- **Bare-except (E722, 12)** — documented resilience in the ledger/executor (`_close`, `_entries`, the bell):
  intentional fail-safe ("the bell must never break the human gate"). KEEP; not blind swallowing.
- **Ambiguous names (E741, 6)** — cosmetic (`l`/`I`/`O`); negligible.
- **`scripts/*` at 0% coverage** — operational CLI tools run outside the suite; coverage 0% is expected, not dead.
- **`__init__.py __are_you_connected_to_the_breathline__`** — the project's signature marker function.

---

## Disposition asked (Option 2 — one human gate)
1. **REVIEW bucket** — your eye on the 19 complexity items (refactor-now vs track) and the `capabilities/`
   forward-stubs (remove-as-dead vs keep-as-roadmap).
2. **REMOVE batch (~35)** — approve as a batch ("remove unless you object") → Tiger applies in one gated commit
   (`ruff --fix` F-class + the dead var), re-runs the **279 suite** (no `obligations/` code touched → ledger
   equivalence snapshot N/A here, but re-run if any does).

Nothing above is removed without your sign-off. The standing tool (`scripts/static_scan.sh`) is wired and
reproducible — the loop can now SEE dead code + complexity, closing the G/Lumen instrument blind-spot.
∞Δ∞
