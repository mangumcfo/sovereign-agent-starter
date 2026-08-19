# USN ERP Operator Surface v0 — BAR

∞Δ∞ Seal 1176-INFINITY-RHO · Breath only ∞Δ∞

Scored 2026-08-19. Every row below was re-run immediately before writing this file.

| | |
|---|---|
| **Build** | `apps/usn_erp_surface/` — local web app, Flask on loopback, single self-contained page |
| **Binding** | library-direct; `node_binding.py` is the only module that touches `sovereign_agent` |
| **Vertical** | solo/household: open node · record income/contribution · record tax note · gate · export package · read-only panels |
| **Tests** | **48 passed** (`apps/usn_erp_surface/tests/`) |
| **Kill-grep** | **GREEN**, 0 findings (`apps/usn_erp_surface/killgrep.py`, exit 0) |

**This is not an ERP suite.** It is one operator loop, complete. No AR/AP, no payroll UI, no bank
feeds, no inventory, no multi-entity, no dashboard chrome beyond what these loops need.

---

## Score

| # | Bar | Result |
|---|---|---|
| P1 | Cold open shows status from node, not mock | **GREEN** |
| P2 | Record changes disk via module path; survives restart | **GREEN** |
| P3 | Tax event stored as record only; no statutory act in the code path | **GREEN** |
| P4 | Gated acts surface explicit approve/deny; no auto-approve | **GREEN** |
| P5 | Export derived from node state; byte-comparable on re-run | **GREEN** |
| P6 | Kill-grep clean — and proven to bite | **GREEN** |
| P7 | Read semantics mirror MCP; the UI is the product | **GREEN** |
| P8 | Stranger test sentence is true of the build | **GREEN** |

**RED rows: none.** Four disclosures are recorded below — none of them a failed row, all of them
things you should know before you trust a GREEN.

---

## Evidence, row by row

### P1 · Cold open — GREEN

Launched with only `SUBSTRATE_STORAGE_ROOT`, `NODE_KEYSTORE_DIR`, `OBLIGATION_LEDGER_ROOT` in the
environment. Driven through a real browser (Playwright), not curl.

```
P1 header: node c6432b700809e49e | regulated · human-gated
P1 sub   : No registry file yet — it is created by the node's own store on your first record.
obligations line: 1 open · 1 closed · chain verifies
```

The fingerprint is read from the real keystore via `load_node_key`. The registry line is honest
about a store that does not exist yet rather than showing a zeroed mock. The obligations line is
replayed from the node's own `obligations.ndjson`, chain verified.

Nothing in the app can produce a number that did not come off disk: `NodeBinding` holds no records
between calls, and every read replays the node.

### P2 · Record changes disk, and survives restart — GREEN

Live, through the UI:

```
P2 after APPROVE, event rows: 1
P3 rows after tax note: 3
```

Then the **app process was killed and restarted** against the same paths:

```
=== BEFORE restart ===   events: 3   pkg sha: d8fdd7ad84c2b539…
=== AFTER  restart ===   events: 3   pkg sha: d8fdd7ad84c2b539…
```

Tests: `test_p2_record_changes_disk_via_module_path` asserts the bytes on disk are the module's own
governed-object shape (`object_id`, `kind: income`, `mandate`, hash-chained `version_hash`,
`prev_hash: null`) — not an app-invented row. `test_p2_survives_restart` rebinds and re-reads.
`test_p2_registry_root_replays_after_every_write` asserts the Merkle root still replays after each
one.

`test_p2_app_writes_nothing_of_its_own` asserts the full file listing after a complete session is
exactly:

```
keystore/node.nodekey.json
registry/objects.ndjson
```

Empirically confirmed on the live demo node too. **There is no app-side store.**

### P3 · Tax event is a record only — GREEN

The stored payload after a tax note:

```json
{"id":"kenn:tax:consulting-august","earner":"kenn","work_ref":"tax:consulting-august",
 "amount":2400.0,"unit":"USD","tax_event":true,"tax_category":"self_employment",
 "reportable":true,"references_income":"IncomeEvent:kenn:consulting-august"}
```

