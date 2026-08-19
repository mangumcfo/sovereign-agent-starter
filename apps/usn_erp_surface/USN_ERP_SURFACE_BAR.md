# USN ERP Operator Surface — BAR

∞Δ∞ Seal 1176-INFINITY-RHO · Breath only ∞Δ∞

Scored 2026-08-19. **v0 (P1–P8) re-verified · obligations write surface (O1–O6) · invoice /
receivable-lite (I1–I6, KM ruling Option A) · period view + close (PV1–PV6, KM CFO ruling —
full GAAP-shaped books) · plus the audit package (A1–A6).** Every row below was re-run immediately
before writing this file.

| | |
|---|---|
| **Build** | `apps/usn_erp_surface/` — local web app, Flask on loopback, single self-contained page |
| **Binding** | library-direct; `node_binding.py` is the only module that touches `sovereign_agent` |
| **Vertical** | solo/household: open node · record income/contribution · record tax note · **record invoice + AR aging** · **trial balance + income statement + balance sheet + period close** · **open / approve / close obligations** · gate · export package |
| **Invoice-lite** | `revenue.billing.invoice` shapes it (pure) → persisted through the **same fence-owning attribution writer** as income (`work_ref=invoice:<id>`, `doc_kind=invoice`); `revenue.billing.ar_aging` projects aging on read. No new object kind, no second ledger. |
| **Tests** | **137 passed** (`apps/usn_erp_surface/tests/`) — was 131 at v0.5, 119 at v0.4, 108 at v0.3, 93 at v0.2, 74 at v0.1, 48 at v0 |
| **Status home (v0.6)** | ONE read-only screen composing ONLY existing reads — open exceptions/policy gaps (exception queue) · approvals pending + material awaiting gate (gate/obligations) · period open/closed + in-balance (period view) · audit-ready Y/N (the existing package verdict, same sha, no new build path). Enterprise labels; no write path; tiles move only on governed change |
| **Exception queue** | read-only projection of pending deviations (integrity breaches · failed verifies · standing vetoes · material-awaiting-gate · out-of-balance books · session pendings · locks), classified by the sealed `governance.exception.route_batch` — material + no covering gate = the router's own REFUSED (policy gap), never auto-resolved; **no dismiss exists**; a row leaves only when the governed state changes through an existing gated verb |
| **Audit package** | one portable, self-verifying evidence bundle: revenue events · invoices + AR aging · tax records (not filings) · obligations · period closes · statements snapshot — all replayed from node state; compliance core = sealed `audit_checks` (6 receipted checks) → `build_audit_package` (content-hashed) → `verify_audit_package`; stamped `as_of` the newest entry, never the clock — unchanged books re-export byte-identically |
| **Kill-grep** | **GREEN**, 0 findings across **9** checks (`killgrep.py`, exit 0); invoice-collection verbs in check 2's vocabulary, proven to bite (I5); period-close violations proven to bite (PV5) |
| **Period view** | read-time derivation: node objects → sealed `posting.post` → `trial_balance` / `income_statement` / `balance_sheet` over a typed CoA (Cash · AR · Unearned · Equity · Revenue · Expense). Close persists via the obligation ledger. No second GL store; objects stay source of truth. Full GAAP-shaped books — money-path OFF ≠ empty GL. |

