# Tiger → KM — A Helix file-management instruction (title → artifacts registry)

*KM steer (2026-06-05): "a helix instruction for a file-management system might be helpful… define it, then
make sure every title in the Series Pipeline works." Yes — Helix is the right tool. Here's the definition.*

## The problem
Today each surface that touches a book's files hardcodes paths (the `book_pdf` endpoint mapped only
`agentic_playbooks` Books 10/11/12; the producer's `BOOK_PATHS` maps a few manuscripts). Books actually live in
many places — `kdp/01_strategic_finance/v1.1/…`, `kdp/agentic_playbooks/11_…/v1.0/…`,
`kdp/metalayer_companion_private/the_sealing_hand/v1.0/…`, `kdp/series_02_…/vol_05_…/v1.0/…`. Hardcoding is
fragile → "other books won't open."

## The bridge (shipped today)
`book_pdf` now **resolves universally** — it locates a title's built **interior** PDF anywhere under the vault
(`kdp/**/<book_id>/v*/final/*.pdf`, covers excluded). Verified: every title opens (Series 0/1/2 + metalayer).
This unblocks you now — but a runtime glob is a *resolver*, not a *source of truth*.

## The Helix answer (the durable definition)
**A deterministic title→artifacts registry — the file-management helix.** One canonical spec that maps each
`book_id` to its artifacts, so EVERY surface reads the same truth (no hardcoding, no glob heuristics):

```
# helix/file_management.helix  (or memory/book_artifacts_registry.yaml)
the_sealing_hand:
  series: metalayer_companion        visibility: private        version: v1.0
  dir:        kdp/metalayer_companion_private/the_sealing_hand/v1.0
  manuscript: …/manuscript_v1.0.md
  pdf:        …/final/The_Sealing_Hand.pdf       epub: …/final/The_Sealing_Hand.epub
  cover:      …/final/cover_KDP.png              kdp_asin: null
11_ma_due_diligence:
  series: agentic_playbooks (S1)     visibility: public         version: v1.5
  dir/manuscript/pdf/epub/cover/kdp_asin: …
```

**Why this is a *helix* (not just a config):**
- **Deterministic + single canonicalizer** — one map; `book_pdf`, the producer (manuscript grounding), the
  build, the coherence lens, and the Series-Pipeline drill all read it (no divergence/drift).
- **Receipted + validated** — a render/registry receipt (hash) + `helix_validate`-style check that every
  title resolves to real, present files; a missing/mismatched path surfaces as **drift** (like the coherence lens).
- **Unfoldable / portable** — any sovereign node unfolds it to know where every artifact lives; federation
  operators get the same file-management without bespoke wiring. *("Destroy every node, chain remains.")*
- **KM-ratified, self-amending** — add a title / bump a version → update the registry (KM ratifies); every
  surface inherits it. This is the file-management equivalent of "update the standard → bump its gate."

## Is Helix the right tool, and when?
**Yes** — file-management-as-deterministic-spec is a textbook Helix use, and it's the **smallest, lowest-risk,
highest-value FIRST Helix increment**: it removes fragile hardcoding from 4+ surfaces, it's concrete (not
abstract), and it proves the lens before the bigger per-card-render-receipt work. **When:** fold it into the
**Helix alignment with G** (the B35-v2.1 design note already routing) and the next coherence pass — recommend
it as **Helix increment #1**. Tiger can build the registry + repoint `book_pdf`/producer to read it in a small
pass once you ratify.

∞Δ∞ Universal resolver unblocks today; the title→artifacts registry is the durable helix — define it once,
every surface and every node reads it, every title in the pipeline works.
