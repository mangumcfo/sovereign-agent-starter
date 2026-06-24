#!/usr/bin/env python3
"""enforcement_claim_lint.py — mechanical backstop for the `exists_is_not_wired` standard (KM Call 3, 2026-06-24).

WHY: twice now a board passed a manuscript "green" while a RECEIPT claimed a policy/gate/scope was ENFORCED /
runs-today when the code only LOADS the struct (the enforcement call is never in a live execution path):
  - S3-V2 SOD "enforced on the verb" (approve() never compares approver to originator)
  - S4-V2 "YAML config enforced at the write" (run_policy_compliance_check never called; get_active_policy()=None)
Both were caught by GB's independent trace, not the board. This lint is the mechanical gate so the catch does NOT
depend on a reviewer remembering: it scans every RECEIPT RUNS-TODAY claim, and any ENFORCEMENT assertion must EITHER
cite a live code trace (a `*.py` ref / "code-traced" / "wired") OR it is flagged. Known-unwired phrasings are HARD-denied.

The lint does NOT (and cannot) prove a cited path actually enforces — that stays the board + GB trace's job. It
guarantees that an *un-cited* or *known-bad* enforcement claim can never silently ship. exists != wired.

Usage:
  python3 scripts/enforcement_claim_lint.py <manuscript.md>     # exit 0 clean / 1 flagged
  (importable: lint_text(text) -> {"flags": [...], "pass": bool})
"""
import re
import sys
from pathlib import Path

# An enforcement CLAIM: the runs-today line asserts the system actively blocks/refuses/enforces a rule at execution.
ENFORCE_PAT = re.compile(
    r"\b("
    r"enforced|enforces|enforcing|enforcement"
    r"|blocks? at the write|refus\w+ at the write|reject\w+ at the write"
    r"|consult\w* (?:it )?on every write|consult\w* a (?:loaded )?policy"
    r"|auto-?block|automatic\w* (?:block|refus|enforc)"
    r"|isolation (?:is )?(?:enforced|live)"
    r")\b", re.I)

# Evidence the claim is WIRED: a code-path citation in the same runs-today block.
TRACE_PAT = re.compile(r"(\b\w+\.py\b|code[- ]traced|\bwired\b|role_binder|ledger\.py|PermissionError|raises?\b)", re.I)

# Known-UNWIRED phrasings caught as overclaims — HARD deny in a runs-today context (regardless of citation),
# because these exact claims were proven false against the live code. Use the qualified form instead.
DENY_PHRASES = [
    r"config enforced at the write",
    r"YAML (?:config )?enforced at the write",
    r"enforced at the write",
    r"enforced at every write",
    r"enforced where the substrate writes",
    r"consults? (?:it )?on every write",
    r"principal isolation are live",
    r"isolation is enforced",
    r"isolation enforced (?:underneath|at)",
]
DENY_PAT = re.compile("|".join(DENY_PHRASES), re.I)

# A runs-today claim that names ONLY a loader/struct as its "enforcement" evidence is the trap — these tokens
# are LOAD/VERSION/ATTEST, never enforcement. If an enforcement claim cites only these, it is not wired.
LOADER_ONLY = re.compile(r"policy_loader|get_active_policy|_loaded_polic|loads?/versions?|merkle.?attest", re.I)

# Phrases that signal the claim is HONESTLY scoped (the enforcement is marked forward) — suppress the flag.
DESIGNED_NEAR = re.compile(r"DESIGNED-?TOWARD|designed.toward|is the (?:token-typed )?build|this series wires|exists ?!= ?wired", re.I)


