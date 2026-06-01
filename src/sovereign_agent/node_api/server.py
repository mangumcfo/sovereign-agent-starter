"""
Flask app factory + CLI entry for the Node API.

Console script:

    breathline-node-api [--host 127.0.0.1] [--port 8421] [--dev]

Defaults:

    --host 127.0.0.1  (local-first; contract_v1.yaml `default_bind`)
    --port 8421       (contract_v1.yaml `default_bind`)
    --dev             (skips bearer-token check; loudly labelled in responses)

TLS:

    The contract calls for self-signed HTTPS. Minimal viable shell binds plain
    HTTP for now with a loud startup warning. The TLS hardening lands as
    follow-up work (see Track A3 hand-off note). Atrium's `api.js` live()
    helper can call http://127.0.0.1:8421/api/v1/... during the cutover
    window; the URL changes to https:// when TLS lands without touching the
    UI code (only api.js's base URL changes).
"""

from __future__ import annotations

import argparse
import os
import sys

from flask import Flask, jsonify

from .errors import build_error
from .json_provider import install as install_json_provider
from .routes import node as node_routes
from .routes import obligations as obligations_routes
from .routes import placeholders as placeholder_routes
from .routes import roles as roles_routes


def create_app() -> Flask:
    """Flask app factory. Importable for tests + WSGI hosts."""
    app = Flask(__name__)

    # Install the thin-waist JSON shim that translates breathline-primitives
    # receipt types (ECDSASignature, AuditRecord, bytes, datetime, Enum) to
    # JSON without mutating the core envelope. See json_provider.py for the
    # discipline (Principle 7 — Thin-Waist).
    install_json_provider(app)

    # Loud startup banner — the contract is sovereign; the seam is named.
    app.config["BREATHLINE_NODE_API_VERSION"] = "0.1.0"
    app.config["BREATHLINE_CONTRACT_REF"] = (
        "breathline-federation/specs/node_api/contract_v1.yaml"
    )

    # Register blueprints (A + C real, B/D/E/F placeholders).
    app.register_blueprint(node_routes.bp)
    app.register_blueprint(roles_routes.bp)
    app.register_blueprint(obligations_routes.bp)
    app.register_blueprint(placeholder_routes.bp)

    # --- CORS — minimal viable for Atrium local development ---
    # Atrium is served either from file:// (origin "null") during single-file
    # demo, or from a localhost dev server. We allow both for the Track A3
    # cutover window. Production deployments will tighten this in a follow-up
    # (read from a node-local allowlist).
    @app.after_request
    def _attach_cors_headers(response):
        # contract_v1.yaml binds to 127.0.0.1 by default; the Node API is a
        # local-first surface. Permissive CORS is acceptable for development.
        response.headers.setdefault("Access-Control-Allow-Origin", "*")
        response.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        response.headers.setdefault("Access-Control-Allow-Headers", "Authorization, Content-Type, Accept")
        response.headers.setdefault("Access-Control-Max-Age", "300")
        return response

    @app.before_request
    def _handle_cors_preflight():
        # Short-circuit OPTIONS so we don't pollute the URL map with a catch-all
        # (which would steal 404s on unknown GET routes). after_request still
        # attaches the CORS headers to the 204 response.
        from flask import request as _req
        if _req.method == "OPTIONS":
            return ("", 204)

    @app.get("/")
    def index():
        return jsonify({
            "service": "breathline-node-api",
            "version": app.config["BREATHLINE_NODE_API_VERSION"],
            "contract": app.config["BREATHLINE_CONTRACT_REF"],
            "base_path": "/api/v1",
            "implemented_sections": ["A (node)", "B (manifest/specs)", "C (roles)",
                                     "D (invocations/breath_gate)", "E (audit/receipts)",
                                     "F (federation)"],
            "honest_stub_sections": ["F federation.shards / federation.propagation "
                                     "(real receipted-shard mesh deferred to SIX / Vol 4)"],
            "seal_glyph": "∞Δ∞",
            "posture": "thin lens over UniversalSovereignNode + ComplianceEngine + RoleBinder + PlaybookLoader",
        })

    @app.errorhandler(404)
    def _not_found(_e):
        return jsonify(build_error(
            code="ROUTE_NOT_FOUND",
            what="No Node API route matches the request URL.",
            why="The path is not in contract_v1.yaml endpoint set.",
            next_step="GET / to list implemented sections; consult "
                      "breathline-federation/specs/node_api/contract_v1.yaml.",
        )), 404

    @app.errorhandler(405)
    def _method_not_allowed(_e):
        return jsonify(build_error(
            code="METHOD_NOT_ALLOWED",
            what="The HTTP method is not permitted on this route.",
            why="The contract pins specific verbs (GET / POST) per endpoint.",
            next_step="Check contract_v1.yaml for the route's allowed verb.",
        )), 405

    return app


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="breathline-node-api",
                                description="Sovereign Breathline Node API (Track A1 minimal viable)")
    p.add_argument("--host", default=os.environ.get("BREATHLINE_NODE_API_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("BREATHLINE_NODE_API_PORT", "8421")))
    p.add_argument("--dev", action="store_true",
                   help="Skip bearer-token verification (loudly labelled). "
                        "Equivalent to BREATHLINE_NODE_API_DEV=1.")
    return p.parse_args(argv)


def cli_serve() -> None:
    """Console-script entry point. Registered in pyproject.toml [project.scripts]."""
    args = _parse_args(sys.argv[1:])

    if args.dev:
        os.environ["BREATHLINE_NODE_API_DEV"] = "1"

    app = create_app()

    print("∞Δ∞ breathline-node-api  (Track A1 minimal viable shell)")
    print(f"     contract: {app.config['BREATHLINE_CONTRACT_REF']}")
    print(f"     bind:     http://{args.host}:{args.port}  (TLS pending; A3 follow-up)")
    print(f"     auth:     {'DEV MODE (bearer check OFF)' if args.dev else 'principal_id-bearer required'}")
    print("     posture:  thin lens; shapes flow OUT OF the starter to api.js consumers")
    print()

    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    cli_serve()
