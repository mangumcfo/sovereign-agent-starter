# Atrium — 3 Directions Design Package (for KM review before build)

**Date:** 2026-06-04 · **From:** Tiger · **Source:** KM in-use feedback (selections are often tooling-direction, chatter is noisy, wants the workflow "pipes" legible) · **Discipline:** design-then-build · all three are lightweight, reuse existing seams, honest-labeled, thin-waist. Nothing built until KM OKs.

---

## 1. ⚙ Tooling / Build packet lane
**5th-grader:** *When you pick text and it's really an idea to improve the app (not the book), you hit the gear button and it makes a to-do for the builder instead of changing the book.*

- **Problem:** Your selections are often direction for the Atrium *tooling*, not the manuscript — but every selection action opens a book-edit packet that fires the manuscript producer, and tooling intent dead-ends as an info-card.
- **Approach:** Add one toolbar action **"⚙ Tooling / Build idea"**. It opens the **same `/obligations` packet**, but titled `Tooling/Build ·` with `ref:'tooling:'+page` → the loop **self-routes**: it does NOT call the producer, and gets no "Process into diffs" button. It lands as a **Tiger build-queue item** you confirm → Tiger implements via propose→approve→execute. (A typed note reuses the existing Misc prompt.)
- **Reuses:** the ATR-9 selection toolbar + `api.openObligation` + `#live_ledger` + the existing ref-prefix routing convention. No new endpoint, no new layer.
- **Open Q (you):** Tooling items inline-badged on the live ledger, **or** a small separate "Tiger build queue" panel? And is opening the packet the gate (Tiger pulls), or do you want a "Confirm for Tiger" click first?

## 2. Relevance chips over the live stream
**5th-grader:** *Instead of every message at once, little buttons let you tap to see just what's waiting for you to say yes.*

- **Problem:** `#live_ledger` shows everything — book edits, tooling, coordination, info-cards, closed — undifferentiated. What awaits your gate is buried.
- **Approach:** A thin **client-side chip bar** over the ledger: `[Needs me*] [Book edits] [Tooling] [Coordination] [Info] [Closed] [All]`, each with a count. **Default = "Needs me"** (open/draft+approved awaiting you); hides closed + FYI. Filters data **already fetched** (no backend, no refetch). Honest caption: *"Showing 2 of 9 — lanes inferred from title/ref/status (best-effort, not a backend classification)."*
- **Reuses:** `fillLiveLedger` render path + `obligationsLog()` seam + existing `.chip` CSS. Nothing dropped silently — unknowns fall to All.
- **Open Q (you):** "Needs me" = status draft/approved (works now), or owner===KM-1176 (also surfaces Tiger items you must ratify)? And should the producer start stamping an authoritative `lane` tag so the heuristic retires later?

## 3. "How it flows" — pipeline visual (for 5th graders)
**5th-grader:** *A picture of pipes: an idea goes in one end, you press one "OK", and the helper safely builds it and stamps a receipt at the other end.*

- **Problem:** You have the Tiger/GB workflow docs but no way to *see* how the pipes flow.
- **Approach:** A **read-only "How it flows" tab** — simple CSS boxes + `→` arrows (no graph libs): **Capture → Packet → Process → Accept → Apply → Seal → Coherence**, with a 3-lane legend (KM ratifies / Tiger builds / GB proposes). Click a stage → existing drawer shows a plain-English + technical line. Data = a small **committed snapshot** (`workflow_snapshot.json`) hand-derived from the alignment package — **not** live-parsed markdown (honest: re-snapshot when the package changes). Strictly read-only (never the gate).
- **Reuses:** the existing tab seam + `renderX()→innerHTML` pattern + the embedded-const data pattern + the existing drawer + `.card/.note/.chip` CSS. No new layer, no api change, no build step.
- **Open Q (you):** Home = Full cockpit (`index.html`) new tab, the Light standalone, or inside the Series Pipeline tab?

---

## Recommended build order + defaults (Tiger)
1. **Relevance filter first** — lightest, immediately cuts your chatter pain, zero backend.
2. **Tooling lane** — small, fixes the "my edits are really tooling" mismatch; *default:* inline-badged on the ledger + opening the packet is the gate (Tiger pulls), you can reject. Producer also stamps `ref:tooling:` so #2's lanes get reliable.
3. **Pipes visual** — *default home:* the **Full cockpit** (`index.html`) as a new tab in the Review group, matching where Series Pipeline / Hopper live.

*All three behind honest labels; each built → reviewer-pass → seal → surfaced for your Atrium review, one at a time.*