def _receipt_runs_today_blocks(text: str):
    """Yield (label, runs_today_text, full_receipt_text) for each RECEIPT fenced block's RUNS-TODAY claim."""
    # RECEIPT fenced blocks: a ```...``` region that contains "RUNS TODAY:"
    for m in re.finditer(r"```[a-z]*\s*\n(.*?)\n\s*```", text, re.S):
        block = m.group(1)
        if "RUNS TODAY" not in block.upper():
            continue
        # extract the RUNS TODAY: ... up to the next field label
        rt = re.search(r"RUNS[ _]TODAY:\s*(.*?)(?:\n\s*>?\s*(?:DESIGNED-?TOWARD|VERIFY|CLAIM)\b|$)", block, re.S | re.I)
        runs = rt.group(1) if rt else ""
        label_m = re.search(r"(RECEIPT[^\n`]*|Ch\.?\s*\d+|Chapter\s*\d+)", block, re.I)
        yield (label_m.group(1).strip() if label_m else "RECEIPT", runs, block)


def _seeit_runs_today(text: str):
    """Yield (label, runs_today_text) for See-It-Work 'Runs-today:' inline markers."""
    for m in re.finditer(r"Runs-?today:\s*([^.)\n]*)", text, re.I):
        yield ("See-It-Work step", m.group(1))


def lint_text(text: str) -> dict:
    flags = []
    # RECEIPT blocks are markdown blockquotes (each line prefixed `> `); strip the quote marker so the ``` fence
    # regex sees a clean fenced block. (Without this the receipts are silently skipped — a false PASS.)
    dequoted = re.sub(r"(?m)^[ \t]*>[ \t]?", "", text)
    units = list(_receipt_runs_today_blocks(dequoted)) + [(l, r, r) for (l, r) in _seeit_runs_today(text)]
    for label, runs, full in units:
        if not runs.strip():
            continue
        runs_one = re.sub(r"\s+", " ", runs)
        # 1) HARD deny: a known-unwired phrase in a runs-today claim, unless the SAME line scopes it designed-toward.
        dm = DENY_PAT.search(runs_one)
        if dm and not DESIGNED_NEAR.search(runs_one):
            flags.append({"sev": "HARD", "where": label, "hit": dm.group(0),
                          "why": "known-unwired enforcement phrasing in a RUNS-TODAY claim (caught before); "
                                 "qualify to loaded/versioned/attested + human-gate, enforcement DESIGNED-TOWARD",
                          "text": runs_one[:200]})
            continue
        # 2) An enforcement claim must cite a live trace; if it cites only a loader, that is the trap.
        if ENFORCE_PAT.search(runs_one) and not DESIGNED_NEAR.search(runs_one):
            cites_trace = bool(TRACE_PAT.search(runs_one))
            loader_only = bool(LOADER_ONLY.search(runs_one)) and not re.search(r"role_binder|ledger\.py|PermissionError", runs_one, re.I)
            if not cites_trace:
                flags.append({"sev": "FLAG", "where": label, "hit": ENFORCE_PAT.search(runs_one).group(0),
                              "why": "enforcement claimed RUNS-TODAY with NO live code trace — cite the enforcement "
                                     "call (file:line) or mark DESIGNED-TOWARD", "text": runs_one[:200]})
            elif loader_only:
                flags.append({"sev": "HARD", "where": label, "hit": "loader-only",
                              "why": "enforcement claim cites only a LOADER (loads/versions/attests, never enforces) — "
                                     "the enforcement call is absent; mark DESIGNED-TOWARD", "text": runs_one[:200]})
    hard = [f for f in flags if f["sev"] == "HARD"]
    return {"flags": flags, "hard": hard, "pass": len(hard) == 0, "n_units": len(units)}


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: enforcement_claim_lint.py <manuscript.md>")
        return 2
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"✗ not found: {p}")
        return 2
    res = lint_text(p.read_text(encoding="utf-8"))
    if not res["flags"]:
        print(f"✅ enforcement-claim lint CLEAN — {res['n_units']} runs-today claims scanned, 0 flags ({p.name})")
        return 0
    flag = "⛔ ENFORCEMENT-CLAIM LINT" if res["hard"] else "⚠ enforcement-claim lint (advisory flags)"
    print(f"{flag} — {p.name}: {len(res['hard'])} HARD, {len(res['flags']) - len(res['hard'])} advisory")
    for f in res["flags"]:
        print(f"  [{f['sev']}] {f['where']} · hit={f['hit']!r}\n        {f['why']}\n        > {f['text']}")
    return 1 if res["hard"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
