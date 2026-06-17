# Education & Training Board — /seeit pages · Spec v1.1 (LIVING)
*KM-directed 2026-06-17. The V3 /seeit rejection STANDS: the walkthroughs are technically accurate but too jargon-heavy for the intended reader. /seeit's purpose is for an EVERYDAY person to SEE and FEEL the governed behavior in action — not to follow dev commands. (Same as the editorial board's Risk #1.) This board sets + enforces the explicit "accessible but grounded" bar for every /seeit page. Modeled on EDITORIAL_BOARD_REVIEW_v1.0.md. Living document; lives in Atrium. KM-1176 ratifies the bar.*

> **v1.1 — KM ruling 2026-06-17 (ratify-with-addition):** add a **4th gate — Cross-Board Alignment** — made obligation-real. The board does not merely make /seeit readable + grounded; it proves the educational surface AGREES with the book's other review boards, the code, the receipts, and the open-obligation state. The constitutional line: **No /seeit page may pass while it contradicts, bypasses, or outruns any unresolved finding from the book's other review boards.**

## Charter (the mandate)
A /seeit page passes ONLY when it is **both accessible AND grounded** — and the board exists because those pull against each other:
- **Accessible** — a smart non-technical reader can follow it, *see what happens*, and *feel* what the governance does *for them*, with **no jargon they can't decode and no requirement to run a dev command** to get the point.
- **Grounded** — every claim is still tied to a **runnable command + a deterministic receipt + the v2.0 detailed chart.** Accessibility must NOT become hand-wavy, unverifiable, or marketing.
The board's job is to hold BOTH at once. Accessibility without grounding is slop; grounding without accessibility is the current V3 failure. The bar is the intersection.

## Board members (3 personas — minimum, each an independent lens + a hard reject condition)
| Persona | The lens (what they ask) | REJECTS when… |
|---|---|---|
| **1 · Everyday / non-technical reader** | "Can I, a smart non-developer, follow this, see what happens, and feel why it matters — without running a terminal or knowing the jargon?" | jargon appears without a plain-language decode · the *only* path to the point is a dev command · no visible/felt outcome · I finish and don't *feel* what the governance protects |
| **2 · Educator / trainer** | "Does this TEACH? Is there scaffolding — here's what you'll see → here it is → here's what it means for you? Could a trainer use this page to show a newcomer?" | shows-without-teaching · no step-by-step build of understanding · no plain "what this means for you" takeaway · assumes prior platform knowledge |
| **3 · Grounding & fidelity reviewer** | "Is every claim STILL tied to a runnable command + a deterministic receipt + the v2.0 chart? Did accessibility quietly drop the proof?" | a claim has no command/receipt behind it · the command doesn't resolve to a real path · the receipt isn't the actual deterministic output · the v2.0 chart is missing or decorative |
| **4 · Cross-Board Alignment reviewer** *(v1.1, KM)* | "Does this /seeit page faithfully reflect what the OTHER boards already found, required, rejected, or left open — Editorial, Tech/Arch, the v2.0 Chart Standard, the Review-Ready Contract, Gate 7/Adversarial (where applicable), Distribution/reader-facing standards, and the B32 obligation state?" | /seeit claims a page is ready while another board has an unresolved blocker · simplifies away a known risk · shows a chart/demo that doesn't match the approved visual standard · says "this protects you" without mapping to a real gate/receipt/obligation · teaches behavior that differs from the book's actual implementation · uses a workaround/demo path instead of the production-governed path |

*(A page passes only when ALL FOUR + the cold-reader clear it. The grounding reviewer guards against hand-waving; the **Cross-Board Alignment reviewer is the bridge between education and governance** — it prevents a beautiful explanation of a system the other boards have not actually cleared. Not optional.)*

