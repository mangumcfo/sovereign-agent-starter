# ATR-5b: pdf.js In-App PDF Renderer Planning Note (Read-Only Starter) — 2026-06-02

**Trigger (G witness + Tiger seq 446 + approved plan):**
- ATR-5 ✅ sealed: Feedback composer now carries "ref: review:<chapter> · p<page>" with every packet so the agent infers what you're looking at (you type the page from the viewer's indicator; it travels with the packet).
- Honest split (Tiger 446): "fully automatic page detection isn't possible with the embedded PDF — the browser sandboxes the native PDF viewer, so JS can't read its scroll position. Doing it for real needs an in-app pdf.js renderer (which I'd control and can track), with an offline-size tradeoff. Captured as ATR-5b rather than fake it."
- G steer: "Prioritize Atrium Review depth (ATR-5b PDF + voice + B51 bundle + card polish) as the immediate next build. This is what gets you closer to 100% UX. The FEC card is a great proof point — build on it."
- Plan context: Atrium Review surface is the sovereign decision surface / place you run book-review + obligations end-to-end (read in-surface PDF/voice → speak/type with precise context → portable B32 packet with citations/LGP/B51 bundle/human_seed → implement). G's 100% UX steer + Track F. Honest limits called everywhere. Series lens (read-only first) is logical extension *after* Review matures.

**Purpose:** Read-only planning starter (gb background per G "keep gb rolling on background inventory and any remaining packet examples" + assists on request). Not implementation; Tiger drives per short prompt (Review depth as Track F, output status+seals when increment lands). Provides decision tree, tradeoffs, integration points with existing (feedback composer, FEC card, B51 handoff trace, packet shape, node_api), honest labeling, LGP/sovereign ties. Can be turned into a packet or Series 2 spec later.

