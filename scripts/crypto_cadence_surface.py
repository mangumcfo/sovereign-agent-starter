#!/usr/bin/env python3
"""
crypto_cadence_surface.py — routes the EXPENSIVE crypto lanes through Atrium (one human gate), instead of
permission-bypassed cron agents. "Everything in Atrium. One human gate only." (the operator 2026-06-12.)

  · Adversarial review (Lane 3) — when a commit touches primitives/adapter, the git hook appends a trigger
    to artifacts/crypto/adversarial_pending.tsv. This drains those triggers into ONE gated Atrium card
    ("adversarial crypto review pending — primitives changed") for the operator to disposition; running the review is
    the accepted action. Also run from the weekly cron to surface the standing Friday review.
  · Deep baseline (Lane 4) — mints the one-time "run deep crypto baseline audit" card once (sentinel).

No agents are spawned here — it only mints cards. the operator's Accept is what authorizes a review to run.
∞Δ∞ The trigger is in Atrium; the gate is the human; the agent runs only on Accept. ∞Δ∞
"""
from __future__ import annotations
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PENDING = REPO / "artifacts" / "crypto" / "adversarial_pending.tsv"
ARCHIVE = REPO / "artifacts" / "crypto" / "adversarial_pending.archive.tsv"
BASELINE_SENTINEL = REPO / "artifacts" / "crypto" / ".deep_baseline_carded"


def _ledger():
    sys.path.insert(0, str(REPO / "src"))
    from sovereign_agent.obligations.ledger import ObligationLedger, get_ledger_root
    return ObligationLedger(root=str(get_ledger_root()))


def surface(stamp: str | None = None) -> dict:
    out = {"adversarial_card": None, "deep_baseline_card": None, "triggers": 0}
    led = _ledger()

    # Lane 3 — drain on-change triggers into one gated adversarial-review card
    triggers = []
    if PENDING.exists():
        triggers = [ln for ln in PENDING.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if triggers:
        out["triggers"] = len(triggers)
        r = led.open(
            title="⚔ Adversarial crypto review pending — primitives/adapter changed",
            owner="owner", classification="C1", material=True, category="judgment",
            next_gate="Human disposition (Atrium Review)", ref="adversarial_crypto:pending",
            intent=("On-change trigger (crypto cadence): the sealed primitives or the adapter changed — the "
                    f"only moment frozen crypto gets riskier. {len(triggers)} change event(s):\n"
                    + "\n".join("  · " + t for t in triggers[:12])
                    + "\nAccept = run the full adversarial crypto review (scripts/cron/"
                      "adversarial_crypto_review_prompt.txt: forgery · invalid-curve · malleability · "
                      "nonce/RFC6979 · constant-time · adapter fidelity). Also: rebase the seal tripwire "
                      "baseline (seal_manifest_tripwire.py --rebase) once the change is witnessed."))
        out["adversarial_card"] = r.get("id")
        # archive + clear the drained triggers
        with ARCHIVE.open("a", encoding="utf-8") as f:
            f.write("\n".join(triggers) + "\n")
        PENDING.write_text("", encoding="utf-8")

    # Lane 4 — one-time deep baseline card (sentinel so it's offered exactly once)
    if not BASELINE_SENTINEL.exists():
        r = led.open(
            title="🔬 Run the one-time DEEP crypto baseline audit (sets the trust floor)",
            owner="owner", classification="C1", material=True, category="judgment",
            next_gate="Human disposition (Atrium Review)", ref="deep_crypto_baseline:run",
            intent=("Schedule the one-time deep crypto baseline audit (multi-agent: full Wycheproof/NIST "
                    "conformance + forgery/invalid-curve/malleability battery + nonce/constant-time + adapter "
                    "fidelity). G: 'baseline once, then never wonder.' Accept = run it (you opted into "
                    "multi-agent); the report is SEALED and surfaced for seeit. Prompt: scripts/cron/"
                    "deep_crypto_baseline_audit_prompt.txt."))
        out["deep_baseline_card"] = r.get("id")
        BASELINE_SENTINEL.write_text("carded\n", encoding="utf-8")

    return out


def main(argv) -> int:
    out = surface()
    print(f"crypto_cadence_surface: triggers={out['triggers']} "
          f"adversarial_card={out['adversarial_card']} deep_baseline_card={out['deep_baseline_card']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
