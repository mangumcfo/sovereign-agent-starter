"""P-2 (2026-07-30) — the Seal Summary must not print a false 'zero by construction' attestation.

Regression guard for the shipped defect: SEAL_SUMMARY_s5_04 said "16 present · 8 HOLD (zero by
construction)" — a literal contradiction on the artifact a human reads to speak the seal word. The
generator must now compute the parenthetical from the real HOLD count and REFUSE (OpenBlockingHolds)
when blocking HOLDs are open, while still emitting the doc so the human sees the true state.
"""
import json as _j

import yaml as _y


def _setup(tmp_path, n_present, n_hold):
    d = tmp_path / "seeds"; d.mkdir()
    _y.safe_dump({"title": "S5-0X V", "subtitle": "sub", "description": "desc"},
                 open(d / "_volume_input.yaml", "w"))
    ex = []
    for i in range(n_present):
        ex.append({"id": f"E{i+1}", "claim": f"present claim {i+1}", "status": "present",
                   "target_module": "src/x.py", "acceptance_test": "tests/test_x.py"})
    for i in range(n_hold):
        ex.append({"id": f"H{i+1}", "claim": f"held claim {i+1}", "status": "HOLD",
                   "blocks_seal": True, "closes_in": "OPEN-DECISION:KM"})
    _y.safe_dump({"chapter": "1", "extrusion": ex}, open(d / "ch1.yaml", "w"))
    cyc = tmp_path / "cycle.json"; cyc.write_text(_j.dumps({"gate_rev": 8, "result": "PASS", "cycle_sha256": "abc"}))
    stl = tmp_path / "s.json"; stl.write_text(_j.dumps({"settled_cycle": "abc", "chapters": []}))
    asm = tmp_path / "a.json"; asm.write_text(_j.dumps({"doc_sha256_16": "deadbeef"}))
    brd = tmp_path / "b.json"; brd.write_text(_j.dumps({
        "parity": [], "reader": {"verdict": "ok", "suspicion_point": "none"},
        "continuity": "PASS", "binding_bar": "CLEAR"}))
    return str(d), str(cyc), str(stl), str(asm), str(brd)


def test_p2_open_blocking_holds_refuses(tmp_path):
    """16 PRESENT + 8 HOLD (the s5_04 shape) → generator REFUSES; doc shows the true 8, no lie."""
    from sovereign_agent.press import seal_summary
    import pytest
    d, cyc, stl, asm, brd = _setup(tmp_path, 16, 8)
    with pytest.raises(seal_summary.OpenBlockingHolds) as ei:
        seal_summary.generate(d, cyc, stl, asm, brd)
    doc = ei.value.doc
    assert ei.value.hold == 8
    assert "8 open blocking HOLD" in doc          # real count, computed
    assert "DO NOT SEAL" in doc                   # unmissable banner
    assert "SEAL BLOCKED" in doc                  # no seal offered
    assert "zero by construction" not in doc      # the false literal is gone


def test_p2_zero_holds_clean(tmp_path):
    """0 HOLD → clean seal-ready summary; no banner, no false literal, seal offered."""
    from sovereign_agent.press import seal_summary
    d, cyc, stl, asm, brd = _setup(tmp_path, 3, 0)
    doc = seal_summary.generate(d, cyc, stl, asm, brd)  # must NOT raise
    assert "0 HOLD — the ledger is fully PRESENT" in doc
    assert "DO NOT SEAL" not in doc
    assert "zero by construction" not in doc
    assert "**Seal**" in doc                      # the seal line is offered when clean


def test_p3_surfaces_board_verdict_and_unknown_keys(tmp_path):
    """P-3: verdict_at_board rendered verbatim; unknown board keys surfaced with a warning, never dropped."""
    from sovereign_agent.press import seal_summary
    d, cyc, stl, asm, brd = _setup(tmp_path, 2, 0)   # 0 HOLD → clean return path
    _j.dump({
        "parity": [], "reader": {"verdict": "ok", "suspicion_point": "none"},
        "continuity": "PASS", "binding_bar": "CLEAR",
        "verdict_at_board": "DOES NOT CLEAR FOR SEAL — strongest first-pass board any volume has run",
        "novel_metric": 0.42}, open(brd, "w"))
    doc = seal_summary.generate(d, cyc, stl, asm, brd)
    assert "DOES NOT CLEAR FOR SEAL" in doc           # verdict rendered verbatim
    assert "BOARD VERDICT:" in doc
    assert "novel_metric" in doc                       # unknown key surfaced, not dropped
    assert "not otherwise rendered" in doc
