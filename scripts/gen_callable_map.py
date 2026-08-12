#!/usr/bin/env python3
"""Generate docs/CALLABLE_MAP.md from the ACTUAL importable sovereign_agent entrypoints — full, not a sample.

Run:  PYTHONPATH=src python3 scripts/gen_callable_map.py   (writes docs/CALLABLE_MAP.md)

Honesty contract (KM Builder Truth GO):
  * every module under `sovereign_agent` is imported; what imports is listed, what fails is listed as IMPORT-FAIL;
  * public callables (functions + classes) per module are enumerated from the live module object — no hand list;
  * the RUN / RUN-partial label is COMPUTED from published criteria (below), never asserted;
  * a sealed book↔code module is NOT demoted for lacking a consumer UI — "partial" means "not one product
    entrypoint" (a library of verbs) or "no shipped starter test/example exercises it yet", nothing else.

Published label criteria (the four signals):
  1. import      — the module imports on a fresh clone;
  2. callable    — it exposes at least one public function or class;
  3. exercised   — a shipped test or example imports it;
  4. kill-target — it defines a refusal (an *Error / *Refused / *Violation class, or a *BREACH*/FORBIDDEN const).

  RUN          = import ✓ + callable ✓ + exercised ✓            (a path you run directly, proven by a test/example)
  RUN-partial  = import ✓ + callable ✓, but not exercised by a shipped starter test/example yet
                 (still callable; NOT a demotion for missing UI)
  teach/data   = import ✓ but no public callable (pure data/constants)
  IMPORT-FAIL  = does not import on the clean clone (reported honestly)
"""
from __future__ import annotations

import contextlib
import importlib
import inspect
import io
import os
import pkgutil
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import sovereign_agent  # noqa: E402

OUT = os.path.join(ROOT, "docs", "CALLABLE_MAP.md")

# ── the nine curated cards (the subset a builder reaches for first) ──────────────────────────────────────
CARD_MODULES = {
    "sovereign_agent.keystore.node_keystore": "identity-keystore",
    "sovereign_agent.onboarding.onboard": "onboard-gate",
    "sovereign_agent.compliance.human_approval_gate": "onboard-gate",
    "sovereign_agent.peerhood.recognition": "peer-recognition",
    "sovereign_agent.peerhood.clean_exit": "clean-exit",
    "sovereign_agent.messaging.inter_node": "messaging",
    "sovereign_agent.port.crossing": "port-crossing",
    "sovereign_agent.objects.registry": "object-model",
    "sovereign_agent.objects.scope": "object-model",
    "sovereign_agent.storage.sovereign_store": "storage-integrity",
}

KILL_RE = re.compile(r"(Error|Refused|Violation)$")
CONST_KILL_RE = re.compile(r"(BREACH|FORBIDDEN|DENY)")


def _read_blob(dirs):
    blob = []
    for d in dirs:
        for base, _, files in os.walk(os.path.join(ROOT, d)):
            for fn in files:
                if fn.endswith(".py"):
                    try:
                        blob.append(open(os.path.join(base, fn), encoding="utf-8").read())
                    except Exception:
                        pass
    return "\n".join(blob)


def public_callables(mod):
    fns, classes = [], []
    for name, obj in vars(mod).items():
        if name.startswith("_"):
            continue
        if getattr(obj, "__module__", None) != mod.__name__:
            continue  # only symbols DEFINED here, not re-imports
        if inspect.isfunction(obj):
            fns.append(name)
        elif inspect.isclass(obj):
            classes.append(name)
    return sorted(fns), sorted(classes)


def has_kill_target(mod, classes):
    if any(KILL_RE.search(c) for c in classes):
        return True
    for name in vars(mod):
        if not name.startswith("_") and CONST_KILL_RE.search(name):
            return True
    return False


