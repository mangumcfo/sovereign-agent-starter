"""/goal Scout propose-only enforcement — the STANDING static guard (GB [375] affirm #2).

The scout MUST remain propose-only: it never creates a real obligation, never commits/seals, never edits
source — it only writes under artifacts/scout/ and posts candidate proposals (status 'proposed') that KM+GB
disposition. This test reads the runner's source and fails if a future edit introduces a forbidden call —
so "scout works" can never silently become "scout decides".
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "scripts" / "scout_run.py"


def test_runner_exists():
    assert RUNNER.is_file(), "scripts/scout_run.py missing"


def test_runner_makes_no_real_obligations_or_mutations():
    """Forbidden: creating/approving/closing obligations, committing, sealing, or invoking the ledger
    mutators. The scout proposes candidates only; a real obligation is born only on KM+GB decision."""
    src = RUNNER.read_text(encoding="utf-8")
    code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    forbidden = [
        r"ObligationLedger",          # never touch the obligation ledger at all
        r"\.open\(", r"\.approve\(", r"\.close\(",   # ledger lifecycle mutators
        r"git\s+commit", r"git\s+add", r"subprocess.*\bgit\b",
        r"seal\.sh", r"--hierarchical",              # never seal a cylinder
    ]
    hits = [pat for pat in forbidden if re.search(pat, code)]
    assert not hits, f"scout_run.py contains forbidden (non-propose-only) calls: {hits}"


def test_runner_only_writes_under_artifacts_scout():
    """Every write target in the runner must live under artifacts/scout/ (its own tree) — never the repo
    source, the obligation ledger, or anywhere else. We assert the write sinks are scout-scoped."""
    src = RUNNER.read_text(encoding="utf-8")
    # The runner's only persistent sinks: BASELINE + the packets/rejected dirs, all under SCOUT.
    assert 'SCOUT = REPO / "artifacts" / "scout"' in src
    assert "BASELINE = SCOUT" in src
    # No write_text / open(..., "w") to a path outside the scout tree (heuristic: no src/ or scripts/ write).
    bad = re.findall(r'(REPO\s*/\s*"(?:src|scripts|tests)").*?\.write_text', src)
    assert not bad, f"runner writes outside artifacts/scout/: {bad}"


def test_candidate_post_is_proposals_not_obligations():
    """The propose-only output path posts to /proposals (candidates, status 'proposed') — NOT /obligations."""
    src = RUNNER.read_text(encoding="utf-8")
    assert "/api/v1" in src and '/proposals"' in src   # candidate post target = the proposals surface
    assert "/obligations" not in src                   # the scout never writes the obligation chain
