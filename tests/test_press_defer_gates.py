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
    # default carries a non-empty (not-yet-existing) test path → test_pending, not a P-6 defect
    e = {"id": "S5-99-E1-1", "claim": "a designed surface", "status": "HOLD",
         "blocks_seal": True, "acceptance_test": "tests/test_future_home.py"}
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


def test_p1_receipt_label_is_d12_clean_and_present_only_drops_marker():
    """D12 (P-5' interaction): the 'Designed-toward' receipt label must not leak an UNHOMED
    forward marker into the assembled interior — a HOLD chapter names its home in the label;
    an all-PRESENT chapter shows no designed-toward marker at all."""
    from sovereign_agent.press import assembler
    from sovereign_agent.press.prescreen import unhomed_forwards
    # HOLD chapter: label carries the closing home inline → D12-clean
    c_hold = {"receipt_box": {"claim": "the thesis"},
              "extrusion": [{"status": "HOLD", "closes_in": "S8-V4", "claim": "the designed surface"}]}
    box_h = assembler._receipt_box_md(1, c_hold)
    assert "Designed-toward — named closing home." in box_h and "Closes in S8-V4." in box_h
    assert unhomed_forwards(box_h) == []
    # all-PRESENT chapter: no designed-toward marker; deployment note under a non-marker heading
    c_present = {"receipt_box": {"claim": "the thesis"},
                 "extrusion": [{"status": "PRESENT", "claim": "a built mechanism"}]}
    box_p = assembler._receipt_box_md(2, c_present)
    assert "Designed-toward" not in box_p and "Your build from here." in box_p
    assert unhomed_forwards(box_p) == []


# ── P-5' / D12: a forward marker must name its closing home within ~200 chars ──

def test_p5_d12_unhomed_forward_is_flagged():
    from sovereign_agent.press import prescreen
    txt = "Helix distribution rendering is designed-toward and unbuilt. The book runs on the record."
    assert len(prescreen.unhomed_forwards(txt)) == 1


def test_p5_d12_homed_forward_is_clean():
    from sovereign_agent.press import prescreen
    assert prescreen.unhomed_forwards(
        "Helix distribution rendering is designed-toward, closes in S6-V5.") == []
    assert prescreen.unhomed_forwards(
        "This surface is designed-toward — OPEN-DECISION:KM until the home is ruled.") == []
    assert prescreen.unhomed_forwards(
        "The join layer is designed-toward; it closes in S6 Inter-Node.") == []


def test_p5_d12_gate_card_kills_unhomed_forward():
    from sovereign_agent.press import prescreen
    card = {"chapter": "2", "runs_today": ["x"],
            "prose": "The rendering layer is designed-toward and unbuilt."}
    v, _adv = prescreen.gate_card(card)
    assert any(x["lens"] == "L0:prescreen:unhomed_forward" for x in v)


# ── P-6: empty acceptance_test is a defect (not a silent pass) ──

def test_p6_empty_acceptance_test_is_defect(tmp_path):
    from sovereign_agent.press import co_extrude
    r = co_extrude.run(_seeds(tmp_path, _hold(closes_in="OPEN-DECISION:KM", acceptance_test="")),
                       repo=str(tmp_path))
    assert any("empty acceptance_test" in (d.get("why") or "") for d in r["defects"])


def test_p6_nonexistent_test_is_pending_not_defect(tmp_path):
    from sovereign_agent.press import co_extrude
    r = co_extrude.run(_seeds(tmp_path, _hold(closes_in="OPEN-DECISION:KM",
                                              acceptance_test="tests/test_nope.py")), repo=str(tmp_path))
    assert r["defects"] == []
    assert r["entries"][0].get("test_pending") == "tests/test_nope.py"


# ── Audit 2026-08-01 (KM GO #1): D12 is now in the board path — cmd_run's assembled-interior
#    scan (continuity_check_assembled) flags unhomed forward markers, not just the seed-side gate ──

def test_d12_assembled_interior_flags_unhomed_forward(tmp_path):
    from sovereign_agent.press import board_stage1
    seeds = tmp_path / "seeds"; seeds.mkdir()
    asm = tmp_path / "assembled.md"
    asm.write_text("The book runs on the record.\n\nThe rendering layer is designed-toward and unbuilt.\n")
    r = board_stage1.continuity_check_assembled(str(asm), str(seeds))
    assert r["result"] == "FAIL"
    assert any("unhomed forward marker (D12)" in f for f in r["findings"])


def test_d12_assembled_interior_clean_when_homed(tmp_path):
    from sovereign_agent.press import board_stage1
    seeds = tmp_path / "seeds"; seeds.mkdir()
    asm = tmp_path / "assembled.md"
    asm.write_text("The rendering layer is designed-toward — a later book in Series 8 builds it.\n")
    r = board_stage1.continuity_check_assembled(str(asm), str(seeds))
    assert not any("unhomed forward marker (D12)" in f for f in r["findings"])


# ── PS-4a (KM ruling 2026-08-02): external-series HOLD = disclosed deferral, not an open debt ──

def _seed_holds(tmp_path, entries):
    import yaml as _y
    d = tmp_path / "seeds"; d.mkdir(exist_ok=True)
    _y.safe_dump({"chapter": "1", "prose": "p", "extrusion": entries}, open(d / "ch1.yaml", "w"))
    return str(d)


def _hold_e(cid, closes_in):
    return {"id": cid, "claim": "a designed surface", "status": "HOLD",
            "blocks_seal": True, "closes_in": closes_in, "acceptance_test": "tests/test_x.py"}


def test_ps4a_external_series_hold_does_not_block(tmp_path):
    from sovereign_agent.press.engine import _open_seal_blocking_holds
    seeds = _seed_holds(tmp_path, [_hold_e("S5-04-E1-2", "S8-V4"), _hold_e("S5-04-E3-3", "S7-V1")])
    # sealing an S5 volume: both HOLDs close in a DIFFERENT series → exempt → nothing blocks
    assert _open_seal_blocking_holds(seeds, this_series=5) == []


def test_ps4a_same_series_and_unhomed_still_block(tmp_path):
    from sovereign_agent.press.engine import _open_seal_blocking_holds
    seeds = _seed_holds(tmp_path, [
        _hold_e("S5-04-Ea", "S5-V6"),   # same series → blocks
        _hold_e("S5-04-Eb", ""),        # unhomed → blocks
        _hold_e("S5-04-Ec", "S8-V4"),   # external → exempt
    ])
    blocking = _open_seal_blocking_holds(seeds, this_series=5)
    assert len(blocking) == 2
    assert any("S5-04-Ea" in b for b in blocking) and any("S5-04-Eb" in b for b in blocking)
    assert not any("S5-04-Ec" in b for b in blocking)


def test_ps4a_disabled_without_series_every_hold_blocks(tmp_path):
    """this_series=None → pre-PS-4a behaviour: every blocks_seal HOLD blocks (fail-closed default)."""
    from sovereign_agent.press.engine import _open_seal_blocking_holds
    seeds = _seed_holds(tmp_path, [_hold_e("S5-04-E1-2", "S8-V4")])
    assert len(_open_seal_blocking_holds(seeds, this_series=None)) == 1
