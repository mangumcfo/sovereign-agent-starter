"""S5-05-E2-2: every object version carries authorship and a resolvable source reference."""
import pytest
from sovereign_agent.objects.identity import VersionRefused, make_version


def test_version_requires_author_and_resolvable_source_ref(tmp_path):
    src = tmp_path / "po_2041.txt"
    src.write_text("signed purchase order")
    v = make_version("customer:C-1", 1, {"limit": 150000}, author="d.reyes",
                     source_ref=str(src), at="2029-01-05")
    assert v["author"] == "d.reyes" and v["source_ref"] == str(src) and v["version_hash"]

    with pytest.raises(VersionRefused):
        make_version("customer:C-1", 1, {}, author="  ", source_ref=str(src), at="2029-01-05")
    with pytest.raises(Exception):  # R22-3: a path-like citation that does not resolve refuses
        make_version("customer:C-1", 1, {}, author="d.reyes",
                     source_ref=str(tmp_path / "missing.pdf"), at="2029-01-05")
    # symbolic refs (not file claims) are lawful per the provenance law
    v2 = make_version("customer:C-1", 2, {}, author="d.reyes",
                      source_ref="PO-2041:countersigned", at="2029-01-06")
    assert v2["seq"] == 2
