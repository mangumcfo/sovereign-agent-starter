"""S5-05-E6-1 · E6-4: one mandate per object; grants are exactly their scope."""
import pytest
from sovereign_agent.objects.registry import MandateViolation, ObjectRegistry
from sovereign_agent.objects.scope import ScopeRefusal, SharingRule, check_access, mandate_root


def _reg(tmp_path):
    reg = ObjectRegistry(str(tmp_path))
    reg.append("vendor:V-9", {"terms": 30}, author="d.reyes",
               source_ref="W9-9:file", at="2029-01-01", mandate="operating")
    reg.append("policy:INS-1", {"carrier": "acme"}, author="h.bhatt",
               source_ref="POL-1:binder", at="2029-01-01", mandate="trust")
    return reg


def test_object_belongs_to_one_mandate_and_roots_are_separate(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(MandateViolation):  # a second mandate refuses
        reg.append("vendor:V-9", {"terms": 45}, author="h.bhatt",
                   source_ref="W9-9:file", at="2029-02-01", mandate="trust")
    r_op, r_tr = mandate_root(reg, "operating"), mandate_root(reg, "trust")
    assert r_op != r_tr  # isolation at the root, not just the row
    reg.append("policy:INS-1", {"carrier": "acme", "renewed": True}, author="h.bhatt",
               source_ref="POL-1:renewal", at="2029-03-01", mandate="trust")
    assert mandate_root(reg, "operating") == r_op   # trust's change never moves operating's root
    assert mandate_root(reg, "trust") != r_tr


def test_shared_object_grants_declared_scope_only(tmp_path):
    reg = _reg(tmp_path)
    rules = [SharingRule("policy:INS-1", to_mandate="operating", scope="read")]
    assert check_access(reg, rules, principal_mandate="operating",
                        obj_id="policy:INS-1", want="read")
    with pytest.raises(ScopeRefusal):  # read grant never authorizes write
        check_access(reg, rules, principal_mandate="operating",
                     obj_id="policy:INS-1", want="write")
    with pytest.raises(ScopeRefusal):  # no rule at all -> refused
        check_access(reg, [], principal_mandate="operating",
                     obj_id="policy:INS-1", want="read")