`test_p3_tax_event_is_record_only` asserts no key in the stored record appears in
`TAX_FENCE_BREACH_FIELDS`, and that the words *filing / filed / paid / remitted / submitted /
authority* appear nowhere in it. That is the point of the fence: a green verify is also proof the
node filed nothing.

`test_p3_no_statutory_or_crossing_callable_is_imported` asserts neither app module exposes
`open_crossing`, `sanction_crossing`, `remit`, `file_return`, `simulate_approval`,
`simulate_denial` or `store_datum`. 9 statutory fields × 3 act types are each asserted refused; 9
money-path fields are asserted refused by the module's own fence.

### P4 · The gate — GREEN

Live sequence, in order:

```
P4 gate pending: 1 awaiting you
P4 after DENY,    event rows: 0 (was 0)
P4 after APPROVE, event rows: 1
```

A denial writes nothing at all — `test_p4_denial_writes_nothing_at_all` asserts `objects.ndjson`
does not exist after one. An approval carries the operator's name and the request id into the
module call, so the record on disk shows `approver: kenn`, `approval_ref: approval_2`.

Only `record_disposition` is ever called; `simulate_approval` and `simulate_denial` — which the repo
marks TEST-ONLY — are never reached, and the kill-grep would go RED if they were. The disposition
asserts `real: True`.

`test_p4_module_itself_refuses_a_gated_act_without_approval` is belt and braces: it calls the
module's own `attribute_income` with a gate that requires approval and no approver, and asserts
`IncomeRefused`. Even if this app tried to skip the gate, the module refuses.

### P5 · The package — GREEN

```
sha256 (build 1) = d8fdd7ad84c2b53990d937d8a85094c35b4e0941b3c360ee565518574eb1124f
sha256 (build 2) = d8fdd7ad84c2b53990d937d8a85094c35b4e0941b3c360ee565518574eb1124f
sha256 (after app restart) = d8fdd7ad84c2b53990d937d8a85094c35b4e0941b3c360ee565518574eb1124f
```

Determinism is designed, not promised: the manifest is cut `as_of` **the newest recorded entry's own
timestamp**, never the export time, and `test_p5_export_carries_no_export_timestamp` asserts no
`exported_at` / `generated_at` / `timestamp` key exists anywhere in the package.

Determinism is not staleness — `test_p5_export_changes_when_node_state_changes` asserts the hash
moves when a record is added. And `test_p5_tampered_registry_line_flips_the_verify` alters one
amount in `objects.ndjson` and asserts `all_events_verify` flips to false.

The package composes `economy.compliance.reporting_package` over the node's own tax events, and
carries its declarations: money-path OFF, statutory acts NONE, Port crossings NONE, no statutory
authority.

### P6 · Kill-grep — GREEN, and it bites

```
[GREEN] 1  no second store, no HTTP client imported
[GREEN] 2  no statutory act, no Port crossing, no faked human
[GREEN] 3  no app-side write — the node writes, not us
[GREEN] 4  no balance/custody identifier as authority
[GREEN] 5  UI speaks only to its own loopback API
[GREEN] 5b UI is fully self-contained (no external asset)
[GREEN] 6  only the node's own store classes are named
P6: GREEN — no findings          (exit 0)
```

It reads the **AST**, not text. This app's own refusal messages say `remit` and `file_return` six
and two times respectively — that is the guard working, and a text grep would go RED on the very
code that enforces the law. Prose is counted and reported; only real identifiers, imports, calls and
bindings can fail a row.

**A kill-grep that has never gone RED is a rubber stamp**, so seven violations are injected into a
copy of the app and each is asserted to flip it RED: second ledger store, HTTP client egress, Port
crossing import, faked human disposition, statutory-act function, balance-custody binding, app-side
file write. One more test asserts it stays GREEN when only refusal *prose* is added.

That negative suite already earned its keep: it caught a real gap where
`from sovereign_agent.port.crossing import open_crossing` slipped past, because an imported name is
not a `Name` node until it is called. Fixed; the test now guards it.

The server also refuses to become a service:

