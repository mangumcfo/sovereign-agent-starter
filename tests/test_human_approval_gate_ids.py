"""AH-6 closure — HumanApprovalGate must never mint a colliding req_id.

Before: req_id = f"approval_{len(self._pending)+1}" derived the id from the CURRENT queue length, so after
any disposition popped the queue, the next request reused a still-live id and silently overwrote a pending
request. A monotonic counter fixes it. Pure stdlib (no sealed crypto substrate required).
"""
from sovereign_agent.compliance.human_approval_gate import HumanApprovalGate, ApprovalRequest


def _req(label: str = "x") -> ApprovalRequest:
    return ApprovalRequest(action_class=f"cls_{label}", role_id="role", principal_id="p",
                           risk_level="high", rationale="r", required_approvers=["Compliance Officer"])


def test_request_approval_never_reuses_a_pending_id_across_disposition():
    g = HumanApprovalGate()
    a = g.request_approval(_req("a"))
    b = g.request_approval(_req("b"))
    assert a != b

    # dispose A → it leaves the pending queue (len drops); the OLD len-based id would now recollide with B
    g.record_disposition(a, status="approved", approver="node")
    c = g.request_approval(_req("c"))

    assert c != b, "req_id reused a live id — C would clobber still-pending B"
    pending = g.get_pending()
    assert b in pending and c in pending, "a pending request was silently overwritten"
    # B is intact and still itself (its action_class not replaced by C's)
    assert pending[b].action_class == "cls_b"
    assert pending[c].action_class == "cls_c"


def test_ids_are_monotonic_and_unique_over_many_disposals():
    g = HumanApprovalGate()
    seen = set()
    for i in range(50):
        rid = g.request_approval(_req(str(i)))
        assert rid not in seen, f"duplicate req_id minted: {rid}"
        seen.add(rid)
        if i % 2 == 0:
            g.record_disposition(rid)   # churn the queue so a len-based id would repeat
    assert len(seen) == 50
