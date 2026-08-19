#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""killgrep — the machine-checkable P6 gate. GREEN or RED, no soft-ship.

Run:  python apps/usn_erp_surface/killgrep.py
Exit: 0 = GREEN, 1 = RED (with every offending line printed)

P6 goes RED if the app introduces a second ledger store, a balance-custody field used as authority,
a filing / remittance path, or a Port crossing without an explicit UI sanction.

**Why this is an AST check and not a text grep.** This app's own refusal messages contain the words
`remit`, `file_return` and `escrow` — that is the guard text working, not a violation. A text grep
would go RED on the very code that enforces the law. So the hard checks read the *abstract syntax
tree* and look at what the code actually does: names it imports, functions it calls, attributes it
touches, names it binds. Prose is counted separately and reported, never failed on.

The checks:

  1. FORBIDDEN IMPORTS  — no second store (`sqlite3`, `shelve`, `dbm`, `pickle`, `tinydb`, …) and no
     HTTP client (`requests`, `httpx`, `urllib`, `aiohttp`), which would let a spine grow over
     :8421 or anywhere else.
  2. FORBIDDEN CALLS/NAMES — no `open_crossing`, `sanction_crossing`, `simulate_approval`,
     `simulate_denial`, and no statutory-act identifier (`file_return`, `remit`, `pay_tax`, …).
  3. NO APP-SIDE WRITES — the app calls `open()` in write/append mode nowhere. Every durable byte is
     written by a `sovereign_agent` module, through the node's own store.
  4. NO CUSTODY FIELD AS AUTHORITY — no identifier binding a balance/custody/escrow/float/netting
     name, which is how a money-path would first appear.
  5. UI IS SAME-ORIGIN — every `fetch` in the page targets a relative `/api/...` path; no external
     host, no CDN, no telemetry beacon.
  6. THE APP OWNS NO STORE — `node_binding` names only the node's own store classes
     (`ObjectRegistry`, `ObligationLedger`).
  7. NO OUT-OF-SCOPE LEDGER VERB — no `repair_chain` (which rewrites the append-only chain) and no
     `reopen`. The scope boundary is machine-checked, not remembered.
  8. NO REACH PAST THE LEDGER'S PUBLIC METHODS — no `_append` / `_entries` / `_get` / `_is_approved`
     and friends. Those public methods are where AH-1, the evidence floor and the veto and
     attestation guards actually live; going around them would write entries no guard ever saw.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from typing import Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
PY_FILES = ["node_binding.py", "server.py"]
UI_FILE = "ui.html"

FORBIDDEN_IMPORTS = {
    # a second ledger / app-side store
    "sqlite3", "shelve", "dbm", "pickle", "cPickle", "tinydb", "sqlalchemy", "psycopg2",
    "pymongo", "redis", "lmdb", "plyvel", "duckdb",
    # any HTTP client — a spine over :8421, or any egress at all
    "requests", "httpx", "urllib", "urllib3", "aiohttp", "http.client", "socket", "websockets",
}

#: Identifiers that would mean the app performs a statutory act, crosses the Port, or fakes a human.
FORBIDDEN_NAMES = {
    # Port — v0 never crosses
    "open_crossing", "sanction_crossing", "authorize_crossing",
    # never fake a human disposition
    "simulate_approval", "simulate_denial",
    # statutory acts — the principal's, never the node's and never the app's
    "file_return", "efile", "e_file", "submit_return", "submitted_return", "return_filed",
    "pay_tax", "tax_paid", "remit", "remittance", "withhold_and_remit", "settle_tax",
    "form_entity", "register_entity", "power_of_attorney", "authorized_agent",
    # money movement
    "transfer_funds", "move_funds", "hold_funds", "held_funds", "disburse", "settle_payment",
    # invoice collection / receipt of payment — this vertical bills as a RECORD; collection is OUT.
    # A money-path would first appear as one of these, so they are machine-checked out.
    "collect_payment", "collect_receivable", "receive_payment", "apply_payment", "record_payment",
    "capture_payment", "process_payment", "settle_invoice", "pay_invoice", "mark_paid", "charge_card",
    # silent-clear verbs — the exception queue is read-only; a deviation leaves it only through a
    # governed act on the panels that own the verbs. A dismiss path is how no-silent-clear dies.
    "dismiss_exception", "clear_exception", "suppress_exception", "ignore_exception", "silent_clear",
    "auto_clear", "bulk_dismiss",
    # tie-out tampering — a drill-down that "fixes" a number instead of reporting it is how the
    # equality proof dies. Plugging a difference is the accounting sin these names would commit.
    "plug_difference", "force_balance", "adjust_total", "override_total", "fudge", "plug_gap",
}

