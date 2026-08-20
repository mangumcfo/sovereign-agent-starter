#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""server — a local-only Flask shell for the USN ERP Operator Surface.

∞Δ∞ The node is the ERP. This process only drives it. ∞Δ∞

What this is: a desktop-style app that happens to render in your browser. It binds to loopback,
serves one page, and exposes a small JSON API that is a thin translation over `node_binding`. It
holds no business logic of its own.

What it is NOT:

  * Not a service. It binds 127.0.0.1 only and refuses to start on a non-loopback host. There is no
    auth layer because there is no remote surface to authenticate.
  * Not a spine over `breathline-node-api`. This process never speaks HTTP to :8421 or anywhere
    else — it imports `sovereign_agent` in-process, exactly as the MCP connector does.
  * Not a store. It writes no database, no cache, no config file. Paths come from the environment
    or from the open-node form, and live in memory for the life of the process.

Launch:
    python apps/usn_erp_surface/server.py            # http://127.0.0.1:8477
    python apps/usn_erp_surface/server.py --port 9000 --open
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import sys
import threading
import webbrowser
from typing import Any, Dict, Optional, Tuple

from flask import Flask, Response, jsonify, request

_HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(_HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(_HERE))

from usn_erp_surface.node_binding import (  # noqa: E402
    ACTION_CLASSES,
    APP_NAME,
    APP_VERSION,
    CLASSIFICATIONS,
    CONTRIBUTION_CLASSES,
    OBLIGATION_ACTION_CLASSES,
    SOURCE_DEFAULT_CLASS,
    TAX_CATEGORIES,
    NodeBinding,
    SurfaceError,
    classify_evidence,
)

DEFAULT_PORT = 8477
UI_FILE = os.path.join(_HERE, "ui.html")

app = Flask(__name__)
app.json.sort_keys = False

#: The single open node for this process. There is exactly one operator at one machine.
_BINDING: Optional[NodeBinding] = None
_LOCK = threading.Lock()


def _bound() -> NodeBinding:
    if _BINDING is None:
        raise SurfaceError("No node is open. Open one first — paths, operator, and posture.")
    return _BINDING


def _ok(payload: Any, code: int = 200) -> Tuple[Response, int]:
    return jsonify(payload), code


def _fail(exc: Exception, code: int = 400) -> Tuple[Response, int]:
    """Errors are shown to the operator verbatim, so they must be worth reading. A refusal from the
    node is a result, not a crash — it is reported as `refused`, never as a bare 500."""
    return jsonify({"error": str(exc), "kind": type(exc).__name__,
                    "refused": isinstance(exc, SurfaceError)}), code


def _body() -> Dict[str, Any]:
    return request.get_json(silent=True) or {}


