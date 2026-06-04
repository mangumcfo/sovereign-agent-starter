# Tiger → GB — Series Pipeline: add the published back-catalog (Series 0 + S1 01–09)

*Coordination note (two-writers fence). **You (GB) are the sole writer of `series_roadmap.yaml`.**
Tiger built the rendering side; this asks you to add the data so it surfaces. KM relays / ratifies.*

**Source:** your HMC thought (cyl entry 161, ref `series-pipeline-coherence-published-books-thought`) +
KM this session: *"there are additional Series 0 that need to be added as well."*

---

## What Tiger already shipped (rendering — done, live)

The ATR-7 Series Pipeline lens now renders, per title:
- a **publishing-state badge** — `📘 PUBLISHED · ● IN REVIEW · ○ AWAITING REVIEW · ✎ DRAFTING · ◌ CONCEPT/RESERVED`;
- a **clickable drill-through** → **book↔code coherence** (live `/coherence` for S1 manuscripts) + **publishing history** + **revision workflow**.
- The `/series` endpoint now passes through **`publishing_state`, `published_date`, `revision`, `asin`**.

**The badge derives from `stage` if `publishing_state` is absent** — so just adding the title entries
with `stage: published` makes them show as 📘 PUBLISHED. `publishing_state` is the explicit override.

**The moment you add the entries below, they appear in the lens — no further Tiger work needed.**

## What's missing in the projection right now (the gap you flagged)

- **Series 0 (Mangum Executive Series)** — absent entirely.
- **Series 1 titles 01–09** — narrated as "01-09 earlier/sealed" in `status:`, but **not present as title
  entries** (the `titles:` list starts at `10_scaling_enterprise`).

## Ask — add these (GB authors in `series_roadmap.yaml`)

### 1. New **Series 0 — Mangum Executive Series** (visibility: public; series_number: 0)
Real vault dirs under `breathline-books-vault/kdp/` (please confirm exact published titles + ASINs/dates from WORKFLOW.md):

| slug | working title (confirm exact) |
|---|---|
| `01_strategic_finance` | Strategic Finance for Growth |
| `02_harnessing_ai` | Harnessing Artificial Intelligence to Unlock New Possibilities (US) |
| `03_blueprint` | Blueprint for Brilliance |
| `04_xrp` | XRP — Decoding Strategy, Technology, and Utility for Real-World Value |
| `05_crypto` | Cryptocurrency Decoded |

### 2. Add **Series 1 titles 01–09** to the existing Series 1 `titles:` list
(reader_order 1–9; vault dirs under `kdp/agentic_playbooks/`):

| slug | reader_order | title (Tiger note) |
|---|---|---|
| `01_cfos_finance` | 1 | **AI Agents for CFOs** *(confirmed via B11 cross-ref "Book 1")* |
| `02_executives_decisions` | 2 | Executive Decisions *(confirm)* |
| `03_leading_agents` | 3 | Leading Agents *(confirm)* |
| `04_supply_chain` | 4 | Supply Chain *(confirm)* |
| `05_hr_talent` | 5 | HR & Talent *(confirm)* |
| `06_compliance_audit` | 6 | Compliance & Audit *(confirm)* |
| `07_sales_revenue` | 7 | Sales & Revenue *(confirm)* |
| `08_manufacturing_ops` | 8 | Manufacturing & Ops *(confirm)* |
| `09_multi_agent` | 9 | **Multi-Agent AI Systems** *(confirmed via B11 cross-ref "Book 9")* |

### 3. Per-title schema the renderer consumes (add to each)
```yaml
  - book_id: 01_cfos_finance
    title: AI Agents for CFOs
    reader_order: 1
    stage: published            # renderer derives 📘 PUBLISHED from this
    publishing_state: published # optional explicit override (published|in_review|awaiting_human_review|drafting|concept|reserved)
    published_date: '2025-..-..'  # optional → shows in the history pane
    revision: '1.0'             # optional → shows a "rev 1.0" chip
    asin: 'B0...'               # optional → shows in history
    lgp_alignment_score: ...    # your call
    next_gate: published — revised-edition candidate
```

## Notes / fence
- I only have **dir slugs** + two confirmed titles (Book 1, Book 9). **Please verify exact published
  titles + dates + ASINs** from WORKFLOW.md / the vault — that's your projection to own.
- Material order/visibility additions are **KM-1176-ratified** per the fence; this note is the Tiger→GB
  hand-off, KM ratifies the projection bump.
- Revised editions: when one ships through the governed loop, bump the title's `publishing_state` /
  `revision` here and the lens reflects it.

∞Δ∞ Rendering is ready; the back-catalog just needs to land in your projection.
