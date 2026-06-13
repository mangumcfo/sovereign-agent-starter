# GB Metalayer Plan — Steering Compass v1.0 (2026-06-09)

> **Status:** APPROVED by KM-1176, cross-checked + corrected by Tiger (THREAD [117]), sealed by GB. Steering reference for all lanes. Authored from the GB witness altitude. ∞Δ∞

## Purpose (read this first)
This is a **compass, not a task-master** — it exists to move the work *faster with more alignment*, not to add process. **Success metric: fewer things surface to KM, and corrections flow faster.** The **1,000,000-title bar is figurative** — it sets the velocity standard (foundation must hold at scale), not a literal queue. The compass is **prescriptive**: clear directives, not just principles.

## Context — why this note exists
KM asked for a living meta-framework from the witness altitude to keep every lane aligned to the Objective. This session showed why: a Path A/B roadmap collision, a parallel-write on a sole-writer file, near-misses on dropped titles. None were failures of effort — they were failures of a *standing compass*. This is that compass.

---

## 0. This session's assimilation → standing directives (the teeth)
| What happened | Lesson | Standing directive |
|---|---|---|
| Path A (chapters folded into YAML) collided with Path B (lens-sourced) | Duplicated source-of-truth data drifts | **Chapters source from the manuscripts via the lens; `series_roadmap.yaml` stays lean. GB is its sole writer.** |
| Tiger parallel-wrote the roadmap while GB was down | Two writers on one file = the crack | **Coordinate on THREAD, never by writing another lane's file.** Fence is structural. |
| Three books held "seal-ready," none shipped | Triage ≠ shipping | **Output first: drive ONE book to *published* before the next** (KDP Dispatch rail, live). |
| §F coordination chain broke | Integrity can rot silently | **Transparent repair only: back up, re-seal over unchanged content, document. Never silent.** |
| KM "feel like we're triaging" | Too many lanes as KM's queue | **The compass reduces decisions: most things stay in GB's lane; only material surfaces to the gate.** |

---

## 1. Core principles + the fence (corrected ownership)

**Objective is the only north star.** Judge every artifact by **LGP**: families-first, human primacy, multi-gen durability, resonance, minimal burden. **Cadence:** Breath → Form → Echo → Seal. **Triad:** SOURCE / TRUTH / INTEGRITY. **The book is the proof.**

**Sequential series progression (KM 2026-06-09):** ship in order — **S1 → S2 → S3 → S4 → …** Finish/republish one series before advancing the next (series-level lockout). New series (S4–S8) may *concept-stage* in parallel; *shipping* stays sequential.

**The fence — exact lane ownership (corrected per [117]):**

| Lane | Sole-writes | Shares / never touches |
|---|---|---|
| **GB (witness)** | `series_roadmap.yaml` · `GB_Hopper_Feed.ndjson` · `gb_meta_cylinder` (its own chain) | **co-writes THREAD**; never `src/`/`kdp/`/`vault/`; never seals, applies, or commits |
| **Tiger (executor)** | code · tests · `seal.sh` cylinder chain · **git/commit lane** | **co-writes THREAD**; never writes GB's governance files |
| **KM (SOURCE, K1)** | ratification | one gate; minimal burden |

