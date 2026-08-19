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
    CONTRIBUTION_CLASSES,
    SOURCE_DEFAULT_CLASS,
    TAX_CATEGORIES,
    NodeBinding,
    SurfaceError,
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
