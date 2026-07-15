#!/usr/bin/env python3
"""
crypto_assurance.py — the daily assurance roll-up (crypto cadence, the peer design + G framing, the operator 2026-06-12).
Combines the two deterministic "daily mathematics" lanes into one simple status the Atrium renders:
  · Lane 1 vector + reference-lib cross-verify (crypto_vector_check)
  · Lane 2 seal-manifest tripwire (seal_manifest_tripwire receipt)
→ a single GREEN/RED status with last-run + Merkle root. "One human gate only": GREEN is just status (a
chip + receipt, no queue noise); RED mints a gating obligation card so the operator disposes the only thing that matters.

  python3 scripts/crypto_assurance.py            # run vectors, read tripwire, write status, gate on red
  python3 scripts/crypto_assurance.py --no-card  # status only (harness-embedded use; tripwire mints its own card)

Status: artifacts/crypto/assurance_status.json (served by GET /crypto_assurance; rendered as the daily card).
∞Δ∞ Daily mathematics, not daily agents. Green is a chip; red is a gate. ∞Δ∞
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATUS = REPO / "artifacts" / "crypto" / "assurance_status.json"
TRIPWIRE_RECEIPT = REPO / "artifacts" / "crypto" / "seal_tripwire_latest.json"


def assess(stamp: str | None = None, mint_card: bool = True) -> dict:
    sys.path.insert(0, str(REPO / "scripts"))
    import crypto_vector_check as V  # noqa: PLC0415
    vec = V.run()
    tw = {}
    if TRIPWIRE_RECEIPT.exists():
        try:
            tw = json.loads(TRIPWIRE_RECEIPT.read_text())
        except Exception:  # noqa: BLE001
            tw = {"status": "unreadable"}
    tw_status = tw.get("status", "not-run")
    vec_pass = bool(vec.get("pass"))
    tw_ok = tw_status in ("clean", "baseline")
    status = "GREEN" if (vec_pass and tw_ok) else "RED"
    reasons = []
    if not vec_pass:
        reasons += [c["name"] for c in vec.get("checks", []) if not c["pass"]]
    if not tw_ok:
        reasons.append(f"seal_tripwire={tw_status}")
    out = {
        "status": status,
        "last_run": stamp or "",        # caller stamps (Date.now() unavailable in some contexts)
        "merkle_root": vec.get("merkle_root"),
        "vectors": {"pass": vec_pass, "n_pass": vec.get("n_pass"), "n_total": vec.get("n_total")},
        "seal_tripwire": {"status": tw_status, "manifest_hash": tw.get("manifest_hash")},
        "reasons": reasons,
        "claim": ("verified against international test vectors + reference-lib cross-check, and "
                  "integrity-checked against its seal — receipts available"),
    }
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(out, indent=2), encoding="utf-8")

    if status == "RED" and mint_card and not vec_pass:
        # Vector failure → gating card (tripwire mints its own CRITICAL card on drift, so don't double up).
        try:
            sys.path.insert(0, str(REPO / "src"))
            from sovereign_agent.obligations.ledger import ObligationLedger, get_ledger_root
            led = ObligationLedger(root=str(get_ledger_root()))
            led.open(title="🔴 CRITICAL — crypto vector assurance RED (primitives fail test vectors)",
                     owner="the owner", classification="C1", material=True, category="judgment",
                     next_gate="Human disposition (Atrium Review)", ref="crypto_assurance:vectors_red",
                     intent=(f"Sealed primitives FAILED deterministic vector/cross-verify: {reasons}. This is a "
                             f"substrate-correctness failure — the books' verifiability claim is at risk. "
                             f"Receipt: artifacts/crypto/vector_check_latest.json. Escalate per crypto cadence."))
        except Exception:  # noqa: BLE001
            pass
    return out


def main(argv) -> int:
    out = assess(mint_card="--no-card" not in argv)
    print(f"crypto_assurance: {out['status']} · vectors {out['vectors']['n_pass']}/{out['vectors']['n_total']} · "
          f"tripwire {out['seal_tripwire']['status']} · merkle {(out['merkle_root'] or '')[:16]}…")
    if out["status"] == "RED":
        print(f"  ✗ reasons: {out['reasons']}")
    return 0 if out["status"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
