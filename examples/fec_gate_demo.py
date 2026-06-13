"""BG-1: wire the real HumanApprovalGate + ComplianceEngine attestor into the obligation ledger.

Proves the gate is AUTHORITATIVE: a MATERIAL obligation (e.g. the FEC propose_pooled_order RED
action) cannot close until it clears the breath-gate. NO mode auto-approves (audit
real_gates_every_mode): in gate_mode='sovereign' the authenticated approve() call IS the human
disposition; in gate_mode='external' approve() returns 'pending' and the obligation stays un-closeable
until a real out-of-band disposition lands. The ledger root stays node-local (boundary guard applies —
never the live seal chain).

Run:  PYTHONPATH=src python3 examples/fec_gate_demo.py
"""
from pathlib import Path
import shutil

from sovereign_agent.obligations.node_integration import wire_node_ledger

ROOT = Path(__file__).resolve().parents[1] / "memory" / "obligations" / "bg_demo"


def main():
    # ── BG-1: the APPROVE path (gate_mode='sovereign' — the authenticated approve() is the disposition) ──
    if ROOT.exists():
        shutil.rmtree(ROOT)  # clean demo run
    led = wire_node_ledger(str(ROOT), node=None, gate_mode="sovereign", principal_id="KM-1176")
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

    # 2) approve through the real HumanApprovalGate — the authenticated principal IS the disposition.
    appr = led.approve(ob["id"], approved_by="KM-1176 (Atrium NLP)", rationale="Reviewed in Atrium.")
    print("  ✓ gate disposition:", appr.get("disposition"))

    # 3) close now succeeds.
    cr = led.close(ob["id"], evidence="E2: /tmp/pooled_order_v1.pdf sha256:abc123def456 + node receipt")
    rec = cr.get("receipt", {})
    print("  ✓ closed; evidence_tier:", rec.get("evidence_tier"))
    print("  chain valid:", led.verify_chain(), "·", led.by_status())

    # ── BG-2: the WITHHOLD/DENY path — no disposition ⇒ no close; an explicit refusal is recorded ──
    print("\nBG-2 — withhold/deny path (gate_mode='external'):")
    denyroot = ROOT.parent / "bg_deny_demo"
    if denyroot.exists():
        shutil.rmtree(denyroot)
    dled = wire_node_ledger(str(denyroot), node=None, gate_mode="external", principal_id="KM-1176")
    dob = dled.open(title="FEC · propose_pooled_order (withheld)", owner="KM-1176",
                    classification="C1", intent="Material — disposition withheld (pending).",
                    ref="fec:propose_pooled_order", material=True)
    # external mode never auto-approves: approve() does NOT grant — it raises (disposition is withheld,
    # the real one arrives out-of-band), so the obligation stays open.
    try:
        dled.approve(dob["id"], approved_by="KM-1176")
        print("  !! ERROR: external mode auto-approved")
    except PermissionError as e:
        print("  ✓ external approve withheld (not granted):", str(e)[:48], "…")
    # while un-approved, the material obligation is NOT closeable.
    try:
        dled.close(dob["id"], evidence="E1: /tmp/x.pdf")
        print("  !! ERROR: withheld obligation closed")
    except PermissionError:
        print("  ✓ withheld obligation stays OPEN — close still blocked")
    # an explicit human REFUSAL is itself a valid disposition: close(rejected=True) records the denial.
    dled.close(dob["id"], evidence="human refused in review", evidence_tier="E1",
               require_e1=False, rejected=True)
    print("  ✓ explicit DENY recorded as a rejection close ·", dled.by_status())

    print("\n∞Δ∞ BG-1/2: real gate — approve permits; pending/withheld blocks; refusal is a recorded disposition. ∞Δ∞")


if __name__ == "__main__":
    main()
