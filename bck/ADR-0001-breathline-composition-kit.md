# ADR-0001 — Breathline Composition Kit (BCK)

**Status:** Accepted (KM plan-of-record + folds · 2026-08-14). Phase 0 worded by KM.

## Context
Builders must compose the sovereign node's PRESENT capabilities without re-reading the whole shelf and without
any capability drifting from what the code does. **Build the missing half (graph generator · contracts-as-data ·
verifier · builder brief), harvest the rest, one domain, no new landlord.** Infrastructure, not apps — for LGP.

## Decision (locks + folds)
- **Name = Breathline Composition Kit (BCK)** — locked here; no weekly renames (fold 1).
- **Home = `sas-public-genesis` (the starter)** — shared authority, P-Push discipline. BCK = **new files only**
  (this ADR · `bck/compose_graph_generator.py` + `bck/compose_graph.yaml` · verifier script · contract
  schema+instance · builder brief). This ADR lives **with the kit** (fold on the pre-fold "federation repo").
- **Pinned tip = `710a40f`** — the post-confidentiality-shield kernel (AA CS-bar GREEN CS1–CS8). Printed in every
  artifact, as a **constant** in the generator. **Fold 2:** if the confidentiality shield had landed mid-harvest,
  re-pin + regenerate the graph ONCE, noted in the graph header. It landed first — the graph is born post-shield.
- **Graph is GENERATED from the tree** at the pin, never hand-authored; the script ships with the graph; CI
  (`--check`) regenerates and diffs the harvested rows, nonzero exit on kernel-surface drift (H3).
- **PRESENT rule (H5):** a capability/contract row claims PRESENT **only by citing passing test IDs** (the
  co-extrusion discipline applied to composition). No test → not PRESENT.
- **Fold 4 — series↔platform maps barred from machine truth.** `compose_graph.yaml` carries **sealed-series homes
  only** (the "series cite"). A **platform≈series** map ("Uber ≈ S6/S10") stays OUT until it passes the four-layer
  check (substrate → pin → boundary → consumer); sketches live in **Appendix A of this ADR only**.
- **Fold 5 — builder brief charter, line one:** *PROPOSE / DRAFT ONLY · KM/owner disposes · own node only · no
  auto-sanction · no hosted tools.* Same secretary law as the web surface.
- **H4 — verifier = a floor with published SCOPE**, never "certified"/"secure."
- **H7 — one domain first:** coordinated capacity (cite the WP3 drill receipts as the lived template — fold 6, do
  not re-litigate the verticals). Not four platform packs in one shot.

## Non-goals
Platform-clone builds · hosted/shared tool endpoint · auto-dispose · hand-authored graph rows · "certified"
language · kernel product growth · touching a WP4 pilot daily-path file. **Option A shield + WP4 pilot are other lanes.**

## Owners / enforcement
GB — graph generator (phase 1) · AA — bars + scores (no self-declared GREEN); cold-agent test = the A↔B acceptance
test · Tiger — fence-verifier v0 + coordinated-capacity contract to AA's bar. **STOP after phase 3 + cold-agent test.**

## Appendix A — platform≈series sketches (designed-toward · NOT machine truth)
*Parked; never merged into `compose_graph.yaml` until each passes substrate→pin→boundary→consumer.*
- *(none ratified — sketches only, filled as platforms pass the four-layer check.)*

∞Δ∞
