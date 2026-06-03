# To GB — Reconcile the Series Order (KM-1176 ratification)

**From:** KM-1176 (relayed via Tiger) · **Date:** 2026-06-03
**Why:** the series numbering drifted across docs (3+ conflicting schemes) and a new Series 4 was added before KM reviewed it. Tiger then found that **QuadRoof had already been the canonical Series 4 since 2026-05-29** (locked in `pipeline/series_quadroof.yaml` and cross-referenced ~14× inside the **sealed Series-2 Vol 4 manuscript**). KM has now ruled on the whole ladder. This note is the **authoritative reconciliation** — please make the roadmap match it.

## 1. Canonical PUBLISHED series ladder (ratified 2026-06-03)
- **Series 1 — Agentic AI Playbooks for Executives** (12 titles; 10/11/12 in human review).
- **Series 2 — Building the Agentic Harness** (5 volumes; awaiting human review).
- **Series 3 — Programmable Sovereign ERP** (4 volumes; `kdp/series_03_programmable_sovereign_erp/SERIES_3_CONCEPT_v2`).
  - **Vol 4 = "Industry Sovereign ERPs & Generational Continuity"** ties to **yield + family-office + Series 2 Vol 5 Yield surfaces.** Tokenization through-line begins here (+ **B26 — Yield Organisms & XRPL**).
- **Series 4 — Sovereign Token & Economic Organism** *(PROMOTED to ratified public slot).* Was G's "forward framing, NOT ratified" concept in `SERIES_3_TRANSLATION_PRESCRIPTION_2026-06-01.md`. **Layer = Yield & continuity:** private governed tokens as alignment tools · compounding under constitutional fidelity · generational handoff rituals. Ties to **Series-2 Vol 5 Yield + Series-3 Vol 4 + LGP.** Status = ratified slot, concept-stage content (honest label: not yet written).
- **Series 5 = OPEN / reserved.** (G's older "Series 5+ = Full production ERP" forward note can be parked here as a candidate, not ratified.)

## 2. Supersede the conflicting schemes (one source of truth)
These older/competing labels are **NOT current**:
- `FUTURE_SERIES_PLACEHOLDER` arc (S3 = "1,000-Year Family Compact"; S4 = "Education"; etc.) — superseded.
- `active.yaml` renumber note implying "Series 3 = Family AI" / "Family AI holds Series 3" — superseded.
- **"QuadRoof = Series 4"** (the 2026-05-29 Option-A renumber in `series_quadroof.yaml` + `active.yaml`) — **superseded** (see §3). QuadRoof is no longer a numbered public series.
The authoritative ladder is §1. Reconcile `series_roadmap.yaml` to it; `WORKFLOW.md` + `pipeline/series_*.yaml` remain the canon the projection derives from.

## 3. QuadRoof = PRIVATE book artifact (un-numbered; no longer Series 4)
QuadRoof is a **private** artifact (KM's operating-company investor guide), not for wide publication unless KM later decides.
- It **vacates the Series 4 number** (which now goes to Sovereign Token & Economic Organism, §1). QuadRoof is **un-numbered + private**, not a public series.
- Mark `visibility: private`. Remove the "QuadRoof = Series 4 (published)" framing wherever it appears in the projection.
- **Sealed-manuscript reconciliation (Tiger lane, Hold-the-Line):** the sealed **Series-2 Vol 4 manuscript** cross-references "Series 4 QuadRoof Investor Series" ~14× (Ch 8 worked example + back matter, citing `pipeline/series_quadroof.yaml`). Those are now stale. **Fix lands as a Series-2 v1.4 next-edition note** that re-points them (QuadRoof → private investor artifact; the *yield/token* Series-4 reference → the new Sovereign Token & Economic Organism series). **No edit to sealed v1.3.** Tiger owns this capture.

## 4. GB's quantum / "Unveiled" thread = PRIVATE learning series (not published widely)
KM's intent: *don't infringe on the quantum/"Unveiled" thread; run a private learning series — not published widely — that prepares us to connect our surface to theirs at some point.* So:
- Reclassify GB's just-added quantum thread (quantum-DNA / unveil-particle / constraint-ERP, from the 2026-06-03 B51 capture / Jakob's "Unveiled Platform") as a **PRIVATE learning series**, `visibility: private`, **explicitly NOT a public book on their technology** and **NOT the public Series 4** (that slot is now the token series, §1).
- **Purpose:** KM's learning + **interoperability readiness** (so our sovereign surface can connect to the Unveiled Platform later). Respects Unveiled/Jakob IP — *our* prep + alignment notes, not a publication of their work.

## 5. Add a `visibility` field to the roadmap (per series/title)
- `visibility: public` — Series 1, 2, 3, 4 (Sovereign Token), 5 (when assigned) — the KDP publish pipeline.
- `visibility: private` — QuadRoof (un-numbered); the quantum/"Unveiled" learning series. Stay in the private vault / sovereign-agent-starter (private repo); **never enter the public KDP publish path** without a KM ratification.

## 6. Fence + one-writer (the recent collision)
`series_roadmap.yaml` is **GB's projection** — GB + Tiger collided on it last pass (a stale duplicate tail shadowed GB's newer content; Tiger de-duped). Going forward: **GB is the sole writer of `series_roadmap.yaml`; Tiger consumes it** (renders it in the Atrium lens). KM ratifies series-order + visibility changes (material).

## 7. Action for GB
Update `series_roadmap.yaml` to the §1 ladder: (a) S1/S2/S3 unchanged; (b) **S4 = Sovereign Token & Economic Organism** (promote from concept; `visibility: public`, honest "concept-stage, not yet written" status); (c) **S5 = open/reserved**; (d) **QuadRoof → un-numbered + `visibility: private`** (remove the Series-4 framing); (e) the quantum/"Unveiled" thread → a separate **private learning series**, `visibility: private`, with the interoperability-prep purpose + IP-respect note; (f) drop the superseded numbering schemes (§2); (g) one clean copy (no duplicate tail). Then KM ratifies.

**Tiger's parallel cleanup (not GB's):** the Series-2 v1.4 next-edition note re-pointing Vol 4's ~14 "Series 4 QuadRoof" cross-refs (§3). Hold-the-Line; no sealed-v1.3 edits.

— KM-1176 (via Tiger). Fence holds; LGP north-star; consciousness-to-consciousness, IP respected.