def _num(v: Any) -> Optional[float]:
    if v in (None, "", "null"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        raise SurfaceError(f"'{v}' is not a number. An amount is an attribution figure — leave it "
                           f"blank if you are recording the fact without a figure.")


def _extra(v: Any) -> Optional[Dict[str, Any]]:
    """Operator-supplied attribution fields, entered as JSON. Parsed here; fenced in node_binding."""
    if not v:
        return None
    if isinstance(v, dict):
        return v
    try:
        parsed = json.loads(v)
    except json.JSONDecodeError as exc:
        raise SurfaceError(f"Extra fields must be a JSON object — {exc}. Example: "
                           f'{{"client": "acme", "invoice": "INV-12"}}')
    if not isinstance(parsed, dict):
        raise SurfaceError("Extra fields must be a JSON object, not a list or a bare value.")
    return parsed


# ==================================================================================================
# Page
# ==================================================================================================

@app.get("/")
def index() -> Response:
    with open(UI_FILE, "r", encoding="utf-8") as fh:
        return Response(fh.read(), mimetype="text/html")


@app.get("/favicon.ico")
def favicon() -> Response:
    """No icon, answered cleanly. A 404 in the console is noise an operator should not have to
    learn to ignore."""
    return Response(b"", status=204)


@app.get("/api/vocab")
def vocab() -> Tuple[Response, int]:
    """The node's own vocabularies, so the UI never invents a category or a proof grade."""
    return _ok({
        "app": {"name": APP_NAME, "version": APP_VERSION},
        "tax_categories": sorted(TAX_CATEGORIES),
        "contribution_classes": sorted(CONTRIBUTION_CLASSES),
        "contribution_sources": SOURCE_DEFAULT_CLASS,
        "gated_action_classes": list(ACTION_CLASSES),
        "obligation_action_classes": list(OBLIGATION_ACTION_CLASSES),
        "classifications": list(CLASSIFICATIONS),
        "env": {"NODE_KEYSTORE_DIR": os.environ.get("NODE_KEYSTORE_DIR"),
                "SUBSTRATE_STORAGE_ROOT": os.environ.get("SUBSTRATE_STORAGE_ROOT"),
                "OBLIGATION_LEDGER_ROOT": os.environ.get("OBLIGATION_LEDGER_ROOT"),
                "USN_OPERATOR": os.environ.get("USN_OPERATOR")},
        "open": _BINDING is not None,
    })


# ==================================================================================================
# 1 · Open the node
# ==================================================================================================

@app.post("/api/open")
def open_node() -> Tuple[Response, int]:
    """Open a node from explicit paths (or the environment). Nothing is persisted — reopening after
    a restart means entering the paths again, or exporting them in the environment."""
    global _BINDING
    b = _body()
    try:
        with _LOCK:
            _BINDING = NodeBinding.from_env(
                keystore_dir=b.get("keystore_dir"), registry_root=b.get("registry_root"),
                ledger_root=b.get("ledger_root"), regulated=bool(b.get("regulated", True)),
                operator=b.get("operator"), mandate=b.get("mandate"))
            return _ok(_BINDING.status())
    except SurfaceError as exc:
        return _fail(exc)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.post("/api/close")
def close_node() -> Tuple[Response, int]:
    global _BINDING
    with _LOCK:
        _BINDING = None
    return _ok({"open": False, "note": "Node closed. Nothing was written by closing."})


@app.get("/api/status")
def status() -> Tuple[Response, int]:
    try:
        return _ok(_bound().status())
    except SurfaceError as exc:
        return _fail(exc, 409)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


# ==================================================================================================
# 2 & 3 · Recording acts
# ==================================================================================================

def _record(fn_name: str) -> Tuple[Response, int]:
    b = _body()
    try:
        nb = _bound()
        with _LOCK:
            if fn_name == "income":
                res = nb.record_income(
                    work_ref=str(b.get("work_ref", "")).strip(), amount=_num(b.get("amount")),
                    unit=str(b.get("unit") or "credits"), port_ref=b.get("port_ref") or None,
                    extra=_extra(b.get("extra")))
            elif fn_name == "contribution":
                res = nb.record_contribution_event(
                    source=str(b.get("source", "")).strip(),
                    work_ref=str(b.get("work_ref", "")).strip(),
                    contribution_class=b.get("contribution_class") or None,
                    amount=_num(b.get("amount")), unit=str(b.get("unit") or "credits"),
                    port_ref=b.get("port_ref") or None, extra=_extra(b.get("extra")))
            else:
                res = nb.record_tax_note(
                    work_ref=str(b.get("work_ref", "")).strip(),
                    category=str(b.get("category", "")).strip(),
                    references_income=b.get("references_income") or None,
                    amount=_num(b.get("amount")), unit=str(b.get("unit") or "credits"),
                    extra=_extra(b.get("extra")))
        # A SHALLOW COPY, deliberately: the binding keeps its own record of a disposition, and
        # folding the gate state (which lists that record) back into the same object would make the
        # response self-referential and unserialisable.
        return _ok(dict(res, gate=nb.gate_state()))
    except SurfaceError as exc:
        return _fail(exc)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.post("/api/record/income")
def record_income() -> Tuple[Response, int]:
    return _record("income")


@app.post("/api/record/contribution")
def record_contribution() -> Tuple[Response, int]:
    return _record("contribution")


@app.post("/api/record/tax")
def record_tax() -> Tuple[Response, int]:
    """A tax event, recorded. This endpoint files nothing, pays nothing and remits nothing — there
    is no such path in this app, and the node has no in-node tax authority to reach."""
    return _record("tax")


@app.post("/api/record/invoice")
def record_invoice() -> Tuple[Response, int]:
    """Record an invoice as a governed billing-event object. This endpoint bills as a RECORD — it
    collects nothing, receives nothing, settles nothing: there is no such path in this app. The
    total is computed by the sealed billing surface from the lines; the operator never types it."""
    b = _body()
    try:
        nb = _bound()
        lines = b.get("lines")
        if not isinstance(lines, list) or not lines:
            raise SurfaceError("An invoice needs at least one line — each with a quantity and a "
                               "unit price. Example line: {\"description\": \"consulting\", "
                               "\"quantity\": 10, \"unit_price\": 150}.")
        with _LOCK:
            res = nb.record_invoice(
                invoice_id=str(b.get("invoice_id", "")).strip(),
                customer=str(b.get("customer", "")).strip(),
                lines=lines, tax=_num(b.get("tax")) or 0,
                currency=str(b.get("currency") or "USD"),
                issued_day=int(b.get("issued_day") or 0),
                due_day=(int(b["due_day"]) if b.get("due_day") not in (None, "") else None),
                credit_limit=_num(b.get("credit_limit")), outstanding=_num(b.get("outstanding")),
                extra=_extra(b.get("extra")))
        return _ok(dict(res, gate=nb.gate_state()))
    except SurfaceError as exc:
        return _fail(exc)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.get("/api/invoices")
def invoices() -> Tuple[Response, int]:
    """The receivables panel — replayed from the node's registry every call. Billing-event records,
    not an AR balance."""
    try:
        return _ok(_bound().invoices(
            only=request.args.get("only", "all"),
            limit=int(request.args.get("limit", 100)),
            offset=int(request.args.get("offset", 0))))
    except SurfaceError as exc:
        return _fail(exc, 409)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.get("/api/ar-aging")
def ar_aging() -> Tuple[Response, int]:
    """AR aging — a read-only projection over the open invoice records, computed on read via the
    sealed billing surface. Nothing is stored; no balance is held."""
    try:
        return _ok(_bound().ar_aging(as_of_day=int(request.args.get("as_of_day", 0))))
    except SurfaceError as exc:
        return _fail(exc, 409)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.get("/api/period-view")
def period_view() -> Tuple[Response, int]:
    """Trial balance + income statement + balance sheet, projected from node state on every call via
    the sealed financials surface. A computed view — no stored GL. Full GAAP-shaped books; the node
    moves no value (money-path OFF)."""
    try:
        return _ok(_bound().period_view())
    except SurfaceError as exc:
        return _fail(exc, 409)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.get("/api/home")
def status_home() -> Tuple[Response, int]:
    """The operator status home — one read-only screen composing the existing reads (exceptions,
    approvals, period, audit readiness). Nothing can be acted on or cleared from here."""
    try:
        return _ok(_bound().status_home())
    except SurfaceError as exc:
        return _fail(exc, 409)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.get("/api/chart-of-accounts")
def chart_of_accounts() -> Tuple[Response, int]:
    """The chart of accounts with live balances — read-only; no account store exists to edit."""
    try:
        return _ok(_bound().chart_of_accounts_view())
    except SurfaceError as exc:
        return _fail(exc, 409)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.get("/api/parties")
def parties() -> Tuple[Response, int]:
    """Party roll-ups (customers · revenue sources) derived from the governed records. No party
    master file exists; vendors are empty by construction (AP not surfaced)."""
    try:
        return _ok(_bound().parties())
    except SurfaceError as exc:
        return _fail(exc, 409)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.get("/api/ar-aging-by-customer")
def ar_aging_by_customer() -> Tuple[Response, int]:
    """AR aging by customer × bucket — the sealed aging rule composed per party, with the
    four-way equality proof in the artifact. Read-only; open = all invoices by construction
    until a cash-application surface exists (and the response says so)."""
    try:
        raw = request.args.get("as_of_day")
        return _ok(_bound().ar_aging_view(as_of_day=(int(raw) if raw not in (None, "") else None)))
    except SurfaceError as exc:
        return _fail(exc, 409)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.get("/api/drill")
def drill() -> Tuple[Response, int]:
    """Transaction/journal drill-down — READ-ONLY. Answers 'which governed records make this
    number' and carries its own equality proof (total vs sum of listed lines)."""
    try:
        return _ok(_bound().drill(kind=request.args.get("kind", ""),
                                  key=request.args.get("key") or None))
    except SurfaceError as exc:
        return _fail(exc)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.get("/api/exceptions")
def exceptions() -> Tuple[Response, int]:
    """The exception queue — pending deviations derived from node state, classified by the sealed
    router. READ-ONLY: nothing here clears anything; a row leaves only when the governed state
    changes through an existing gated verb on the other panels."""
    try:
        return _ok(_bound().exceptions_queue())
    except SurfaceError as exc:
        return _fail(exc, 409)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.get("/api/audit-package")
def audit_package() -> Tuple[Response, int]:
    """Preview the audit evidence package plus its hash. Read-only: the package RECORDS — tax memos
    are records not filings, invoices are earned billings never cash, and no pay/remit/file appears
    as a completed act because no such act exists on this node."""
    try:
        pkg, digest = _bound().audit_package()
        return _ok({"sha256": digest, "package": pkg})
    except SurfaceError as exc:
        return _fail(exc, 409)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.get("/api/audit-package/download")
def audit_package_download() -> Response:
    """The audit package as a file — byte-identical on re-export against unchanged node state."""
    payload, digest = _bound().audit_package_bytes()
    return Response(payload, mimetype="application/json", headers={
        "Content-Disposition": f'attachment; filename="usn-audit-package-{digest[:12]}.json"',
        "X-Package-SHA256": digest,
    })


@app.post("/api/close-period")
def close_period() -> Tuple[Response, int]:
    """Open a period-close intent. Under the regulated posture it is held at the human gate — nothing
    is written until you approve it; a denial writes nothing. On approval the close is persisted
    through the node's own obligation ledger. This surface moves no money and files nothing."""
    b = _body()
    try:
        nb = _bound()
        with _LOCK:
            res = nb.close_period(period_id=str(b.get("period_id", "")).strip())
        return _ok(dict(res, gate=nb.gate_state()))
    except SurfaceError as exc:
        return _fail(exc)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


# ==================================================================================================
# 4 · The gate
# ==================================================================================================

@app.get("/api/gate")
def gate() -> Tuple[Response, int]:
    try:
        return _ok(_bound().gate_state())
    except SurfaceError as exc:
        return _fail(exc, 409)


@app.post("/api/gate/<req_id>/approve")
def gate_approve(req_id: str) -> Tuple[Response, int]:
    """An explicit human approval. Reached only from an operator click — there is no caller in this
    app that approves on the operator's behalf, and `simulate_approval` is never used."""
    return _dispose(req_id, True)


@app.post("/api/gate/<req_id>/deny")
def gate_deny(req_id: str) -> Tuple[Response, int]:
    """An explicit human denial. Writes nothing at all — the refusal is the act."""
    return _dispose(req_id, False)


def _dispose(req_id: str, approve: bool) -> Tuple[Response, int]:
    b = _body()
    try:
        nb = _bound()
        with _LOCK:
            res = nb.dispose(req_id, approve, approver=b.get("approver"),
                             reason=str(b.get("reason") or ""))
        # Copy before folding in gate state — `res` is the binding's own stored disposition record,
        # and gate_state() lists it. Mutating it in place would create a cycle.
        return _ok(dict(res, gate=nb.gate_state()))
    except SurfaceError as exc:
        return _fail(exc)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


# ==================================================================================================
# 5 & 6 · Reads and the portable package
# ==================================================================================================

@app.get("/api/events")
def events() -> Tuple[Response, int]:
    try:
        return _ok(_bound().events(
            only=request.args.get("only", "all"),
            limit=int(request.args.get("limit", 100)),
            offset=int(request.args.get("offset", 0))))
    except SurfaceError as exc:
        return _fail(exc, 409)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.get("/api/verify/<path:object_id>")
def verify(object_id: str) -> Tuple[Response, int]:
    try:
        return _ok(_bound().verify_object(object_id))
    except SurfaceError as exc:
        return _fail(exc, 404)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.get("/api/package")
def package() -> Tuple[Response, int]:
    """Preview the portable package plus its hash, without downloading it."""
    try:
        core, digest = _bound().export_package()
        return _ok({"sha256": digest, "package": core})
    except SurfaceError as exc:
        return _fail(exc, 409)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.get("/api/package/download")
def package_download() -> Response:
    """The package as a file. Byte-identical on re-export against unchanged node state — the hash in
    the filename is over the same bytes, so two exports of the same state collide by design."""
    payload, digest = _bound().export_bytes()
    return Response(payload, mimetype="application/json", headers={
        "Content-Disposition": f'attachment; filename="usn-package-{digest[:12]}.json"',
        "X-Package-SHA256": digest,
    })


# ==================================================================================================
# 7 · Obligations — read the node's ledger, and drive its own lifecycle
# ==================================================================================================

@app.get("/api/obligations")
def obligations() -> Tuple[Response, int]:
    """The panel. Replayed from the node's obligations.ndjson on every call — never from a cache,
    because there is no cache."""
    try:
        return _ok(_bound().obligations(
            only=request.args.get("only", "all"),
            limit=int(request.args.get("limit", 100)),
            offset=int(request.args.get("offset", 0))))
    except SurfaceError as exc:
        return _fail(exc, 409)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.get("/api/obligations/evidence-tier")
def evidence_tier() -> Tuple[Response, int]:
    """Classify a draft evidence string with the ledger's own classifier, so the operator sees the
    tier before they try to close on it. Pure computation; writes nothing."""
    text = request.args.get("evidence", "")
    tier = classify_evidence(text)
    return _ok({
        "evidence": text, "tier": tier.value,
        "closes": tier.value != "E0",
        "note": {"E0": "claim-only — this will not close an obligation. Add a path, URL, hash or receipt id.",
                 "E1": "artifact pointer — enough to close.",
                 "E2": "artifact plus verification — the preferred grade."}[tier.value],
    })


def _obligation_act(fn_name: str, obligation_id: Optional[str] = None) -> Tuple[Response, int]:
    """One shape for every obligation act: dispatch, then hand back the fresh gate and panel so the
    UI never has to guess what changed."""
    b = _body()
    try:
        nb = _bound()
        with _LOCK:
            if fn_name == "open":
                roles = b.get("requires_attestation")
                if isinstance(roles, str):
                    roles = [r.strip() for r in roles.split(",") if r.strip()]
                res = nb.obligation_open(
                    title=str(b.get("title", "")).strip(),
                    intent=(b.get("intent") or None),
                    classification=str(b.get("classification") or "C2"),
                    ref=(b.get("ref") or None),
                    material=bool(b.get("material", False)),
                    next_gate=(b.get("next_gate") or None),
                    requires_attestation=roles or None,
                    mandate=(b.get("mandate") or None))
            elif fn_name == "approve":
                res = nb.obligation_approve(obligation_id, rationale=str(b.get("rationale") or ""))
            elif fn_name == "close":
                res = nb.obligation_close(
                    obligation_id, evidence=str(b.get("evidence", "")),
                    rejected=bool(b.get("rejected", False)),
                    method=(b.get("method") or None))
            elif fn_name == "attest":
                res = nb.obligation_attest(obligation_id, role=str(b.get("role", "")))
            elif fn_name == "veto":
                res = nb.obligation_veto(obligation_id, role=str(b.get("role", "")),
                                         reason=str(b.get("reason", "")))
            else:
                res = nb.obligation_clear_veto(obligation_id, role=str(b.get("role", "")))
        return _ok(dict(res, gate=nb.gate_state(), obligations=nb.obligations()))
    except SurfaceError as exc:
        return _fail(exc)
    except Exception as exc:  # noqa: BLE001
        return _fail(exc, 500)


@app.post("/api/obligations")
def obligation_open() -> Tuple[Response, int]:
    """Open a draft obligation. Under the regulated posture it is held at the gate first — nothing
    reaches the ledger until you approve it."""
    return _obligation_act("open")


@app.post("/api/obligations/<obligation_id>/approve")
def obligation_approve(obligation_id: str) -> Tuple[Response, int]:
    """Approve a draft through the breath-gate. The disposition recorded on the chain is yours."""
    return _obligation_act("approve", obligation_id)


@app.post("/api/obligations/<obligation_id>/close")
def obligation_close(obligation_id: str) -> Tuple[Response, int]:
    """Close with evidence, or record a refusal. The ledger's evidence floor and breath-gate rule
    both apply, and its refusals are surfaced verbatim."""
    return _obligation_act("close", obligation_id)


@app.post("/api/obligations/<obligation_id>/attest")
def obligation_attest(obligation_id: str) -> Tuple[Response, int]:
    return _obligation_act("attest", obligation_id)


@app.post("/api/obligations/<obligation_id>/veto")
def obligation_veto(obligation_id: str) -> Tuple[Response, int]:
    return _obligation_act("veto", obligation_id)


@app.post("/api/obligations/<obligation_id>/clear-veto")
def obligation_clear_veto(obligation_id: str) -> Tuple[Response, int]:
    return _obligation_act("clear_veto", obligation_id)


# ==================================================================================================
# Launch
# ==================================================================================================

def _assert_loopback(host: str) -> None:
    """Refuse to expose this process. There is no auth layer here because there is no remote
    surface — binding off-loopback would silently create one."""
    try:
        if not ipaddress.ip_address(host).is_loopback:
            raise ValueError
    except ValueError:
        raise SystemExit(
            f"Refusing to bind '{host}'. The operator surface is loopback-only: it drives your node "
            f"in-process and has no authentication because it is not meant to be reachable. If you "
            f"need access from another machine, that is a Port-governed crossing — not a bind flag."
        )


def main(argv: Optional[list] = None) -> None:
    ap = argparse.ArgumentParser(description=f"{APP_NAME} v{APP_VERSION} — local operator surface")
    ap.add_argument("--host", default="127.0.0.1", help="loopback only (default 127.0.0.1)")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--open", action="store_true", help="open a browser window on start")
    args = ap.parse_args(argv)
    _assert_loopback(args.host)

    url = f"http://{args.host}:{args.port}/"
    print(f"\n{APP_NAME} v{APP_VERSION}", file=sys.stderr)
    print("  library-direct · loopback-only · no second ledger · money-path OFF", file=sys.stderr)
    print(f"  open {url}\n", file=sys.stderr)
    if args.open:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
