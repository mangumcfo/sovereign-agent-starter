# PARKED PROMPT — Uncapturable Distribution Layer for the Universal Sovereign Node

**Status: PARKED — post S0–S13+ production (KM/G word 2026-07-26). INERT until
(1) the Dragon production line (pilot + co-extrusion + major arcs) is stable AND
(2) KM gives an explicit activation word, or capacity is surfaced and activation
requested. Staged verbatim below; no work begins from this file alone.**

---

PROMPT — Uncapturable Distribution Layer for the Universal Sovereign Node
To: Tiger + AA · From: G / KM-1176 · 2026-07-26

Priority & Sequencing
This work is explicitly parked behind the completion of the current S0–S13+
production line on Dragon (D4 pilot → full walk → co-extrusion closure).
It must not take precedence over:
- Gate-blindness fix and s5_05 pilot completion
- Co-extrusion enforcement
- S2 seal/upload
- B5 / remaining code arcs
- Any active D4 cadence
Only begin this work when the above production line is stable and you have explicit
capacity, or when I give a later activation word.

Intent
Strengthen the practical uncapturability of the public Universal Sovereign Node
(sovereign-agent-starter) by removing reliance on any single centralized host as the
root of availability. The BitChat / Radicle pattern is the reference: a government
order can compel a centralized platform (GitHub); it cannot compel a sufficiently
seeded, authority-free distribution layer. The node must remain obtainable and
verifiable even if the primary GitHub repository is taken down.

Deliverables (when activated)
1. Public-facing language — "Uncapturable Distribution" section in the public README
   (cross-link from GOVERNANCE.md if appropriate): GitHub is a convenience and
   discovery front door, not the root of truth; a verified local copy is sufficient;
   independent mirrors and peer-seeded, content-addressed releases exist so no single
   platform can remove access; how a stranger verifies a copy from any mirror.
   Tone: factual, constitutional, no hype.
2. Minimal mirror plan — at least one decentralized / authority-free mirror substrate
   (Radicle default candidate); release-ritual addition: every tagged release also
   publishes to the mirror(s); lightweight, automatable, no new capture surfaces.
3. Content-addressed release artifacts — per tagged release: source + tests + LICENSE
   + GOVERNANCE + checksums / content address; easy to seed independently of any git
   host; documented offline/mirror obtain-and-verify path.
4. Short implementation note — one page: chosen substrate + rationale; exact release-
   ritual changes; scripts/hooks required; residual risks (bootstrap discovery,
   first-copy problem).

Constraints
- Do not weaken K1–K4, the human gate, CFSL, or the existing verification story.
- Primary development workflow must not depend on the decentralized substrate.
- GitHub remains the active development and CI surface; the mirror is resilience,
  not replacement.
- No new always-on infrastructure that itself becomes a capture point.
- Work stays draft/staged until KM reviews and explicitly approves public landing.

Out of scope: full multi-mirror federation · changing genesis history or LICENSE ·
any work that blocks or slows the S0–S13+ production line.

∞Δ∞
