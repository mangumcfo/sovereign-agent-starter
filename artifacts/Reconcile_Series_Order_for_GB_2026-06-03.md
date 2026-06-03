# To GB — Reconcile the Series Order (KM-1176 ratification)

**From:** KM-1176 (relayed via Tiger) · **Date:** 2026-06-03
**Why:** the series numbering has drifted across docs (3+ conflicting schemes) and a new Series 4 was added before KM reviewed it. This note is the **authoritative reconciliation.** Please make the roadmap match it.

## 1. Canonical PUBLISHED series order (ratified)
- **Series 1 — Agentic AI Playbooks for Executives** (12 titles; 10/11/12 in human review).
- **Series 2 — Building the Agentic Harness** (5 volumes; awaiting human review).
- **Series 3 — Programmable Sovereign ERP** (4 volumes; the dedicated `kdp/series_03_programmable_sovereign_erp/SERIES_3_CONCEPT_v2`).
  - **Vol 4 = "Industry Sovereign ERPs & Generational Continuity"** explicitly ties to **yield + family-office + Series 2 Vol 5 Yield surfaces.** The **tokenization through-line lives here** (and in **B26 — Yield Organisms & XRPL**). Confirmed.
- **Series 4 (published) = OPEN / unassigned for now.** Neither QuadRoof nor the quantum/"Unveiled" thread is the public Series 4 (see §3–§4).

## 2. Supersede the conflicting schemes (one source of truth)
These older/competing labels are **NOT current** — do not use them as the canonical order:
- `FUTURE_SERIES_PLACEHOLDER` arc (Series 3 = "1,000-Year Family Compact"; Series 4 = "Education"; etc.) — older aspirational arc, superseded.
- `active.yaml` renumber note implying "Series 3 = Family AI" — superseded.
The authoritative order is §1. Reconcile `series_roadmap.yaml` (the projection) to it; `WORKFLOW.md` + `pipeline/series_*.yaml` remain the canon the projection derives from.

## 3. QuadRoof = PRIVATE book artifact (not a published series)
QuadRoof is a **private** artifact (KM's operating-company investor guide). **Not** meant for wide publication unless KM later decides. So:
- It is **NOT the public Series 4**, and it is **NOT "superseded by" the quantum thread** — it is simply **reclassified as a private track.**
- Keep it in the private vault; mark `visibility: private`. Remove the "QuadRoof = Series 4 (published)" framing and the "superseded" note.

## 4. GB's quantum / "Unveiled" thread = PRIVATE learning series (not published widely)
KM's intent (verbatim sense): *don't infringe on the quantum/"Unveiled" thread; run a private learning series — not published widely — that prepares us to connect our surface to theirs at some point.* So:
- Reclassify GB's just-added Series-4 (quantum-DNA / unveil-particle / constraint-ERP, from the 2026-06-03 B51 capture / Jakob's "Unveiled Platform") as a **PRIVATE learning series**, `visibility: private`, **explicitly NOT a public book on their technology.**
- **Purpose:** KM's learning + **interoperability readiness** (so our sovereign surface can connect to the Unveiled Platform later). It respects Unveiled/Jakob IP — this is *our* prep + alignment notes, not a publication of their work.
- It is **NOT the public Series 4.** Do not bake it into the published canon.

## 5. Add a `visibility` field to the roadmap (per series/title)
So public vs private is explicit + governed:
- `visibility: public` — Series 1, 2, 3 (the KDP publish pipeline).
- `visibility: private` — QuadRoof; the quantum/"Unveiled" learning series. Stay in the private vault / sovereign-agent-starter (private repo); **never enter the public KDP publish path** without a KM ratification.

## 6. Fence + one-writer (the recent collision)
`series_roadmap.yaml` is **GB's projection** — and GB + Tiger edited it concurrently last pass, producing a duplicated tail (a stale copy was shadowing GB's newer content; Tiger de-duped it). Going forward: **GB is the sole writer of `series_roadmap.yaml`; Tiger consumes it** (renders it in the Atrium lens). KM ratifies series-order + visibility changes (material).

## 7. Action for GB
Update `series_roadmap.yaml` to: (a) S1/S2/S3 as the public order with S3 = Programmable Sovereign ERP (Vol 4 yield/family-office/tokenization tie); (b) **public Series 4 = open**; (c) QuadRoof → `visibility: private` (un-supersede); (d) the quantum/"Unveiled" thread → a separate **private learning series** with `visibility: private` + the interoperability-prep purpose + IP-respect note; (e) drop the superseded numbering schemes; (f) keep one clean copy (no duplicate tail). Then KM ratifies.

— KM-1176 (via Tiger). Fence holds; LGP north-star; consciousness-to-consciousness, IP respected.