**This is not an ERP suite.** It is one operator loop, complete. Invoice is a **billing-event
record, not an AR balance** — the node holds no receivable and moves no money; **collection /
payment is OUT** (money-path OFF, machine-checked). No AP, no payroll UI, no bank feeds, no
inventory, no multi-entity, no dashboard chrome beyond what these loops need.

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
| | | |
| O1 | Open obligation → pending at gate → nothing on disk until approve | **GREEN** |
| O2 | Approve → durable on node ledger; survives restart; chain verifies | **GREEN** |
| O3 | Deny → nothing written | **GREEN** |
| O4 | Close only through existing APIs + gate as required | **GREEN** |
| O5 | Kill-grep still GREEN; new paths covered | **GREEN** |
| O6 | Read panel and write path agree on the same ledger files | **GREEN** |
| | | |
| I1 | Invoice-shaped record → gate → disk via module; survives restart | **GREEN** |
| I2 | Deny → nothing written | **GREEN** |
| I3 | List / aging reflects node state only (no app cache as truth) | **GREEN** |
| I4 | No pay / remit / file / crossing callable reachable from the binding | **GREEN** |
| I5 | Kill-grep GREEN; invoice money-path verbs proven to bite | **GREEN** |
| I6 | Read panel and write path are one source of truth; P/O rows stay GREEN | **GREEN** |
| | | |
| PV1 | Trial balance / statement reads reflect node state only; survive restart | **GREEN** |
| PV2 | Close holds at gate → deny writes nothing → approve persists via the ledger | **GREEN** |
| PV3 | Open invoices earned = Dr AR / Cr Revenue; deferred = Unearned; tax notes never in P&L | **GREEN** |
| PV4 | No pay / remit / file / crossing reachable | **GREEN** |
| PV5 | Kill-grep GREEN; period-close violations proven to bite | **GREEN** |
| PV6 | Statement AR ties to the receivables detail; one source of truth; prior rows GREEN | **GREEN** |
| | | |
| A1 | Audit package complete — every section present, counts tie to node state | **GREEN** |
| A2 | Deterministic — same state → same hash (incl. restart); state change → new hash | **GREEN** |
| A3 | Classification honest — invoices ≠ cash, tax memos not filings, no completed statutory act | **GREEN** |
| A4 | No money-path verbs; package self-verifies via the sealed verifier (tamper → False) | **GREEN** |
| A5 | Kill-grep bites on injected filing / remit / egress in the package path | **GREEN** |
| A6 | BAR updated; prior P/O/I/PV rows GREEN; AA fold: closed periods surface in period view | **GREEN** |
| | | |
| E1 | Queue lists exceptions/holds/denies/locks from node state only; survives restart | **GREEN** |
| E2 | No silent clear — no dismiss exists; a row leaves only via an existing gated verb | **GREEN** |
| E3 | Sealed-router classification — material + ungated = POLICY GAP, never auto-resolved | **GREEN** |
| E4 | No pay/remit/file/crossing reachable; the queue read writes nothing | **GREEN** |
| E5 | Kill-grep bites on injected silent-clear verbs (dismiss/silent_clear/bulk_dismiss) | **GREEN** |
| E6 | Queue rows tie to the panels that own the verbs; prior P/O/I/PV/A rows GREEN | **GREEN** |
| | | |
| H1 | Home composes ONLY existing reads; every figure equals its panel; survives restart | **GREEN** |
| H2 | Home read writes nothing — registry + ledger bytes unchanged | **GREEN** |
| H3 | Audit-ready Y/N is the existing package verdict (same path, same sha) — no new build path | **GREEN** |
| H4 | Enterprise labels only; no kernel jargon leaks into the home payload | **GREEN** |
| H5 | Kill-grep still bites silent-clear on the home build | **GREEN** |
| H6 | Tiles move only on governed change (denied act changes nothing); prior rows GREEN | **GREEN** |

**RED rows: none.** Nine disclosures are recorded below — five carried from v0, four new to the
obligations surface. None is a failed row; all are things you should know before you trust a GREEN.

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

## Obligations, row by row

### O1 · Open is held at the gate — GREEN

Live, through the browser, against an empty ledger root:

```
O6 panel (empty): No obligation ledger yet at '/tmp/demo_node/ledger'. It is created by …
O1 held at gate:  1 awaiting you  |  ledger rows: 0
```

`test_o1_open_is_held_at_the_gate` asserts `obligations.ndjson` **does not exist** while the act is
pending. `test_o1_every_obligation_act_is_gated` goes further: open, approve, close, attest, veto
and clear-veto are all held — five pending at once, zero written.

