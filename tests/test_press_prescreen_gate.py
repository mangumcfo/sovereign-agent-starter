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


def test_ps4_open_holds_scanner(tmp_path):
    import yaml as _y
    from sovereign_agent.press.engine import _open_seal_blocking_holds
    d = tmp_path / "seeds"; d.mkdir()
    _y.safe_dump({"chapter": "1", "extrusion": [
        {"id": "X-E1", "claim": "c", "status": "HOLD", "blocks_seal": True},
        {"id": "X-E2", "claim": "c2", "status": "PRESENT"}]}, open(d / "ch1.yaml", "w"))
    _y.safe_dump({"meta": 1}, open(d / "_volume_input.yaml", "w"))
    holds = _open_seal_blocking_holds(str(d))
    assert len(holds) == 1 and holds[0].startswith("X-E1")


def test_ps4_no_holds_when_resolved(tmp_path):
    import yaml as _y
    from sovereign_agent.press.engine import _open_seal_blocking_holds
    d = tmp_path / "seeds"; d.mkdir()
    _y.safe_dump({"chapter": "1", "extrusion": [
        {"id": "X-E1", "claim": "c", "status": "PRESENT"},
        {"id": "X-E2", "claim": "c2", "status": "DOWNGRADED", "receipt": "honest design voice"}]},
        open(d / "ch1.yaml", "w"))
    assert _open_seal_blocking_holds(str(d)) == []


def _ps2_seed_dir(tmp_path):
    import yaml as _y
    d = tmp_path / "seeds"; d.mkdir()
    frame = "Acme Corp is a worked scenario built to show the design."
    (d / "_frame_declaration.md").write_text(frame)
    _y.safe_dump({"title": "T", "subtitle": "S", "book_id": "s9_01_x",
                  "continuity_canon": {"company": "Acme Corp"},
                  "chapters": [{"n": 1}]}, open(d / "_volume_input.yaml", "w"))
    _y.safe_dump([{"name": "f1", "must_pattern": "Acme", "required_in": [1]}],
                 open(d / "_continuity_facts.yaml", "w"))
    _y.safe_dump({"chapter": "1", "title": "One", "settled": True,
                  "prose": frame + "\n\nBody prose here.",
                  "receipt_box": {"claim": "c", "runs_today": "the mechanism is implemented and test-checked",
                                  "designed": "your deployed system is the design you build"},
                  "verify_affordance": ["check it yourself"],
                  "extrusion": [{"id": "E1", "claim": "x", "status": "HOLD",
                                 "blocks_seal": True}]}, open(d / "ch1.yaml", "w"))
    return d


def test_ps2_assembles_and_places_verbatim(tmp_path):
    from sovereign_agent.press.assembler import assemble
    d = _ps2_seed_dir(tmp_path)
    out = tmp_path / "vol.md"
    r = assemble(str(d), str(out), str(tmp_path / "r.json"))
    doc = out.read_text()
    assert "Body prose here." in doc and "worked scenario" in doc
    assert doc.count("**How you check.**") == 1
    assert r["claims_hold"] == 1 and r["chapters"] == 1


def test_ps2_refuses_on_gaps_with_full_list(tmp_path):
    import pytest, yaml as _y
    from sovereign_agent.press.assembler import assemble, AssemblyRefusal
    d = _ps2_seed_dir(tmp_path)
    (d / "_frame_declaration.md").unlink()
    c = _y.safe_load(open(d / "ch1.yaml")); del c["receipt_box"]
    _y.safe_dump(c, open(d / "ch1.yaml", "w"))
    with pytest.raises(AssemblyRefusal) as ei:
        assemble(str(d), str(tmp_path / "vol.md"))
    gaps = ei.value.gaps
    assert any("frame declaration missing" in g for g in gaps)
    assert any("receipt_box.claim" in g for g in gaps)  # full list, not first-fail


def test_rev5_bare_numeral_end_detector():
    from sovereign_agent.press.prescreen import bare_numeral_ends
    # the two production-board garbles fire (number reappears with its dropped unit)
    body = ("The proof uses a set of 16 siblings. It is absolute but limited to a single 16. "
            "The audit runs 640 hashes; the audit is a calculation of 640.")
    hits = bare_numeral_ends(body)
    assert any("single 16" in h for h in hits) and any("of 640" in h for h in hits)
    # predicate values and unit-carrying ends are spared
    assert bare_numeral_ends("The proof depth is 16. It took 12 minutes and cost $412,000.") == []
    # rhetorical elision with no domain-unit reappearance is spared
    assert bare_numeral_ends("You pay for 20 salespeople and get the selling capacity of 7.") == []


def test_rev5_apparatus_leak_detector():
    from sovereign_agent.press.prescreen import apparatus_leaks
    hard, stale = apparatus_leaks([
        "traced in src/sovereign_agent/merkle_accumulator.py, proven in tests/test_merkle_accumulator.py",
        "the rules module stays in its lane", "Nothing in this volume's object model runs today"])
    assert any(".py" in h for h in hard) and any("test_" in h for h in hard)
    assert any("lane" in h for h in hard) and stale
    # clean reader prose passes
    h2, s2 = apparatus_leaks(["Dana reconciles the ledger of accounts to the bank statement each month."])
    assert h2 == [] and s2 == []


