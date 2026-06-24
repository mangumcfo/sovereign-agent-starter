# Review Brief — S4 V2: "Governed Token Mechanics"
*book_id: vol_02_governed_token_mechanics · manuscript_v0.1.md (post-fold, vault 783234f) · GB-sealed 2026-06-24 · audience: sovereign operators + finance/compliance advisors*

**Status going in:** all 13 gates GREEN — but this volume took the same detour V2 did, and worth your knowing. The first board passed it "green" while it carried a live overclaim — *"versioned YAML config enforced at the write"* runs-today, which the code doesn't do (the policy engine loads/versions but enforcement is never wired into execution). Your `exists_is_not_wired` instinct caught it (2nd time this class of miss happened). Tiger folded it honestly — and the **re-run board, now armed with the new check, caught a sibling** (multi-mandate isolation also claimed "enforced"). I re-traced both directions: the runs-today claims are genuinely wired (`role_binder.py` raises on an out-of-envelope action), and every automated-enforcement capability is honestly designed-toward against genuinely unwired code.

## The judgment calls (yours to decide — GB is witness here, not author)

1. **Decision — Does "Governed Token Mechanics" carry when the *automated* governance is designed-toward?** What runs today is the **human breath-gate + declared role scoping + role-envelope refusal** — real, wired guarantees. What's designed-toward is the *automated* layer: YAML-policy-enforced-at-write, per-verb conditions, automated cross-mandate block, the token action classes themselves. Is "human-gated + declared-envelope governance now, automated enforcement next" honest framing for this title, or does "Governed" risk implying the automation runs? (Same family as the S4-01 title call.)

2. **Decision — Approve "the human gate is the runs-today guarantee; automation is the build" as the standing S4 honesty frame?** This volume (and the governance series) now lean on: *the human-witnessed gate + declared envelope hold the line today; automated policy/SOD/cross-mandate enforcement is designed-toward.* Approve this as the consistent way S4 describes enforcement depth, or tighten?

3. **Decision (process) — Is the now-codified `exists_is_not_wired` board-check + the independent GB trace enough, or add a mechanical lint?** This is the **2nd board miss of the exact "engine exists ≠ wired → claimed enforced" class.** It's now codified and the board re-bit it — but do you want an additional *mechanical* gate before S4 publishes (e.g., a lint: any RECEIPT "enforced/runs-today" claim about a policy/gate must grep-match a live enforcement call), so it can't depend on the board remembering?

4. **Decision — Where do the token action classes (mint/transfer/burn) actually close?** Ch3 marks them designed-toward "in this volume and S4-03" — but S4-02 doesn't build them (it's the governance *frame* for tokens). Confirm they close in **S4-03**, or is "this volume" a self-reference that should be tightened (the kind of soft dangling we fixed in V3)?

## GB witness note (context, not a decision)
S4-02 is the proof the codification works: a recurring blind spot (the build lane reads "we built the engine" as "it runs") got named in `book_standard.yaml`, and the very next board re-run caught a sibling instance the first pass missed. The independent fidelity layer has now caught this class twice; the third time, the board should catch it itself. The four calls are scope/framing decisions only you can make; the exists-vs-wired honesty was verified both directions, independently.

∞Δ∞ The gate and the envelope hold the line today; the automation is honestly next. The blind spot is now named. — GB