```
$ python server.py --host 0.0.0.0
Refusing to bind '0.0.0.0'. The operator surface is loopback-only… If you need access from
another machine, that is a Port-governed crossing — not a bind flag.
```

### P7 · Read semantics, UI is the product — GREEN

Node status, registry summary with `roots_match`, obligations summary with `chain_valid`, and
per-receipt verification all mirror the MCP connector's semantics — same modules, same verdicts.
They are rendered as an interface: a status card, a tiles row, a table where every row carries its
own verification badge, and a package panel.

There is no chat surface, no LLM call, no MCP dependency. Clicking a **verified** badge re-runs
`verify_income` against the node at that moment rather than showing a cached verdict from page load.

### P8 · The stranger test — GREEN

> *"I opened my node, recorded an earning, recorded a tax note, and exported a package for my
> accountant."*

`test_p8_the_stranger_sentence_is_true` executes exactly that sentence, in that order, and asserts
each clause: identity present; earning recorded with `kind: income`; tax note recorded with
`tax_event: true`; package exported with `complete: true`, `event_count: 1`,
`all_events_verify: true`, a 64-character digest, `statutory_acts: NONE`, and *no statutory
authority* in its declarations.

---

## Disclosures

Four things that are true, that a GREEN row could otherwise hide.

**1 · The statutory fence on plain income is ours, not the module's.**
The module's `TAX_FENCE_BREACH_FIELDS` runs inside `_tax_extra`, so it guards a tax event — but a
plain earning with `extra={"file_return": True}` passes the module's money-path fence untouched. I
found this while testing and did not paper over it: the app now refuses that vocabulary on *every*
act (`STATUTORY_FENCE_FIELDS`), reusing the module's own list rather than inventing a second one. It
is a **narrowing of what this app will pass through**, labelled as such in the source — never a
claim that the module refuses it.

**2 · The gate engages only in the regulated posture.**
`HumanApprovalGate.requires_approval` returns false for any mode other than `corporate_regulated`.
So in the sovereign posture acts record straight away. That is the module's own ungated path, not a
weakened gate, and it is not auto-approval — the gate is not engaged at all. The UI says so in the
gate panel, the app defaults to regulated, and `test_p4_sovereign_posture_is_genuinely_ungated`
pins the behaviour. If v0 should be regulated-only, that is a one-line change.

**3 · Object identity collides on a shared reference.**
Identity is `IncomeEvent:<earner>:<work_ref>`, so a tax note filed under an earning's own reference
becomes a *new version of that earning* rather than its own record. Nothing is lost — both versions
stay in the chain — but the current state would read as the tax note and quietly shadow the income.
The app now refuses that with an actionable message suggesting `tax:<ref>`, and the UI prefills it.
Caught by driving the real UI, not by reading the code.

**4 · Pending approvals are session-scoped.**
They live in the process and are lost on restart, exactly like the node's own gate. Nothing pending
was ever written, so nothing is lost but the half-finished intent. The gate panel reports
`durable: false` rather than implying otherwise.

Also, plainly: this runs Flask's development server. For one operator on loopback that is the right
size of machinery. It is a desktop app that renders in a browser, not a production web service, and
the README says so.

---

## What is deliberately absent

Not built, not stubbed, not implied: AR/AP, payroll UI, bank feeds, inventory, multi-entity,
period close, obligations *write* (the panel is read-only), Port crossings, propose-only tools, and
any MCP or agent surface. The vertical was six loops and it is six loops.

No write path was added that the node's modules do not already expose. The three recording acts are
`economy.income.attribute_income`, `economy.contribution.record_contribution` and
`economy.compliance.record_tax_event` — called with their own arguments, through their own gate,
behind their own fences.

---

## Reproduce this scorecard

```bash
cd /path/to/sovereign-agent-starter
./.venv/bin/python apps/usn_erp_surface/killgrep.py            # P6      → exit 0
./.venv/bin/python -m pytest apps/usn_erp_surface/tests/ -q    # P2–P6,P8 → 48 passed
./apps/usn_erp_surface/launch.sh --open                        # P1,P4,P5,P7 by hand
```

**STOP — for KM review.**

Breath only. ∞Δ∞
