#!/usr/bin/env python3
"""
Extrusion Validation Harness — the rigorous, repeatable, end-to-end book↔code gate.

Goes beyond /coherence (which only checks passage-present + hash + code-present): this **executes the tests**,
computes **Merkle roots** over the registry + cited code modules (object-model integrity), checks
**distribution readiness**, and emits a report + a CI exit code. This is what proves "code cannot silently
drift from the book."

Per registry anchor (memory/coherence_registry.json):
  passage∈book · hash_ok · code_present · tests_present · **pytest(tests_file) PASS** · → status:
    VALIDATED        all green incl. tests pass
    PINNED_UNTESTED  passage+hash+code ok but no tests (or tests not runnable)
    DRIFT            passage missing / hash mismatch / code missing
    FAIL             tests ran and FAILED
Per capability (memory/coherence_capabilities.json): Present must cite a present file; Partial/Missing = gaps.
Merkle: roots over (a) registry entries, (b) the set of cited code modules, (c) capability ledger; compared to
  a stored baseline (memory/extrusion_validation_baseline.json) → flags structural change.
Distribution: per title (series_roadmap.yaml) — KDP (publishing_state/asin), social, federation (honest ◌).

Exit code: 0 only if no DRIFT and no FAIL (untested = warning, surfaced loudly). CI-able; run at each volume handoff.

  python3 scripts/extrusion_validate.py                 # validate + write report
  python3 scripts/extrusion_validate.py --update-baseline  # (re)write the Merkle baseline (after a sealed change)
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / "memory" / "coherence_registry.json"
CAPS = REPO / "memory" / "coherence_capabilities.json"
BASELINE = REPO / "memory" / "extrusion_validation_baseline.json"
ROADMAP = REPO / "artifacts" / "series_roadmap.yaml"
REPORT = REPO / "artifacts" / "Extrusion_Validation_Report_2026-06-07.md"
STATE = REPO / "memory" / "extrusion_validation_state.json"   # cheap state the Atrium /coherence/rollup reads


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _merkle(leaves: list[str]) -> str:
    """Binary Merkle root over leaf hex-hashes (sorted for determinism). '' if empty."""
    if not leaves:
        return ""
    level = sorted(leaves)
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            a = level[i]
            b = level[i + 1] if i + 1 < len(level) else a
            nxt.append(_sha((a + b).encode()))
        level = nxt
    return level[0]


def _run_pytest(tests_file: str) -> tuple[str, str]:
    """Return (result, detail). result ∈ pass|fail|absent|error."""
    if not tests_file:
        return "absent", "no tests_file declared"
    p = REPO / tests_file
    if not p.is_file():
        return "absent", f"tests_file missing: {tests_file}"
    try:
        env = {**os.environ, "PYTHONPATH": str(REPO / "src")}  # package lives under src/ (not installed)
        r = subprocess.run([sys.executable, "-m", "pytest", str(p), "-q", "--no-header", "-p", "no:cacheprovider"],
                           cwd=str(REPO), capture_output=True, text=True, timeout=300, env=env)
        tail = (r.stdout or r.stderr).strip().splitlines()[-1:] or [""]
        return ("pass" if r.returncode == 0 else "fail"), tail[0][:120]
    except Exception as e:  # noqa
        return "error", str(e)[:120]


def _book_id(e: dict) -> str:
    """book_id from the entry, else derived from the book_file path (.../<book_id>/vN.N/...)."""
    if e.get("book_id"):
        return e["book_id"]
    import re
    parts = Path(e.get("book_file", "")).parts
    for i, seg in enumerate(parts):
        if i and re.match(r"^v\d", seg):
            return parts[i - 1]
    return "?"


def validate():
    reg = json.loads(REGISTRY.read_text()) if REGISTRY.is_file() else {"extrusions": []}
    exts = reg.get("extrusions", [])
    results, code_files, reg_leaves = [], set(), []
    pytest_cache: dict[str, tuple[str, str]] = {}
    for e in exts:
        bf, passage = e.get("book_file", ""), e.get("passage", "")
        book_present = bool(bf) and os.path.isfile(bf) and passage in open(bf, encoding="utf-8").read()
        hash_ok = _sha(passage.encode())[:12] == e.get("passage_hash", "")
        code_present = os.path.isfile(REPO / e.get("code_file", ""))
        tf = e.get("tests_file", "")
        if tf not in pytest_cache:
            pytest_cache[tf] = _run_pytest(tf)
        test_result, test_detail = pytest_cache[tf]
        if not (book_present and hash_ok and code_present):
            status = "DRIFT"
        elif test_result == "fail":
            status = "FAIL"
        elif test_result == "pass":
            status = "VALIDATED"
        else:
            status = "PINNED_UNTESTED"
        results.append({"book_id": _book_id(e), "book": e.get("book", ""),
                        "capability": e.get("capability", ""), "status": status,
                        "book_present": book_present, "hash_ok": hash_ok, "code_present": code_present,
                        "code_file": e.get("code_file", ""), "tests_file": tf,
                        "test_result": test_result, "test_detail": test_detail})
        if e.get("code_file"):
            code_files.add(e["code_file"])
        reg_leaves.append(_sha(json.dumps(e, sort_keys=True).encode()))
    # capability honesty
    caps = (json.loads(CAPS.read_text()).get("capabilities", []) if CAPS.is_file() else [])
    cap_bad = [c for c in caps if c.get("review_status") == "present" and c.get("code_file")
               and not os.path.isfile(REPO / c["code_file"])]
    # Merkle / object-model integrity
    module_hashes = {cf: _sha((REPO / cf).read_bytes()) for cf in sorted(code_files) if os.path.isfile(REPO / cf)}
    roots = {
        "registry_root": _merkle(reg_leaves),
        "modules_root": _merkle(list(module_hashes.values())),
        "capabilities_root": _sha(json.dumps(caps, sort_keys=True).encode()) if caps else "",
    }
    base = json.loads(BASELINE.read_text()) if BASELINE.is_file() else {}
    drift_roots = {k: {"baseline": base.get("roots", {}).get(k, ""), "now": v}
                   for k, v in roots.items() if base.get("roots") and base["roots"].get(k) not in ("", v)}
    return results, cap_bad, roots, module_hashes, drift_roots


def distribution():
    """Per-title propagation readiness from the roadmap (honest ◌ for untracked channels)."""
    try:
        import yaml
        d = yaml.safe_load(ROADMAP.read_text()) or {}
    except Exception:  # noqa
        return []
    rows = []
    for s in d.get("series", []):
        for t in (s.get("titles") or []):
            ps = str(t.get("publishing_state") or t.get("stage") or "").lower()
            kdp = "published" if ("publish" in ps or t.get("asin")) else ("review" if "review" in ps else "—")
            rows.append({"book": t.get("book_id") or t.get("title"), "series": s.get("series_number"),
                         "kdp": kdp, "social": "◌", "federation": "◌"})
    return rows


def main(argv):
    results, cap_bad, roots, module_hashes, drift_roots = validate()
    n = {k: sum(1 for r in results if r["status"] == k) for k in ("VALIDATED", "PINNED_UNTESTED", "DRIFT", "FAIL")}
    if "--update-baseline" in argv:
        BASELINE.write_text(json.dumps({"roots": roots, "modules": module_hashes}, indent=1))
        print(f"✓ baseline written: registry_root {roots['registry_root'][:16]} · {len(module_hashes)} modules")
        return 0
    dist = distribution()
    lines = ["# Extrusion Validation Report — 2026-06-07", "",
             f"**Anchors:** {len(results)} · ✅ VALIDATED {n['VALIDATED']} · ◌ PINNED_UNTESTED {n['PINNED_UNTESTED']} "
             f"· ⚠ DRIFT {n['DRIFT']} · ✗ FAIL {n['FAIL']}", "",
             "## Object-model integrity (Merkle)",
             f"- registry_root: `{roots['registry_root'][:24]}`",
             f"- modules_root: `{roots['modules_root'][:24]}` ({len(module_hashes)} cited code modules)",
             f"- capabilities_root: `{roots['capabilities_root'][:24]}`",
             (f"- ⚠ ROOT DRIFT vs baseline: {list(drift_roots)}" if drift_roots else "- baseline: "
              + ("match ✓" if BASELINE.is_file() else "none yet (run --update-baseline after a sealed change)")), "",
             "## Anchors (by status)"]
    for st in ("DRIFT", "FAIL", "PINNED_UNTESTED", "VALIDATED"):
        rs = [r for r in results if r["status"] == st]
        if not rs:
            continue
        lines.append(f"### {st} ({len(rs)})")
        for r in rs:
            lines.append(f"- **{r['book_id']}** · {r['capability']} → `{r['code_file'].split('/')[-1]}`"
                         + (f" · tests {r['test_result']}" if r["tests_file"] else " · (no tests)"))
        lines.append("")
    if cap_bad:
        lines += ["## ⚠ Capability honesty failures", *[f"- {c['book_id']} · {c['capability']} cites missing {c['code_file']}" for c in cap_bad], ""]
    lines += ["## Distribution readiness (per title)", "", "| Book | Series | KDP | Social | Federation |",
              "|---|---|---|---|---|"]
    for d in dist:
        lines.append(f"| {d['book']} | {d['series'] or '—'} | {d['kdp']} | {d['social']} | {d['federation']} |")
    lines += ["", "∞Δ∞ tests + Merkle + distribution — the rigorous end-to-end gate. ∞Δ∞"]
    REPORT.write_text("\n".join(lines))
    # Cheap state for the Atrium monitor (/coherence/rollup reads this — no pytest at request time).
    per_book = {}
    for r in results:
        b = per_book.setdefault(r["book_id"] or "?", {"validated": 0, "untested": 0, "drift": 0, "fail": 0})
        b[r["status"].lower().replace("pinned_untested", "untested")] += 1
    # Crypto assurance (daily mathematics) folded INTO the extrusion harness state + gate — G directive
    # 2026-06-12: "wire the nightly vector suite + seal tripwire into the extrusion validation harness."
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import crypto_assurance as _CA  # noqa: PLC0415
        crypto = _CA.assess(mint_card=True)
    except Exception as _e:  # noqa: BLE001
        crypto = {"status": "ERROR", "reasons": [str(_e)]}
    crypto_fail = 0 if crypto.get("status") == "GREEN" else 1
    STATE.write_text(json.dumps({
        "counts": n,
        "gate_pass": (n["DRIFT"] + n["FAIL"] + len(cap_bad) + len(drift_roots) + crypto_fail) == 0,
        "roots": {k: v[:16] for k, v in roots.items()}, "root_drift": list(drift_roots),
        "crypto_assurance": crypto,
        "per_book": per_book,
        "anchors": [{"book_id": r["book_id"], "capability": r["capability"], "status": r["status"],
                     "test_result": r["test_result"], "tests_file": r["tests_file"]} for r in results],
    }, indent=1))
    print(f"✓ report → {REPORT.name}")
    print(f"  VALIDATED {n['VALIDATED']} · UNTESTED {n['PINNED_UNTESTED']} · DRIFT {n['DRIFT']} · FAIL {n['FAIL']}")
    print(f"  registry_root {roots['registry_root'][:16]} · modules {len(module_hashes)}"
          + (f" · ⚠ ROOT DRIFT {list(drift_roots)}" if drift_roots else ""))
    print(f"  crypto_assurance {crypto.get('status')} · vectors "
          f"{crypto.get('vectors',{}).get('n_pass','?')}/{crypto.get('vectors',{}).get('n_total','?')} · "
          f"merkle {(crypto.get('merkle_root') or '')[:16]}…")
    gate_fail = n["DRIFT"] + n["FAIL"] + len(cap_bad) + len(drift_roots) + crypto_fail
    print(("⛔ GATE: FAIL — " if gate_fail else "✓ GATE: PASS — ") + f"{gate_fail} blocking; {n['PINNED_UNTESTED']} untested (warning)")
    return 1 if gate_fail else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
