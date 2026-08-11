# Launch Surface Set — what a visitor can read

This file writes down the **launch surface set**: the explicit, **sweep-derived** list of everything a visitor can
read, and the rule for what is in and out. The set is defined by a filesystem sweep, not a hand-typed list, so a
new shipped file cannot silently escape the claim lints.

## The rule (in / out)

**IN** — every **git-tracked** file a visitor can read after cloning
`github.com/mangumcfo/sovereign-agent-starter`, plus the live `six-sov.com/seeit` page (source copy
`RUN_THE_NODE.md`). The prose members are swept with:

```
git ls-files '*.md'      # + '*.sh' '*.txt' 'LICENSE' for the non-prose members
```

**OUT** — anything **not git-tracked** (local build/test artifacts never shipped in a clone), private repositories,
sealed-substrate source internals beyond their shipped READMEs, and workbench-only tooling/rulings.
Explicitly excluded, verified untracked this pass: `.pytest_cache/README.md` (local pytest artifact — not shipped).

**Operator-facing but shipped** — files written for an operator/engineer, and example fixtures, are marked below.
Shipping them is a **recorded decision, not a lint to dodge**: they stay in the set and must pass the same lints or
carry a dated exemption.

## The set — every git-tracked `.md` (19 files)

| File | Audience | T-07 lint |
|---|---|---|
| `CLAUDE.md` | operator | GREEN |
| `ENGINE_CODE_QUALITY_BAR.md` | operator | GREEN |
| `GOVERNANCE.md` | visitor | GREEN |
| `LAUNCH_SURFACE_SET.md` | visitor | GREEN |
| `QUICKSTART.md` | visitor | GREEN |
| `README.md` | visitor | GREEN |
| `RUN_THE_NODE.md` | visitor | GREEN |
| `docs/ARCHITECTURE.md` | operator | GREEN |
| `docs/CONSTITUTIONAL_ALIGNMENT.md` | visitor | GREEN |
| `docs/PACKAGING_AND_ONBOARDING_PLAN.md` | operator | GREEN |
| `docs/PRESS.md` | operator | GREEN |
| `docs/READING_PATH_S0_S4.md` | visitor | GREEN |
| `docs/specs/S5-05_sovereign_object_model_v0.1.md` | operator | GREEN |
| `examples/two_document_catalog/charter_src/charter.md` | example fixture | GREEN |
| `examples/two_document_catalog/fieldguide_src/guide.md` | example fixture | GREEN |
| `scripts/README.md` | operator | GREEN |
| `src/primitives/sealed/layer_1_root/README.md` | operator | GREEN |
| `src/sovereign_agent/node_api/README.md` | operator | GREEN |
| `tools/README.md` | operator | GREEN |

**Non-prose members** (git-tracked, visitor-readable, not reader-prose): `LICENSE`, `activate-breathline.sh`, `constraints.txt`, `requirements.txt`, `scripts/mint_node_token.sh`, `scripts/run_node_api.sh`, `scripts/static_scan.sh`, `sovereign-install.sh`, `src/overlays/v1.0.1-merkle-repair/AUTHORIZATION.txt`, `src/overlays/v1.0.1-merkle-repair/PATCH_MANIFEST.txt`, `src/overlays/v1.0.2-zk-repair/AUTHORIZATION.txt`, `src/overlays/v1.0.2-zk-repair/PATCH_MANIFEST.txt`, `src/overlays/v1.0.3-zk-range/AUTHORIZATION.txt`, `src/overlays/v1.0.3-zk-range/PATCH_MANIFEST.txt`, `src/primitives/sealed/SEAL.txt`, `src/primitives/sealed/SEAL_MANIFEST.txt`, `tools/create-sovereign-bundle.sh`.
Claim language in the shell installers is held to the same bar by the owning lane; the prose lints cover the
Markdown members above.

## Exemptions

**None.** Every prose member is GREEN on the claim lints this pass — no dated exemption required.
If a future member cannot pass, record a **written, dated exemption** here (file · line · why the claim is
true-as-written), rather than weakening the gate or the truth.

## Claim discipline on the set (pointers, not new claims)

- **Series names** — reader-facing citations use the full series title, optionally qualified by number as in
  "Full Production ERP (Series 5)". A bare series number with no name is ambiguous and is flagged — except CLI
  arguments and id-format examples inside code spans, which the lint carves (the gate is fixed, not the tool).
- **No token / coin / yield / security *offer*** anywhere on the surface. Educational treatment and disclaimers are
  not offers. The economic substrate proves value; `money_path` is OFF — it moves nothing.
- **No claim of a capability the clone lacks** — a self-held identity mints, signs, verifies, and survives a
  restart from a bare public clone; that is what is claimed, not that every sealed operation runs from a bare clone.
- **No unbuilt series advertised** (no Sovereign Governance / Series 15 claim), **no agent seal** — sealing is the
  sovereign's keyboard alone.

*Written for Phase 4 (P4.1a / finish). Sweep-derived, reader-facing. GB pen; the sovereign holds the word on any
broader public claim.*
