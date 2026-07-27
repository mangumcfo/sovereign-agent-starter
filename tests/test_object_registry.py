"""S5-05-E2-1: one registry, stable identity, one integrity root over the population."""
from sovereign_agent.objects.registry import ObjectRegistry, root_from_object_list


def test_root_recomputes_byte_identical_from_object_list(tmp_path):
    reg = ObjectRegistry(str(tmp_path))
    for i in range(7):
        reg.append(f"part:P-{i:03d}", {"qty": i * 10}, author="d.reyes",
                   source_ref=f"COUNT-{i}:sheet", at="2029-01-10", mandate="operating")
    reg.append("part:P-003", {"qty": 999}, author="d.reyes",
               source_ref="ADJ-9:sheet", at="2029-01-11", mandate="operating")
    root = reg.population_root()
    # an outsider recomputes the SAME root from the bare object list — byte-identical
    assert root_from_object_list(reg.entries()) == root
    # and the root is a pure function of state: a fresh replay agrees
    assert ObjectRegistry(str(tmp_path)).population_root() == root