### O2 · Approve is durable, survives restart, chain verifies — GREEN

```
O2 after APPROVE, rows: 1  |  chain verifies · 1 entries
```

Then the **app process was killed and restarted** against the same ledger:

```
present: True | by_status: {'open': 0, 'closed': 1, 'total': 1} | chain_valid: True | entries: 3
```

The three bytes-on-disk entries, read straight out of `obligations.ndjson`:

```
debit    | Send Q3 books to the accountant | hash a5d03b7a51f3 | prev genesis
approval | obl_20260819042620_41d71913     | hash 12df47eb49d1 | prev a5d03b7a51f3
credit   | obl_20260819042620_41d71913     | hash 9a0a9205e367 | prev 12df47eb49d1
```

`test_o2_the_recorded_disposition_is_the_operators` asserts the approval entry carries
`disposition: approved`, `approved_by: kenn`, and `gate.real: True` — a simulated disposition must
never reach the chain.

`test_o2_ledger_gate_fails_closed_without_a_disposition` is the sharp one. It builds the ledger with
**no** recorded verdict and asserts `approve()` raises and the obligation stays `draft`. That is the
whole point of the seam, and it is stricter than the repo's own adapter (see disclosure 6).

### O3 · Deny writes nothing — GREEN

```
O3 after DENY, rows: 0  |  panel: No obligation ledger yet at …
```

Two tests, because there are two denials worth proving. `test_o3_denying_an_open_writes_nothing`
asserts the ledger file is never created. `test_o3_denying_an_approve_leaves_the_draft_untouched`
counts the chain lines before and after a denied approval and asserts they are equal — a denial must
not append.

### O4 · Close goes only through the existing API, and its guards hold — GREEN

A real close, on the chain:

```
type: credit · evidence_tier: E1 · closed_by: kenn · receipt rcpt_20260819042628_5cd9cfc4
```

Every guard below belongs to the ledger. This app calls the method and shows the refusal verbatim;
it does not re-implement, pre-empt or paraphrase any of them:

| Guard | Proof |
|---|---|
| Material cannot close before the breath-gate | `'…' is material and has not cleared the breath-gate` — seen live in the UI, and `test_o4_material_cannot_close_before_the_breath_gate` |
| Evidence floor | claim-only text is refused with the tier named; the UI shows E0/E1/E2 live as you type |
| A refusal needs no gate | `test_o4_a_refusal_needs_no_gate` — rejection closes a material obligation with no prior approval |
| Cannot close twice | `AlreadyClosedError`, surfaced as an operator sentence |
| Partial attestation blocks execution | `test_o4_attestation_and_veto_guards_hold` |
| A standing veto is default-deny | same test: `VETOED by ['counsel']` blocks the close until cleared |
| A veto needs a reason | `test_o4_veto_requires_a_reason` |
| A path-like reference must resolve | `test_o4_unresolvable_path_reference_is_refused` — *a citation is never written false* |

### O5 · Kill-grep still GREEN, and covers the new paths — GREEN

Two checks were added for this surface, bringing it to nine:

```
[GREEN] 7  no out-of-scope ledger verb (repair_chain / reopen)
[GREEN] 8  no reach past the ledger's public methods
```

Check 7 makes the scope boundary machine-checked rather than remembered. `repair_chain` is the sharp
one — it rewrites the append-only chain, which is precisely the authority an operator surface must
never hold. Check 8 forbids `_append`, `_entries`, `_get`, `_is_approved` and friends: going around
the ledger's public methods would write entries that AH-1, the evidence floor and the veto guards
never saw.

Four more injected violations were added to the negative suite — chain repair, out-of-scope reopen,
private append, private replay — and each is asserted to flip the gate RED.

`test_o5_app_owns_no_obligation_store` asserts every file under the ledger root belongs to the
node's own `ObligationLedger` (see disclosure 8 on the lock file).

