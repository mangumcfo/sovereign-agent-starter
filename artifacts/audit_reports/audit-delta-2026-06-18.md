# Night-Watch Delta Audit — 2026-06-18 (HEAD 0ba1396 vs baseline audit-delta-2026-06-17 @ 9510a6c)
*Token-light delta: ONE Opus 4.8 read-only finder, scope = the code/config changed since the 2026-06-17 delta (baseline 9510a6c). Verification only on new findings.*
*Baseline: `audit-delta-2026-06-17.md` @ 9510a6c — Health 79/100, 0 CRIT, 4 HIGH (all CLOSED), 2 LOW.*
*Changed since baseline: commits f03fc3d + 0ba1396 plus working tree. Code/config surface: `routes/feedback.py` ([390] mis-route fix), new `scripts/roadmap_sealed_guard.py` + `roadmap_sealed_baseline.yaml`, tests for both, `SCOUT_CRONTAB.txt`, and 3 deleted scout output packets. Everything else is regenerable data (memory/obligations/artifacts ndjson/json/yaml).*

## Verdict
0 CRIT / 0 HIGH / 0 MED / 2 LOW new; 0 regressions; 1 fixed (crontab LOW#2). **No Tiger escalation needed** — both changed code paths (feedback.py reply-linkage, roadmap_sealed_guard.py) are constitutionally sound and test-covered. All 18 feedback/guard tests pass.

## New findings

### LOW
- **[LOW][code quality] scripts/roadmap_sealed_guard.py:45** — `_titles()` derives `book_id` via `t.get("book_id") or t.get("id") or t.get("title")`. If a title dict has neither `book_id` nor `id`, the *title string* becomes the merge key. Two titles sharing a name would collide in `_sealed_now`/baseline, and a title rename would orphan its baseline entry (read as a silent "drop", failing the guard, or vice-versa masking a real drop). Cross-verified against live code: yes (line 45, key used at 53/74/80/88). **FIX:** require a real id for sealed/published rows — in `_sealed_now`, skip (or `print` a loud WARN for) any sealed row whose `bid` fell through to the title-string branch, so a sealed title without a sovereign id is surfaced, never silently keyed on a mutable label.

- **[LOW][test coverage] tests/test_roadmap_sealed_guard.py:28** — `test_live_roadmap_passes_the_guard` asserts `rsg.main() == 0`, but the live `series_roadmap.yaml`/baseline may legitimately reach the `not base_ids` empty-baseline branch (line 91-93) which *also* returns 0 without proving the drop-detection path. The unit `test_guard_detects_dropped_sealed_title` builds its own dicts and never invokes `main()`, so the `--check` exit-1 drop path in `main()` is not exercised end-to-end. Cross-verified against live code: yes. **FIX:** add a test that monkeypatches `rsg.ROADMAP`/`rsg.BASELINE` to temp files where the baseline lists a sealed id absent from the roadmap, and assert `rsg.main() == 1` — earning the guard's actual failure exit code.

(No new security, performance, dependency, architecture, or constitutional-conformance findings.)

## High-risk targets — clean

**feedback.py reply-to-card linkage (lines 82-150) — verified solid:**
- **principal_id still flows**: the `open()` call (line 129-140) is unchanged in its `owner=current_principal()` binding (line 131). The reply-linkage block (122-127) only mutates `ref`, `category`, `route`, `title` — it never touches `owner`. Ledger mutation still stamps the authenticated principal. `test_feedback_binds_owner_to_authenticated_principal` confirms body-spoofed `owner` is overridden to `KM-1176`.
- **gate model not bypassed**: a reply to an open gate that *would have* batched is re-routed `batch → technical` (line 125-126), i.e. `lane="discrete"`, `material=False`, `next_gate="KM confirm → Tiger implement"`. It becomes *visible discrete work*, not auto-approved and not a new KM judgment gate. It does **not** force `material=True` or skip a gate — it moves the item from invisible-born-approved into a visible Tiger-implement lane. Correct: input is linked + visible, not silently disposed.
- **no silent drop / no auto-approve of KM input**: the re-route is the opposite of dropping — it rescues the input from `batch:mechanical` invisibility. `test_reply_on_open_gate_attaches_and_never_batches` proves `lane != "batch"`, `replies_to == parent.id`, and `ref == card:<parent.id>`.
- **false-attach guarded**: `_open_obligation` (87-94) returns `None` for an absent/closed id (it scans only `open_obligations()`), so a stale/closed `reply_to` is ignored and the packet classifies normally — `test_reply_to_closed_or_missing_id_does_not_attach` confirms `replies_to is None`. A pointer is never written false.
- **no new exception swallowing**: the only `except` in the changed region (line 141, `ValueError → 422`) is pre-existing and surfaces loudly via `route_error`.

**roadmap_sealed_guard.py — verified solid:**
- Exit-coded, no silent failure: missing roadmap → `print FAIL` + `return 1` (63-65); dropped sealed titles → loud per-title `✗` list + `return 1` (94-100). Append-only baseline (`if bid not in base_ids`, line 74) — never removes, matching the doctrine that a sealed title persists forever.
- Read-only in `--check` mode; only `--update` writes, and only the baseline file. No ledger mutation, so no principal_id obligation applies (it is a Tiger-owned tooling guard, not a ledger writer — correctly outside the gate model).
- `_load` tolerates a missing baseline (returns default `{}`) and the empty-baseline case prints an init NOTE rather than crashing.

## Regressions
None.

## Fixed-since-baseline
- **LOW#2 (crontab `;`→`&&`) — FIXED.** `scripts/cron/SCOUT_CRONTAB.txt:13` now chains `build_book_code_tree.py && scout_run.py` (was `; `). If the tree build fails, scout_run no longer runs against a stale/half-written tree. Bonus hardening folded in: the first command's output now also tees to the dated cron log (`>> artifacts/scout/cron-$(date ...).log 2>&1`) instead of `>/dev/null`, so a tree-build failure is now captured rather than discarded. Cross-verified against live file: yes.
- **Deleted scout packets — clean.** `artifacts/scout/packets/2026-06-16/{01_cfos_finance,02_harnessing_ai,05_crypto}.yaml` are regenerable nightly scout *output* (the cron run re-derives them). No code globs that directory by path; the `01_cfos_finance` tokens in `coherence_*.py`/`playbook_loader.py` are stable book/playbook ids, not references to the deleted files. No dangling refs.

## Test run result
`python3 -m pytest tests/test_node_api_feedback.py tests/test_roadmap_sealed_guard.py -q` → **18 passed**. The new code paths are exercised: `test_reply_on_open_gate_attaches_and_never_batches`, `test_plain_mechanical_still_batches_when_no_reply_to`, and `test_reply_to_closed_or_missing_id_does_not_attach` cover the three reply-linkage branches; `test_sealed_now_extracts_published_and_sealed`, `test_guard_detects_dropped_sealed_title`, and `test_live_roadmap_passes_the_guard` cover the guard.

## Counts
**NEW: 0 CRIT, 0 HIGH, 0 MED, 2 LOW | REGRESSIONS: 0 | FIXED: 1**

---
*Night watch 2026-06-18 — one finder, verification-only, read-only. Counts logged to GB meta-cylinder.*
