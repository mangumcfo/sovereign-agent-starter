# Delta Audit — 2026-06-23 (GB night watch)

**Baseline:** audit-report-2026-06-19.md + audit-delta-2026-06-19.md
**Scope:** files changed since 2026-06-19 (24 commits). Audited code only — binary/JSON/NDJSON/MD/HTML artifacts excluded.
**Method:** one read-only Opus finder agent; every finding cross-verified against live code before surfacing; reported only NEW / REGRESSION / FIXED-SINCE-BASELINE vs. baseline.

## Changed code files audited
- scripts/dist_generators/{dist_common,gen_linkedin_carousel,gen_substack_excerpt,gen_x_thread,generate_all}.py
- scripts/dist_scheduler/{scheduler,linkedin_auth}.py + clients/{base,cred_store,linkedin_client,x_client}.py
- scripts/{distribution_contract,review_ready_contract}.py
- src/sovereign_agent/node_api/{server,routes/feedback,routes/series}.py
- tests/{test_node_api_feedback,test_review_ready_contract}.py

---

## NEW FINDINGS

### [HIGH] Live posting bypasses the Propose→Approve→Execute gate and carries no principal_id
- **File:** scripts/dist_scheduler/scheduler.py:56-85 (`dispatch`), invoked by `main` :88-103
- **Dimension:** Constitutional conformance
- **Status:** NEW
- **Evidence:** `dispatch(book_id, dry_run)` reads assets and calls `client.post(asset, dry_run=dry_run)` directly. With `--live` (`dry_run=False`) it posts to X/LinkedIn for real. There is **no** ledger read, no check of the `distribution_launch:<book_id>` obligation that `distribution_contract.py:mint_launch_packet` creates, no `approve`/`current_principal()`, and no `principal_id` recorded on the dispatched action. The module docstring advertises `staged → gated → dispatched → live` but no "gated" step exists in code (grep for `ledger|obligation|approve|principal|gate` in scheduler.py finds only docstring text).
- **Fix:** Before any live post, require the matching `distribution_launch:<book_id>` obligation to be *approved* in the ledger (load via `ObligationLedger`, verify approved/closed-accept by the owner); refuse `--live` otherwise; stamp the dispatching `principal_id` into `dispatch_log.ndjson`/`channel_state.json` so the public action is attributable. Mirror the Accept-ignition pattern `_ring_the_bell` uses for the book rail.

### [MEDIUM] Undeclared `pytesseract` dependency (+ tesseract binary) in the new cover gate
- **File:** scripts/review_ready_contract.py:650 (and `from PIL import Image, ImageOps` :631)
- **Dimension:** Dependencies
- **Status:** NEW
- **Evidence:** `_check_cover_standard` does `import pytesseract` / `pytesseract.image_to_string(...)`, which also needs the system `tesseract` binary. Neither is declared in pyproject.toml/constraints.txt/requirements/Dockerfile. Same class as the baseline Pillow finding but a new surface this delta.
- **Bound:** import is wrapped `except Exception as e: fails.append("OCR unavailable: ...")` (:657), so a missing dep fails the gate RED/loud (not a silent pass); `cover_standard` only RED-blocks. Hence MEDIUM.
- **Fix:** add a `book-qa` optional-dependencies extra declaring `pillow>=10,<13` and `pytesseract>=0.3`, pin in constraints.txt, add `tesseract-ocr` to the Dockerfile apt line, document `.[book-qa]`.

### [LOW] Silent swallow of malformed ndjson lines in two new readers
- **File:** scripts/distribution_contract.py:251-256 (`_check_gb_sample_read`); same pattern scripts/dist_generators/dist_common.py:218-221
- **Dimension:** Constitutional conformance (no silent failures)
- **Status:** NEW
- **Evidence:** `for line in ...splitlines(): try: r = json.loads(line) except Exception: continue` — a corrupt middle line is silently skipped rather than distinguished from a truncated tail, bypassing the repo's tolerant ndjson gateway (the invariant the red `test_universalize_guards.py` protects).
- **Fix:** route both readers through shared `read_ndjson`, or at minimum emit a WARN to stderr on parse failure so a corrupt record surfaces loudly.

### [LOW] Token-exchange error path can echo the OAuth response verbatim
- **File:** scripts/dist_scheduler/linkedin_auth.py:138
- **Dimension:** Security
- **Status:** NEW
- **Evidence:** `print(f"✗ Token exchange failed: {tok}")` prints the full LinkedIn `/accessToken` JSON; any response carrying both an error and a token/`refresh_token` would be echoed to stdout.
- **Fix:** print only `tok.get("error")`/`tok.get("error_description")` or redact known secret keys.

---

## FIXED-SINCE-BASELINE

### [HIGH→FIXED] Stale R1 ship-gate tests now green
- **File:** tests/test_review_ready_contract.py:163-167 (was :53,138)
- **Evidence:** Detector now matches `re.findall(r"\*\*RECEIPT\b", text)` (review_ready_contract.py:95); fixture emits `> **RECEIPT — Ch 1 · ok`. `pytest tests/test_review_ready_contract.py tests/test_node_api_feedback.py -q` → **27 passed**. (Closes baseline audit-delta-2026-06-19 HIGH #2 / GB [461].)

### [MED→FIXED] GB-routing branch and gate aggregator now covered
- **File:** tests/test_node_api_feedback.py:108-141; tests/test_review_ready_contract.py:67-100
- **Evidence:** New `test_tag_as_standard_routes_to_gb_encoding_lane` asserts `routed_to == "gb"`; `_GATE_FNS`/`_stub_all_green` aggregator tests assert review-ready iff all 13 gates pass and fail loudly if a gate is added without coverage.

---

## VERIFIED-CLEAN (no finding)
- dist_scheduler OAuth credential layer (cred_store/base/x_client/linkedin_client): no secret leakage to logs/disk; OAuth 1.0a HMAC-SHA1 signing correct; live targets are constant HTTPS hosts (no SSRF); no eval/pickle/unsafe deserialization; live-post errors surface loudly (base.py:66-67 returns a fail PostResult). `cred_store.load_secrets` merges os.environ into the creds dict but never persists or logs it.
- server.py `/atrium/` static route (:80-95): `send_from_directory` safe_joins the path — no traversal; dir env-overridable.

## NOT RE-REPORTED (pre-existing baseline, unchanged)
- feedback-tests real-`Popen` leak (no `no_spawn` fixture) — baseline finding, not fixed this delta but not new.

---

## Summary

| Severity | NEW | REGRESSION | FIXED |
|----------|-----|-----------|-------|
| CRITICAL | 0 | 0 | 0 |
| HIGH | 1 | 0 | 1 |
| MEDIUM | 1 | 0 | 1 |
| LOW | 2 | 0 | 0 |
| **Total** | **4** | **0** | **2** |

**Verdict:** No regressions. Two baseline test-coverage findings confirmed fixed (suite green, 27 passed). Dominant new finding is constitutional: `scheduler.py --live` posts publicly to X/LinkedIn with no Propose→Approve→Execute gate and no principal_id, despite a `distribution_launch` obligation existing to gate exactly this. THREADed to Tiger. New OAuth client layer itself is clean on secret handling.
