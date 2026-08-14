#!/usr/bin/env python3
"""BCK F10 fixture — a DELIBERATELY-VIOLATING surface that POSTs the node on GET.

A real operator surface must be GET-only toward the USN (the secretary law). This fixture breaks that fence
on purpose: every GET it serves triggers a POST to the node, so the fence-verifier's F2 (GET-only boundary)
probe can be shown to actually FAIL — a verifier that has never failed proves nothing.

The POST carries a bogus NON-owner bearer (RED-2): presenting ANY token makes the node skip its loopback-owner
shortcut and run real verification → 401, so the fixture can NEVER be owner-attributed and disposes NOTHING —
even on a node started with BREATHLINE_NODE_LOOPBACK_OWNER (the standard rig). A violation *fixture* must be as
unable to dispose as the verifier itself. The refused POST still appears as a `"POST ...` line in the node's
access log window, which is exactly what F2 catches.

Usage:  posting_surface.py <node-url> <port>   # then point the verifier's --web-url at http://127.0.0.1:<port>
"""
import json
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

NODE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8421"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8799
# same bogus non-owner bearer the verifier's mutating probes use — exists to be refused (401), never owner
NON_OWNER_BEARER = "bck-prober:not-a-real-credential-exists-to-be-refused"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # THE VIOLATION: a surface must never POST the node — this one does, on every GET.
        try:
            req = urllib.request.Request(
                NODE.rstrip("/") + "/api/v1/storage/datum",
                data=json.dumps({"content": "f2-fixture-violation", "visibility": "private"}).encode(),
                method="POST", headers={"Content-Type": "application/json",
                                        "Authorization": f"Bearer {NON_OWNER_BEARER}"})  # RED-2: never owner
            urllib.request.urlopen(req, timeout=3).read()
        except Exception:  # noqa: BLE001 — the 401 (or any failure) is fine; the POST attempt already logged
            pass
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"deliberately-violating surface (posts the node on GET)")

    def log_message(self, *a):  # keep the fixture quiet
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