#: Identifiers that would make the app hold value as authority rather than record it as attribution.
CUSTODY_NAMES = {
    "balance", "balances", "custody", "custodied", "escrow", "wallet", "float_", "netting",
    "net_position", "pool_balance", "clearing_balance", "ledger_balance", "running_balance",
    "account_balance",
}

#: Ledger verbs outside this version's scope. `repair_chain` is the sharp one — it rewrites the
#: append-only chain, which is precisely the authority an operator surface must never hold. `reopen`
#: is simply not in scope; forbidding it here is how the scope boundary stays machine-checked rather
#: than remembered.
OUT_OF_SCOPE_LEDGER_VERBS = {"repair_chain", "reopen"}

#: The ledger's private internals. Reaching past its public methods would mean writing entries the
#: ledger's own guards never saw — AH-1, the evidence floor, the veto and attestation rules all live
#: in those public methods.
LEDGER_PRIVATES = {"_append", "_entries", "_get", "_require", "_is_approved", "_is_closed"}

#: Whole node modules this app must never reach into. Importing one is the violation, whatever it
#: then does with it.
FORBIDDEN_MODULES = {
    "sovereign_agent.port.crossing",       # the Port — v0 never crosses
    "sovereign_agent.storage.sovereign_store",
    "sovereign_agent.role_binder",
    "sovereign_agent.node_api",            # the :8421 surface — this app is library-direct
}

#: Store classes the app is allowed to name at all. Both belong to the node.
ALLOWED_STORE_CLASSES = {"ObjectRegistry", "ObligationLedger"}


class Finding(Tuple[str, int, str, str]):
    pass


def _findings_to_str(f: List[Tuple[str, int, str, str]]) -> str:
    return "\n".join(f"      {path}:{line}  [{rule}] {detail}" for path, line, rule, detail in f)


# --------------------------------------------------------------------------------------------------
# AST walkers
# --------------------------------------------------------------------------------------------------

def _imported_names(tree: ast.AST) -> List[Tuple[int, str]]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.append((node.lineno, a.name.split(".")[0]))
                out.append((node.lineno, a.name))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            out.append((node.lineno, mod.split(".")[0]))
            out.append((node.lineno, mod))
            for a in node.names:
                out.append((node.lineno, a.name))
    return out


def _code_identifiers(tree: ast.AST) -> List[Tuple[int, str]]:
    """Every identifier the code actually uses: names, attributes, call targets, bindings, kwargs.

    Deliberately excludes `ast.Constant` — a string literal is prose, and this app's prose says the
    word `remit` precisely to refuse it.
    """
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            out.append((node.lineno, node.id))
        elif isinstance(node, ast.Attribute):
            out.append((node.lineno, node.attr))
        elif isinstance(node, ast.arg):
            out.append((node.lineno, node.arg))
        elif isinstance(node, ast.keyword) and node.arg:
            out.append((node.lineno, node.arg))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append((node.lineno, node.name))
    return out


def _write_mode_opens(tree: ast.AST) -> List[Tuple[int, str]]:
    """`open(...)` in a write or append mode, anywhere in the app."""
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "open"):
            continue
        mode = ""
        if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
            mode = str(node.args[1].value)
        for kw in node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                mode = str(kw.value.value)
        if any(ch in mode for ch in ("w", "a", "x", "+")):
            out.append((node.lineno, f"open(..., {mode!r})"))
    return out


# --------------------------------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------------------------------

