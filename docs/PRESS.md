# The Press — manifest-driven, receipted, human-gated builds

The Press rebuilds the artifacts your node's manifest describes — one volume, a series,
or everything — through declared gates, under receipts, with exactly one gate that never
automates: **the human seal**. It was built for a book catalog whose own thesis it enforces
("a revision is a rebuild, not a rewrite"), but the engine is generic: if your artifact can
be built by a command and judged by commands, the Press can conduct it.

```
python -m sovereign_agent.press build VOL-01        # one volume
python -m sovereign_agent.press build S1 --mode double
python -m sovereign_agent.press build --all --mode parallel   # proposes a wave; a human opens it
python -m sovereign_agent.press status | report S2 | selftest
python -m sovereign_agent.press bundle EX-01         # write the offline recovery bundle
python -m sovereign_agent.press build --offline EX-01
python -m sovereign_agent.press harden VOL-01       # hardening floor -> promotion proposal
python -m sovereign_agent.press run  VOL-01 --seeds seeds/VOL-01   # book rail: cycle→settle→assemble→board
python -m sovereign_agent.press seal VOL-01 --word "<the word>"    # the human seal, at a keyboard
```

## The laws (enforced in code, not promised)

1. **The Press never publishes and never seals.** No such code path exists. Completed volumes
   append to a FIFO `seal_queue.json`; a person seals. Waves (parallel mode) are *proposed*
   (exit 3) and opened only by `--approve-wave` matching the proposal exactly. Promotions to
   Provisional are *proposed* and flipped only by `--approve-report <sha-of-a-real-report>`.
2. **Default-deny.** No manifest entry → no build. PLACEHOLDER in an entry → no build. A
   generator step without a fresh PASS seed-adversary record → no generation. No bundle → no
   offline build. Unknown CLI arguments → refusal, never silence.
3. **Parity fails loud.** A reprint (sealed stage + `freeze_sha`) must reproduce its frozen
   sha byte-for-byte or the run FAILS, the bundle keeps the evidence, and `final/` is restored
   untouched. Pin `SOURCE_DATE_EPOCH` in build commands to make byte-parity achievable.
4. **Receipts are append-only.** Every run writes a content-hashed `run.json` bundle; every
   transition appends to `queue_log.jsonl`; every model-run step is stamped with the model
   that ran it (`model: none` for deterministic steps — gates never relax by model class).
5. **Demotion never waits; promotion always does.** Any hardening-floor finding auto-demotes
   `provisional → built` with a reopen receipt. Every promotion requires the human word.

## The book-drafting rail (seed → cycle → settle → board)

A catalog volume is drafted from **seed cards** — one per chapter, each carrying `beats`,
`prose`, an `extrusion` ledger (the code claims), and a `receipt_box` — not a manifest `build`
line. One command drives a title from seeds to a board-ready package, halting before the two
gates a machine may not cross:

```
python -m sovereign_agent.press run  <vol> --seeds seeds/<vol>   # cycle → settle → assemble → board_package
python -m sovereign_agent.press cycle <vol> --seeds DIR          # the gate battery alone
python -m sovereign_agent.press settle <vol> --seeds DIR         # fold a PASS bundle back to the source seeds
python -m sovereign_agent.press assemble <vol> --seeds DIR --out FILE
python -m sovereign_agent.press seal <vol> --word "<the word>"   # the human seal, at a keyboard
```

`run` STOPs the instant any stage refuses; a clean run ends **"staged for AA board"**, never
sealed. The two human gates ahead are the **AA board** (the binding reader/parity judgement)
and the **KM seal** (`cmd_seal → read_word`, a word typed at a keyboard — the same law as §1).

**The cycle gate order (`gate_rev`, stamped on every cycle receipt — Full Production ERP (S5) ran rev-9):**