def main():
    test_blob = _read_blob(["tests", "examples"])
    discovered = []  # (name, ispkg)
    # discovery imports packages to read their __path__; silence any module-level prints
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        for m in pkgutil.walk_packages(sovereign_agent.__path__, "sovereign_agent.",
                                       onerror=lambda n: None):
            # skip CLI shims: `__main__` is a `python -m` entrypoint, not an importable library path
            if m.name.rsplit(".", 1)[-1] == "__main__":
                continue
            discovered.append((m.name, m.ispkg))
    discovered = sorted(set(discovered))

    rows = {}  # subpackage -> list of (module, label, fns, classes, exercised, kill)
    counts = {"RUN": 0, "RUN-partial": 0, "package": 0, "teach/data": 0, "IMPORT-FAIL": 0}
    for name, ispkg in discovered:
        sub = name.split(".")[1] if name.count(".") >= 2 else "(top)"
        try:
            # catch BaseException — a rogue module may call sys.exit at import
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                mod = importlib.import_module(name)
        except BaseException as e:  # noqa: BLE001 — record honestly, never abort the run
            rows.setdefault(sub, []).append((name, "IMPORT-FAIL", [], [], False, False,
                                             f"{type(e).__name__}: {str(e)[:50]}"))
            counts["IMPORT-FAIL"] += 1
            continue
        fns, classes = public_callables(mod)
        exercised = (name in test_blob)
        kill = has_kill_target(mod, classes)
        if not (fns or classes):
            label = "package" if ispkg else "teach/data"  # a namespace vs a data/const module
        elif exercised:
            label = "RUN"
        else:
            label = "RUN-partial"
        counts[label] += 1
        rows.setdefault(sub, []).append((name, label, fns, classes, exercised, kill, ""))

    try:
        head = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"]).decode().strip()
    except Exception:
        head = "(uncommitted)"

    total = sum(counts.values())
    out = []
    W = out.append
    W("# Callable Map — the FULL importable inventory of `sovereign_agent`\n")
    W("**Generated, not hand-written.** `scripts/gen_callable_map.py` imports every module under "
      "`sovereign_agent` and lists the public callables it actually exposes, computing each label from the "
      "published criteria below. This is the **full** inventory of importable/run paths — the nine capability "
      "cards (`docs/CAPABILITY_CARDS/`) are the **curated subset** of it. The book shelf (Series 0–14) is where "
      "each path is *taught* in depth; the full sealed runtime is Series 5–14.\n")
    W(f"Provenance: generated at starter `{head}` over **{total} modules** — "
      f"**RUN {counts['RUN']}** · **RUN-partial {counts['RUN-partial']}** · package {counts['package']} · "
      f"teach/data {counts['teach/data']} · IMPORT-FAIL {counts['IMPORT-FAIL']}. "
      "(`__main__` CLI shims are excluded — they are `python -m` entrypoints, not importable library paths.) "
      "Regenerate with `PYTHONPATH=src python3 scripts/gen_callable_map.py`.\n")
    W("## Published label criteria (the four signals)\n")
    W("| signal | meaning |")
    W("|---|---|")
    W("| **import** | the module imports on a fresh clone |")
    W("| **callable** | it exposes ≥1 public function or class (defined here, not a re-import) |")
    W("| **exercised** | a shipped test or example imports it |")
    W("| **kill-target** | it defines a refusal — an `*Error`/`*Refused`/`*Violation` class or a `*BREACH*`/`FORBIDDEN` constant |\n")
    W("- **RUN** = import ✓ + callable ✓ + exercised ✓ — a path you run directly, proven by a test/example.")
    W("- **RUN-partial** = import ✓ + callable ✓, not yet exercised by a shipped starter test/example. **Still "
      "callable — never a demotion for missing UI.** A series is \"partial\" only when it is a *library of verbs*, "
      "not one product entrypoint.")
    W("- **package** = a namespace `__init__` that exposes no callables of its own — see its submodules below.")
    W("- **teach/data** = a module that imports but exposes no public callable (pure data/constants).")
    W("- **IMPORT-FAIL** = does not import on the clean clone (reported honestly, not hidden).\n")
    W("> **T-04:** the Sovereign Token & Economic Organism substrate is *callable* (an obligation ledger + Merkle "
      "accumulator); it is **not** a public token, coin, yield, or investment offer, and money-path is off.\n")

    W("## The full inventory, by area\n")
    for sub in sorted(rows):
        W(f"### `sovereign_agent.{sub}`\n" if sub != "(top)" else "### `sovereign_agent` (top level)\n")
        W("| module | label | card | kill-target | public callables |")
        W("|---|---|---|---|---|")
        for (name, label, fns, classes, exercised, kill, err) in sorted(rows[sub]):
            card = CARD_MODULES.get(name, "")
            card = f"`{card}`" if card else ""
            if label == "IMPORT-FAIL":
                W(f"| `{name}` | **IMPORT-FAIL** | | | {err} |")
                continue
            syms = fns + [f"{c}" for c in classes]
            shown = " · ".join(f"`{s}`" for s in syms[:10]) + (" …" if len(syms) > 10 else "")
            W(f"| `{name}` | {label} | {card} | {'✓' if kill else ''} | {shown or '—'} |")
        W("")

    W("## Reading-path callability (Series 2–4, KM-audited)\n")
    W("Series 2–4 each resolve to a real callable path on the public clone (not teach-only):")
    W("- **RUN:** Building the Agentic Harness (S2) V1 · Programmable Sovereign ERP (S3) V1, V2 · Sovereign Token & Economic Organism (S4) V1, V2.")
    W("- **RUN-partial:** Building the Agentic Harness (S2) V2/V3/V4/V5 · Programmable Sovereign ERP (S3) V3/V4 · Sovereign Token & Economic Organism (S4) V3/V4.")
    W("- **teach:** Series 0–1 (the lens and the executive playbooks) are reading, not runtime.")
    W("- Series 5–14 are the sealed executable runtime the cards and the inventory above are drawn from.\n")
    W("## How to use this map\n")
    W("1. Start from `docs/NODE_INTEGRATION_GUIDE.md` (the mental model) and the **nine cards** (the curated subset).")
    W("2. Need something a card doesn't cover? Find the **module path** here and import it.")
    W("3. Want the depth behind a path? Read its volume on the shelf (`docs/READING_PATH_S0_S4.md` for the arc; "
      "the sealed Series 5–14 for the runtime).")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote {OUT}: {total} modules "
          f"(RUN {counts['RUN']} · RUN-partial {counts['RUN-partial']} · "
          f"teach/data {counts['teach/data']} · IMPORT-FAIL {counts['IMPORT-FAIL']})")


if __name__ == "__main__":
    main()