def run() -> int:
    reds: List[Tuple[str, int, str, str]] = []
    notes: List[str] = []
    prose: Dict[str, int] = {}

    trees: Dict[str, ast.AST] = {}
    sources: Dict[str, str] = {}
    for name in PY_FILES:
        path = os.path.join(HERE, name)
        with open(path, "r", encoding="utf-8") as fh:
            src = fh.read()
        sources[name] = src
        trees[name] = ast.parse(src, filename=path)

    # 1 — forbidden imports
    for name, tree in trees.items():
        for lineno, mod in _imported_names(tree):
            if mod in FORBIDDEN_IMPORTS:
                reds.append((name, lineno, "second-store-or-egress",
                             f"imports '{mod}' — the app must own no store and open no socket"))
            if mod in FORBIDDEN_MODULES:
                reds.append((name, lineno, "statutory-act-or-crossing",
                             f"imports '{mod}' — this vertical does not reach that surface at all"))

    # 2b — out-of-scope ledger verbs and private ledger internals
    for name, tree in trees.items():
        for lineno, ident in list(_code_identifiers(tree)) + list(_imported_names(tree)):
            if ident in OUT_OF_SCOPE_LEDGER_VERBS:
                reds.append((name, lineno, "out-of-scope-ledger-verb",
                             f"'{ident}' is outside this version's scope — chain repair and reopen "
                             f"are not an operator-surface authority"))
            if ident in LEDGER_PRIVATES:
                reds.append((name, lineno, "ledger-private",
                             f"'{ident}' reaches past the ledger's public methods, where AH-1, the "
                             f"evidence floor and the veto guards live"))

    # 2 — forbidden identifiers, whether written in code OR pulled in by an import. An
    # `from … import open_crossing` never appears as a Name node until it is called, so the import
    # list is checked against the same vocabulary. (This gap was found by the negative test that
    # injects exactly that line — which is why that test exists.)
    for name, tree in trees.items():
        for lineno, ident in list(_code_identifiers(tree)) + list(_imported_names(tree)):
            low = ident.lower()
            if low in FORBIDDEN_NAMES:
                reds.append((name, lineno, "statutory-act-or-crossing",
                             f"code identifier '{ident}' — this app records; it never files, remits, "
                             f"crosses the Port, or fakes a human"))

    # 3 — no app-side writes
    for name, tree in trees.items():
        for lineno, what in _write_mode_opens(tree):
            reds.append((name, lineno, "app-side-write",
                         f"{what} — every durable byte must be written by a sovereign_agent module"))

    # 4 — no custody identifier
    for name, tree in trees.items():
        for lineno, ident in _code_identifiers(tree):
            if ident.lower() in CUSTODY_NAMES:
                reds.append((name, lineno, "balance-custody-as-authority",
                             f"code identifier '{ident}' — the node records attribution; it holds no balance"))

    # 5 — UI is same-origin
    ui_path = os.path.join(HERE, UI_FILE)
    with open(ui_path, "r", encoding="utf-8") as fh:
        ui = fh.read()
    for m in re.finditer(r"""fetch\(\s*([`'"])(.*?)\1""", ui, re.S):
        target = m.group(2)
        if not target.startswith("/api/") and "/api/" not in target:
            reds.append((UI_FILE, ui[: m.start()].count("\n") + 1, "ui-egress",
                         f"fetch target '{target}' is not a same-origin /api path"))
    for m in re.finditer(r"""\b(?:src|href)\s*=\s*["'](https?:)?//""", ui):
        reds.append((UI_FILE, ui[: m.start()].count("\n") + 1, "ui-external-asset",
                     "external asset reference — the page must be fully self-contained"))
    for m in re.finditer(r"\b(fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon)\b", ui):
        tok = m.group(1)
        if tok != "fetch":
            reds.append((UI_FILE, ui[: m.start()].count("\n") + 1, "ui-egress",
                         f"'{tok}' — the page speaks only to its own loopback API"))

    # 6 — the app names only the node's own stores
    store_like = re.findall(r"\b([A-Z][A-Za-z0-9_]*(?:Registry|Ledger|Store|DB|Database))\b",
                            sources["node_binding.py"] + sources["server.py"])
    unexpected = sorted({s for s in store_like if s not in ALLOWED_STORE_CLASSES})
    if unexpected:
        reds.append(("node_binding.py", 0, "second-ledger",
                     f"names a store class that is not the node's own: {unexpected}"))

    # prose tally — reported, never failed on
    for word in ("remit", "file_return", "escrow", "balance", "custody", "open_crossing"):
        prose[word] = sum(s.lower().count(word) for s in sources.values()) + ui.lower().count(word)

    # ---- report -------------------------------------------------------------------------------
    print("P6 kill-grep — USN ERP Operator Surface")
    print("=" * 78)
    checks = [
        ("1  no second store, no HTTP client imported", "second-store-or-egress"),
        ("2  no statutory act, no Port crossing, no faked human", "statutory-act-or-crossing"),
        ("3  no app-side write — the node writes, not us", "app-side-write"),
        ("4  no balance/custody identifier as authority", "balance-custody-as-authority"),
        ("5  UI speaks only to its own loopback API", "ui-egress"),
        ("5b UI is fully self-contained (no external asset)", "ui-external-asset"),
        ("6  only the node's own store classes are named", "second-ledger"),
        ("7  no out-of-scope ledger verb (repair_chain / reopen)", "out-of-scope-ledger-verb"),
        ("8  no reach past the ledger's public methods", "ledger-private"),
    ]
    for label, rule in checks:
        hits = [f for f in reds if f[2] == rule]
        print(f"  [{'RED ' if hits else 'GREEN'}] {label}")
        if hits:
            print(_findings_to_str(hits))

    print("-" * 78)
    print("  prose mentions (reported, not failed — these are the refusal messages):")
    print("      " + " · ".join(f"{k}×{v}" for k, v in prose.items()))
    for n in notes:
        print("  note: " + n)
    print("=" * 78)
    verdict = "RED" if reds else "GREEN"
    print(f"P6: {verdict}" + (f" — {len(reds)} finding(s)" if reds else " — no findings"))
    return 1 if reds else 0


if __name__ == "__main__":
    sys.exit(run())
