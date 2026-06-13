#!/usr/bin/env python3
"""
seal_manifest_tripwire.py — Lane 2 of the crypto cadence (GB design ratified KM 2026-06-12).
"Tripwire what's sealed" (G): the breathline-sealed primitives are frozen. This does NOT patrol them — it
fingerprints every sealed file and compares to a recorded baseline. ANY change to a sealed file (the only
moment frozen crypto gets riskier) → an auto-CRITICAL obligation card in Atrium for KM, plus a receipt.

  python3 scripts/seal_manifest_tripwire.py            # check vs baseline (mint CRITICAL card on drift)
  python3 scripts/seal_manifest_tripwire.py --rebase   # (re)establish the baseline AFTER a witnessed change

Deterministic, ~zero tokens — runs nightly. Receipt: artifacts/crypto/seal_tripwire_latest.json.
∞Δ∞ Patrol what moves; tripwire what's sealed. A change to frozen crypto is a constitutional event. ∞Δ∞
"""
from __future__ import annotations
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SEALED = Path(os.environ.get("BL_SEALED_ROOT", str(Path.home() / "work-repos" / "breathline-sealed")))
BASELINE = REPO / "artifacts" / "crypto" / "seal_baseline.json"
RECEIPT = REPO / "artifacts" / "crypto" / "seal_tripwire_latest.json"
# the frozen surface: every sealed primitive source + the seal anchors + the adapter
SCAN_GLOBS = ["primitives/sealed/layer_*/**/*.py", "primitives/sealed/SEAL*.txt", "bl-verify"]


def _fingerprint() -> dict:
    files = {}
    for g in SCAN_GLOBS:
        for p in sorted(SEALED.glob(g)):
            if p.is_file() and "__pycache__" not in str(p):
                rel = str(p.relative_to(SEALED))
                files[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    manifest_hash = hashlib.sha256(
        "\n".join(f"{k}:{v}" for k, v in sorted(files.items())).encode()).hexdigest()
    return {"files": files, "manifest_hash": manifest_hash, "n_files": len(files)}


def _diff(base: dict, now: dict) -> dict:
    bf, nf = base.get("files", {}), now.get("files", {})
    added = sorted(set(nf) - set(bf))
    removed = sorted(set(bf) - set(nf))
    changed = sorted(k for k in (set(bf) & set(nf)) if bf[k] != nf[k])
    return {"added": added, "removed": removed, "changed": changed,
            "drift": bool(added or removed or changed)}


def _mint_critical_card(d: dict, now: dict) -> str | None:
    try:
        sys.path.insert(0, str(REPO / "src"))
        from sovereign_agent.obligations.ledger import ObligationLedger
        led = ObligationLedger(root=str(REPO / "memory" / "obligations" / "atrium_review"))
        detail = (f"CRITICAL — sealed-primitives integrity drift detected. The breathline-sealed crypto "
                  f"substrate is frozen; a change here is a constitutional event. changed={d['changed']} "
                  f"added={d['added']} removed={d['removed']}. new manifest_hash={now['manifest_hash'][:16]}…. "
                  f"Disposition: confirm the change was witnessed + authorized, then rebase the baseline "
                  f"(scripts/seal_manifest_tripwire.py --rebase); if UNEXPECTED, this is a substrate "
                  f"compromise — escalate to constitutional ceremony. Receipt: artifacts/crypto/seal_tripwire_latest.json")
        r = led.open(title="🔴 CRITICAL — breathline-sealed integrity drift (crypto tripwire)",
                     owner="KM-1176", classification="C1", material=True, category="judgment",
                     next_gate="Human disposition (Atrium Review)", ref="crypto_tripwire:breathline_sealed",
                     intent=detail)
        return r.get("id")
    except Exception as e:  # noqa: BLE001
        return f"card-mint-failed: {e}"


def main(argv) -> int:
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    now = _fingerprint()
    if "--rebase" in argv or not BASELINE.exists():
        BASELINE.write_text(json.dumps(now, indent=2), encoding="utf-8")
        action = "baseline-established" if "--rebase" not in argv else "baseline-rebased"
        RECEIPT.write_text(json.dumps({"status": "baseline", "action": action,
                                       "manifest_hash": now["manifest_hash"], "n_files": now["n_files"]}, indent=2))
        print(f"seal_tripwire: {action} · {now['n_files']} files · manifest={now['manifest_hash'][:16]}…")
        return 0
    base = json.loads(BASELINE.read_text())
    d = _diff(base, now)
    card = _mint_critical_card(d, now) if d["drift"] else None
    receipt = {"status": "DRIFT" if d["drift"] else "clean", "diff": d,
               "manifest_hash": now["manifest_hash"], "baseline_hash": base.get("manifest_hash"),
               "n_files": now["n_files"], "critical_card": card}
    RECEIPT.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    if d["drift"]:
        print(f"🔴 seal_tripwire: DRIFT — changed={d['changed']} added={d['added']} removed={d['removed']}")
        print(f"   CRITICAL card minted: {card}")
        return 1
    print(f"seal_tripwire: clean · {now['n_files']} files · manifest={now['manifest_hash'][:16]}… (matches baseline)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
