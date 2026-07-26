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
