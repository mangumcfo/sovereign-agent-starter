"""Pattern-regression guards — Universalize Wave §7 (G4): the disease must not re-enter.

The wave universalized five disciplines by extracting ONE primitive each. These lightweight static +
behavioral guards fail the moment a future change reintroduces the propagation pattern — so the next
sweep cannot find a sibling the wave already eliminated. The law they also pin: scripts may import
package code; package code must NEVER import scripts.
"""
import re
from pathlib import Path

import sovereign_agent
from sovereign_agent.ndjson import read_ndjson

SRC = Path(sovereign_agent.__file__).resolve().parent          # …/src/sovereign_agent
REPO = SRC.parents[1]                                          # repo root
NODE_API = SRC / "node_api"
SCRIPTS = REPO / "scripts"
LEDGER = SRC / "obligations" / "ledger.py"


def _py(root):
    return [p for p in root.rglob("*.py")]


def test_no_request_path_syspath_mutation_in_node_api():
    """No route/module under node_api may inject onto sys.path at request time (§5/G4)."""
    offenders = [p.relative_to(SRC) for p in _py(NODE_API)
                 if "sys.path.insert" in p.read_text(encoding="utf-8")
                 or "sys.path.append" in p.read_text(encoding="utf-8")]
    assert not offenders, f"request-path sys.path mutation in node_api: {offenders}"


def test_no_raw_perline_ndjson_parse_outside_gateway():
    """Per-line ndjson parsing must route through ndjson.py (§1/G2). The ledger's guarded append-aware
    tail fast-path is the ONE allowed exception — it falls through to the gateway on any parse error."""
    pat = re.compile(r"json\.loads\((l|s|ln|line)\b")
    offenders = []
    for base in (SRC, SCRIPTS):
        for p in _py(base):
            if p.name == "ndjson.py" or p == LEDGER:
                continue
            for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if pat.search(ln):
                    offenders.append(f"{p.relative_to(REPO)}:{i}")
    assert not offenders, f"raw per-line ndjson parse outside the gateway: {offenders}"


def test_package_never_imports_scripts():
    """G4 law: package code must not depend on scripts/ (scripts→package is the only allowed direction)."""
    offenders = []
    for p in _py(SRC):
        for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            s = ln.strip()
            if s.startswith("import scripts") or s.startswith("from scripts ") or s.startswith("from scripts."):
                offenders.append(f"{p.relative_to(REPO)}:{i}")
    assert not offenders, f"package→scripts import (forbidden): {offenders}"


def test_no_direct_private_entries_consumer_outside_ledger():
    """The chain is read through the public gateway (iter_entries/refs), never the private _entries() (G3)."""
    offenders = []
    for base in (SRC, SCRIPTS):
        for p in _py(base):
            if p == LEDGER:
                continue
            for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if "._entries()" in ln:
                    offenders.append(f"{p.relative_to(REPO)}:{i}")
    assert not offenders, f"direct private _entries() consumer outside ledger.py: {offenders}"


def test_gateway_truncated_tail_survives_and_middle_is_loud(tmp_path):
    """Behavioral G2 at the guard layer: truncated tail survives (ok), corrupt middle is loud."""
    tail = tmp_path / "tail.ndjson"
    tail.write_text('{"n": 0}\n{"n": 1, "part', encoding="utf-8")
    rt = read_ndjson(tail)
    assert rt.ok and not rt.chain_corrupt and rt.repair_required and [e["n"] for e in rt.entries] == [0]

    mid = tmp_path / "mid.ndjson"
    mid.write_text('{"n": 0}\n{bad}\n{"n": 2}\n', encoding="utf-8")
    rm = read_ndjson(mid)
    assert rm.chain_corrupt and not rm.ok and rm.bad_line == 2
