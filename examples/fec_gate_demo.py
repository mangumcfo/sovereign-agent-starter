"""BG-1: wire the real HumanApprovalGate + ComplianceEngine attestor into the obligation ledger.

Proves the gate is AUTHORITATIVE: a MATERIAL obligation (e.g. the FEC propose_pooled_order RED
action) cannot close until it clears the breath-gate, and every close mints a node receipt via
the ComplianceEngine. Honest: gate disposition is simulated here (simulate_gate=True); a LIVE node
supplies the real human disposition + the USN Merkle anchor. The ledger root stays node-local
(boundary guard applies — never the live seal chain).

Run:  PYTHONPATH=src python3 examples/fec_gate_demo.py
"""
from pathlib import Path
import shutil

from sovereign_agent.obligations.node_integration import wire_node_ledger

ROOT = Path(__file__).resolve().parents[1] / "memory" / "obligations" / "bg_demo"


def main():
    if ROOT.exists():
        shutil.rmtree(ROOT)  # clean demo run
    led = wire_node_ledger(str(ROOT), node=None, simulate_gate=True, principal_id="KM-1176")
    print("wired ledger:", led.path)

    ob = led.open(title="FEC · propose_pooled_order (material)", owner="KM-1176",
                  classification="C1", intent="Draft pooled order — MATERIAL, must clear the gate.",
                  ref="fec:propose_pooled_order", material=True)
    print("opened material obligation:", ob["id"])

    # 1) closing BEFORE approval must be refused — the gate is authoritative on material.
    try:
        led.close(ob["id"], evidence="E1: /tmp/draft_order.pdf (premature)")
        print("  !! ERROR: material closed without the gate")
    except PermissionError as e:
        print("  ✓ gate blocked premature close:", str(e)[:64], "…")

    # 2) approve through the real HumanApprovalGate (simulated disposition here).
    appr = led.approve(ob["id"], approved_by="KM-1176 (Atrium NLP)", rationale="Reviewed in Atrium.")
    print("  ✓ gate disposition:", appr.get("disposition"))

    # 3) close now succeeds and mints a node receipt via the ComplianceEngine attestor.
    cr = led.close(ob["id"], evidence="E2: /tmp/pooled_order_v1.pdf sha256:abc123def456 + node receipt")
    rec = cr.get("receipt", {})
    print("  ✓ closed; evidence_tier:", rec.get("evidence_tier"),
          "| node_receipt present:", "node_receipt" in rec,
          "| receipt_hash:", rec.get("node_receipt_hash"))
    print("  chain valid:", led.verify_chain(), "·", led.by_status())

    # ── BG-2: the DENY path — a human DENY blocks the close; the obligation stays open ──
    print("\nBG-2 — deny path:")
    denyroot = ROOT.parent / "bg_deny_demo"
    if denyroot.exists():
        shutil.rmtree(denyroot)
    dled = wire_node_ledger(str(denyroot), node=None, simulate_gate=True, simulate_deny=True,
                            principal_id="KM-1176")
    dob = dled.open(title="FEC · propose_pooled_order (denied)", owner="KM-1176",
                    classification="C1", intent="Material — human will DENY.",
                    ref="fec:propose_pooled_order", material=True)
    try:
        dled.approve(dob["id"], approved_by="KM-1176 (Atrium NLP)", rationale="On review, no.")
        print("  !! ERROR: deny did not raise")
    except PermissionError as e:
        print("  ✓ human DENY recorded + raised:", str(e)[:50], "…")
    # after a deny, the material obligation must still be un-closeable
    try:
        dled.close(dob["id"], evidence="E1: /tmp/x.pdf")
        print("  !! ERROR: denied obligation closed")
    except PermissionError:
        print("  ✓ denied obligation stays OPEN — close still blocked")
    st = dled.by_status()
    print("  deny ledger:", st, "(open stays 1, closed 0)")

    print("\n∞Δ∞ BG-1/2: real gate wired — approve permits, DENY blocks; every close is receipted. ∞Δ∞")


if __name__ == "__main__":
    main()
