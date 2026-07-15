#!/usr/bin/env python3
"""
Universal Sovereign Node — Executable Role Binding Demo

This demo shows the full power of dynamic binding:
- Load a real role spec from breathline-federation (YAML)
- Automatically bind to the Python handler if present (role.py + frameworks)
- Execute a task through the bound handler
- Full sovereign attestation on top

This turns static specs into living, callable intelligence.
"""

from sovereign_agent import UniversalSovereignNode

def main():
    print("=" * 75)
    print("UNIVERSAL SOVEREIGN NODE — EXECUTABLE ROLE BINDING DEMO")
    print("=" * 75)
    print()

    node = UniversalSovereignNode("BindingDemo", context_type="corporate")

    print(">>> Loading cfo_agent role with dynamic Python binding (zero-friction)")
    bound_role = node.load_role("cfo_agent")

    print(f"Role loaded: {bound_role.role_id}")
    print(f"Handler bound: {bound_role.handler is not None}")
    print(f"Allowed action classes (from real role_spec.yaml): {bound_role.get_allowed_action_classes()}")
    print(f"Framework: {bound_role.framework}")
    print()

    # Zero-friction execution: supply only business data.
    # The binder automatically resolves a valid action_class from the spec's
    # allowed_action_classes and validates it before the handler ever sees the request.
    payload = {
        "financial_data": {"revenue": [1200, 1350, 1100], "expenses": [800, 820, 790]},
        "forecast_horizon": 3
    }

    print(">>> Executing task (no manual action_class — it just works)")
    result = bound_role.process(
        payload=payload,
        principal_id="owner",
        request_id="demo-forecast-001"
    )

    print("\nBound Role Result (real FORECAST artifact + sovereign attestation):")
    print(result)

    # Demonstrate that other roles are equally zero-friction
    print("\n>>> Loading a second role (family_cfo_agent) to prove the pattern generalizes")
    try:
        family_role = node.load_role("family_cfo_agent")
        print(f"    family_cfo_agent handler bound: {family_role.handler is not None}")
        print(f"    allowed actions: {family_role.get_allowed_action_classes() or '(inherits or uses defaults)'}")
    except Exception as e:
        print(f"    (family_cfo_agent not yet executable in this environment: {e})")

    print("\n" + "=" * 75)
    print("Zero-friction binding complete. Any properly-specified federation role")
    print("can now be loaded and executed with minimal developer code while")
    print("preserving full constitutional attestation and permission envelopes.")
    print("=" * 75)


if __name__ == "__main__":
    main()