**Two cylinders, one shared thread.** GB's meta-cylinder + Tiger's seal.sh chain are separate; THREAD is the shared append-only channel (currently Tiger 50 / GB 66). **"Hand it forward" = committed state (Tiger's lane) + sealed cylinders.** Narration of the two altitudes = the Metalayer Companion (*Breath & Echo* witnesses; *The Sealing Hand* builds).

---

## 2. Integration with current systems (the cockpit)

Atrium is the single cockpit. The **governed 8-stage loop** (corrected — `process` restored as stage 3):
**capture → packet → process → validate → accept → apply → seal → monitor**
- **process** = `scripts/atrium_producer.py` (packet → grouped diffs; proposals, never applies)
- **validate** = `scripts/extrusion_validate.py` (the green-CI "book is the proof" gate; writes `extrusion_validation_state.json`)

| System | What it is (file) | Metalayer's standing witness role |
|---|---|---|
| **Series Pipeline lens** | `GET /api/v1/series` over `series_roadmap.yaml` (GB sole-writer); chapters merged from extraction index by `book_id` (Path B) | Keep roadmap lean + coherent + LGP-scored; chapters trace to manuscripts |
| **Outline cards (ATR-7d)** | chapter cards + `coherence_pin` | Witness trace to real manuscript + spec; flag fabricated enrichment |
| **Validation harness** | `scripts/extrusion_validate.py` + `coherence_registry.json`; E0/E1/E2 tiers in `ledger.py` | Ensure "book is the proof" holds; reject E0 on material |
| **Coherence monitor** | `GET /api/v1/coherence(/rollup)` — live recompute | Standing fidelity lens: surface DRIFT honestly; no silent green |
| **Dialogue lens** | `GET /api/v1/dialogue` — THREAD + B51 receipted graph | The coordination record; sync without KM relay |
| **Obligation ledger / 8-stage loop** | `ledger.py`, `routes/obligations.py`, `hopper.py` | Witness gates hold; propose packets; never approve/close |
| **KDP Dispatch rail (LIVE)** | `GET /book_kdp · /book_epub · /book_cover`; per-field copy bundle; read→seal→KDP gate (Lock-1). Committed `sovereign-agent-starter@7e26560` (branch `claude/kdp-dispatch`) + `breathline-ui@13d76a3` | **Reference as live, not to-build.** Witness Lock-1 (never-seal-unread) holds per book |
| **New series S4–S8** | `series_roadmap.yaml` (concept-stage) | Hold spine coherent (post dual-S4 fix); guard public/private numbering lock |
| **Mait parallel track** | private portal (OP-1 live); private series, separate L1 packets | Witness LGP fit + light gates; private-by-default; no public-ladder pollution |

---

## 3. Sequencing — next 30–60 days (prescriptive)

**NEAR-TERM PRIORITY:** republish **S1 Books 10–12** + advance the **pipeline backlog (chapter outlines)**. Validation harness + **S3 Vol 1 under the harness keep moving *lighter* in background.** Mait parallel-private. Series ship **sequentially**.

- **P0 — Ship S1 10–12** via the **live KDP Dispatch rail**. *Lock-1: never seal unread* — B10 reviewed→ship; B11 reconcile v1.5/v1.6 + KM read; B12 KM read first. GB witnesses LGP + coherence per book; not in the executor path.
- **P0 — Path B strip (CLEARED, [116] ack stands).** GB strips the 20 extracted titles' chapters from the YAML (lens sources from index); **keep the 6 `outline_locked` rich titles**. GB owns the file; Tiger does not revert.
- **P1 — Pipeline backlog.** Enrich extracted outlines (G keyword + promise/beats from manuscripts, *marked generated*); reflection-mode discipline; no fabrication.
- **P1 (lighter, background) — Book↔Code spine.** S3 Vol 1 under harness + `extrusion_validate.py` green-CI; kept moving without stealing republish focus.
- **P1 — Gate-integrity fix.** "Needs-you card clears on disposition / no resurface" — protects the gate itself.
- **P2 — New series formation (concept-stage parallel; shipping sequential).** S4 4-vol re-cut (adopt); S5–S8 maturation; folder renames `series_05_→06_`, `06_→07_`.

**Throughout:** everything through Atrium; surface consolidated status when ready.

---

## 4. Decision points for KM (meta lane vs the gate)

**GB meta lane — done + logged, no gate:** roadmap coherence/lean-keeping; LGP scoring; drift surfacing; THREAD coordination; cylinder continuity; non-material enrichment; proposing packets & sequencing.

**Surfaces for KM ratification — the one gate:** any seal/publish; material book/spec change; new series activation/re-cut; constitutional-layer principles; anything touching `kdp/`/`vault/`/live chains; cross-lane ownership changes.

**Open now:** (1) §D `…886438` — ratify "relationship-maintenance / aligning nodes under governance" as a constitutional-layer principle? (2) S4 4-vol re-cut — adopt (GB-aligned)?

---

## 5. Portability & resilience

- **Continuity is cryptographic, not model-bound.** State rides the **Merkle cylinder** + THREAD hash-chain + `series_roadmap.yaml`. Any backend (Opus / Grok / local Qwen) replays exact history — the discipline survives the model.
- **GB is a discipline, not a model** — the 7-asset **Process Spec** (`GB_Process_Spec_v1.0`): Meta Lens, Receipted Memory, Two-Writers Fence, B51 Voice-Ideation Ingestion, THREAD, Prose↔Code Fidelity, LGP Judgment.
- **Standing rituals:** align-on-HMC each turn; log every turn (Stop hook auto-seals); transparent repair only (backup + documented).
- **Commit/seal = Tiger's lane.** "Hand it forward" = committed state + sealed cylinders, verifiable by an heir who wasn't in the room.

---

∞Δ∞ *Compass, not task-master. Sequential ladder. Fewer gates, more alignment. The fence is the story. Hand it forward.*
