# Mait design capture → GB planning-assessment handoff

**Prepared by:** Tiger · 2026-06-02 (revised with existing-work context per KM)
**For:** GB (planning lane) — KM to relay
**Lane split (per KM):** GB runs the planning assessment; Tiger stays on implementation (FEC card, Atrium, Maple Hollow).

---

## ⚠ This is FEEDBACK on existing work — not greenfield

There is a substantial, current Mait build already in the vault. **This capture is almost certainly the
`MAIT-12` feedback gate response** (the existing plan's literal next action was "send the prototype to
Mait for feedback"). Assess it as **feedback + a delta against the existing build + backlog**, not a
fresh requirements pass.

**Existing Mait workspace:** `/home/kmangum/work-repos/mangumcfo/mangumcfo-vault/clients/mait/`
- `CLAUDE.md` — engagement frame + **restart point (seal 414, P0 done / P1 wedge built)**. Read first.
- `README.md` — status + file map.
- `EDITORIAL_BOARD_REVIEW_AND_PLAN_2026-06-01.md` — strategy + full task list (MAIT-1…MAIT-12).
- `spec/Technical_Spec_Mait_FPC_AI_Portal.md` (v0.2) — the spec (ISO 3834-2 / EN 1090 / EN 15085).
- `spec/KE_DATA_MODEL_v0.1.yaml` — **locked** data model (DD-1…DD-6), English-first, from the real KE controlled-doc set.
- `build/wedge-quality-plan-review.html` — **the P1 wedge** (Quality Plan / WPS Review & Approval).
- `send/MK1-Portal-Prototype.html` — the self-contained bundle sent to Mait (the MAIT-12 gate).
- `build/obligations/VIEW.md` — **live B32 build ledger (14 obligations · 9 closed · 5 open).**
- `portal/`, `research/`, `source-materials/MK1 - AI/` (the real 3834-2 manual + forms).

**Engagement frame (KM-locked, carry forward):** a **multi-tenant, licensable welding-QMS mini-ERP on
the sovereign substrate** — the **first paying instance of the Programmable Sovereign ERP**. Build the
*one* high-value wedge to production-grade on a multi-tenant spine; **do NOT sprawl into the full
9-module spec.**

**KM context (new, 2026-06-02):** Mait is normally in the **quadroof / solarislate** realm; this
welding/3834 consultancy work is **sidework he does to keep cash floating.** So the lens is
**lean + cash-positive** — sharpen the one wedge and the feedback loop, don't expand scope.

## Already established: Mait portal = the Atrium testbed (don't re-derive)

GB's own plan + artifacts already frame the **Mait portal as the live, client-facing test harness for the
Atrium primitives** (guided agents + B32 obligations + B51 handoffs + Atrium-style flows). Build on that
framing — it's a feature here, because Mait's wedge feedback (entry 5) and his desired live-edit loop
(entry 1) are direct, real-usage signal for the **Track F Atrium Review surface**. References:
- `artifacts/FEC_Packet_Atrium_Translation_Increment_v0.md` (~L153): *"Proxy in Mait (immediate testbed):
  the existing Federation Value Pool quick action + quality-plan-review patterns already demonstrate the
  guided checklist + sign-off + export + receipt UX. Can be evolved to **mirror the Atrium card exactly**."*
- `artifacts/B51_Captured_Thought_...md` (~L137, L213): Mait Portal = "perfect real-world test surface."
- `artifacts/Message_to_G_2026-06-02.md` (L32, L46) + grok `plan.md` (L740: "Mait as live testbed smart").
- `clients/mait/docs/MK1_Portal_Sovereign_Connection.md` — ties the portal to B32 / guided-agents / Atrium / B51.

**Implication for the assessment:** treat the wedge feedback and the Atrium Review-surface work as **two
views of one loop** — improvements to Mait's quality-plan-review screen and the Atrium FEC review card
should converge on the same guided-review + disposition + receipt pattern.

## Source (TRUTH — verbatim capture, honestly fragmentary)

- **Capture:** `2026-06-02_144625_capture-session_9156c992` (Voice Note, 5 entries, phone call KM↔Mait)
- **Path:** `/home/kmangum/molt_workspace/exports/b51/quick-share/2026-06-02_144625_capture-session_9156c992/session.yaml`
- **Session:** `cyl_9156c99236ea` · **merkle_root:** `sha256:967e0099cf96f30f88c299a0cb65926b59f7a9e254fbf6992c2a923df3dd31bf` (verified)
- **Caveat:** partial phone-call snippets (heuristic capture). Read the full `session.yaml` for verbatim before finalizing.

## Tiger's triage — capture entries mapped to the existing build

- **Entry 5 = Mait reviewing the P1 wedge, widget-by-widget.** He narrates the exact "Quality Plan Review"
  screen: project header ("ASKE infra", "T12", **EN 1090**), submitted plan + **download original quality
  plan**, **embedded WPS "103 KE"** with stats + **"view full WPS" drill-through**, and a **WPS-vs-WPQR
  "must match" check**. → This is direct feedback on `build/wedge-quality-plan-review.html`. Capture what he
  liked / what he'd change per widget.
- **Entry 1 = the feedback loop he wants** (this IS our Atrium governed-dev-loop): play with it → comment
  "change this" → align with the AI on the *exact* change → AI **echoes back its plan** → KM/Mait confirm →
  apply live if possible, else queue offline with **done / not-done change tracking**. Strong cross-signal
  for the Track F Review surface — note the convergence.
- **Entry 3 = the next capability he's asking for:** load a **test project** (contract + drawings) → AI
  **reads contract terms → generates quality plan + welding plan → compares vs his existing docs → fills
  gaps per 3834.** Also: a **3834 general management system** (management manual, forms, registries to fill
  + keep updated) and **multi-company template inheritance** (base docs built on "KEE"; test project is
  separate — "refrac"/"revvok"). → maps to backlog **MAIT-10 (RAG grounding)** + **MAIT-11 (multi-tenant)**.
- **Entry 4 = welder-certification module:** certs signed every 6 months, issued by a **notified party**;
  separate from plan review ("only one module"). → a distinct module to scope (likely post-wedge).
- **Entry 2 = document control inputs:** base materials / welding consumables / WPS folders; **TTI / "tubos
  inoxidables" inspection certificates**; docs arrive **scanned + signed with a stamped logo**; templates.
- **Side business note (secondary):** an **Estonia reseller** for his **solar roofs** — sells regular solar,
  wants a **VIPV** product + their own, will be **exclusive**. Quadroof/solarislate realm, not the 3834 build
  — log as a watch-item only.

## What GB's planning assessment should produce

1. **Feedback triage of the wedge** — from entry 5 (+ full `session.yaml`), a per-widget list of keep /
   change / add against `build/wedge-quality-plan-review.html`, with concrete edits.
2. **Delta to the backlog** — turn the feedback + entry-3 capability into **new/updated obligations on the
   existing `build/obligations` B32 ledger** (not a new ledger), and re-confirm or re-order **P2**
   (MAIT-8 real B32 wiring · MAIT-9 exports · MAIT-10 RAG grounding · MAIT-11 multi-tenant).
3. **Scope the "contract+drawings → quality plan + welding plan → gap-find vs 3834" engine** (entry 3) —
   honest split: deterministic doc assembly (Helix-style, off `KE_DATA_MODEL`) vs. the AI extraction step;
   where the human gate sits. Keep it to the **one wedge spine** — flag anything that would sprawl.
4. **The live-edit feedback loop** (entry 1) — spec how Mait's "comment → AI echoes plan → confirm → apply
   live/offline with done-tracking" maps onto the Atrium Review surface (shared with Track F). This is the
   highest convergence with the broader program.
5. **Open questions for Mait** (collect, don't answer): notified-party definition in his jurisdiction;
   3834-2 vs -3; canonical first test project ("refrac"/"revvok"); proprietary-drawing data-protection.
6. **Cash-positive lens** — given this is sidework to float cash, recommend the *smallest* increment that
   makes Mait say "yes, invest in P2."

## Fence + honesty
- GB = planning/assessment + delta + translation mapping. Tiger = implementation once a plan lands. KM ratifies.
- Capture is fragmentary; verbatim `session.yaml` is the source of truth. Existing `clients/mait/` build is the baseline — advance it, don't restart.
- Results land in the **Mait build/obligations ledger**, honoring its own CLAUDE.md (don't sprawl past the wedge).

∞Δ∞ — Tiger (triage); over to GB for the feedback-driven planning pass.