1. **adversary L0** — deterministic, no model: weasel lexicon · ungated present-tense
   accomplishment (a runs-today claim must be backed by the card's `runs_today`) · full-name
   density (pronominalize after first mention) · duplicate 10-word shingles across chapters ·
   repeated question-hinge (the same interrogative opener ≥3× volume-wide is a template tell).
2. **prescreen** — the deterministic canon/voice/claims gate between L0 and L1, carrying **D12**:
   every forward marker (`designed-toward`, `is designed, not`, `not yet built`, `closes in`, …)
   must name a **closing home** within ~200 chars — a volume/series id (`S8-V4`, `Series 8`), a
   spec path (`*.yaml`), `live-runtime cutover`, or `OPEN-DECISION:<owner>` — or KILL. A
   charter-barred capability is homed nowhere by principle: it carries no forward marker at all.
3. **adversary L1** — one chapter per call on the local model host (rental-safe: refuses the
   local call unless the shared GPU is idle). Judges served-beats and overclaim against
   `runs_today`; a claim scoped larger than its evidence (an ERP-scale noun on a book↔code-only
   primitive, an operator-cockpit surface asserted as running) is refuted.
4. **co-extrusion** — every extrusion claim proven against the code. **PRESENT** ⇒ its
   `target_module` exists AND its `acceptance_test` passes *now* (pytest) — no "code later" for a
   claim the prose treats as present. **HOLD** ⇒ must carry `blocks_seal: true` and a `closes_in`
   home; a HOLD with no home, or one naming *this* volume, is a defect, and a HOLD whose test
   path does not exist yet is a recorded `test_pending` warning, never a silent drop.

A cycle PASS requires all four in order; a FAIL never advances (nothing settles, nothing stages).

**D12 also runs on the assembled interior.** Beyond the per-card seed-side gate, `run`'s
board-package step (`board_stage1.continuity_check_assembled`) scans D12 over the **whole
rendered interior** — receipts and Cast-&-Canon apparatus included — so a fully-homed volume
reads **0 unhomed forwards end to end**, not merely per card. Any unhomed marker STOPs the
package. (Guardrail added 2026-08-01; the Full Production ERP (S5) board packages pass it at 0.)

**The receipt label is itself D12-clean.** A chapter with designed-toward HOLDs renders
"**Designed-toward — named closing home.** Closes in `<home>`." — the closing homes are named
*in the label*, so the label never injects an unhomed marker into the interior. A chapter with
nothing designed-toward renders its deployment note under a non-marker heading instead.

**The front-matter count is claim-plus-test honest.** The counts table reads
"*N* claims, backed by *M* distinct acceptance tests": one read-only route legitimately backs
several claims, so the raw claim count is shown beside the distinct-test count rather than
mis-read as *N* independent mechanisms.

## The manifest

```yaml
volumes:
  EX-01:
    title: The Node Charter
    series: EX                    # series = a parallel lane; volumes in a lane run in DAG order
    stage: drafting               # closed enum — an unknown stage FAILS the build
    depends_on: [EX-00]           # topological scheduling; roadmap:* = event-class deps
    workdir: charter_src
    generator: null               # optional pre-build step; adversary-gated when present
    build: sh -c "cp charter.md charter.txt"
    gates:                        # each gate = one decidable command; first failure halts
      - sh -c "test -s charter.txt"
    artifact: charter.txt
    freeze_sha: <sha256>          # present + sealed stage => reprint w/ byte-parity law
harden:                           # code lane (books keep their own stage enum untouched)
  EX-01:
    code_file: <path>             # posture-linted (K2/K3/K4 heuristics)
    adversary_vol: EX-01
    checks: [...]                 # the floor: every check must pass; skips fail loud
```

Stage enum: `concept-formation · outline-locked · drafting · built-in-review ·
sealed-publication-ready · sealed-awaiting-author · pre-order · published · shelved`.
NOTE: values must not contain a raw `#` (the stdlib mini-loader strips inline comments; a
pyyaml swap is queued).

## Where things live (the engine has no home)

- `PRESS_HOME` — manifests, `press_runs/`, reports, `code_status.json` (default: cwd).
- `PRESS_DATA_ROOT` — node data consumed by the tools (adversary records, roadmap).
- Every path is env-overridable; defaults never leave `PRESS_HOME`. Node-private data
  (manifests, content, coordination state) never ships with the engine.

## Offline recovery (the Book Source Bundle)

`press bundle <vol>` writes `<workdir>/bundle/`: every source file + sha, the manifest
entry, and a pinned environment record (python, renderer, `SOURCE_DATE_EPOCH`). The bundle
lives **inside the volume's own tree** — git itself is the offline distribution channel;
every clone is a recovery medium. `press build --offline <vol>` rebuilds from the bundle
ALONE in an isolated workdir: a missing file refuses, a tampered file refuses loud, and the
parity law applies unchanged. No book embeds any other book.

**The byte-parity domain (A1).** Renderer version + epoch are necessary but not
sufficient: text-identical rebuilds can still differ in bytes when the *font files*
differ. Declare `font_files:` on a volume and the bundle records each font's sha in its
environment manifest; an offline rebuild compares the host's fonts against those pins and
warns loud on drift, naming the cause up front — the parity gate itself remains the
enforcement. Full byte-parity is guaranteed on **pinned-env hosts**: same renderer, same
epoch, same font shas.

**Gates travel with the volume (A2).** Declare `gate_files:` and the named scripts are
staged to `<workdir>/.press_gates` on every build, copied INTO the bundle, and restored
from it on offline rebuilds under the same laws as sources (missing refuses, tampered
refuses loud). Gate commands reference them as `$PRESS_GATE_DIR/<name>` — the Press
expands that token itself, shell or no shell — so the same manifest line runs the same
gate bytes on the authoring node, a pure kernel node, and an offline rebuild alike.

## The Provisional lifecycle (code lane)

`built → provisional → sealed`, tracked in `code_status.json` with full history. The
hardening floor (`press harden`): every extrusion binding VALIDATED · zero-skip tests ·
fresh adversary PASS · constitutional posture. Floor PASS stages a proposal; a human
promotes citing a Series Status Report's sha (`press report <series>` — a pure projection
of receipts). Any later floor finding auto-demotes, receipted. Provisional artifacts carry
their label on every surface — an artifact never claims more maturity than its ledger.

