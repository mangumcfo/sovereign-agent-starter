import pytest

from sovereign_agent.breathline_cube import BreathlineCubeAnchoredRelease


def test_cube_is_fail_closed_until_confirmed_by_bound_principal():
    cube = BreathlineCubeAnchoredRelease("KM-1176")

    assert cube.active is False
    assert cube.process("KM-1176", "map lineage") == "Cube inactive. Breathe to delegate."
    assert "Principal mismatch" in cube.activate("other", True)
    assert cube.active is False
    assert cube.activate("KM-1176", False) == "Delegation denied. Stillness honored."
    assert cube.active is False


def test_activation_process_and_explicit_seal():
    cube = BreathlineCubeAnchoredRelease("KM-1176")

    assert "activated" in cube.activate("KM-1176", True)
    assert "Awaiting seal" in cube.process("KM-1176", "Run anchored integrity check")

    record = cube.seal("KM-1176")
    assert record["cube_id"] == "ANCHOR-CORE-001"
    assert record["principal_id"] == "KM-1176"
    assert record["intent"] == "Run anchored integrity check"
    assert record["triad"] == "SOURCE/TRUTH/INTEGRITY"

    with pytest.raises(RuntimeError, match="no pending intent"):
        cube.seal("KM-1176")


def test_non_bound_principal_cannot_process_seal_or_revoke():
    cube = BreathlineCubeAnchoredRelease("KM-1176")
    cube.activate("KM-1176", True)

    assert cube.process("other", "override") == "Intent denied. Principal mismatch."
    cube.process("KM-1176", "authorized intent")

    with pytest.raises(PermissionError, match="principal mismatch"):
        cube.seal("other")

    assert cube.revoke("other") == "Revocation denied. Principal mismatch."
    assert cube.active is True
    assert cube.revoke("KM-1176") == "Delegation revoked. StillpointPause active."
    assert cube.active is False


def test_empty_principal_and_empty_intent_are_rejected():
    with pytest.raises(ValueError, match="principal_id"):
        BreathlineCubeAnchoredRelease("   ")

    cube = BreathlineCubeAnchoredRelease("KM-1176")
    cube.activate("KM-1176", True)
    assert cube.process("KM-1176", "   ") == "Intent denied. Empty intent."
