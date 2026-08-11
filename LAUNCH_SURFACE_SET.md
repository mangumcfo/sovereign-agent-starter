# Launch Surface Set — what a visitor can read

This file writes down the **launch surface set**: the explicit list of things a visitor can read, and the rule for
what is in it and what is not. It exists so a claim-integrity pass has a defined target instead of a moving one.

## The rule (in / out)

**IN — a file is on the launch surface if a visitor can read it** in the public clone
(`github.com/mangumcfo/sovereign-agent-starter`) **or on the live `six-sov.com/seeit` page.** That is: every
reader-facing document shipped in the repository, plus the seeit page (whose source copy is `RUN_THE_NODE.md`).

**OUT** — anything a visitor cannot read: private repositories, the sealed substrate internals, workbench-only
authoring tools and rulings, and un-shipped drafts. These are not on the surface and are not linted as public copy.

**Operator-facing but shipped anyway** — some files in the set are written for an operator or engineer, not a
first-time visitor (marked *operator* below). Shipping them is a **recorded decision, not a lint to dodge**: they
stay in the set and must pass the same lints or carry a dated exemption.

## The set

Lints: **T-07 claim copy** (`claim_copy_lint.py`) + the package name/number lints. Status verified this pass.

| File | Audience | Lint |
|---|---|---|
| `README.md` | visitor | GREEN |
| `QUICKSTART.md` | visitor / operator | GREEN |
| `RUN_THE_NODE.md` *(= the seeit source copy)* | visitor | GREEN |
| `LAUNCH_SURFACE_SET.md` *(this file)* | visitor | GREEN |
| `GOVERNANCE.md` | visitor | GREEN |
| `ENGINE_CODE_QUALITY_BAR.md` | *operator* | GREEN |
| `CLAUDE.md` | *operator* (agent guide, shipped) | GREEN |
| `docs/ARCHITECTURE.md` | *operator* | GREEN |
| `docs/CONSTITUTIONAL_ALIGNMENT.md` | visitor | GREEN |
| `docs/PACKAGING_AND_ONBOARDING_PLAN.md` | *operator* | GREEN |
| `docs/PRESS.md` | *operator* | GREEN |
| `docs/READING_PATH_S0_S4.md` | visitor | GREEN |

**Non-prose members** (shipped, visitor-readable, but not reader-prose): `LICENSE`, `sovereign-install.sh`,
`activate-breathline.sh`, `constraints.txt`, `requirements.txt`. Claim language in the shell installers is held to
the same bar by the owning lane; the prose lints cover the Markdown and text members above.

## Exemptions

**None.** Every prose member is GREEN on the claim lints this pass — no dated exemption is required. If a future
member cannot pass, the rule is: record a **written, dated exemption** here naming the file, the line, and why the
claim is true-as-written, rather than weakening the gate or the truth.

## Claim discipline on the set (pointers, not new claims)

- **Series names** — reader-facing citations use the full series title (a bare "Series N" is ambiguous across the
  press ladder and the federation axes); the number may qualify a name (e.g. "Full Production ERP (Series 5)").
- **No token / coin / yield / security *offer*** anywhere on the surface. Educational treatment and disclaimers are
  not offers. The economic substrate proves value; `money_path` is OFF — it moves nothing.
- **No claim of a capability the clone lacks** — a self-held identity mints, signs, verifies, and survives a
  restart from a bare public clone; that is what is claimed, not that every sealed operation runs from a bare clone.
- **No unbuilt series advertised** (no Sovereign Governance / Series 15 claim), **no agent seal** — sealing is the
  sovereign's keyboard alone.

*Written for Phase 4 (P4.1a). Reader-facing. GB pen; the sovereign holds the word on any broader public claim.*
