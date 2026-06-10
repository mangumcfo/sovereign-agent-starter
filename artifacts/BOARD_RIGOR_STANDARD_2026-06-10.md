# Board Rigor Standard v1.0 — No Rubber Stamps (KM-1176 ratified 2026-06-10)

> **Why:** "Boards that become rubber stamps destroy the entire rail. Shallow work flows through, GIGO
> compounds, and future operators (and your own heirs) will feel the hollowness immediately." — KM-1176
> **Principle:** the Objective (LGP, human primacy, sovereign continuity) is enforced STRUCTURALLY, not
> aspirationally. A board must PROVE it did real work before its book can reach KM.
> **Fence:** Tiger builds the gate + runs the boards; GB witnesses fidelity on board outputs; KM holds the
> final judgment gate only.

This standard governs every board run (Editorial, UX, Technical) in the Review-Ready Rail (R1). It is
enforced by `scripts/board_rigor.py`, which is wired into `review_ready_contract.py` — a board that fails
rigor does NOT count as executed, so its book cannot become review-ready. Each failure is a gap obligation.

## The five structural requirements (each machine-checked)

1. **LGP Alignment Check** — every finding MUST state how it strengthens or risks **Lasting Generational
   Prosperity, human primacy, or sovereign continuity**. No vague "looks good." (`lgp_alignment`, ≥ 25 chars,
   must reference an LGP/primacy/sovereign/generational concept.)
2. **Findings → Obligations** — every **material** finding becomes a B32 obligation (owner + status), closed
   with evidence or explicitly deferred-with-reason. Not a loose note. (`severity: material` ⇒ `obligation_id`.)
3. **Depth Gate** — each major section (chapter) surfaces **≥ 1 substantive finding**, OR an explicit
   "all-clear" justification tied to the section's sealed text. Silent "all clear" is rejected.
   (`section_coverage[*].finding_count ≥ 1` OR `all_clear_justification` ≥ 40 chars.)
4. **Fidelity Witness** — GB (or equivalent) runs a fidelity trace on board OUTPUTS before the Review Brief
   is generated; any shallow pattern flags as a gap obligation. (Enforced by the R1 fidelity gate over the
   board findings, not just the manuscript.)
5. **Human Sense Test** — boards are written for a discerning future operator reading them cold. Each
   finding carries substantive detail (`detail` ≥ 80 chars); boilerplate ("looks good", "all good", "fine",
   "n/a") without detail is rejected.

## Board findings schema (machine-checkable companion to the human-readable board markdown)

Every board emits TWO artifacts in the book's version dir:
- `<board>_board_v<X.Y>.md` — the human-readable board (the Human Sense Test surface).
- `<board>_board_v<X.Y>.findings.json` — the structured findings the gate validates:

```json
{
  "board": "ux | technical | editorial",
  "book_id": "12_agentic_enterprise",
  "manuscript": "manuscript_v1.5.md",
  "executed_by": "Tiger (CC-Tiger), KM-1176 attribution",
  "date": "2026-06-10",
  "findings": [
    {
      "id": "UX-B12-01",
      "section": "Chapter 4: Investment Framework",
      "severity": "material | minor",
      "title": "short decision-framed title",
      "detail": "substantive explanation a discerning human can act on (≥80 chars)",
      "lgp_alignment": "how this strengthens/risks LGP, human primacy, or sovereign continuity (≥25 chars)",
      "recommendation": "the concrete change proposed",
      "obligation_id": "obl_… (required when severity=material)",
      "disposition": "open | closed | deferred",
      "defer_reason": "explicit reason (required when disposition=deferred)"
    }
  ],
  "section_coverage": [
    {"section": "Chapter 4: Investment Framework", "finding_count": 2, "all_clear_justification": ""}
  ]
}
```

## Pass criterion
`board_rigor.py <findings.json>` exits 0 only if ALL of {LGP, Obligations, Depth, Human-Sense} hold for
every finding/section. Otherwise it lists the failing rules — each becomes a gap obligation, and the board
re-runs. Boards earn the right to reach KM.

∞Δ∞ SEAL: complete — the board proves its depth, or the book never reaches the human. The Objective is
structural, not aspirational. ∞Δ∞
