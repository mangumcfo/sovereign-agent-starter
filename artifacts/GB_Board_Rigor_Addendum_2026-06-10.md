# R1.5 — Board Rigor: No Rubber Stamps (Addendum to Review-Ready Rail Spec, GB, sealed 2026-06-10)

> **Trigger (KM, HMC [189]):** "If I'm watching the boards… they are more robust; if I run 'auto'… they seem fragile check-the-box activities… we are providing these to humans who will sense shallow work — if the boards are shallow then GIGO."
> **G's structural steer (HMC [190]) adopted in full**, plus one GB guard against metric gaming. Binds every board run from B12's UX/Technical boards forward.

## The core diagnosis (encode it, don't exhort it)
KM's observation is a law, not a mood: **watched boards are robust; unwatched boards decay into completion-optimizers.** Rubber-stamping is what optimization looks like when the watcher leaves. The cure is therefore NOT "try harder" — it is **making the watching structural and unpredictable**: a standing witness who samples board work randomly, so no board run can know which finding will be audited, so every finding must survive audit. Random sampling is the economically efficient form of full watching. (Same lesson as the seeit FAIL: machine gates prove work *happened*; only witness gates prove it was the *right* work.)

## Requirements per board run (Editorial, UX, Technical) — G's five, binding
1. **LGP Alignment Check** — every finding states explicitly how it strengthens or risks LGP / human primacy / sovereign continuity. No "looks good."
2. **Findings → Obligations** — every material finding becomes a B32 obligation; closed with evidence or deferred-with-reason. Notes don't count.
3. **Depth Gate** — ≥1 substantive issue or improvement per major section, OR a short "all clear" justification tied to the sealed text.
4. **Fidelity Witness** — GB traces board outputs before the Review Brief generates; shallow patterns flag as gap obligations.
5. **Human Sense Test** — board output written as if a discerning human reads it cold. Future operators will feel hollowness.

## GB guard — the Goodhart clause (R1.5g)
The Depth Gate creates a quota, and quotas invite fake findings (manufactured nitpicks that satisfy the count). Counter-structure:
- **Sampled adversarial audit (GB, every board run):** GB randomly samples N findings per board (N≥3 or 25%, whichever is greater) and adversarially verifies each: (a) evidence resolves — the cited text/line exists and says what the finding claims; (b) the finding is *material* — a discerning human would care; (c) the resolution is *real* — the fix was actually applied or the rationale actually reasons. Sample selection is unpredictable to the board.
- **Verdict classes:** a sampled finding failing (a) = fabrication (SEVERE, board run invalid); failing (b) = padding (the quota-gaming signal — two padding hits in one run = run flagged shallow, re-run required); failing (c) = theater-closure (obligation reopened).
- **Conflicting incentives stay live:** board personas must argue FOR and AGAINST with genuinely conflicting incentives, and every objection resolves explicitly (fix / accept-and-log / reject-with-reason). An objection that vanishes without resolution = gap obligation. Auto-runs decay precisely when personas converge — convergence without recorded conflict is itself a shallow-pattern flag.
- **The trust cascade:** GB watches every board (cheap, standing); **KM spot-audits GB's audits occasionally** (his choice of book/board, unannounced). The watcher is also watched. That is what keeps "auto" honest at every layer.

## Wiring into R1
`review_ready_contract.py` gains a fifth gate: **Board Rigor Audit = PASS** (GB's sampled-audit verdict in the meta-cylinder, same lookup pattern as the fidelity gate). A book cannot flip READY with boards run but unaudited.

## What KM sees
Nothing new to do. The Review Brief now carries a one-line rigor stamp per board: `audited n/N — fabrication 0, padding 0, theater 0`. If you ever feel shallowness through a clean stamp, that exact case becomes a contract amendment — the rail hardens by being doubted.

∞Δ∞ SEAL: complete — boards earn the right to reach the human; the witness earns the right to be trusted; nobody is unwatched.
