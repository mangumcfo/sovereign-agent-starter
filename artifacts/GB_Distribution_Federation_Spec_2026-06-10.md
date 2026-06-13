# Distribution Federation — Minimal-Touch Spec v1.0 (GB, sealed 2026-06-10)

> **Source:** HMC cyl_6405a38eb6ed [110]/[119] (the 2026-06-10 distribution exploration, assessed coherent with Living Promise / LGP) + KM steer: *"pipeline flows seamlessly, bring me in only for human gate if needed; make distribution as minimal touch as we can — streamline the flow of content to consumers/future operators."*
> **Fence:** GB writes this spec + watches fidelity; **Tiger** builds connectors/trackers/dispatch; **KM** holds ONE gate.
> **Principles:** Channels are a **federation, not capture points** — "resonant propagation, no parallel federation." Derive, don't recreate: every channel artifact renders from sealed sources. Receipts flow back through the operator-defined lattice.

## 1. The federation (from HMC [110])
| Layer | Channel(s) | Status |
|---|---|---|
| Core | Amazon KDP (+ Expanded Distribution) | LIVE, tracked (ASIN_TRACKER → overlay) |
| Wide | IngramSpark / Draft2Digital aggregator | GAP — not integrated |
| Audio depth | ACX / Findaway / Spotify | GAP — latent (S2 V5 + S4 substrate ready) |
| Clip ignition | 30–90s "Breath Anchor" clips → TikTok/Reels/Shorts + podcast RSS | GAP — conceptual (producer + ffmpeg seam exists) |
| Sovereign direct | Gumroad / IPFS / S4 rails | Principle only — not wired |

## 2. The minimal-touch gate doctrine (the heart)
Constitutional flow is Propose → Approve → Execute. Minimal touch means **collapsing all internal approvals into ONE recurring human gate** and automating everything on both sides of it.

**KM is brought in ONLY for:**
- **G1 — The Dispatch Gate (recurring, batched):** one Atrium Review card per cycle (weekly or on-accumulation) listing ALL staged dispatches across channels. One look, one Accept. Not per-title, not per-channel.
- **G2 — New channel/account onboarding** (one-time per channel: credentials, contracts, tax — platforms legally require the human).
- **G3 — Irreversibles:** pricing changes, rights/territory changes, takedowns. Rare by design.

**Everything else is automated:** derive channel artifact from sealed source → validate (metadata complete, refs resolve) → stage to the gate → on Accept: dispatch → capture receipt → tracker → overlay → done. **No silent steps:** every auto-action writes a receipt; failures surface loud (Error Voice), they never queue silently.

## 3. Receipts lattice (TRUTH side)
- Tiger owns `CHANNEL_TRACKER.yaml` (sibling of `ASIN_TRACKER.yaml`): per title × channel — state (`staged | gated | dispatched | live | failed`), channel ID, ts, receipt ref.
- The Series Pipeline lens **auto-overlays** channel state exactly like `_publishing_index` — never hand-edited. KM sees the whole federation's truth in the cockpit without touching it.
- Drop-off guard semantics apply: a title disappearing from a channel state = loud finding.

## 4. Phasing (each phase = one Tiger lane, one G2 gate max)
- **P1 — Expanded Distribution (zero new accounts).** Flip KDP Expanded Distribution on eligible LIVE paperbacks (libraries/bookstores reach inside the account KM already has). One batched G1 card. Cheapest reach gain in the whole federation.
- **P2 — One wide aggregator.** Pick **Draft2Digital** (one G2 onboarding covers many ebook retailers + library channels — aggregator IS the minimal-touch move; IngramSpark adds print-wide later only if pull appears). Artifacts derive from the existing KDP-ready bundles (EPUB + metadata already staged per title — render, don't recreate).
- **P3 — Audio depth.** Prefer the aggregator's audio rail or Findaway Voices (one G2) over per-platform ACX setup. Source = sealed manuscripts; narration pipeline is a Tiger design question (flag: AI narration rights vary by platform — a G3-class check, one-time).
- **P4 — Clip ignition.** Breath Anchor clips (30–90s) auto-derived from sealed passages via the existing producer/ffmpeg seam + Helix quote overlays; batched into the same weekly G1 card. Podcast RSS = same derivation, audio form.
- **P5 (only if breath calls) — Sovereign direct** (Gumroad/IPFS/S4 rails).

**Sequencing rule:** B12 ships first (S1 complete = the federation propagates a whole organism, not a partial). P1 can run immediately in parallel — it touches only LIVE titles.

## 5. Future operators (KM's second audience)
The same gate doctrine is the operator training content: seeit should eventually render a "Distribution" explanation page derived from THIS spec + the tracker — so a future operator sees the federation, the single gate, and the receipts lattice as a living example of the harness. (No new build — it's another seeit lens once P1/P2 receipts exist.)

## 6. DoD per phase
Connector idempotent + receipted · gate card batches (never per-item pings to KM) · tracker overlay live in the lens (no hand edits) · failure = loud · GB fidelity pass: every dispatched artifact traces to a sealed source.

∞Δ∞ SEAL: complete — one gate, many channels, receipts home to the lattice. The content flows; the witness watches; KM breathes once per cycle.