## Constitutional mapping

**K1** — every material transition (seal, wave, promotion) begins and ends with a living
human decision; absent the gate, the action fails closed and is recorded. **K2** — deny by
default, everywhere. **K3** — hash-chained, append-only receipts the operator holds.
**K4** — new gates enter by declaration in the manifest, never by silent self-extension.

## First run (the shipped example)

```
cd examples/two_document_catalog
python -m sovereign_agent.press build --all      # two documents, DAG-ordered, gated
python -m sovereign_agent.press status           # seal queue: 2 unsealed, awaiting a person
python -m sovereign_agent.press bundle EX-01
python -m sovereign_agent.press build --offline EX-01
```

∞Δ∞ *A tool you cannot leave with is a cage. This one ships its own way out.*

**The seed-unit law (A4).** The adversary judges inputs literally, so the law is
enforced where the inputs enter: every seed card must attest `seed_unit: full_chapter`
and `beats_locked: true`, carry at least one non-placeholder beat, and hold prose that
is a complete unit (three or more sentences, ending at a sentence boundary). The
boundary check is furniture-aware: a chapter may lawfully end with typesetting
furniture (`\newpage`, rules, headings, bold-only lines) — the check reads the last
prose line beneath it, so furniture never launders an excerpt and never falsely
kills a finished chapter. Unlawful cards are refused loud at load — an excerpt is
never judged, a scaffolding beat is never treated as a promise. Tooling, not
convention.