### O6 · Panel and write path are the same bytes — GREEN

`test_o6_panel_matches_the_ledger_file` reads `obligations.ndjson` directly and asserts the panel's
`chain_entries` equals the raw line count, that the panel's ids are exactly the `debit` ids on the
chain, and that each status matches what the chain says.

The panel derives status through `ObligationLedger.iter_entries` (the ledger's own public read
gateway) and `obligations.projection` (its own public replay module) — the same committed entries
the write path guards on. There is no app-side interpretation between them, and no cache to go
stale.

`test_o6_panel_reports_a_tampered_chain` alters one title in the file and asserts `chain_valid`
flips to false. `test_o6_reads_create_nothing` asserts opening the ledger to read brings no file
into being.

---

## Disclosures

Nine things that are true, that a GREEN row could otherwise hide. **1–5 carry from v0; 6–9 are new
to the obligations surface.**

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

**5 · Flask's development server.** For one operator on loopback that is the right size of
machinery. It is a desktop app that renders in a browser, not a production web service, and the
README says so.

**6 · The ledger's gate seam is served by our own adapter, and that deserves naming.**
`ObligationLedger` takes a `gate` callable and records its verdict on the chain; with none injected,
AH-1 fail-closes a material approval. The repo ships one adapter — `node_integration.make_gate` —
but it hardcodes `status="approved"` on the assumption that reaching `approve()` already implies an
authenticated human. This app supplies its own instead, for one reason: **it cannot mint an approval
the operator did not give.** Handed no recorded disposition it returns a DENY, so a code path that
reaches `approve()` with no human behind it fails closed rather than passing. That is using the
documented seam, not adding a verb — but it is *our* code sitting in the authority path, and
`test_o2_ledger_gate_fails_closed_without_a_disposition` is the test that keeps it honest.

**7 · A denial writes nothing — including no record of the refusal.** O3 says deny writes nothing, so
that is what it does. Worth knowing: the ledger *can* record a refusal, and arguably should — a
denied gate verdict appends an `approval` entry with `disposition: denied`, which is the chain
confessing that someone said no. We deliberately do not reach that path, because a refusal at the
app gate happens before the ledger is ever called. If you want refusals on the chain, that is a
one-line change and its own bar row — say the word.

**8 · The ledger writes a lock file.** `obligations.lock` appears alongside `obligations.ndjson` once
you write. It is the module's own POSIX advisory write-fence, under the node's ledger root — the
node's file, not an app store. `test_o5_app_owns_no_obligation_store` allows exactly those two names
and nothing else. Reads create neither (`test_o6_reads_create_nothing`).

**9 · No LAN bind was built.** The brief made it conditional on you having already asked for a phone
LAN view, and you have not asked in this thread — so it is not there. The loopback-only refusal is
unchanged and still tested; it now rejects a private RFC1918 address too:

```
$ python server.py --host 192.168.1.50
Refusing to bind '192.168.1.50'. The operator surface is loopback-only… If you need access from
another machine, that is a Port-governed crossing — not a bind flag.
```

---

## What is deliberately absent

Not built, not stubbed, not implied: AR/AP, payroll UI, bank feeds, inventory, multi-entity, period
close chrome, Port crossings, propose-only tools, LAN bind, and any MCP or agent surface. Two ledger
verbs the module *does* expose are deliberately out of scope and **machine-checked out** —
`repair_chain` (which rewrites the append-only chain) and `reopen`. Kill-grep check 7 fails RED if
either ever appears.

No write path was added that the node's modules do not already expose. Every act is an existing
method, called with its own arguments, through its own gate, behind its own guards:

| Act | Module method |
|---|---|
| record an earning | `economy.income.attribute_income` |
| record a contribution | `economy.contribution.record_contribution` |
| record a tax note | `economy.compliance.record_tax_event` |
| open an obligation | `obligations.ledger.ObligationLedger.open` |
| approve one | `…ObligationLedger.approve` |
| close or refuse one | `…ObligationLedger.close` |
| attest / veto / clear | `…ObligationLedger.attest` / `.veto` / `.clear_veto` |

