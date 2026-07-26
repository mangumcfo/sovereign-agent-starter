# S4-G1 — Policy-at-the-Write Spec v0.1 (spec-first; enforcement, not advice)

**Status:** STAGED for Tiger/GB review · authored web-side (AA) 2026-07-26 per KM/G word
**Closes:** S4 gap G1 (BOOK_CODE_AUDIT wave-1 unblocker #1) — the composed 3-layer
enforcement leg S2-V3 ch4's own receipt marks "the build."
**Sources (transcription, not invention):** S4-V1 Ch4 (K1–K4) · S2-V3 ch2 (policy as
YAML) / ch4 (enforcement at the write, not review after the fact) / ch5 (per-action-class
gating) · existing code (`obligations/ledger.py` open/approve/close ·
`compliance/human_approval_gate.py` DENIED disposition · `obligations/quorum_guard.py` ·
`compliance/policy_loader.py` — whose silent permissive placeholder this spec retires).
**Fences:** rules constrain writes to the ledger; they never author writes. Nothing here
touches `cmd_seal`. money_path stays OFF.

---

## 1 · Design rule: the rule fires AT the write, or it isn't a rule

Advice reviews after the fact; **policy refuses at the write**. Every rule in a policy
document binds to one or more of the three existing write points — `open()`, `approve()`,
`close()` — and its only power is **refusal with the rule cited**. There is no
post-hoc scan lane in this spec: a rule that cannot be evaluated at a write point does
not belong in the document (put it in review tooling instead, honestly labeled).

## 2 · Rule-document schema (YAML; loads through the existing PolicyLoader path)

```yaml
# specs/governance/<policy_id>.yaml — extends the existing policy document shape;
# new top-level key `write_rules:` so legacy documents stay valid unchanged.
id: <policy_id>
version: "1.0"            # monotonic; amendments bump it (see §6)
write_rules:
  - id: ISSUANCE-2        # stable, citable id — appears verbatim in every refusal
    applies_to:           # selector — ALL listed conditions must match
      kind: token.mint    #   entry kind glob (e.g. token.*) and/or
      classification: material   # action class, both optional but ≥1 required
    predicate: {name: <vocab §3>, ...args}
    effect: refuse        # v0.1 has exactly two effects: refuse | require_second_approver
    message: "mint above ceiling requires charter amendment"   # human sentence, shown with the id
```

- Unknown predicate name, malformed args, or empty `applies_to` ⇒ **the document
  refuses to load** (fail-closed at load, not at first use).
- Rule ids are unique per document; a duplicate id is a load failure.

## 3 · Predicate vocabulary v0.1 (deliberately minimal — covers every worked example)

| predicate | args | write point | worked-example source |
|---|---|---|---|
| `amount_ceiling` | `max: <Decimal str>` | open | ISSUANCE-class examples |
| `supply_cap` | `cap: <Decimal str>` (per token_id) | close — replay **including** the closing entry | S4-G2 §4 |
| `require_evidence` | `floor: E1\|E2` | close | TRUTH-class examples |
| `require_gate` | `gate: human` | approve — delegates to AH-1, adds nothing | K1/K2 |
| `forbid_class` | `class: <action class>` | open | charter forbidden classes |
| `threshold_second_approver` | `above: <Decimal str>` | approve — via `quorum_guard` amount-aware floor | K4 / S4-G5 |

No boolean composition in v0.1 (no and/or/not trees). One predicate per rule; several
rules express what composition would. Vocabulary grows only when a sealed chapter
demands a predicate — never speculatively.

## 4 · Enforcement + refusal semantics (mirrors AH-1, exactly)

- At each write point the ledger evaluates matching rules **before** the write.
  First failing rule ⇒ the write is **refused** and a refusal record is appended —
  the same recorded-disposition pattern as AH-1's DENIED: `{refused_at, write_point,
  rule_id, policy_id, policy_version, message, entry_ref}`. A refusal is a ledger
  fact, not an exception swallowed in the caller (TRUTH-2: the record of the "no"
  is as durable as any "yes").
- `require_second_approver` effect does not refuse — it raises the quorum floor for
  that entry (quorum_guard path); an approve() that doesn't meet the raised floor is
  then refused with the rule cited.
- Evaluation order: document order, deterministic. Replay of a chain re-derives the
  same refusals given the same policy versions (§6 makes versions replayable).

## 5 · The loud fallback (retires the placeholder)

`policy_loader.load_policy` currently fabricates a permissive placeholder when no
document is found — a green light with no bulb. Under this spec, for any ledger
constructed with policy enforcement **enabled**: missing/unloadable policy document ⇒
**every material write refuses** with rule id `POLICY-0` ("policy declared but not
loadable — fail-closed"). Ledgers with no policy declared behave exactly as today
(433 tests untouched). The placeholder path is retained only behind an explicit
`allow_placeholder=True` for dev harnesses, and it stamps `policy_version: "PLACEHOLDER"`
on every entry it blesses — visible in replay, impossible to mistake for governance.

## 6 · Policy amendment is a sealed event

A policy document change becomes effective only through a **material obligation**
(`policy.amend` kind): evidence = the new document's file hash (E2), AH-1 human gate,
sealed like any other entry. Replay applies rules **as-of** each entry's time —
the policy version cited in a refusal is the version that was in force, forever.
The PolicyLoader's Merkle root over document content is the attestation hook;
**sealed-host caveat stated honestly:** on today's substrate that root attests
content integrity web-of-trust-locally — anchoring it externally rides the existing
SEALED-HOST-SEAM sentinels and is NOT claimed here.

## 7 · Non-goals (fence, explicit)

No rule engine DSL, no boolean trees, no runtime rule authoring by agents · no
post-hoc scan lane dressed as enforcement · no policy that can *create* writes ·
no change to AH-1's authority (a rule may demand the human gate; nothing may waive it).

## 8 · Acceptance tests (build = these pass)

1. Document with the six v0.1 predicates loads; unknown predicate refuses to load.
2. `amount_ceiling` breach at open ⇒ refusal recorded with rule id + version; nothing appended as an obligation.
3. `supply_cap` breach at close of a `token.mint` ⇒ refused; replay-including-entry math per S4-G2 test 7 (shared fixture).
4. `require_evidence: E2` with E1 evidence at close ⇒ refused, rule cited.
5. `threshold_second_approver` above threshold: single approve refused; two approvals (distinct principals, proposer excluded) seals.
6. `require_gate: human` composes with AH-1 — simulated approval still DENIED path, real gate passes; refusal record shape identical to AH-1's.
7. Missing policy document on an enforcement-enabled ledger ⇒ POLICY-0 refusal on material write; placeholder only via `allow_placeholder=True` and stamps PLACEHOLDER.
8. `policy.amend` flow: new version effective only after seal; pre-amendment entries replay under the old version (as-of correctness).
9. Refusal records survive replay byte-identically; chain verify stays green.
10. Existing 433-test suite stays green with no policy declared (no behavior change by default).

∞Δ∞

---

## Addendum — reconciled against Tiger's B5 substrate contract (workbench 2bcf59b, starter 23a081d)

- **Intercept points confirmed against live code:** the contract confirms there is *no policy
  consult today* on `open/close` — those two are the intercepts (§1/§4 as written). The
  `approve()`-point enforcement in this spec is **not a third intercept**: it is the quorum-floor
  raise through the existing `quorum_guard` path plus AH-1 delegation — no new gate code, per
  the contract's "exists ≠ wired" framing.
- **Refusal contract bound:** refusals raise in the `EconomicActionRefused` posture (loud,
  fail-closed, proposed obligations left open on the chain — B4's `_try_gate` precedent) AND
  append the §4 refusal record. Raise-and-record, never raise-only: the "no" must survive replay.
- **A4 precedent honored:** refuse-at-load (§2) mirrors the adversary's unattested-card
  refusal exactly as the contract recommends; refuse-at-the-write-with-rule-cited is §4.
- **Declared-config-never-constants:** confirmed — every threshold/cap/floor in this spec
  lives in the policy document (§2/§3); zero constants, matching B4's required-`threshold`
  (no-default) discipline.

∞Δ∞

---

## Build notes v0.1 (AA web-side, 2026-07-26)

**Module locations.** Rule documents, the 6-predicate vocabulary, evaluation, refusal records:
`src/sovereign_agent/obligations/write_rules.py`. Ledger insertion points: `ledger.py` —
constructor `write_policy=` / `allow_placeholder=` (declaring a policy is the enforcement opt-in);
`_open_write_checks()` / `_approve_point_policy()` / `_close_write_checks()` at the three write
points; `_refuse_write()` implements raise-AND-record; `_policy_in_force()` derives the active
policy by replay fold. The §5 retirement landed in `compliance/policy_loader.py`: `load_policy`
now RAISES `PolicyNotLoadableError` on a missing document; the placeholder survives only behind
`allow_placeholder=True` and stamps `version: PLACEHOLDER`. Acceptance tests:
`tests/test_policy_at_write.py`, numbered 1–10 to §8 (test 3 shares G2's supply-cap fixture;
test 10 = no policy declared ⇒ entry-for-entry identical shapes).

**Module-location choice (stated loudly).** `write_rules.py` lives in `obligations/`, not
`compliance/`: the ledger's write points import it, and importing `compliance.write_rules` would
execute `compliance/__init__` → `compliance_engine` inside the ledger import path (heavier,
cycle-prone). The "loads through the existing PolicyLoader path" clause is honored structurally:
`load_write_policy` accepts a PolicyLoader-loaded `Policy` object (duck-typed on `.raw_content`),
a dict document, a YAML path, or a `WritePolicy` — same document shape, `write_rules:` key added,
legacy documents load unchanged.

**Ambiguities resolved (stated loudly, not guessed silently):**
1. *threshold_second_approver.* At open() a matched rule raises the quorum floor to 2 through the
   existing quorum_guard compose (stamped `quorum` + `quorum_source: "rule:<id>"` — replayable
   provenance; class floors and rule floors compose as floors, higher bar wins). approve() keeps
   the existing Slice-2.2 semantics EXACTLY: a 1-of-2 approval appends and does not raise (that is
   how quorum-pending approvals already behave). The spec's "an approve() that doesn't meet the
   raised floor is then refused with the rule cited" is delivered at the close() write point —
   where an under-floor EXECUTION is actually attempted — as a recorded refusal citing the rule
   (acceptance test 5). Rule floors bind the material class only (AH-1's boundary, same as
   class_quorum).
2. *require_gate adds zero code by design* — it loads/validates (`gate: human` only) and delegates
   wholly to AH-1; the DENIED record shape is byte-compatible with a policy-less ledger's (test 6).
3. *POLICY-0 scope.* Refuses MATERIAL writes only (§5's words); non-material writes proceed on a
   declared-but-unloadable-policy ledger.
4. *As-of versioning.* Implemented as as-of-CHAIN-POSITION, not wall-clock: the active policy is
   `active_policy(entries, declared)` — a fold taking the LAST SEALED (executed, not rejected)
   `policy.amend` entry, whose full document + sha256 travel ON the debit (validated loadable at
   open, E2-hash evidence enforced at close). On an append-only chain this is the same ordering
   §6 names by time. Historical refusal records permanently carry the version in force at their
   write (test 8 asserts 1.0 / 1.0 / 2.0); a fresh instance over the same chain re-derives the
   same active version. Compromise stated: there is no retroactive rule re-EVALUATION lane — the
   durable refusal records ARE the as-of derivation, which is §4's own posture (replay re-derives
   the same refusals).
5. *Amount source.* `token.amount` first, else `lgp.economic_value` (the B4 denomination seam). A
   matched amount rule with NO readable amount refuses loudly — never a silent pass.
6. *Load strictness.* Rule/effect pairing is fixed at load (threshold_second_approver ⇔
   require_second_approver); duplicate ids, empty applies_to, unknown selectors/predicates,
   float-typed Decimals and float YAML versions all refuse to load.
7. *Evaluation ordering at close.* Policy close rules run after the evidence-tier guards and
   BEFORE the human-primacy approval guard, so a rule-cited refusal is not masked by the generic
   gate message. Applies only to policy-declared ledgers (opt-in, no default-path change).
8. *classification selector* matches the entry's `classification` field verbatim — operator
   vocabulary, no meaning hardcoded.

**Not delivered (loud):** external anchoring of the document Merkle root — exactly as §6 already
scopes (SEALED-HOST-SEAM; not claimed). No boolean rule composition, no runtime rule authoring
(§7 fences). Suite proof: 442 baseline tests green before, 462 (442 + 20) green after; zero
existing tests modified. `cmd_seal` untouched; money_path OFF.

∞Δ∞
