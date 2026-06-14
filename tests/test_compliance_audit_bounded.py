"""Bounded + persisted compliance audit trail — Universalize Wave §6 (D5).

The chain-of-custody record was an unbounded in-process list (grew for the life of the process). It is now
a bounded RAM working-set (deque maxlen) whose evicted records are persisted append-only — bounded yet not
forgotten. get_audit_trail / export_evidence_bundle keep working over the window."""
from sovereign_agent.compliance.compliance_engine import ComplianceEngine


def _attest(engine, i):
    return engine.attest_execution(
        role_id="r", action_class="read", principal_id="KM-1176",
        payload={"i": i}, result_summary=f"event {i}")


def test_audit_trail_is_bounded_and_overflow_persisted(tmp_path, monkeypatch):
    monkeypatch.setenv("BREATHLINE_AUDIT_TRAIL_MAX", "3")
    overflow = tmp_path / "audit_overflow.ndjson"
    monkeypatch.setenv("BREATHLINE_AUDIT_OVERFLOW", str(overflow))

    eng = ComplianceEngine(mode="sovereign")   # no node — pure in-process floor
    for i in range(5):
        _attest(eng, i)

    # RAM window is capped at the configured max
    assert len(eng._audit_trail) == 3
    # the two evicted records were persisted append-only (bounded, not forgotten)
    assert overflow.exists()
    assert overflow.read_text(encoding="utf-8").count("\n") == 2
    # consumers still work over the window
    assert len(eng.get_audit_trail(50)) == 3
    bundle = eng.export_evidence_bundle()
    assert bundle["record_count"] == 3 and len(bundle["audit_trail"]) == 3


def test_audit_trail_without_overflow_path_still_bounded(tmp_path, monkeypatch):
    """No overflow path configured → still bounded (the node's append-only memory is the signed record)."""
    monkeypatch.setenv("BREATHLINE_AUDIT_TRAIL_MAX", "2")
    monkeypatch.delenv("BREATHLINE_AUDIT_OVERFLOW", raising=False)
    eng = ComplianceEngine(mode="sovereign")
    for i in range(6):
        _attest(eng, i)
    assert len(eng._audit_trail) == 2          # bounded — never grows unbounded
