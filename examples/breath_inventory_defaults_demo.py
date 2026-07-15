"""P0-4 — Breath Inventory Tier-1 defaults embedded into roles.

Proves every action_class auto-inherits the right 'always approve on' Tier-1 primitives:
  - B32 on every action (receipt everything),
  - B51 handoff trace on material actions,
  - crypto (B43/B39/B25) on zk/proof actions, B26 yield on value/distribution, B28 legal on commitments, etc.

Run:  PYTHONPATH=src python3 examples/breath_inventory_defaults_demo.py
"""
from pathlib import Path

import yaml

from sovereign_agent.breath_inventory import enrich_role, TIER1

ROLE = Path(__file__).resolve().parents[1] / "src" / "sovereign_agent" / "demo_roles" / "federation_procurement_coordinator" / "role_spec.yaml"


def main():
    print("Tier-1 'always approve on' cluster:", ", ".join(TIER1))
    spec = yaml.safe_load(open(ROLE))
    enriched = enrich_role(spec)
    print("\nrole:", enriched["role"]["id"], "· breath_inventory.tier1_applied:", enriched["breath_inventory"]["tier1_applied"])
    print("\nPer-action Tier-1 defaults (auto-suggested):")
    for a in enriched["action_classes"]:
        print(f"  {a.get('breath_gate',''):20} {a['id']}")
        print(f"       -> {', '.join(a['tier1_defaults'])}")

    by = {a["id"]: a["tier1_defaults"] for a in enriched["action_classes"]}
    assert all("B32" in v for v in by.values()), "B32 must be on every action (receipt everything)"
    assert "B51" in by["propose_pooled_order"], "material action gets a B51 handoff trace"
    assert "B43" in by["generate_zk_statistical_profile"], "zk action gets the crypto stack"
    assert "B26" in by["execute_value_distribution"], "value/distribution gets B26 yield"
    assert "B28" in by["propose_pooled_order"], "a pooled order (commitment) gets B28 legal hardening"

    print("\n∞Δ∞ P0-4: Tier-1 defaults embedded — new roles inherit the battle-tested primitives. ∞Δ∞")


if __name__ == "__main__":
    main()
