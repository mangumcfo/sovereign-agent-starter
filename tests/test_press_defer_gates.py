"""P-1/HG-1 (2026-07-30) — a HOLD must name a closing home (`closes_in`).

Root-cause fix for the unhosted-designed-toward hole: the extrusion HOLD record now carries a required
`closes_in` (a volume id, spec path, `live-runtime cutover`, or `OPEN-DECISION:<owner>`). Co-extrusion
refuses a HOLD with no home; assembly refuses it too; the receipt box renders the home beside each
designed-toward bullet. A `closes_in` naming THIS volume is unbuilt scope, not a deferral.
"""
import yaml as _y


def _seeds(tmp_path, entry):
    d = tmp_path / "seeds"; d.mkdir(exist_ok=True)
    _y.safe_dump({"chapter": "1", "prose": "p", "extrusion": [entry]}, open(d / "ch1.yaml", "w"))
    return str(d)


def _hold(**kw):
    e = {"id": "S5-99-E1-1", "claim": "a designed surface", "status": "HOLD",
         "blocks_seal": True, "acceptance_test": ""}
    e.update(kw)
    return e


def test_p1_hold_without_closes_in_is_defect(tmp_path):
    from sovereign_agent.press import co_extrude
    r = co_extrude.run(_seeds(tmp_path, _hold()), repo=str(tmp_path))
    assert any("without closes_in" in (d.get("why") or "") for d in r["defects"])


def test_p1_open_decision_home_passes_but_still_blocks_seal(tmp_path):
    from sovereign_agent.press import co_extrude
    r = co_extrude.run(_seeds(tmp_path, _hold(closes_in="OPEN-DECISION:KM")), repo=str(tmp_path))
    assert r["defects"] == []                              # a homed HOLD is not a defect
    e = r["entries"][0]
    assert e["status"] == "HOLD" and e.get("closes_in") == "OPEN-DECISION:KM"
    assert r["holds"] == 1                                 # still counted → PS-4 blocks the seal


def test_p1_closes_in_naming_this_volume_is_defect(tmp_path):
    from sovereign_agent.press import co_extrude
    r = co_extrude.run(_seeds(tmp_path, _hold(id="S5-06-E1-1", closes_in="S5-V6")), repo=str(tmp_path))
    assert any("names this volume" in (d.get("why") or "") for d in r["defects"])


def test_p1_receipt_box_renders_the_home(tmp_path):
    from sovereign_agent.press import assembler
    c = {"receipt_box": {"claim": "the chapter thesis"},
         "extrusion": [{"status": "HOLD", "closes_in": "S6-V5", "claim": "the designed surface"}]}
    box = assembler._receipt_box_md(2, c)
    assert "closes in S6-V5" in box
    assert "Designed-toward — named closing home" in box
