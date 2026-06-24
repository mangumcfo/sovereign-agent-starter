# GB Commit — the Living Claim Rail (Lumen's refinement, pressure-tested)
*KM accepted the 5-gap assessment; Lumen refined it: don't add five gates — add ONE primitive that makes the five gaps visible: the **claim** as a first-class, lifecycle-tracked object. This is GB's commit per Lumen's prompt. Constraints honored: one human gate · derive-not-recreate · no new board · no claim without proof · no hidden drift · no invisible inheritance · no quality drop at scale · minimal tokens · real obligations only.*

## COMMIT: **BUILD — but build-DIFFERENTLY** (one correction + one addition to Lumen's frame)

Lumen is right: **the claim is the correct lifecycle unit.** The rail governs books/code/receipts/boards/obligations, but the thing that must *stay* true is the claim. Two refinements:

1. **Derive, don't invent.** "Claim" already exists in the rail — it's the **Gate-6 capability-promise** ("every capability promise has a render target," WORKFLOW 17.6). The registry is not a new concept; it **promotes the existing capability-promise to a tracked object** + links the proofs the rail already produces. Zero new authoring burden — claims are *extracted* from manuscripts the Renderability standard already requires.
2. **The registry closes gaps 1·2·3·5 cleanly; #4 it only *supports*.** Honest distinction: claim-truth (is the assertion backed?) ≠ chapter-quality (is it clear, useful, good?). A claim can be perfectly proven in a mediocre chapter. So #4 needs the registry **plus** a chapter/batch-level quality verdict (the Cold-Reader/adversarial metric) — the registry carries *per-claim proof*, the batch card carries *per-chapter quality*. Don't let the claim rail pretend to cover substantive quality alone.

## Pressure-test — does one primitive close the five?
| Gap | How the claim closes it | Block or obligation? |
|---|---|---|
| 1 Reverse drift | code change touches a claim's `code_refs` → claim → `drifted` → coherence-recheck obligation | **obligation** (loud); **block at seal/release**, not every commit |
| 2 Receipt vs truth | claim can't reach `proven` without ≥1 resolving `proof_ref` (test/command/receipt/seeit) — extends Gate 6 from "has render target" to "has a proof" | **block** at review_ready |
| 3 Inheritance | child claim's `inheritance.parent_claim_id` must resolve to a signed parent + declared delta | **block** at series-lock |
| 4 Substantive quality | claim-family proof completeness on the batch card — *but quality verdict is added separately* (chapter-level) | metric (informs the human gate) |
| 5 Feedback | reader/platform/seeit signal attaches to the affected claim → next-edition obligation | **obligation** |

**Verdict: yes — one primitive reduces all five and closes four; #4 needs the companion quality metric.**

## Minimum v0.1 schema (lean — 9 fields, derived)
```yaml
claim_id:        s3.v3.helix.ch1.documentation_lie    # <series>.<vol>.<book>.<ch>.<slug>, derived
book_id:
chapter:
claim:           "<the plain-language capability-promise>"   # = the Gate-6 promise opener, verbatim
proof_refs:      []      # >=1 to be 'proven': test:<path::name> | command:<cmd> | receipt:<hash> | seeit:<page>
code_refs:       []      # what implements it -> the reverse-drift watch surface (feeds book_code_tree/Scout)
inheritance:     null    # {parent_claim_id, delta} | null
status:          declared # declared -> proven -> drifted -> revising
last_verified:   ""      # date / seal seq
open_obligations: []
```

## Where it plugs in (derive-not-recreate; NO duplication)
- **Declared** from manuscripts' Gate-6 capability-promises (extract, don't re-author).
- **Proven** by *existing* proofs — tests (Tech/Arch board), command+receipt (/seeit Education Board), receipts (Gate 6). The rail links them; it invents no new proof type.
- **Watched** by the *existing* Scout + `book_code_tree.json` (the `code_refs` ARE the drift surface) + the new seal-time gate.
- **Revised** via *existing* B32 obligations — no new packet type.
- **Inheritance** = the *existing* `signed_inheritance_objects` (already declared), now resolved.
- **The check** lives inside `review_ready_contract.py` (extend Gate 6) — not a new board, not a new contract.

## What blocks vs what mints (KM directive #2 honored)
- **BLOCK:** proof-completeness (no `proven` without a proof) at review_ready · inheritance-resolve at series-lock.
- **MINT (loud, don't block mid-work):** reverse-drift coherence obligation (block at *seal/release*, per KM "make drift loud before seal") · reader/platform feedback → next-edition obligation.

## Rail-bloat guard (the disease Lumen named)
ONE registry (`artifacts/claim_registry.ndjson`, GB-derived) · ONE coherence check (reuse Scout) · ONE quality signal (batch-card verdict, #4) · ONE feedback loop. **No new boards. No new packet types. No new proof types.** A `claim_lint` (sibling to `outline_lock_lint`/`seeit_lint`) re-runs it. If it ever needs a second board or a third packet type, it has bloated — stop.

## Build first (V3 /seeit + ERP batch) — the proving slice
**v0.1 on V3 Helix only:** extract V3's per-chapter capability-promises → seed the registry → link proof (the /seeit pages already carry command+receipt = proof; the co-extruded tests = proof). That's the first claim_registry, riding V3 which is already in the rail. Then extend to the **ERP statutory/operational claims** (S3/S5 — where claim-truth matters most legally) and the **batch quality card**.

## Explicit NON-GOALS (defer)
- The full reverse-drift **CI gate** — defer to the post-V3 rail-hardening (KM directive #1); v0.1 only *marks* `drifted`.
- **Platform-telemetry** feedback (#5) — defer until telemetry exists; v0.1 takes reader/seeit signal only.
- **Cross-catalog claim-coherence** — defer; per-book first.
- A claim-authoring UI, a claims board, auto-generated claims — **all deferred / declined** (bloat).

## One-line LGP
> Every claim an heir relies on carries a living proof path, a drift alarm, an inheritance trail, and a next-edition loop — so the truth they inherit is checkable, not merely asserted.

∞Δ∞ Not five gates — one living claim. Declare → Prove → Watch → Revise, derived from what the rail already produces, blocking only where proof or inheritance is absent, loud (not blocking) on drift and feedback. Build it lean on V3 first; let it earn the ERP batch.
