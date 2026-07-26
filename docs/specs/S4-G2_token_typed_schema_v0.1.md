# S4-G2 — Token-Typed Schema Spec v0.1 (spec-first; the series' namesake layer)

**Status:** STAGED for Tiger/GB review · authored web-side (AA) 2026-07-26 per KM/G word
**Closes:** S4 gap G2 (BOOK_CODE_AUDIT wave-1 unblocker #2) — GB-confirmed absent from src/
**Sources (transcription, not invention):** S4-V1 *The Sovereign Token Substrate* Ch2–3
(conventions locked in prose) · Ch4 (K1–K4) · S4 framing decision 4 (KM: "the standing
S4 accounting-framing pattern") · existing code conventions (`obligations/ledger.py`,
`evidence.py`, `projection.py`, Decimal-exact per `yield_organism/value_flow.py`).
**Fences:** private, ledgered, receipt-derived only. Never a coin, never floating,
never exchange-tradeable. money_path stays OFF. Nothing here touches `cmd_seal`.

---

## 1 · Design rule: token events ARE balanced obligations

No parallel ledger. A token event is a **B32 obligation with token legs** on the
existing chain — same seal, same hash-chain, same gate, same replay. The book's
conventions, encoded:

- **credit = increase** to an account's token balance; **debit = decrease**.
- Two **system accounts per token_id**, neither ever "circulating":
  - `issuance_authority` (IA) — the contra source. Supply enters circulation only by
    debiting IA. IA's balance is definitionally negative-or-zero (contra).
  - `supply_retirement` (SR) — the burn sink. Supply leaves circulation permanently
    only by crediting SR.
- **Entry kinds and their mandatory legs** (exactly two legs, always balanced):

| kind | dr (decrease) | cr (increase) | evidence floor | gate class |
|---|---|---|---|---|
| `token.mint` | issuance_authority | holder | **E2** | material — AH-1 human gate, always |
| `token.transfer` | sender holder | receiver holder | **E1+** | per policy (S4-G1); default material |
| `token.redeem.return` | holder | issuance_authority | **E2** | material |
| `token.redeem.burn` | holder | supply_retirement | **E2** | material |

Burn-vs-return is distinguished **by target account** (the book's rule), never by a
flag. There is no `token.adjust`, no balance-set, no mutation kind — corrections use
the existing reopen/reference pattern (a new balanced event citing the prior one).

## 2 · Field schema (extends the existing entry; no schema break)

```yaml
# additional fields on an obligation entry when kind is token.*
token:
  token_id:   str        # charter-registered id; unregistered id => refuse at open (S4-G1 rule TOKEN-1)
  amount:     str        # Decimal string, > 0, precision per token policy (default 18); Decimal-exact math ONLY (code convention)
  dr_account: str        # account id per §1 legs table
  cr_account: str
  memo:       str        # optional, never load-bearing
# holder identity model: an account id is a principal id (same identity space as
# approved_by/owner) or a declared entity account registered via node_identity —
# no new identity system is introduced by this spec.
```

Validation at `open()`: legs match the kind's table exactly · amount parses as
positive Decimal within precision · token_id registered · dr≠cr. Any failure =
refusal with reason (never a silent drop).

## 3 · Derivations — never stored, always replayed

- `balance(token_id, account, as_of=None)` = Σ cr − Σ dr over **closed** (sealed)
  token entries, by replay (`projection.py` extension). Open/refused entries count 0.
- `circulating_supply(token_id)` = Σ balances over holder accounts
  = −balance(IA) − balance(SR) (identity check — both computed, MUST agree; disagreement is a
  loud integrity breach).
- **Checkpoint** = a sealed `token.checkpoint` attestation entry:
  `{as_of_entry_hash, token_id, balances: {account: amount…}, chain_tip}` — E2,
  material-gated. A checkpoint **never substitutes** for replay: verification
  recomputes from genesis (or prior verified checkpoint) and any drift is a named,
  loud breach ("a drifted checkpoint cannot quietly stand" — V1 Ch3). Replay-to-date
  rides S3-G1's `as_of` parameter when built; until then checkpoints verify against
  full-genesis replay only.

## 4 · Gates & caps (composition with existing built code)

- Mint/redeem are **material**: AH-1 fail-closed human gate + proposer-exclusion +
  `class_quorum` floors all apply as already built and tested. No new gate code.
- **K4 cap-tiering (S4-G5, unblocked by this spec):** token policy may declare
  `second_approver_above: <amount>`; `quorum_guard` gains an amount-aware floor
  (quorum=2 when `amount > threshold`). Declared in policy (S4-G1), enforced at
  approve().
- Supply cap: `supply_cap: <amount>` per token_id — enforced at close() of any
  `token.mint` by replaying supply **including the closing entry** (S4-G1 rule class).

## 5 · Non-goals (fence, explicit)

No transfer surface to external systems · no pricing, pools, or AMM (separate spec,
post-B3 ruling) · no fade/yield math here (yield_organism consumes balances read-only)
· no floating token, ever · staking schema (S4-G4) composes ON this later — this spec
deliberately ships without it.

## 6 · Acceptance tests (build = these pass; the spec is done when the list is green)

1. mint→transfer→burn round-trip: balances and supply replay correctly; IA/SR identity holds.
2. Unbalanced/foreign-leg token entry refused at open with reason.
3. Mint without real human gate → DENIED recorded (AH-1 path), never sealed.
4. Transfer with E0 evidence refused at close (`require_e1` path).
5. `token.redeem.burn` vs `.return` land in SR vs IA respectively; supply reflects burn only.
6. Checkpoint seals; tampered checkpoint → loud drift breach on verify.
7. Supply-cap breach at close refused, rule cited (needs S4-G1 wire; until then the
   check lives in the token validator with the same refusal shape).
8. Amount precision overflow / negative / zero → refused at open.
9. Replay determinism: byte-identical balance map across two replays.
10. Existing 433-test suite stays green (no schema break).

∞Δ∞

---

## Addendum — reconciled against Tiger's B5 substrate contract (workbench 2bcf59b, starter 23a081d)

The contract packet landed after this spec was staged; reconciliation, point by point:

- **Ground truth advanced:** starter main is now `23a081d` (B4 Tiger-half: Breath-26 engines
  wired). Verified: nothing in that commit conflicts with this spec; B4's adapter books value
  as **free-string `lgp` attribution blocks** (`economic_value`, `denomination`,
  `money_path: OFF`) on paired dr/cr obligations — the exact seam the contract names.
- **The denomination seam, made explicit:** B4's `denomination`/`denomination_in/out` strings
  are the pre-schema surface; this spec is their law. When G2 builds, a denomination string
  resolves against the charter-registered `token_id` space (unregistered ⇒ refuse at open,
  rule TOKEN-1). The `token:` block supersedes free-string denomination **for `token.*` kinds
  only**; existing sealed B4 entries are never rewritten (append-only — coexistence, not
  migration).
- **Contract recommendations already honored as written:** field-extensions + projection-fold,
  not a parallel store (§1/§3) · valuation/fee model left to B3 (§5) · stake greenfield,
  composes later as S4-G4 (§5).
- **Refusal idiom bound:** G2 validation refusals at the adapter surface ride
  `EconomicActionRefused` (the PermissionError family, loud, fail-closed, proposed entries
  left open) — extended, never bypassed; the ledger-level refusal record shape is S4-G1 §4's.

∞Δ∞
