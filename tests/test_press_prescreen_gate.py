"""Regression: the gate_rev-1 prescreen gate + pilot loader/targeting fixes."""
import json, os, sys, tempfile
import yaml
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sovereign_agent.press.prescreen import gate_card, GATE_REV
from sovereign_agent.press.adversary import load_cards
from sovereign_agent.press.engine import _pick_killed_card
from pathlib import Path

GOOD = (
    "The receipt is the atom of trust here — a sealed, signed record the operator can replay. "
    "You verify it yourself; nothing asks for faith. Lasting Generational Prosperity (LGP) is the "
    "test every design choice answers to, and it is a demanding one. Consider a distributor with "
    "1,400 SKUs whose auditor asks for March's inventory position: the answer is a replay, not a "
    "spreadsheet. Each movement seals as a balanced obligation, so the number carries its own proof. "
    "When the founder hands the company to her daughter, the record does not ask to be believed — "
    "it recomputes. That difference, small on a quiet day, is the entire inheritance on a bad one. "
    "A registry entry is versioned; a version is sealed; a seal is checkable by anyone she names. "
    "The pattern repeats up the stack without repeating its sentences, which is rather the point.")

def _card(prose, ch="2"):
    return {"chapter": ch, "prose": prose, "beats": ["b"], "runs_today": []}

def test_gate_rev_exists():
    assert isinstance(GATE_REV, int) and GATE_REV >= 1

def test_gate_kills_voice_and_canon():
    bad = GOOD.rstrip() + " Furthermore, we utilize the system. Ledger-General-Purpose (LGP) drives it."
    v, _ = gate_card(_card(bad, "3"))
    lenses = {x["lens"] for x in v}
    assert any("voice_empty_transition" in l for l in lenses)
    assert any("voice_consultant" in l for l in lenses)
    assert any("canon_drift" in l for l in lenses)
    assert all(x["chapter"] == "3" for x in v)  # verdicts name their chapter (D-3 chain)

def test_gate_passes_house_prose():
    v, _ = gate_card(_card(GOOD))
    assert v == [], v

def test_gate_kills_unqualified_live_claim():
    v, _ = gate_card(_card(GOOD + " The token engine is live and enforces every rule."))
    assert any(x["lens"] == "L0:prescreen:live_claim" for x in v)

def test_loader_skips_undrafted_never_crashes(capsys):
    d = tempfile.mkdtemp()
    full = ("A full sentence of lawful chapter prose that carries the argument forward. " * 60).strip()
    yaml.safe_dump({"chapter": "1", "prose": full, "seed_unit": "full_chapter", "promise": "p",
                    "beats": ["b"], "beats_locked": True, "runs_today": []}, open(f"{d}/ch1.yaml", "w"))
    yaml.safe_dump({"chapter": "2", "prose": "", "draft_status": "UNDRAFTED"}, open(f"{d}/ch2.yaml", "w"))
    yaml.safe_dump({"vol_id": "x"}, open(f"{d}/_volume_input.yaml", "w"))
    cards = load_cards(Path(d))
    out = capsys.readouterr().out
    assert len(cards) == 1 and cards[0]["chapter"] == "1"
    assert "SKIP (undrafted" in out  # loud, per the binding condition

def test_picker_targets_refuted_chapter():
    d = tempfile.mkdtemp()
    for n in ("1", "2", "3"):
        yaml.safe_dump({"chapter": n, "prose": "x"}, open(f"{d}/ch{n}.yaml", "w"))
    rec = f"{d}/rec.json"
    json.dump({"verdicts": [{"chapter": "3", "refuted": True, "reason": "r"}]}, open(rec, "w"))
    assert _pick_killed_card(d, rec).endswith("ch3.yaml")
