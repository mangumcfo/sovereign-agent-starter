"""R22-2 Queryable actions projection — success-metric regression test.
Pins: every returned row resolves to its Merkle leaf+proof; read-only; filters; tamper-evident."""
import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import actions_projection as AP
from sovereign_agent.obligations.ledger import ObligationLedger

def _fixture(tmp):
    led = ObligationLedger(root=str(tmp), principal_id="owner")
    for i in range(4):
        o = led.open(title=f"a{i}", owner="owner", material=False, next_gate="batch:mechanical")
        led.approve(o["id"], approved_by="owner")
        led.close(o["id"], evidence=f"path {i}", evidence_tier="E1")
    return led

def test_every_row_anchors_and_filters_and_read_only():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d); _fixture(root)
        res = AP.query_actions(root)
        assert res["count"] >= 12 and res["read_only"]
        # success metric: every row's proof resolves
        assert all(AP.verify_proof(r["leaf"], r["merkle_proof"], r["root"]) for r in res["actions"])
        # filters
        assert AP.query_actions(root, type="close")["count"] == 4
        # re-runnable: same root
        assert AP.query_actions(root)["root"] == res["root"]
        # tamper a leaf → its proof must fail
        r0 = res["actions"][0]
        assert not AP.verify_proof("00"*32, r0["merkle_proof"], r0["root"])
