# GB Session Handoff — 2026-06-10 (restart brief)

> **For the next GB-on-Opus session.** You boot with live HMC hydration + the role/Compass already injected by `claude-gb`. This is the "resume here" so nothing drops. Run the start ritual first: `gb_meta_cylinder.py manifest` · `thread.py show` · align on HMC · 50k-foot meta-lens. ∞Δ∞

## Who you are
GB — metalayer/witness altitude. **The fence:** GB **sole-writes** `series_roadmap.yaml`, `GB_Hopper_Feed.ndjson`, the GB meta-cylinder; **co-writes** THREAD. **Tiger** executes/commits/seals + owns git + `ASIN_TRACKER.yaml`. **KM** ratifies at one gate. Principle above all: **Book↔Code — derive, don't duplicate; single source; render, don't recreate.**

## Standing rituals (non-negotiable)
- **Align on HMC every turn** (pull the live cylinder); **capture the sealed HMC before any rollover** (a restart is a rollover — see "On this restart").
- **Log every turn** (Stop hook auto-seals `gb_turn_sealed`); rich content logged explicitly.
- **Transparent repair only** (backup + documented; never silent).
- **Pipeline edits → snapshot** (`scripts/pipeline_snapshot.py`, drop-off guard). Hook script ready; **PostToolUse wiring still pending KM's paste** (see open items).

## State of the board (what's done)
- **Publishing (S1):** B01–B07 **LIVE**, B08–B11 **pre-order**, **B12 = only one left** (KM read → submit). Truth lives in `ASIN_TRACKER.yaml`; the lens **auto-overlays** publishing_state (Tiger's `_publishing_index`, verified live — B10/B11 `pre_order_live`, B01 `published`). Do NOT hand-edit publishing_state in the roadmap.
- **Titles corrected to Amazon:** B10 → "Scaling AI Agents"; B11 → "AI Agents for M&A".
- **Enrichment COMPLETE:** every chapter, every series has chapter-level KW + outlines (224/224 in the index + rich S3/S4/S8). S2 canonical KW folded from `OUTLINE_V1_G.md` (vol_04: 6 ch flagged `pending G re-map` — manuscript reordered vs outline).
- **Path B:** chapters source from `extracted_chapter_outlines*.json` via the lens; roadmap stays lean.
- **S3 vol_01_immutable_core:** corrected `sealed`→`phase_1` (active build per `pipeline/active.yaml`; "sealed" was stale).
- **Metalayer Compass v1.0** sealed: `artifacts/GB_Metalayer_Plan_Steering_Compass_2026-06-09.md`.
- **seeit DECIDED (GB+G+KM aligned):** a **derived, non-technical operator training surface** rendered from the living books (primarily **S2**) via Helix, **inside Atrium** (lens/Review group), strict source-from-sealed-passages + auto-refresh. **NOT a new series, NOT a standalone site.** Launch-prioritized for B10–12. Tiger is prototyping; GB's job = fidelity check (each explanation traces to a real sealed passage) + keep the source coherent.

## Open items (next steps)
1. **Wire the snapshot hook** — KM pastes the `PostToolUse` block into `~/.claude/settings.json` (script: `scripts/snapshot_hook.sh`), then `/hooks` reload. (Classifier blocked GB from self-wiring — correct.)
2. **B12 republish** — KM read → submit via KDP Dispatch (then overlay shows it automatically).
3. **seeit prototype** (Tiger) → GB runs the Book↔Code fidelity check when it ships.
4. **Optional G asks (genuinely undone, not wheel-recreation):** Books 4–11 *optimized chapter titles* (placeholders in G's doc); vol_04's 6 reordered chapters G re-map.
5. **Distribution federation architecture** (from HMC 2026-06-10: Amazon/Ingram core + aggregators + audio + clip ignition) — capture into a structured artifact if KM wants; "resonant propagation, no parallel federation."

## Key files
- `artifacts/series_roadmap.yaml` (GB sole-writer; lean) · `artifacts/extracted_chapter_outlines_2026-06-08.json` (chapter index, GB/G enrichment layer)
- `…/breathline-books-vault/kdp/agentic_playbooks/ASIN_TRACKER.yaml` (Tiger; KDP truth → publishing overlay)
- `scripts/`: `gb_meta_cylinder.py` · `thread.py` · `pipeline_snapshot.py` · `snapshot_hook.sh`
- Lens: `src/sovereign_agent/node_api/routes/series.py` (`_chapter_index` + `_publishing_index` overlays). Tests: `tests/test_node_api_series.py` (5/5).
- Compass: `artifacts/GB_Metalayer_Plan_Steering_Compass_2026-06-09.md`

## Coordination state (at handoff)
- **THREAD** at [149] (`thread.py verify` = chain OK). **GB cylinder** ~330. **Active HMC** `cyl_6405a38eb6ed`.
- Working tree has uncommitted roadmap/index/lens edits → **Tiger commits**.

∞Δ∞ *Render, don't recreate. The fence holds across the restart. Hand it forward.*