def test_rev5_pinned_continuity_fact_kills(tmp_path):
    import subprocess, sys, yaml as _y, os
    d = tmp_path / "seeds"; d.mkdir()
    _y.safe_dump([{"name": "insurance_owner", "pin": True,
                   "canonical": "Family Trust owns the policy; Operating holds a read grant",
                   "scope": [6], "forbid_pattern": r"policy[^.]{0,60}(owned by|belongs to)[^.]{0,20}Properties LLC"}],
                 open(d / "_continuity_facts.yaml", "w"))
    good = {"chapter": 6, "prose": "The insurance policy belongs to the Family Trust; Operating holds a read grant. "
            "This crossing is one of twelve. The population is 41,830 objects across the classes.", "runs_today": []}
    bad = {"chapter": 6, "prose": "The insurance policy is owned by Properties LLC. "
           "This crossing is declared. The population is 41,830 objects across the classes.", "runs_today": []}
    other = {"chapter": 2, "prose": "The registry gives each object a stable identity. "
             "Authorship travels with every version. Ridgeline holds 41,830 objects in all.", "runs_today": []}
    _y.safe_dump(good, open(d / "ch6.yaml", "w"))
    _y.safe_dump(other, open(d / "ch2.yaml", "w"))
    r = subprocess.run([sys.executable, "-m", "sovereign_agent.press.prescreen", "--seeds", str(d)],
                       cwd=str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"),
                       capture_output=True, text=True, env={**os.environ, "PYTHONPATH": ""})
    assert '"result": "PASS"' in r.stdout, r.stdout
    _y.safe_dump(dict(bad), open(d / "ch6.yaml", "w"))
    r = subprocess.run([sys.executable, "-m", "sovereign_agent.press.prescreen", "--seeds", str(d)],
                       cwd=str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"),
                       capture_output=True, text=True, env={**os.environ, "PYTHONPATH": ""})
    assert "continuity_pin" in r.stdout and "PINNED" in r.stdout, r.stdout


def test_rev6_tissue_budgets():
    from sovereign_agent.press.prescreen import tissue_budgets
    lenses = lambda body: {v[0] for v in tissue_budgets(body)}
    # "This X allows [Name] to Y" frame killed
    assert "tissue_this_x_allows" in lenses("This mechanism allows Dana to verify the root herself.")
    # full name twice in one paragraph -> pronominalize
    assert "tissue_pronominalize" in lenses("Dana Reyes opened the ledger. Later, Dana Reyes closed it.")
    # 2+ cast as reaction-verb subjects in one paragraph -> cast-as-decoration
    assert "tissue_cast_decoration" in lenses(
        "Dana observes the change. Ilse notes the discrepancy. The root holds.")
    # clean disciplined prose passes
    assert tissue_budgets(
        "Dana opened the ledger and recomputed the root; it matched the published value. "
        "The proof carried sixteen siblings, and the check took a single pass.") == []


def test_rev6_calibration_published_clean():
    # the disciplined register must not fire on genuinely-varied published-style prose
    from sovereign_agent.press.prescreen import tissue_budgets
    good = ("Send too little context, and the specialist produces a shallow analysis. "
            "Send the wrong context, and the specialist produces a confident but wrong answer. "
            "The controller reconciles cash to the bank statement each month, tying every line "
            "to a record held outside her own books.")
    assert tissue_budgets(good) == []


def test_ps4_default_deny_no_ledger(tmp_path, monkeypatch):
    """The HOLD-check hole: a production volume whose manifest entry omits extrusion_ledger
    must REFUSE (default-deny), not silently skip. Legacy volumes (extrusion:none) skip."""
    import subprocess, sys, os, textwrap
    man = tmp_path / "m.yaml"
    man.write_text(textwrap.dedent('''
      volumes:
        prod_no_ledger:
          title: p
          stage: built-in-review
          freeze_sha: "0000000000000000"
        legacy_ok:
          title: l
          stage: published
          freeze_sha: "1111111111111111"
          extrusion: none
    ''').lstrip())
    src = str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src")
    env = {**os.environ, "PYTHONPATH": "", "PRESS_MANIFEST": str(man),
           "PRESS_SEAL_KEY": os.path.expanduser("~/.press_seal_key"), "PRESS_PRINCIPAL": "KM-1176"}
    env.pop("PRESS_EXTRUSION_LEDGER", None)
    def _seal(vol):
        r = subprocess.run([sys.executable, "-c",
            f"import sys; sys.path.insert(0,{src!r}); from sovereign_agent.press.engine import main; "
            f"sys.argv=['x','seal',{vol!r}]\ntry:\n main()\nexcept SystemExit:\n pass"],
            capture_output=True, text=True, env=env)
        return r.stdout + r.stderr
    # production volume without a ledger -> default-deny refusal (not the word line)
    out = _seal("prod_no_ledger")
    assert "default-deny" in out and "no extrusion_ledger" in out, out
    # legacy volume -> passes the HOLD gate to the word line (no default-deny)
    out = _seal("legacy_ok")
    assert "default-deny" not in out, out


def test_co_extrude_present_and_hold(tmp_path):
    """P-G3: PRESENT with a passing test validates; HOLD without blocks_seal is a defect;
    a missing PRESENT module is a defect."""
    from sovereign_agent.press import co_extrude
    import yaml as _y
    d = tmp_path / "seeds"; d.mkdir()
    (tmp_path / "src").mkdir(); (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "real.py").write_text("x = 1\n")
    (tmp_path / "tests" / "test_real.py").write_text("def test_ok():\n    assert True\n")
    _y.safe_dump({"chapter": "1", "extrusion": [
        {"id": "E1", "claim": "c", "status": "present",
         "target_module": "src/real.py", "acceptance_test": "tests/test_real.py"},
        {"id": "E2", "claim": "c2", "status": "HOLD"},                      # missing blocks_seal
        {"id": "E3", "claim": "c3", "status": "present",
         "target_module": "src/missing.py", "acceptance_test": "tests/test_real.py"}]},
        open(d / "ch1.yaml", "w"))
    r = co_extrude.run(str(d), repo=str(tmp_path))
    assert r["present_validated"] == 1
    ids = {x["id"] for x in r["defects"]}
    assert ids == {"E2", "E3"}, r["defects"]
