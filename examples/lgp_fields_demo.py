"""P0-2 — LGP fields first-class: families-first travels role → result → obligation → replay.

Proves every layer of the sovereign identity now KNOWS + carries its LGP contribution (the judgment rule):
  1. role_spec.yaml has a first-class `lgp:` block.
  2. Every FEC handler RESULT carries `lgp`.
  3. An obligation opened WITH `lgp` carries it through the hash-chained replay (the chain remembers it).

Run:  PYTHONPATH=src python3 examples/lgp_fields_demo.py
"""
import importlib.util
import shutil
from pathlib import Path

import yaml

from sovereign_agent.obligations.ledger import ObligationLedger

ROOT = Path(__file__).resolve().parents[1]
ROLE_DIR = ROOT / "src" / "sovereign_agent" / "demo_roles" / "federation_procurement_coordinator"


def main():
    # 1) role_spec carries a first-class lgp block
    spec = yaml.safe_load(open(ROLE_DIR / "role_spec.yaml"))
    print("1) role_spec.lgp:", spec["lgp"]["alignment_score"], "·", spec["lgp"]["families_first_impact"][:48], "…")
    assert spec["lgp"]["alignment_score"] and spec["lgp"]["families_first_impact"]

    # 2) every handler result carries lgp
    s = importlib.util.spec_from_file_location("fec", ROLE_DIR / "role.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    r = m.FederationProcurementCoordinatorAgent().process({"action_class": "run_optimization_coordination"})
    print("2) handler result lgp:", r["lgp"]["alignment_score"], "·", r["lgp"]["families_first_impact"][:40], "…")
    assert r["lgp"]["families_first_impact"]

    # 3) an obligation opened WITH lgp carries it through the chained replay
    led_root = ROOT / "memory" / "obligations" / "lgp_demo"
    if led_root.exists():
        shutil.rmtree(led_root)
    led = ObligationLedger(root=str(led_root), principal_id="KM-1176")
    led.open(title="FEC pooled-order proposal (material)", classification="C1", material=True,
             lgp=dict(m.LGP), next_gate="Atrium disposition (RED)")
    replayed = led.replay()["open"][0]
    print("3) obligation.lgp via replay:", replayed["lgp"]["alignment_score"], "· next_gate:", replayed["next_gate"])
    assert replayed.get("lgp") and replayed.get("next_gate")
    print("   chain valid:", led.verify_chain())

    print("\n∞Δ∞ P0-2: LGP first-class — role → result → obligation → replay all carry families-first. ∞Δ∞")


if __name__ == "__main__":
    main()
