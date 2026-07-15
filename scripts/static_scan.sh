#!/usr/bin/env bash
# Standing static-analysis pass (audit 2026-06-16 #8/M1): ruff + vulture + coverage.
# REPORT-ONLY — never --fix, never delete. Feeds the candidates-not-delete 3-bucket triage; removals/fixes
# are a separate the operator-gated commit. Reproducible: same code -> same candidate set (the upgrade over an LLM
# sweep). Run from repo root with the project's python (BREATHLINE_SEALED_ROOT set for the coverage step).
#   PYTHON=/path/to/venv/bin/python scripts/static_scan.sh
set -uo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"

echo "== ruff: dead (F) + complexity (C90 ≤10, §5) + bare-except (E722) + ambiguous (E741) =="
"$PY" -m ruff check src scripts --statistics || true
echo
echo "== vulture: dead symbols (min-confidence 80, whitelisted) =="
"$PY" -m vulture src scripts analysis/vulture_whitelist.py --min-confidence 80 || true
echo
echo "== coverage: use-evidence (never-executed code under the suite) =="
"$PY" -m coverage run --source=src,scripts -m pytest -q >/dev/null 2>&1 || true
"$PY" -m coverage report --sort=cover 2>/dev/null | awk 'NR==1 || $4+0<100' | head -30 || true
echo
echo "Report-only. Removals/fixes = a separate the operator-gated commit (re-run 279 suite + ledger equivalence snapshot)."