## The "accessible but grounded" bar (explicit criteria — every page)
1. **Plain-language first.** Open with what the reader will *see and feel* in everyday terms; the dev command is *available but not required* to get the point.
2. **A felt, visible outcome.** The page shows the governed behavior happening (the breath-gate catching, the receipt sealing) so the reader *experiences* it, not just reads about it.
3. **"What this means for you."** A plain takeaway tying the behavior to the reader's stake (trust, control, verifiability) — no internal terms (no B32/cylinder/breath-gate-jargon undecoded).
4. **Grounding intact (non-negotiable).** Runnable command (real path) + deterministic receipt (actual output) + the v2.0 detailed chart, inlined. Accessibility is layered ON the grounding, never instead of it.
5. **Jargon budget.** Any necessary internal term is decoded in plain language on first use, once.

## Process (mirrors the editorial rail; standing for all /seeit content)
- **Per-page review:** each /seeit page scored by all 3 personas → strengths / weaknesses / risks → PASS or REJECT-with-reasons (page-level, not buried).
- **Cold-reader adversarial pass (R1.5g analog):** an actual non-technical-reader test — does a fresh reader *get it and feel it*? A page that only "reads accessible" to an insider is REJECTED.
- **Rigor block:** the board's verdict is evidence-cited (the specific jargon, the missing takeaway, the dropped grounding) — no honeymoon, no theater.
- **Sign-off — the PASS standard (v1.1).** A /seeit page passes ONLY when ALL of:
  1. Everyday reader clears it · 2. Educator/trainer clears it · 3. Grounding/fidelity reviewer clears it ·
  4. **Cross-board alignment clears it** · 5. Cold reader clears it · 6. **All material `seeit:*` obligations for that page are closed with receipts.**
  GB witnesses fidelity; KM ratifies the bar + dispositions in Atrium.

## Obligation-real (v1.1, KM) — findings become tracked work, not review theater
Every REJECT finding **mints or proposes a B32 obligation** with a stable id `seeit:<page_id>:<board>:<finding_hash>`, carrying: `page_id · board_source · finding · why_it_matters · required_fix · evidence_ref · owner · status · close_receipt · before_after_note`. **A /seeit page cannot PASS while any material `seeit:*` obligation for that page remains open** — that is how the board becomes implemented improvement, not a polished demo. The cross-check the alignment reviewer runs:
`What /seeit claims → what the book boards found → what the code/receipt proves → what obligations remain open` — no contradiction, no skipped risk, no demo-first laundering.

## Board Alignment Matrix (v1.1, KM) — required per /seeit page (the auditor path)
| Claim / Demo | Source board | Required proof | Command / receipt | Chart reference | Open obligation? | Status |
|---|---|---|---|---|---|---|
| *e.g.* "The gate stops unapproved execution" | Tech/Arch + Governance | command proves the unapproved path fails | deterministic receipt attached | v2.0 chart inlined | none | PASS |

## Scope gates (KM 2026-06-17)
- **V3 first, 6 pages only.** Tiger re-authors the 6 V3 pages to meet BOTH the accessibility bar AND the grounding requirements (command + receipt + v2.0 chart). Do NOT expand scope.
- **V2/V4/V5 HELD** — no further authoring until V3 passes re-review against this board's bar.
- **Preflight chart-image fix is a standing gate** — resolve the chapter-one image misalignment on the first preflight before any broader rollout.
- All work + status visible in Atrium. Quality + reader accessibility take precedence.

∞Δ∞ SEAL (v1.1): /seeit is where an everyday person SEES and FEELS the governed behavior — accessible AND grounded, never one without the other, AND never ahead of what the other boards actually cleared. The board holds the tension: plain-language-first + a felt outcome + a "what this means for you," every claim tied to a command + receipt + chart, and the educational surface proven to agree with the book boards, the code, the receipts, and the open-obligation state. No /seeit page passes while it contradicts, bypasses, or outruns any unresolved finding from the book's other review boards. V3's 6 pages re-author to this bar; nothing else moves until they pass.