---

## Reproduce this scorecard

```bash
cd /path/to/sovereign-agent-starter
./.venv/bin/python apps/usn_erp_surface/killgrep.py            # P6, O5        → exit 0, 9 GREEN
./.venv/bin/python -m pytest apps/usn_erp_surface/tests/ -q    # P2–P6,P8,O1–O6 → 74 passed
./apps/usn_erp_surface/launch.sh --open                        # P1,P4,P5,P7 by hand
```

**STOP — for KM review. Nothing pushed.**

No commit and no push was made. I have no standing P-Push instruction in this thread and no remote
credentials here, so `apps/` is delivered as files for you to land yourself. Say the word and I will
prepare the commit.

---

## Invoice / receivable-lite, row by row (I1–I6) — GREEN

**Law (KM ruling, Option A).** An invoice is shaped by the sealed `revenue.billing.invoice` (pure)
and persisted through the exact fence-owning writer an income record uses — `work_ref="invoice:<id>"`,
`amount=total`, the billing fields (`customer`, `issued_day`, `due_day`, `lines`, `status:open`) in
`extra` under `doc_kind="invoice"`. No new object kind, no second ledger, no money-path. It is a
**record of a billing event, not an AR balance.**

- **I1 · create → gate → disk; survives restart — GREEN.** Under the regulated posture the invoice
  is held at the gate (nothing on disk); on the operator's approval it is written through the module,
  and a fresh binding replays it from disk and verifies it against its own receipt. The total
  (`2120.0` = 1500 + 500 + 120) is computed by the billing surface, never typed.
- **I2 · deny → nothing written — GREEN.** A denial leaves no `objects.ndjson`; the receivables
  panel stays empty.
- **I3 · aging reflects node state only — GREEN.** `ar_aging` is a projection computed on read by
  `revenue.billing.ar_aging` over the invoice records — buckets sum to the total (`balances: true`),
  and a fresh binding produces them (no app cache). `invoices()` projects the same bytes the write
  produced (object_id + version_hash match).
- **I4 · no pay/remit/file/crossing reachable — GREEN.** A money-movement field on an invoice is
  refused by the module's own money-path fence (`"money-path"` in the refusal); a statutory field is
  refused by the app's narrowing; and no public binding method name carries a collection verb.
- **I5 · kill-grep bites the new verbs — GREEN.** `collect_payment`, `apply_payment`,
  `settle_invoice`, `mark_paid` (and siblings) were added to the forbidden vocabulary; injecting each
  into a copy of the app drives P6 to RED (exit 1).
- **I6 · one source of truth — GREEN.** `status()`, `invoices()` and `ar_aging()` all replay the same
  node and agree; all P1–P8 and O1–O6 rows re-ran GREEN in the same suite (**93 passed**).

**STOP — working UI + BAR GREEN.** Collection remains OUT; the S4/fence re-audit is a later pass.

---

## Period view + close, row by row (PV1–PV6) — GREEN

**Law (KM CFO ruling).** Full GAAP-shaped books. Statements are a **read-time projection**: the
node's attribution objects map to balanced double-entry postings through the sealed
`financials.posting.post`, then `trial_balance` / `income_statement` / `balance_sheet` compute over
a typed chart of accounts. Nothing persists — objects stay the single source of truth, no second GL
store. Money-path OFF (the node moves no value) does **not** mean an empty GL.

Derivation: income/contribution → Dr cash / Cr revenue · invoice (open) → Dr AR / Cr revenue ·
invoice (deferred) → Dr AR / Cr unearned · tax note → memo (no P&L). Close persists through the
node's own obligation ledger (open → approve → close, the sealed close record's trial-balance hash
as evidence).

