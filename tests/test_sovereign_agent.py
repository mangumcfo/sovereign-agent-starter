"""
Minimal sovereign test for SovereignAgent core (action + attestation).

Exercises the real VerifiableMemory + ConstitutionalGovernor + breathline_primitives
self-attestation path. No external dependencies beyond the package itself.
"""

from sovereign_agent import SovereignAgent


def test_basic_action_and_attestation():
    agent = SovereignAgent("TestAgent-LGP")

    # LGP-flavored task that should score well on the Governor
    task = "Develop antifragile multi-generational family capital allocation strategy"
    result = agent.act(task, context={"consistent_with_past": True, "horizon_years": 50})

    # Real fields returned by the current act() implementation
    assert result.get("status") == "executed"
    assert "memory_root" in result
    assert "signature" in result
    assert "constitutional_score" in result
    assert result["constitutional_score"] >= 0.65  # LGP threshold

    # The result also carries its own self_attestation leaf
    assert "self_attestation" in result

    # Memory root is stable and non-empty after the action
    final_root = agent.get_memory_root()
    assert final_root is not None and len(final_root) > 10

    print("Basic sovereign attestation test passed.")
    print(f"  agent: {agent.name}")
    print(f"  score: {result['constitutional_score']}")
    print(f"  memory_root: {final_root[:32]}...")


if __name__ == "__main__":
    test_basic_action_and_attestation()
