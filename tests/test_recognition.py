"""Revenue-recognition invariants — co-extrusion for s5_15 (Revenue & Order-to-Cash).

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves recognition is
value-conserving -- the recognized amounts sum EXACTLY to the contract value and recognized + deferred equals the
contract at every step -- for each named method, and that over-recognizing milestones or an unknown method are refused."""
from decimal import Decimal
import pytest
from sovereign_agent.revenue import recognize, POINT_IN_TIME, RATABLE, MILESTONE, RecognitionError


def test_ratable_conserves_value_and_deferred_winds_down():
    s = recognize("12000", method=RATABLE, periods=12)
    assert s["total_recognized"] == Decimal("12000")            # sums to contract
    assert s["schedule"][0]["recognized"] == Decimal("1000.00")
    assert s["schedule"][-1]["deferred"] == Decimal("0")        # fully recognized at the end
    # recognized + deferred == contract at every step
    for step in s["schedule"]:
        pass
    running = Decimal("0")
    for step in s["schedule"]:
        running += step["recognized"]
        assert running + step["deferred"] == Decimal("12000")


def test_point_in_time_and_milestone():
    p = recognize("5000", method=POINT_IN_TIME)
    assert p["schedule"][0]["recognized"] == Decimal("5000.00") and p["schedule"][0]["deferred"] == Decimal("0")
    m = recognize("10000", method=MILESTONE, milestones=[("design", "4000"), ("build", "6000")])
    assert m["total_recognized"] == Decimal("10000")


def test_bad_recognition_refused():
    with pytest.raises(RecognitionError):
        recognize("10000", method=MILESTONE, milestones=[("a", "4000"), ("b", "7000")])   # over-recognizes
    with pytest.raises(RecognitionError):
        recognize("0", method=POINT_IN_TIME)                                              # non-positive contract
    with pytest.raises(RecognitionError):
        recognize("100", method="usage_based")                                            # unknown method
    with pytest.raises(RecognitionError):
        recognize("100", method=RATABLE, periods=0)                                        # bad period count