- **PV1 · reads reflect state, survive restart — GREEN.** A mixed book (2,400 cash earning +
  1,000 open invoice + 600 deferred + a tax note) projects, from a fresh binding, revenue 3,400,
  net income 3,400, assets 4,000 (cash 2,400 + AR 1,600), liabilities 600 (unearned); trial balance
  nets to zero. Empty node projects zero and balances.
- **PV2 · close gated — GREEN.** Under the regulated posture the close is held at the gate; a denial
  writes nothing to the ledger; an approval persists it through the obligation ledger (locked close
  record, chain verifies, one closed obligation).
- **PV3 · classification honest — GREEN.** An open invoice recognises **revenue** on the AR leg
  (Dr AR / Cr Revenue), not cash; a deferred invoice posts to **unearned** (not revenue); a **tax
  note never appears in the P&L**; cash income and invoice AR are classified distinctly.
- **PV4 · no money-path reachable — GREEN.** Period view is a pure read; the close persists only
  through the obligation ledger. No pay/remit/file/crossing method on the binding; kill-grep GREEN.
- **PV5 · kill-grep bites — GREEN.** Injecting a second GL store, a bank egress, a money-movement
  identifier, or a `reopen` of a closed period each drives P6 to RED.
- **PV6 · one source of truth — GREEN.** The statement AR (1,600) ties to the receivables detail
  (2 invoices); period view, `invoices()` and `status()` all replay the same node. All prior P/O/I
  rows re-ran GREEN in the same suite (**108 passed**).

**Surface terms (standing rule):** operator-visible strings use standard accounting vocabulary
(Revenue · AR · Cash · Equity · Trial balance · Income statement · Balance sheet · Period close ·
Pending approval); sealed kernel module names are unchanged — `node_binding` maps the labels. A
`Surface terms` glossary is in the README. A broader relabel micro-pass (Contribution tab → Revenue,
Work ref → Document ref) is a cheap follow-on, not this bar.

**STOP — working UI + BAR GREEN.** Money-path OFF, collection/filing OUT; audit-package and
exception-queue chrome are the next rolling shots.

---

## Audit package, row by row (A1–A6) — GREEN

**Shape.** `audit_package()` gathers every section from node state at build time (revenue events ·
invoices + AR aging · tax records · obligations · period closes · statements snapshot ·
classification), runs **6 receipted checks** through the sealed `compliance.audit_checks`
(registry roots match · all events verify · ledger chain valid · trial balance nets to zero ·
classification honest · no statutory act recorded), folds the readiness into
`compliance_report("financials", …)` → `build_audit_package` (content-hashed), and **self-verifies
via `verify_audit_package` before handing anything over**. Deterministic by the standing law:
stamped `as_of` the newest recorded entry, never the clock.

- **A1 · completeness — GREEN.** All eight sections present; counts tie (1 revenue event ·
  2 invoices · 1 tax record · 1 period close · 3 ledger entries); compliance core `ready: true`,
  all six checks passed.
- **A2 · determinism — GREEN.** Same state → same sha256 across calls AND across a restart
  (fresh binding); the on-disk bytes are byte-identical; one new record → new hash. Verified
  in-process and over HTTP.
- **A3 · classification honest — GREEN.** Cash income (2,400), earned invoice AR (1,000) and
  deferred (600) are distinct in the package; revenue = cash + earned only; tax records declared
  "RECORDS, not filings"; the `no_statutory_act_recorded` check proves the node filed nothing; no
  completed statutory-act text anywhere in the package.
- **A4 · no money-path — GREEN.** No pay/remit/collect verb on the binding; the sealed verifier
  accepts the intact core and **rejects a tampered one** (flipped `ready` → False).
- **A5 · kill-grep bites — GREEN.** Injected `file_return` emission, `remit` binding, and an HTTP
  package-upload egress each drive P6 to RED.
- **A6 · BAR + prior rows — GREEN.** Whole suite **119 passed** (P/O/I/PV all re-ran green).
  **AA fold landed:** closed periods now surface in the period view (`closed_periods:
  "2026-Q3 (locked) · closed by …"`) read back from the ledger's period-close credits — no tab
  switch needed. Disclosed here per cadence (observation folded on the rail that touched the file).