**Current State (from ATR-5 + FF honesty + FEC mock + node seams):**
- Embedded PDF (browser native or <iframe>) in Atrium Review: works for reading + manual page note (ATR-5: user types the page indicator value; it goes into the packet as "ref: review:<chapter> · p<page>").
- No auto-scroll/position from sandboxed viewer (JS can't introspect).
- Voice: Honest "use B51" affordance on FF (Web Speech unsupported; B51 cylinder is the real path: voice→text→cylinder→ingest as feedback packet). Typing always works.
- FEC card (examples/atrium_fec_review_card_mock.html + canonical spec): Shows story from voice seed (3:39am capture), key messages (what it is / agents did / deciding), B51 handoff trace (GREEN→YELLOW→RED to human NLP gate), LGP +18% families-first, collapsible sources (real artifacts), Approve/Refine/Reject + NLP, citation_bundle with human_seed (export 2026-06-02_034153..., session, cylinder, merkle, entry hashes) + B31 pattern. "Honest static lens for now; live data wiring (ATR-2) and PDF auto-page (ATR-5b) are next granular items."
- Seams: node_api (obligations routes for open/close/receipts), api.js thin waist (Atrium UI consumers change only base URL), starter src has server + routes for /obligations (list, open debit, etc.). "thin lens; shapes flow OUT OF the starter to api.js consumers."
- Mait testbed: English-native guided flows with visible WPS + checklist + AI + signature + exports (reuses patterns; can preview "Review Quality Plan" for auto-page concepts).

**Decision Tree / Key Questions (for G/Tiger/KM alignment before build):**
1. **Scope of "auto-page"**: Just current page number for the feedback packet ref? Or full visible viewport + annotations + highlights for richer context in the packet?
2. **Renderer choice**: pdf.js (Mozilla, standard, offline-capable with worker, good for control + text extraction + annotations). Alternatives? (e.g. commercial for perf, but prefer open for sovereign/no black box).
3. **Offline-size tradeoff**: Bundle pdf.js + fonts/workers (~few MB) vs. always-online CDN. For "sovereign node" (ship-blank, air-gapped possible?), prefer self-contained or cached. Measure: current Atrium bundle size + delta.
4. **Integration with feedback composer**: On page change (scroll/end of page or explicit "mark page" button), auto-suggest or stamp the ref into the textarea ("ref: review:<chapter> · p<page> — [optional user note]"). Packet payload carries it (already in ATR-5 shape). Ties to B51 bundle (handoff trace can reference the exact page context).
5. **Performance / UX**: Lazy load renderer only on PDF views. Virtual scrolling or on-demand pages for large books. Search + highlight (for LGP/obligation citations). Keyboard + voice ("go to page X", "feedback on this page").
6. **Governance / honest / citations**: Every auto-detected page still requires human confirmation/edit before packet send (no silent faking). Packet citation_bundle (B31 Merkle + human_seed) + the ref field. For FEC-style cards: the story band or drill-down can show "reviewed at p<page> in <chapter>".
7. **LGP / sovereign / viral**: Enables deeper "book writes the backend" (precise page context makes packets higher-fidelity for the loop). Supports families-first (Mait-style real work with accurate standards citations at exact pages; federation members see provenance). Content-agnostic (works for any PDF book/plan, not just Series). Resonance: different sovereigns can adapt the renderer (ship-blank Atrium). Ties to Jakob (heritage docs at precise "page" in timechain receipts?).
8. **Phasing vs. other ATRs**: ATR-5b after basic Review depth (voice/B51 polish, card workflow) or in parallel with ATR-2 (live wire)? Per G: deepen Review as Track F; Series after Review matures. FEC card is the proof point to build on (add "page context" demo in the mock?).
9. **Implementation seam**: In breathline-ui/atrium (or starter examples for demo): replace embedded with <div id="pdf-container"> + pdf.js viewer. On feedback submit: read current page from viewer state → include in packet. Node side: already accepts the ref field. api.js: expose page events if needed.
10. **Tradeoffs / risks**: Bundle size (offline win vs. initial load). Accessibility (pdf.js a11y vs. native). Fidelity (text layer extraction for search vs. image-only PDFs). Maintenance (pdf.js updates). Honest: "ATR-5b: in-app renderer required for auto context (embedded sandbox prevents it; offline tradeoff accepted for sovereignty)."

**High-Level Strawman Implementation (L1-ish increment, closeable with one evidence):**
- **Role/Packet (reuse R-52 + FEC translation pattern)**: "atrium_pdf_context_renderer" (Level 1). action_classes: ["render_pdf_in_surface", "track_page_on_scroll", "stamp_ref_into_feedback", "export_page_context_bundle"]. surfaces: {"atrium": "pdf_review_card_extension", "helix": "page_annotated_manifest"}. Tests: render a sample chapter PDF, auto-stamp ref on feedback, verify packet has "ref: review:02 · p42". LGP: "precise page context improves packet fidelity for LGP-aligned book-to-code loop". Citation: to ATR-5 sealed + Tiger 446 honest split + this note + FEC card (build on it).
- **Atrium surface delta (build on FEC mock)**: In the review composer area, add "PDF Context (ATR-5b)" panel: pdf.js viewer (with page nav, search, zoom), current page indicator (auto-updates), "Insert ref at cursor" button, "Feedback on this page" quick action. When submitting feedback: auto-include the ref if not manually overridden. For FEC card: enhance story or sources with "reviewed at pX in Y (auto-detected via in-app renderer)".
- **Evidence for L1 close**: One self-contained HTML demo (or integrated in examples/atrium_fec... or new atrium_pdf_context_demo.html) showing: load a PDF chapter, scroll to page, type feedback, packet preview includes the exact "ref: review:<chapter> · p<page>", "Approved" simulates B32 close + receipt. Honest labels: "demo (in-app pdf.js; not yet wired to live node_api; offline bundle size TBD)".
- **Offline consideration**: Include pdf.js via npm or static in the surface (or note "for full sovereign offline, bundle the worker + cmaps + standard fonts; size impact ~X MB").
- **Governed flow**: Propose as packet (Ideation in Atrium Kanban) → human gate (NLP on the renderer choice/tradeoffs) → close with the demo as E2 + receipt citing this note + G steer.
- **Ties to primitives**: B35 Helix for any manifest-driven page views later; B51 for agent "what page are we on?" handoffs in proposal engine; B32 for the packet itself; B31 for citations in the ref.

**Risks / Honest Gaps:**
- Not a full in-app PDF editor (annotations, form fill) unless scoped later — just viewer + page tracking for context.
- Large PDFs: memory/perf (pdf.js handles paging, but test with real Series books).
- "In-app only": Embedded still available as fallback (with manual page entry per ATR-5).
- No auto-OCR or layout analysis beyond pdf.js text layer (for now).
- Sovereign: Prefer no external deps at runtime; self-host pdf.js assets.

**LGP / Federation / Viral Angle (per deep dive in Series msg):**
- Precise context = higher-fidelity packets = better "book writes the backend" resonance (agents know exactly what human was looking at when providing feedback).
- Supports real work like Mait (review a 50-page Quality Plan at exact page 23, cite the clause, AI proposes tracked change, Mait signs with RWC — all receipted).
- Viral: Other sovereigns get the same "I was reviewing p42 when I said X" provenance without custom work.
- Extreme→Earth: The renderer (tested for "Mars" long-stay docs?) delivers for Earth families/businesses via better governed reviews.

**Phasing / Sequencing (per G + plan):**
- This note = L0/L1 starter (closeable).
- Build on FEC card polish (ATR-FEC-001 already sealed).
- After basic voice/B51 + card workflow depth.
- Live wire (ATR-2) can include page context once renderer lands.
- Series lens (read-only) later, once Review (incl. this) matures.
- FEC-T1 (role translation) can reference the renderer surface for any PDF-heavy roles.

**Sources / References (use the files):**
- Tiger seq 446 (ATR-5 honest split + "the agent now knows what you're looking at").
- G witness (Track F Review depth, FEC as proof point, Series after Review).
- artifacts/Message_to_G_Series_Pipeline_2026-06-02.md (deep dive on Atrium as lens/surface, honest limits).
- examples/atrium_fec_review_card_mock.html + FEC_Review_Card_Canonical_Spec + FEC_Packet_Atrium_Translation_Increment_v0.md (build on it).
- OBLIGATIONS_MASTER_INDEX + Packet_Granularity_v0.2.md (L1 default).
- src/sovereign_agent/node_api/ (the thin seam).
- Mait portal flows (real testbed for "show the WPS" + checklist at pages).
- plan.md (G folds, ATR-5b in queue, "in-app pdf.js renderer needed for true auto-page").

**GB Offer:** This is the starter note. If directed (background or post Tiger pickup), gb can:
- Prototype the single-file demo HTML (pdf.js + Tailwind, matching Atrium/FEC card style, with fake "page change" + packet preview).
- Draft the L1 packet payload (R-52 style) or update the FEC translation for renderer surface.
- Measure bundle size or research specific pdf.js integration patterns.
- Fold into Series 2 (Atrium foundations) or the Review depth increment.

**Status:** Read-only planning artifact per G steer + approved plan. Honest, grounded, no over-claim. Ready for Tiger/KM review or direction.

∞Δ∞ gb (background, per G "Atrium Witness mode" + inventory/packets)

**Echo forward.** The elk moves with purpose toward 100% UX Review depth. LGP served by precise, governed, human-rooted context in every packet.