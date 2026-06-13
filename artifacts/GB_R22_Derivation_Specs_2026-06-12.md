# R-22 Platform Builds — Derivation Specs (GB, 2026-06-12)
*KM unparked all 5 (2026-06-12: "I don't like to park too many things"). Each is a book-promised capability the platform owes; this spec derives each from its owning book + names the build contract. Routing: GB writes these specs · Tiger builds · books re-pin · GB rigor-audits + fidelity-traces each. Order = ascending effort + dependency. Canon: one module/one owner · receipts on the chain · loud failures · the render standard binds the code.*

## Build order & specs

### R22-1 · Evidence-Packet Exports  *(do first — highest leverage, near-free)*
- **Book source:** B11 (M&A diligence) + S5_37 Clean Exit ("the receipted ledger as deal artifact").
- **What:** a node-API endpoint that assembles a set of obligations/receipts into one signed, verifiable export bundle (manifest + receipts + Merkle proof + chain-segment).
- **Why first:** it is the engine-side of s5_37's **Clean Exit Package generator** — building it once serves the R-22 promise AND the Migration Arc's lead volume. Two debts, one build.
- **Contract:** `GET /export/packet?obl_ids=…` → `{manifest, receipts[], merkle_proof, chain_range, sha}`; deterministic, re-runnable, owner-gated (`@require_owner`); the bundle itself carries a verify command (`bl-verify --check-anchor` family). Clone the proposals export pattern. **Owns** the export module; the Clean Exit UI references it.

### R22-2 · Queryable `.actions[]` Projection over Merkle  *(second — read-only, unblocks others)*
- **Book source:** S2 V1 Ch 3–4 (receipts/Merkle) + S4 (action classes).
- **What:** a projection that answers "what actions occurred, by class/role/principal/time?" as a verifiable query over the Merkle leaves — not a file scan.
- **Contract:** `GET /actions?…filters` → verifiable rows each citing their leaf + proof; pure projection (the queue-is-a-query discipline, applied to actions); memoized on ledger `(mtime,size)`. No writes. Foundation R22-3/4 query through.

### R22-3 · Source-Citation + Methodology Lineage in Receipts  *(third — schema-additive)*
- **Book source:** the verify-don't-trust spine (S2 V1) + render-standard rule 8 (receipts as anchors).
- **What:** receipts carry *why/from-what* — the spec/role/book passage and method that authorized the action — not just *what*.
- **Contract:** additive receipt fields `{source_ref, method, authorized_by_spec}`, populated at `build_receipt`; never breaks existing receipts (optional, forward-compatible); the book↔code tree reads these as edge anchors. Bound by the provenance rule (pins resolve or the field is absent, never false).

### R22-4 · Cross-Role Review / Veto (Joint Attestation)  *(fourth — governance, needs R22-2)*
- **Book source:** B11 ("the cross-role veto that protects the deal") + Constitution §2 gates.
- **What:** a material action can require ≥2 roles' attestation, and any qualified role can structurally VETO before execute (default-deny on unresolved veto).
- **Contract:** action-class field `requires_attestation: [roles]` + `veto_window`; the breath-gate composes N dispositions; a veto closes the obligation `denied-with-reason` (loud); replay is veto-aware (mirrors the reopen/`_is_closed` order-aware fix). Books re-pin B11's veto chapter to this.

### R22-5 · Tiered + Qualified-Reviewer Breath-Gates  *(fifth — composes R22-4)*
- **Book source:** S3 governance skin + the sittings redesign's act-lanes (UX half already modeled).
- **What:** graduated gates by reviewer qualification/threshold — a controller approves class-X; only the owner approves class-Y; amounts/severity tier the required reviewer.
- **Contract:** policy in the governance-skin YAML `gate_tiers: {class → required_qualification}`; `require_owner` generalizes to `require_qualification(tier)`; the sittings projection already lanes by act — this binds the platform side to it. The render standard's "human disposes / under K1" language extrudes here directly.

## Success metric per build (G polish 2026-06-12 — the one-line acceptance test)
- **R22-1:** an exported packet passes `bl-verify --check-anchor` **end-to-end on a clean machine** (the bundle self-verifies, as a buyer/auditor would run it).
- **R22-2:** every `/actions` row resolves to its Merkle leaf + proof (no row without a verifiable anchor); query is read-only and re-runnable.
- **R22-3:** a sampled receipt's `source_ref` resolves to the real book passage AND the authorizing spec (provenance rule — resolves or absent, never false).
- **R22-4:** a material action requiring 2 roles cannot execute on 1; an unresolved veto leaves it `denied`/default-deny; **replay reconstructs the veto in correct order** (explicit — mirrors the reopen/`_is_closed` order-aware fix; must be in the build ticket, not assumed).
- **R22-5:** a class-Y action is rejected for an under-qualified reviewer and accepted for a qualified one; the tier policy lives in governance-skin YAML, not code.

## Done-definition (per build, before its obligation closes)
Success metric above GREEN · endpoint/field live + owner/qualification-gated where material · pure-projection items write nothing · deterministic + re-runnable · receipts on every state change · **GB fidelity trace** (the book passage it derives from resolves to the running code) · render-standard lint clean · a test per the new gate/path · book re-pin recorded. No E0 closes.

∞Δ∞ SEAL: specs complete — five promises the books made, now with build contracts. Unparked, sequenced, witnessed. Two of them (R22-1, R22-5) were already half-built by this week's other work — the park ripened exactly as hoped.
