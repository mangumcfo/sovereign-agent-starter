"""S5-05-E7-1 · E7-3: cutover honesty — stamps, permanent unsourced, reconciliation."""
import pytest
from sovereign_agent.objects.migrate import (ReconciliationError, SealRefused,
                                             promote_to_sealed, reconcile, stamp_cutover)

POP = [{"object_id": f"part:P-{i}", "payload": {}} for i in range(6)]
ATT = {f"part:P-{i}": f"BIN-{i}:count sheet" for i in range(4)}  # 4 sourced, 2 not


def test_unsourced_object_cannot_be_marked_sealed():
    stamped = stamp_cutover(POP, ATT)
    assert all(o["origin"] == "asserted" for o in stamped)
    sealed = promote_to_sealed(stamped[0])
    assert sealed["sealed"] is True
    unsourced = [o for o in stamped if o.get("unsourced")]
    assert len(unsourced) == 2
    with pytest.raises(SealRefused):
        promote_to_sealed(unsourced[0])  # no paper, no seal — permanently


def test_sourced_plus_unsourced_equals_population():
    stamped = stamp_cutover(POP, ATT)
    r = reconcile(stamped)
    assert (r["sourced"], r["unsourced"], r["population"]) == (4, 2, 6)
    assert r["reconciles"]
    broken = stamped[:-1] + [dict(stamped[-1], unsourced=False, sourced=False)]
    with pytest.raises(ReconciliationError):
        reconcile(broken)
