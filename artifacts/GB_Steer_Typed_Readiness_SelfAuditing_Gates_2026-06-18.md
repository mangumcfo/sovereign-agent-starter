# GB Steer — Typed Readiness + Self-Auditing Gates (the autonomous, self-capturing rail)
*KM asked GB to steer: "the rail should have autonomy and capture issues like this itself." Synthesis of three voices — GB (gate-completeness meta-gap), Lumen (readiness is typed, not boolean; every gate declares its consumer), KM (autonomy: the rail self-captures). This is the unifying fix for the V3 class of failure. Lean — reuses the contract/lints/obligations; no gate explosion.*

## The root cause, sharpened (Lumen, accepted)
The rail didn't fail for lack of intelligence. **It failed because "ready" was a boolean when it needed to be a typed state.** The contract checked `review_ready = boards + obligations + fidelity + brief`. KM needed `human_review_ready = …+ reviewable artifacts`. Different predicate. The fix is not "add more checks to one ready" — it's to **type readiness** and make **each gate declare its consumer.**

## The unifying primitive (GB gate-completeness, made autonomous per KM)
**Every gate declares — and at flip-time self-checks — four things:**
```text
consumer:        who is this gate serving?               (e.g. KM doing human review)
decision:        what decision will they make?           (accept/amend the 6 judgment calls)
required:        what artifacts must EXIST for that       (PDF · figures · cover · /seeit · KDP)
                 decision to be real?
evidence:        what proves each artifact is present,    (file resolves · current commit · renders)
                 current, and correct?
```
A gate with no declared consumer + artifact manifest is **incomplete by construction** — and the rail refuses to flip it. This is gate-completeness operationalized: not a one-time manual audit, but a property each gate carries and checks **itself, every flip.** That is the autonomy KM asked for — the rail captures its own incompleteness instead of a human discovering it at the end. **A missing manifest item doesn't silently pass; the gate stays red and mints an obligation naming exactly what's missing.**

## Readiness MODES (typed, but FEW — bloat guard)
A short ladder, not an explosion. Each mode = a gate with its consumer + manifest:
| Mode | Consumer | Manifest must include |
|------|----------|----------------------|
| `content_ready` | the boards | manuscript + outline coverage |
| `board_ready` | the rail | 3 editorial + UX + Tech/Arch RIGOR-PASS · Gate 6 |
| `claim_ready` | truth | every capability-promise has a resolving proof (Living Claim Rail) |
| **`human_review_ready`** | **KM (human review)** | **board_ready + fidelity + brief + the ARTIFACT PACKAGE (PDF · v2.0 figures · cover · /seeit · KDP structure)** |
| `distribution_ready` | the distribution lane | covers/metadata per channel |
| `publish_ready` | KDP/ACX | sealed + KDP files validated |

`review_ready` as used today was really `board_ready` *mislabeled* as `human_review_ready`. That mislabel IS the V3 bug.

## Immediate fix — the Artifact Package Gate (#6, for Tiger)
The concrete `human_review_ready` manifest, machine-checked, blocking:
```yaml
artifact_package:
  book_id:
  package_type: human_review
  commit:                 # the manuscript version the package was built from
  required:
    - manuscript_pdf:      final/*.pdf exists · built from current commit
    - figures:            v2.0 figures present · caption-bug-clean
    - cover:              front/spine/back to v2.0 standard
    - seeit_pages:        core-chapter /seeit pages live (seeit_lint pass)
    - kdp_structure:      KDP-ready file layout confirmed
  evidence: [path-resolves · commit-current · renders-clean]
```
`human_review_ready` **cannot flip** until every `required` item resolves with evidence. Tiger adds this to `review_ready_contract` as the 5th check (the one I missed). GB specs the criteria above + verifies; this is what closes V3.

## How the rail self-captures going forward (the autonomy)
Because each gate carries its consumer + manifest, **the gate evaluates its own completeness every time it's asked to flip.** A missing/stale/incorrect artifact → gate stays red + mints a B32 obligation ("human_review_ready blocked: cover not built") → surfaced in Atrium. No human reaches an empty package; the rail names the gap before the gate opens. The gate-completeness audit becomes a runtime property, not a hope.

## Relation to the Living Claim Rail (one shape, two concerns)
The claim rail protects **truth** (claim → proof_refs). The readiness manifest protects **delivery** (gate → artifact_refs). **Same shape — a thing that must resolve with evidence before a state flips.** Truth and delivery, both gated, both self-checking. The claim rail is `claim_ready`; the artifact package is `human_review_ready`. They compose; neither substitutes for the other.

## Bloat guard (Lumen's standing warning)
Six modes, not sixty. No new boards. The modes are *labels on the existing contract's outputs* + one new check (artifact_package). Reuse: contract, lints, B32, Claim Rail. If it grows a mode without a real consumer, or a board, it has bloated — stop.

∞Δ∞ The rail captures its own blind spots when every gate must name its consumer and prove that consumer has what they need. "Ready" stops being a hopeful boolean and becomes a typed state that checks itself. The human reaches a complete package or the gate never opens — and the rail says, in red, exactly what's missing. — GB
