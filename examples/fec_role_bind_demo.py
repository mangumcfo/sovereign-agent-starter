"""FEC role bind demo (FEC-T3).

Loads + binds the federation_procurement_coordinator role (role_spec.yaml + role.py) via the
starter's demo binder, then runs a GREEN action (executes) and a RED action (returns a
human-gated proposal — never auto-executes). Proves the packet → role → bound-handler arc.

Run:  PYTHONPATH=src python3 examples/fec_role_bind_demo.py
"""
from pathlib import Path
import json
import yaml

from sovereign_agent.playbook_loader import _bind_demo_role

ROLE_DIR = Path(__file__).resolve().parents[1] / "src/sovereign_agent/demo_roles/federation_procurement_coordinator"


def main():
    spec = yaml.safe_load(open(ROLE_DIR / "role_spec.yaml"))
    bound = _bind_demo_role(ROLE_DIR, spec, None)
    print(f"role: {spec['role']['id']}")
    print(f"handler_bound: {bound.handler is not None}")
    print(f"allowed_action_classes: {len(spec['allowed_action_classes'])}")
    assert bound.handler is not None, "FEC handler did not bind"

    print("\n--- GREEN action (executes) ---")
    green = bound.handler.process({"action_class": "generate_zk_statistical_profile", "participants": 12})
    print(json.dumps({k: green[k] for k in ("action_class", "breath_gate", "status")}, indent=2))
    print("  zk raw_data_leaked:", green["zk_profile"]["raw_data_leaked"])

    print("\n--- RED action (proposal only — human gate) ---")
    red = bound.handler.process({"action_class": "propose_pooled_order"})
    print(json.dumps({k: red[k] for k in ("action_class", "breath_gate", "status", "requires_human_disposition")}, indent=2))
    print("  committed (must be False):", red["proposal"]["committed"])
    assert red["requires_human_disposition"] and red["proposal"]["committed"] is False

    print("\n∞Δ∞ FEC role bound; agents propose, the human disposes, families first, all receipted. ∞Δ∞")


if __name__ == "__main__":
    main()
