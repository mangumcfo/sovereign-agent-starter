#!/usr/bin/env bash
# vendor_wheels.sh — pre-fetch the node's pinned runtime wheels so a COLD machine installs with NO pip index.
#
# The hotspot test (AA_DAY1_NODE_SOVEREIGNTY_PATH §3, P0-2): a second laptop on a phone hotspot, no pip
# index reachable, must still stand the node up. The crypto substrate (breathline_primitives) is already
# vendored in-tree; the one remaining network dependency is `pip install -e .` resolving flask + pyyaml
# (+ transitives) from PyPI. This script downloads those ONCE on a networked machine into vendor/wheels/,
# hash-pinned via constraints.txt, so the cold machine can:  pip install --no-index --find-links vendor/wheels
#
# RUN THIS on a networked machine, then carry the repo (with vendor/wheels/ populated) to the cold one.
# stand_up_node.sh --offline auto-uses vendor/wheels/ if present.
#
# Usage:  scripts/vendor_wheels.sh            # core runtime (flask + pyyaml + transitives)
#         scripts/vendor_wheels.sh --dev      # also the dev/crypto-assurance extras (pytest, cryptography)
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"
DEST="$REPO/vendor/wheels"
EXTRAS=""
[ "${1:-}" = "--dev" ] && EXTRAS="[crypto-assurance,dev]"

command -v pip >/dev/null 2>&1 || { echo "✗ pip not found — run this on a networked machine with pip."; exit 2; }
[ -f "$REPO/constraints.txt" ] || { echo "✗ constraints.txt missing — cannot hash-pin the vendored set."; exit 2; }

mkdir -p "$DEST"
echo "== vendoring pinned wheels into $DEST =="

# constraints.txt carries pip --hash= lines. Passing it to `pip download` flips pip into global
# require-hashes mode, which then demands a hash for EVERY transitive too (flask pulls werkzeug/jinja2/…,
# which the lock does not hash) and for the editable project dir (a directory cannot be hashed) — both
# hard-error. So we vendor with a VERSION-ONLY view of the lock: the resolve is still pinned to the locked
# majors (PyYAML 6 / Flask 3.1.x / cryptography / pytest), and byte-provenance comes from the wheels you
# CARRY (--no-index --find-links), not from PyPI hashes on the cold side.
VC="$(mktemp)"; trap 'rm -f "$VC"' EXIT
grep -oE '^[A-Za-z0-9_.-]+==[0-9][^ ]*' "$REPO/constraints.txt" > "$VC"
echo "   version pins (from constraints.txt, hashes stripped for the resolve):"; sed 's/^/     /' "$VC"

# Runtime closure = the project's own deps + the BUILD backend (a modern venv ships no setuptools, so an
# editable `-e .` install needs setuptools/wheel present offline too; pyproject pins setuptools>=68,<81).
REQS=(Flask PyYAML "setuptools>=68,<81" wheel)
[ -n "$EXTRAS" ] && REQS+=(pytest cryptography)
pip download "${REQS[@]}" -c "$VC" --dest "$DEST" --only-binary=:all: 2>/dev/null \
  || { echo "  (a dep was sdist-only; retrying allowing sdists — still fully offline-installable)";
       pip download "${REQS[@]}" -c "$VC" --dest "$DEST"; }

COUNT=$(find "$DEST" -maxdepth 1 \( -name '*.whl' -o -name '*.tar.gz' \) | wc -l | tr -d ' ')
echo "== done: $COUNT distribution file(s) in $DEST =="
echo "   platform: $(python3 -c 'import platform;print(platform.platform())')"
echo "   python  : $(python3 -c 'import sys;print(sys.version.split()[0])')"
echo
echo "COLD-MACHINE install (no index needed), from the repo root:"
echo "   python3 -m venv .venv && . .venv/bin/activate"
echo "   pip install --no-index --find-links vendor/wheels -e ."
echo "   (versions are the ones you vendored = the locked resolve; bytes come from the carried wheels,"
echo "    not PyPI. Do NOT add -c constraints.txt here: its --hash lines flip pip to require-hashes,"
echo "    which the unhashed transitives cannot satisfy.)"
echo "or simply:  scripts/stand_up_node.sh --offline"
echo
echo "NOTE: wheels are platform+python-specific. Vendor on a machine matching the cold one"
echo "      (same OS/arch, same Python minor). vendor/wheels/*.whl are .gitignored — carry them"
echo "      in the release tarball, not the git history."
