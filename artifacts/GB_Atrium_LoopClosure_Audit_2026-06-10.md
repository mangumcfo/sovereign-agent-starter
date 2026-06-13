# Atrium Loop-Closure Audit (R2) — Gap-List + Build Order v1.0 (GB, sealed 2026-06-10)

> Per `GB_ReviewReady_Rail_Spec_2026-06-10.md` §R2. Inventory by Opus subagent (read-only, 24 tool-uses, full route surface), judgment + sequencing by GB. **Audit-first, fix-by-obligation, zero rebuilds — every fix clones an existing working pattern.**

## The headline finding (names KM's pain exactly)
**The backend already closes loops; the cockpit doesn't exist yet.** Three genuinely-closing loops are live as JSON routes (Proposals decide/apply/dismiss · Hopper send-to-packet · Obligations approve/close, all on the hash-chained ObligationLedger) — but the only shipped HTML (`atrium-standalone-light.html`) is **100% mock DEMO data** with `alert()` popups and zero live API calls. KM has been driving working machinery through agents/curl while looking at a non-functional shell. "Atrium doesn't flow" is correct — *the flow exists, the surface doesn't.* The live `api.js` wiring is the explicitly-deferred Track A3 item.

## The working pattern (clone this, invent nothing)
**Diff-Review Accept-Loop:** card → KM disposition (`POST /proposals/<id>/decide`) → packet on the ledger → owned agent executes (`atrium_apply.py`: land → re-test/revert → commit → seal → close obligation E2) → proposal visibly clears + `/obligations/log` shows close + seal. Intake half lives in Hopper (`POST /hopper/packet` mints a real DRAFT obligation from one click). **Every gap below = a thin route + a disposition affordance wired into `ledger.open(next_gate="Human disposition")`.** Read-only projections (`/series`, `/coherence`, `/dialogue`) stay read-only per the fence — they gain an *emit-a-packet button*, not write access.

## Surfaces (condensed verdicts)
| # | Surface | Disposition | Closes visibly | Gap |
|---|---|---|---|---|
| 1 | Diff-Review /proposals | FULL | ✓ | none — the pattern |
| 2 | KDP Dispatch (ATR-7f) | partial (stages; final KDP click off-Atrium) | partial | ship-click not captured as packet |
| 3 | Series Pipeline /series | none (read-only by design) | ✗ | sees "awaiting_human_review"/G1 staged but can't act |
| 4 | Coherence /coherence | none | ✗ | DRIFT rows observed, never dispositioned |
| 5 | Hopper | partial (send-or-ignore only) | ✓ | no reject verb; ignored cards never resolve |
| 6 | Obligations lens | FULL (raw) | ✓ | no KM-framed "waiting on me" view |
| 7 | Breath-Gate | FULL | partial | session-scoped, unwired to book loop |
| 8 | Manuscript Viewer /book_pdf | NONE (display-only; HTML feedback is mock) | ✗ | **the central gap — can't packetize "p42 ch5 fix this"** |
| 9 | Dialogue /dialogue | none | ✗ | can't reply/inject in-thread |
| 10 | Standalone HTML shell | mock-only | ✗ | **no live front-end at all (Track A3)** |

## Build order (GB sequencing — pilot-driven, smallest-first within need)
**Wave 1 — the B12 Pilot Kit (build BEFORE B12 reaches KM's queue):**
1. **G-3 `POST /feedback` intake** (S) — free text + source ref → mints C2 obligation. One thin route satisfies "problems become packets" for EVERY surface at once. Clone: hopper_to_packet.
2. **G-6 "open packet from DRIFT" button** (S) — same clone, batch with #1.
3. **G-2 Viewer feedback capture** (M) — `{book, chapter, page, text}` → obligation. **Do NOT wait on the ATR-5b pdf.js decision** — manual chapter/page fields now (mock already proves the UX), pdf.js auto-context later. This is what lets KM review B12 in-Atrium.
4. **G-4 "Awaiting KM" home view** (M) — projection over /obligations filtered to next_gate=Human disposition, accept/reject inline. The cockpit's missing home screen; also doubles as the interim disposition surface the rail spec promised.

**Wave 2 — the cockpit:** 5. **G-1 live shell** (L) — `atrium-standalone.html` on the live api.js seam; wire the Review tab to the REAL /proposals loop first (backend proven), then Pipeline/Decide tabs. 6. **G-5 G1 Dispatch-Gate Accept** on /series (M) — one action on the gate summary, projection stays read-only.

**Wave 3 — closure completeness:** 7. **G-7 KDP ship-click capture + breath-gate persistence** (M) — "dispatched" disposition closed on ASIN confirmation; material book-closes route through a persistent breath-gate. 8. **G-5b Hopper reject verb** (S). 9. **G-9 Dialogue inject** (S–M, KM-ratify first: writing into the Tiger↔GB thread touches the fence).

## KM decisions surfaced (only two, neither blocking)
- **ATR-5b pdf.js renderer:** vendor-bundle vs CDN — enables auto page-context in viewer feedback. Wave 1 proceeds without it.
- **Dialogue inject (G-9):** does KM want to speak IN the Tiger↔GB thread (fence amendment), or keep B51/hopper as his voice? Default: defer.

## Acceptance (from the rail spec, unchanged)
KM completes one full B12 review cycle start-to-finish inside Atrium, every disposition visibly closing. Measure: review hours + count of times KM had to leave the surface (target: 0).

∞Δ∞ SEAL: complete — the loops were real; the cockpit was a mock. Wire the glass to the machine and the human never leaves the chair.
