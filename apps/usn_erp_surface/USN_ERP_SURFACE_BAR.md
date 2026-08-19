# USN ERP Operator Surface — BAR

∞Δ∞ Seal 1176-INFINITY-RHO · Breath only ∞Δ∞

Scored 2026-08-19. **v0 (P1–P8) re-verified · obligations write surface (O1–O6) · plus
invoice / receivable-lite (I1–I6, KM ruling Option A).** Every row below was re-run immediately
before writing this file.

| | |
|---|---|
| **Build** | `apps/usn_erp_surface/` — local web app, Flask on loopback, single self-contained page |
| **Binding** | library-direct; `node_binding.py` is the only module that touches `sovereign_agent` |
| **Vertical** | solo/household: open node · record income/contribution · record tax note · **record invoice + AR aging** · **open / approve / close obligations** · gate · export package |
| **Invoice-lite** | `revenue.billing.invoice` shapes it (pure) → persisted through the **same fence-owning attribution writer** as income (`work_ref=invoice:<id>`, `doc_kind=invoice`); `revenue.billing.ar_aging` projects aging on read. No new object kind, no second ledger. |
| **Tests** | **93 passed** (`apps/usn_erp_surface/tests/`) — was 74 at v0.1, 48 at v0 |
| **Kill-grep** | **GREEN**, 0 findings across **9** checks (`killgrep.py`, exit 0); invoice collection verbs added to check 2's vocabulary and proven to bite (I5) |

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

Breath only. ∞Δ∞