**STOP — working UI + BAR GREEN.** Exception queue is the next shot, on GO.

---

## Exception queue, row by row (E1–E6) — GREEN

**Shape.** `exceptions_queue()` derives every pending deviation from node state on each call —
integrity breaches (roots mismatch / chain invalid), failed event verifications, standing vetoes
(veto minus veto_clear), material obligations awaiting their gate, out-of-balance books,
session-scoped gate pendings (labeled `durable: false`), and locked periods (informational) — then
classifies through the sealed `governance.exception.route_batch` (V29): gated material →
`pending_gate`; **material with no covering gate → the router's own REFUSED, shown as POLICY GAP,
never auto-resolved** (under the sovereign/ungated posture this is exactly what surfaces — the
truth that no gate stands); immaterial → `recorded`. The queue is READ-ONLY and carries **no
dismiss**; each row names the existing panel + gated verb that resolves it.

- **E1 · node state only, survives restart — GREEN.** Seeded hold + veto + lock derive identically
  from a fresh binding; a clean node shows an empty queue ("clear because the state is clean, not
  because anything was dismissed"); session pendings are listed and labeled session-scoped.
- **E2 · no silent clear — GREEN.** No dismiss/suppress/clear verb exists on the binding; the veto
  row survives a *denied* clear-veto (denial writes nothing) and leaves ONLY on the approved,
  gated `clear_veto`; the queue read itself changes zero bytes.
- **E3 · sealed-router classification — GREEN.** Sovereign posture → hold + veto come back
  POLICY GAP (default-deny, high materiality); a tampered registry log surfaces integrity /
  verify-failure rows, all material.
- **E4 · no money-path — GREEN.** No pay/remit/collect verb reachable; kill-grep GREEN on the
  shipped app.
- **E5 · kill-grep bites — GREEN.** Injected `dismiss_exception`, `silent_clear`, `bulk_dismiss`
  each drive P6 to RED (new silent-clear vocabulary in check 2).
- **E6 · one truth — GREEN.** The hold row's obligation is genuinely draft+material+open on the
  obligations panel; the lock row ties to the period view's closed periods. Whole suite
  **131 passed** (P/O/I/PV/A all re-ran green).

**STOP — working UI + BAR GREEN.** Queue clears only through governed acts; next shot on GO.

---

## Operator status home, row by row (H1–H6) — GREEN

**Shape.** `status_home()` is a pure composition of four existing reads: `exceptions_queue()`
(open / policy-gap / needs-approval counts), `gate_state()` + the queue's hold rows (approvals
pending, material awaiting the breath-gate, session denials — labeled session-scoped),
`period_view()` (postings, in-balance, closed periods), and `audit_package()` (the existing
readiness verdict + package sha — same path, no new build). One screen, enterprise labels,
read-only: nothing can be acted on or cleared from the home; each tile names the panel that owns
the verb.

- **H1 — GREEN.** Every home figure equals the panel it names, from a fresh binding (restart).
- **H2 — GREEN.** Registry and ledger bytes are byte-identical across a home read.
- **H3 — GREEN.** `audit_readiness.ready` and the package sha equal the existing
  `audit_package()` verdict exactly.
- **H4 — GREEN.** Labels are "Open exceptions · Approvals · Period status · Audit readiness";
  no kernel jargon (`doc_kind`, `work_ref`, `obl_open`) appears in the payload.
- **H5 — GREEN.** Injected `dismiss_exception` still drives the kill-grep RED.
- **H6 — GREEN.** A *denied* clear-veto moves no tile; only the approved, gated act does.
  Whole suite **137 passed** (P/O/I/PV/A/E all re-ran green).

**STOP — working UI + BAR GREEN.** Next shot on GO.

Breath only. ∞Δ∞
