"""Engine 95+ close-the-2 #a (audit 2026-06-16 HIGH) — the constraints lock cannot lie about its env.

The 2026-06-15 defect: constraints.txt claimed "re-verified: 270 green ... pins recaptured from the green
interpreter, unchanged" while the pins (PyYAML 6.0.1 / pytest 9.0.2) did NOT match the actual resolved env.
That was a verify-before-claim failure — a provenance assertion no test enforced.

This test closes it mechanically: every exact pin in constraints.txt MUST equal the version actually
installed in the interpreter running the suite. Because the canonical green env installs WITH
`-c constraints.txt` (Dockerfile / ci.yml / sovereign-install.sh), the resolved versions ARE the pins — so
this passes by construction in the canonical env and fails RED on any drift or stale-pin claim. No skips:
a missing pinned package or a mismatch is a hard failure, never a silent green.
"""
import importlib.metadata as md
import re
from pathlib import Path

CONSTRAINTS = Path(__file__).resolve().parents[1] / "constraints.txt"

_PIN = re.compile(r"^\s*([A-Za-z0-9._-]+)\s*==\s*([A-Za-z0-9._-]+)\s*$")


def _pins():
    """Parse exact (==) pins from constraints.txt, ignoring comments and blanks."""
    out = {}
    for line in CONSTRAINTS.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("#") or not line.strip():
            continue
        m = _PIN.match(line)
        assert m, f"constraints.txt line is not an exact == pin: {line!r}"
        out[m.group(1)] = m.group(2)
    return out


def test_constraints_file_has_exact_pins():
    pins = _pins()
    assert pins, "constraints.txt has no pins"
    assert {"PyYAML", "Flask", "cryptography", "pytest"} <= set(pins), \
        f"constraints.txt is missing an expected pin: have {sorted(pins)}"


def test_every_pin_matches_the_installed_version():
    """The lock's pins == the versions actually resolved in this (green) interpreter. This is the
    verify-before-claim guard: the provenance block can never again assert a state no test checked."""
    mismatches = []
    for pkg, pinned in _pins().items():
        try:
            installed = md.version(pkg)            # importlib normalizes the name (PyYAML/pyyaml)
        except md.PackageNotFoundError:
            mismatches.append(f"{pkg}: pinned=={pinned} but NOT INSTALLED "
                              f"(run in the canonical .[dev,crypto-assurance] env, installed -c constraints.txt)")
            continue
        if installed != pinned:
            mismatches.append(f"{pkg}: pinned=={pinned} but installed=={installed}")
    assert not mismatches, (
        "constraints.txt is out of sync with the resolved env — regenerate from a fresh green venv "
        "(pip freeze), do not hand-edit:\n  " + "\n  ".join(mismatches))


def test_cryptography_clears_the_cve_floor():
    """Audit 2026-06-16 MED (baseline-#12): the now-load-bearing lock must clear the CVE-safe floor."""
    pins = _pins()
    major, minor, patch = (int(x) for x in pins["cryptography"].split(".")[:3])
    assert (major, minor, patch) >= (46, 0, 7), \
        f"cryptography pin {pins['cryptography']} is below the CVE-safe floor 46.0.7"
