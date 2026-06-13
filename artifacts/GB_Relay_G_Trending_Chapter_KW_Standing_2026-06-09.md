# GB → G (x.com) — STANDING relay: chapter-level keywords, trend-aligned

> **Purpose (KM 2026-06-09):** Keywords live at the **chapter level**, and G keeps them **aligned to what's trending in socials / search** so the catalog stays relevant. This is a **reusable** relay — KM re-sends it per book (or on a cadence) and folds G's return into the chapter cards. ∞Δ∞

---

**G — chapter-level keyword refresh for `<SERIES / BOOK>`.**

We've moved keyword targeting to the **chapter level** (each chapter card carries its own KW set). Your job on this relay: make each chapter's keywords **current** against what's trending *right now* on x.com / social + Amazon/KU search, so the book surfaces for the terms people are actually using this quarter.

**For each chapter below, return 3-5 chapter-level keywords:**
- Grounded in the chapter's actual topic (I'll paste the chapter title + promise).
- **Trend-aligned**: weight toward terms rising in x.com / social discourse + current Amazon/KU long-tails; flag any that are fading.
- Mix one broad head term + 2-4 specific long-tails per chapter.
- Note any **emerging term** you'd add that we're missing (new trend we should ride).

**Chapters (paste per book):**
```
Ch N — <title>
  promise: <one-line>
  current KW: <existing chapter KW, if any>
```

**Return:** per chapter — `Ch N: [kw1, kw2, kw3, …]` + a one-line "trend note" (what's rising/fading). Clean list so GB folds verbatim into the chapter cards (extraction index, marked generated + dated).

**Cadence:** run on each book as it enters enrichment, and **re-run periodically** (quarterly or on a notable trend shift) so chapter KW never goes stale. LGP-first, KDP/x.com-aware.

---
*Mechanism: G returns → GB folds chapter-level `keywords` into `artifacts/extracted_chapter_outlines*.json` (marked `generated`, dated) → lens/KDP Dispatch render current terms. Book-level KDP-slot bundle stays as the 7-slot Amazon set; chapter KW drives pipeline relevance.*
