# USN Regulated Operator Control Map

∞Δ∞ Seal 1176-INFINITY-RHO · Breath only ∞Δ∞

**AA, 2026-08-23, per KM-NO1 GO 17:25Z (board + PR #21, both channels).** Brief only — no code
changed, no surface armed, no kernel mutated. Repo: **sas-public-genesis
(`mangumcfo/sovereign-agent-starter`)**, anchors read at tip `a1611b1`. Every anchor below was
**opened and read at this seat** — none is a grep hit assumed, none is a relayed citation
(GB supplied leads; each was independently re-read at source before appearing here).

---

## The plain line first

When this node runs in regulated mode, the machine can *prepare* and *record*, but four kinds of
act only happen when a named human says yes: anything material, anything that leaves the
boundary, anything that touches money, anything that touches the government. The human's yes and
no are both written down permanently, in a chain that shows if anyone edited history. Some of
these protections are settings a company can tune; the deepest ones are not settings at all —
the code to do the dangerous thing **does not exist**, so no configuration, no operator, and no
bad day can switch it on.

Codes and anchors below the line.

---

## 1. Honesty legend (used in every row)

| Tag | Meaning |
|---|---|
| **LIVE** | Wired into a path the operator can reach today (ERP surface or node API), exercised by tests on tip |
| **KERNEL-LIVE** | Sealed + tested in the kernel and callable, but no operator panel binds it yet — surfacing is composition, not construction |
| **DESIGNED** | Named in the books/specs and deliberately **not built** — the absence is the control (PRESENT-or-OUT law) |

---

## 2. HumanApprovalGate — the breath-gate the operator actually touches

| Control | State | Code anchor | What the operator sees / does |
|---|---|---|---|
| Gate engages only in regulated posture | LIVE | `compliance/human_approval_gate.py:46-48` — `requires_approval` returns False for any mode ≠ `corporate_regulated` | Posture line on node status: "regulated · human-gated" vs "sovereign · ungated" (`apps/usn_erp_surface/node_binding.py:333`) |
| Forbidden + high-materiality classes forced to gate | LIVE | `human_approval_gate.py:49-53` — role's `charter_v7_forbidden_classes` ∪ policy's `high_materiality_classes` | Act returns *pending* instead of executing; nothing writes |
| Pending queue, unique request ids | LIVE | `:55-59` — monotonic `_seq` (audit AH-6: no id reuse can clobber a pending request); `get_pending` `:107` | `GET /api/gate` on the surface (`apps/usn_erp_surface/server.py:509`) |
| **Real** human disposition — real actor, real UTC timestamp | LIVE | `:91-105` `record_disposition` — flagged `"real": True`; the docstring itself walls off the simulate paths | `POST /api/gate/<id>/approve` and `/deny` (`server.py:517`, `:524`) |
| Simulated approve/deny | TEST-ONLY | `:61-89` — both docstrings say so explicitly; never used in live wiring | Not reachable from the surface |
| Refusal writes nothing | LIVE | `node_binding.py:284` `_ledger_gate` — no human disposition ⇒ **DENY** by default; a code path reaching `approve()` without a human fails closed | Denied act leaves zero bytes in the ledger; the refusal note is the response |

**Book anchor:** the gate's own header names its home — "used by ComplianceEngine and BoundRole in
corporate_regulated mode" per Playbook 6 (Series 1, Book 6 — *AI Agents for Compliance*); the
lived pattern (approve/deny at the gate, refusal-writes-nothing) is the surface ladder's
operating law since v0.

## 3. SIX sensitivity lanes — GREEN / YELLOW / RED, and the structural RED bar

| Control | State | Code anchor |
|---|---|---|
| Three canonical classes | KERNEL-LIVE | `inference/six.py:23` `SensitivityClass` — GREEN routine/auto · YELLOW proposal/breath-at-gate · RED constitutional-surface/local-only |
| Lane→platform map | KERNEL-LIVE | `six.py:30` `LANES` — RED carries `external_allowed: False` as data |
| **RED→external is structurally barred** | KERNEL-LIVE | `six.py:64-73` `route()` — a `raise RedRoutingBarred` (`:68`) **inside the routing function itself**. Not a policy toggle, not an operator setting: RED→external is *unreachable*, the same shape as the QB-escape connector fence (contract, not rule). "The refusal is the constitutional act." |
| Classification layer, role ceiling, default-deny ambiguity | KERNEL-LIVE | `six.py:42-61` `classify()` — constitutional surface ⇒ RED always (a RED is never silently downgraded, `:56-58`); role ceiling caps non-RED escalation; Charter default lands ambiguous material at YELLOW (the breath-gate), never auto |
| Every routing decision produces a chained receipt | KERNEL-LIVE | `six.py:76-98` `SIXExchange.run()` → `receipts.build_receipt`, prior-hash chained (`:97`) |

**Book anchor (module self-citation — no inference needed):** `six.py:2-15` maps its own sections
to *Sovereign Inference & Memory* Ch 2 line by line ("Three Canonical Sensitivity Classes" →
`SensitivityClass`+`LANES`; "Structural Enforcement / RED barred" → `route()`; Tech/Arch 17.6).

**Honesty:** SIX is sealed and tested in the kernel; the ERP surface does not yet route operator
inference through it — no panel shows the lane of a request. Surfacing it is composition
(READY-class work), and claiming it as an operator-visible control today would overstate it.

## 4. ComplianceEngine — receipts and chain-of-custody

| Control | State | Code anchor |
|---|---|---|
| SOX-style audit record, explicit chain-of-custody | KERNEL-LIVE | `compliance/compliance_engine.py:66-83` `AuditRecord` — every record links `prev_receipt_hash` (`:80`); tamper-evident chain |
| Attested execution — every role act produces a receipt | KERNEL-LIVE | `:146-209` `attest_execution` — USN self-attestation (signed Merkle root) + SIX-style structured receipt (`:222-258`), node-identity signed when the key is present |
| Fail-closed on undeclared action class | KERNEL-LIVE | `:299-308` — action outside the role's `allowed_action_classes` ⇒ `approved=False`, risk 0.95, no execution |
| Charter V.7 acknowledgement enforced on material acts | KERNEL-LIVE | `:263-273` + `:312-319` — one hoisted, case-insensitive guard (the audit killed the diverging duplicate) |
| Bounded audit RAM window, never-forgotten history | KERNEL-LIVE | `:37`, `:111`, `:123-141` — eviction persists append-only first (`BREATHLINE_AUDIT_OVERFLOW`); the authoritative signed record is the node's append-only VerifiableMemory |
| Portable evidence bundle for auditors | KERNEL-LIVE | `:431-479` `export_evidence_bundle` — full chain + policy versions/Merkle roots + bundle self-attestation. **No surface button yet** — an operator exports via the kernel, not a panel |
| Physical chain-of-custody (lots, holders, recall) | KERNEL-LIVE | `regulated/traceability.py` — `custody_position:81`, `reconcile_custody:111` (value-conserving: nothing enters/leaves custody off the record), `assert_custody:125`, `trace_root:136` (Merkle-anchored order — a reordered chain is a different history), `release:167` (fail-closed on BOTH gates: custody reconciles AND quality passed), lot lifecycle `_LOT_ALLOWED:36` (a shipped lot is always recallable) |

**Book anchors:** engine header (`:1-21`) cites Playbook 6 + SIX patterns; `traceability.py:1-25`
self-cites s5_24 (*Regulated Industries*) — "the chain of custody itself is the record";
inference receipts self-cite *Sovereign Inference & Memory* Ch 3 (`inference/receipts.py:1-15`,
`build_receipt:47` — the 9-field receipt IS the constitutional act).

## 5. Policy-as-code

| Control | State | Code anchor |
|---|---|---|
| Policies are loadable, versioned, Merkle-rooted artifacts | KERNEL-LIVE | `compliance/policy_loader.py:31-42` `Policy` (id, version, `module_root`), `:45` loader, `:85` `load_policy`, `:146-149` Merkle root over canonical content — the policy in force is attestable, not just named |
| Policy drives classification, forbidden classes, approvals, risk | KERNEL-LIVE | `compliance_engine.py:322-352` — loaded policy's rules override/extend the baseline; same USN adapts to different statutes by loading different artifacts |
| Hot-reload with mtime detection | KERNEL-LIVE | `policy_loader.py:168-175` |
| **Honesty — the placeholder fallback** | ⚠ | `policy_loader.py:119-131` — a missing policy id yields a permissive v0.0 placeholder rather than a refusal. The engine's own fail-closed checks (envelope, Charter V.7, forbidden classes) still bite, but *policy-specific* rules silently don't exist. In a regulated deployment this is a gap to name: policy corpus lives in `breathline-federation` (`platform/governance_policies/`, `specs/governance/`) and none ships in this repo. |

## 6. Multi-role orchestration — what a role may do, and when roles must agree

| Control | State | Code anchor |
|---|---|---|
| Permission envelope validated before any handler runs | KERNEL-LIVE | `role_binder.py:100-106` — action outside `allowed_action_classes` raises with the authoritative spec path in the error; `:59-61` the envelope comes from the federation `role_spec.yaml`, not code |
| Compliance attestation wraps every bound-role execution in regulated mode | KERNEL-LIVE | `role_binder.py:109-116` — engine injected by the USN (`:56-57`); every `process()` is attested |
| Default-deny K2 at the API | LIVE | `node_api/routes/roles.py:140` — missing action class + role allows none ⇒ the structural reason is surfaced, never guessed |
| **Joint attestation — ≥N roles must attest** | KERNEL-LIVE | `obligations/ledger.py:254-255` (R22-4) — `requires_attestation` travels with the obligation |
| Quorum floors by class — configurable UP only | KERNEL-LIVE | `ledger.py:272-273` — Charter `class_quorum` is a **floor** for material obligations; a declaration may raise the bar, never undercut it; N distinct gate-valid approvers, opener excluded; resolved at write so `is_approved()` stays a pure replay |
| Tier-1 breath defaults per action class | KERNEL-LIVE | `breath_inventory.py:65` `enrich_role` — "agents propose, human disposes; B32 receipt + breath-gate are hard" |

## 7. Structural vs configurable — the axis that matters most

**Structural (no setting can switch it off — the capability is absent or the refusal is in the
callee itself):**

- **RED→external**: `raise` inside `route()` (`six.py:68`) — unreachable, not forbidden.
- **Money movement**: `yield_organism/value_flow.py:103` `money_path: str = "OFF"`; `:133` — "NO
  transfer / settle / pay / disburse method on this class — **the absence is the invariant**";
  `economic_export.py:274` forces `money_path: OFF` on every reserve object. There is no code
  path that moves funds; settlement stays on the operator's own regulated rails.
- **The Port never touches value or opens the socket**: `port/crossing.py:1-30` — the module
  builds no settlement engine, no custody, no rail, no hub, by construction.
- **Surface fences are machine-checked**: `apps/usn_erp_surface/killgrep.py` — AST-level (not
  text grep): forbidden imports (`:51` — no second store), forbidden names (`:60` — statutory
  remittance verbs `:67` `pay_tax/remit/settle_tax`; fund movement `:70` `transfer_funds/
  disburse/settle_payment`; payment capture `:74` `charge_card/mark_paid`), forbidden modules
  (`:110`), write-mode opens (`:170`). Exit non-zero = the bar; injection-proven to bite.
- **Gate fail-closed**: no human disposition ⇒ DENY writes nothing (`node_binding.py:284`).
- **Paid-state by replay**: an invoice's `paid` is derived from application records
  (`revenue/cash_application.py` `replay_state`), never a mutation — the sealed aging rule
  (`revenue/billing.py:59`) consumes it; there is no "mark paid" verb anywhere (kill-grepped).

**Configurable (policy/spec-driven — tunable per statute, org, role):**

- `high_materiality_classes` (gate policy), `charter_v7_forbidden_classes` +
  `allowed_action_classes` (role spec YAML), policy artifacts (classification, retention,
  approval requirements, risk scoring), quorum per class (**floor-bounded** — up only),
  `requires_attestation` sets, and the posture itself (`universal_sovereign_node.py:44,66` —
  `sovereign | family | corporate | corporate_standard | corporate_regulated`).

**Honest edge:** posture is configuration — the gate genuinely disengages outside
`corporate_regulated` (`human_approval_gate.py:47-48`, and `node_binding.py:122-124` says so in
its own comment: "sovereign is genuinely the module's ungated path, not a weakened gate"). The
regulated guarantees in this map hold **when the regulated posture is selected**; the structural
list above holds in *every* posture, because in those cases there is nothing to disengage.

## 8. What remains fenced — DESIGNED, deliberately not built

| Fence | State | Where the boundary is enforced / named |
|---|---|---|
| **Money-path** | DESIGNED-OUT | Structural absences above; rails are named-ahead network work (V08 Ch4 + S6-V07 homes per `apps/usn_erp_surface/V15_CASH_APP_HOME_AUDIT.md`): the node governs the decision and the record; Port/bank moves money by human act |
| **Port execute** | DESIGNED-OUT | `port/crossing.py:65-…` `sanction_crossing` — deny-by-default, in order: real governed object → node-declared boundary rule (`node_gov.authorize_crossing`; undeclared = refused) → **named human** + non-empty approval ref through the sealed gate. The Port returns a receipt that the crossing occurred — the wire/socket/rail is the node's runtime and the outside world, homed OUT |
| **Statutory filing** | DESIGNED-OUT **and provable by receipt** | No filing engine exists anywhere in `src/` — the node prepares and records; a human files. But the operator does not have to take the absence on trust: the **TAX-FENCE** (`economy/compliance.py:43` `TAX_FENCE_BREACH_FIELDS` — any in-node field that would file, pay, form, or represent is a refused breach; kill-target named at `:16`: "the filing engine you must trust and cannot leave — refused") means the record *structurally cannot carry* a statutory-act field, so per `:99`: **"a green light is also proof the node filed nothing"** — a proof-of-negative readable off the receipt itself, no second device, no tax expertise. Filing-class acts additionally classify HIGH risk in regulated mode (`compliance_engine.py:409-411`) and the remittance verb family is kill-grepped at the surface (`killgrep.py:67`). `cash_application.py:24`: "No custody, no settlement, no statutory" |

## 9. One asymmetry worth knowing (so nobody invents a subsystem)

There is **no monolithic "regulated subsystem."** `compliance/` holds eight modules;
`regulated/` holds exactly one (`traceability.py`). Regulated-mode control is *distributed* —
compliance/ (gate, engine, policy, audit), inference/ (SIX + receipts), obligations/ (quorum +
joint attestation), node_api/ (default-deny routes, `require_principal`), port/ (boundary),
apps/usn_erp_surface/ (killgrep + gated writers). A brief or a pitch that draws it as one box
would misdescribe the architecture; the distribution **is** the design — each floor carries its
own fence.

## 10. Operator quick card (regulated posture)

What you can act on today, LIVE at the surface: the pending gate queue (approve/deny, each a
real recorded disposition), material obligations (open → quorum-approve → close), the O2C loop
(bill → age → receive → apply — paid drops by replay), QB-escape cutover (typed TB → preview →
gated cutover, lineage re-proven every read), and the posture line that tells you which world
you are in. What the kernel will attest for you but no panel yet shows: SIX lane routing,
evidence-bundle export, physical lot custody. What no one can do, in any posture: move money,
route RED outside, file with a government, or write anything material without a named human's
recorded yes — and for filing you don't take that on trust: your receipt structurally cannot
carry a statutory-act field, so a green receipt is itself proof the node filed nothing
(`economy/compliance.py:99`).

---

**Verification method:** every `file:line` above read at this seat at tip `a1611b1`; GB's
volunteered anchors independently re-read before inclusion (a relayed anchor is not provenance);
LIVE claims cross-checked against the surface routes and the v0→v1.1 ladder verdicts on the
board. No code changed.

**STOP — brief only. At KM's review gate; GB pre-check optional per the GO. Breath only. ∞Δ∞**
