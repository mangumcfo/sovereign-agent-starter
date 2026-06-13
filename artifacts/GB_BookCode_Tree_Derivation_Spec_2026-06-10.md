# Book↔Code Tree — Derivation Spec v1.0 (GB, sealed 2026-06-10)

> **Ratified by KM 2026-06-10:** "write the derivation spec. yes, let's align with/as seeit. I'd like it to be a helpful interactive surface."
> **Family:** derived surface, sibling-of/inside **seeit** (live on six-sov.com) — second lens on the same engine, NOT a new build.
> **Fence:** GB sole-writes this spec + the mapping layer; **Tiger** builds the deriver/renderer; **KM** ratifies surface placement.
> **Principle:** Render, don't recreate. Every node and edge is derived from an existing source of truth. Nothing hand-drawn.

## 1. What it is
An interactive view showing **how the code tree represents the books**: the book tree (series → volumes → chapters) and the code tree (repo `src/` modules) facing each other, joined by **derivation edges** — the visible lines that say *"this module exists because that chapter breathed it."*

The visualization **is** the Book↔Code audit, drawn. A missing edge is not a rendering gap — it is a **fidelity finding**.

## 2. Sources (all existing; zero new canon)
| Side | Source of truth | Supplies |
|---|---|---|
| Book tree | `artifacts/series_roadmap.yaml` (GB sole-write) | series → volumes/titles spine, status |
| Book leaves | `artifacts/extracted_chapter_outlines_2026-06-08.json` | chapter nodes, KW, outlines |
| Publishing color | `ASIN_TRACKER.yaml` via `series.py _publishing_index` | live/pre-order/draft overlay (never hand-set) |
| Code tree | `git ls-tree -r HEAD src/` | module nodes (path, size, last-commit) |
| Code meaning | module docstrings + `∞Δ∞` Seal blocks | per-module purpose text |
| Edges | `artifacts/book_code_map.yaml` (**new, derived, GB sole-write** — see §3) | derivation edges |
| Excerpts | sealed manuscript passages (seeit's source rule) | click-through text |

## 3. Edge derivation rules (the heart)
Edges live in one mapping artifact, `artifacts/book_code_map.yaml`, built by these rules **in priority order** — higher rule wins on conflict:

1. **R1 — Explicit anchor (class: `derived`).** A module cites a book/chapter (docstring, Seal block, `generated_from`, roadmap `references`). Strongest edge; machine-extractable.
2. **R2 — Structural identity (class: `derived`).** Module purpose = a constitutional/book structure by construction. Seed set (extend, don't invent):
   - `compliance/human_approval_gate.py` ↔ approval-gates chapters (Propose→Approve→Execute)
   - `obligations/ledger.py` ↔ TRUTH/receipts chapters
   - `obligations/arc_guardrail.py` ↔ guardrail/INTEGRITY chapters
   - `demo_roles/ma_data_room/` ↔ B11 *AI Agents for M&A*
   - `demo_roles/*_cfo_demo/` ↔ S1 CFO/finance books
   - `kdp_metadata.py` ↔ publishing-pipeline chapters
   - `node_api/routes/series.py` ↔ the Atrium/lens chapters (the lens rendering itself — recursion is a feature, show it)
3. **R3 — Slug/keyword resonance (class: `inspired`).** Chapter KW (already enriched, 224/224) ∩ module identifier/docstring terms above a threshold. Weaker; rendered thinner; never auto-promoted to `derived` without R1/R2 evidence.
4. **R4 — No edge (class: `orphan` / `unrendered`).** Code with no book lineage → `orphan` (finding: where did this come from?). Chapter with no code form → `unrendered` (finding or roadmap: not all chapters must have code — mark `n/a: narrative` to silence intentionally, loudly, in the map file).

**Edge record schema:** `{book: <series>/<vol>/<ch>, code: <path>, class: derived|inspired|pending, rule: R1|R2|R3, anchor: <quote-or-ref>, note}`. **TRUTH discipline: every edge's `anchor` must resolve** — a real docstring line, roadmap ref, or sealed passage. No vibes-edges.

## 4. Interactive surface (KM: "helpful")
- **Click a chapter** → its code nodes light; side panel shows the sealed passage excerpt + edge anchors (seeit's source-from-sealed rule applies verbatim).
- **Click a module** → its book lineage lights; panel shows docstring/Seal + the chapters it renders.
- **Color** = publishing overlay (LIVE / pre-order / draft) on the book side; edge weight = class (derived > inspired).
- **Filters:** by series, by edge class, **"findings mode"** = show only orphans + unrendered (the audit view — likely the most *helpful* mode for KM).
- **Search** across both trees.
- **Cross-link with seeit:** a seeit explanation page links to its node in the tree; the tree panel links back to the seeit explanation. One engine, two lenses.

## 5. Build contract (Tiger's lane)
- One deterministic deriver → `book_code_tree.json` (`{book_tree, code_tree, edges[], findings[], meta:{generated_from, hashes, ts}}`). Idempotent; content-hashed like `pipeline_snapshot.py`.
- Renderer inside the seeit/Helix engine on six-sov.com (Atrium lens/Review group). No second site.
- **Auto-refresh** on roadmap/index/src change (same trigger family as the snapshot hook).
- **Drop-off guard on edge counts:** derived-edge count decreasing vs prior build = loud warning, same semantics as the pipeline guard.

## 6. Fidelity protocol (GB's lane, recurring)
1. Sample edges per series → verify each `anchor` resolves to real text/code.
2. Sweep `findings[]` → classify orphans (real gap vs missing anchor) and unrendered (gap vs `n/a: narrative`).
3. Verify counts only grow or are explained (guard log).
4. Log result to meta-cylinder + THREAD. First run: against Tiger's first `book_code_tree.json`, alongside the now-due seeit fidelity check.

## 7. Phasing
- **P1 (small):** deriver + R1/R2 edges only + static interactive tree in seeit. Findings mode included from day one.
- **P2:** R3 resonance edges + cross-links with seeit explanations.
- **P3 (only if breath calls):** time axis — tree at each sealed snapshot, watching the form grow from the books.

## 8. DoD
Deriver idempotent + hashed · every rendered edge has a resolving anchor · findings mode works · publishing overlay sourced from `_publishing_index` (not duplicated) · GB fidelity pass logged · KM ratifies placement.

∞Δ∞ SEAL: complete — the books are the breath, the code is the form, this surface is the echo that lets the witness see both at once.
