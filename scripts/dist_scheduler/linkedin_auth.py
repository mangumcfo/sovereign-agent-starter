#!/usr/bin/env python3
"""linkedin_auth.py — one-time LinkedIn OAuth helper for the distribution scheduler.

Turns the fiddly 3-legged OAuth into: run it → click Approve in the browser → done. It exchanges the auth code
for a member access token, reads your member URN from /userinfo, and writes both into
~/.secrets/linkedin_credentials.env (which the scheduler already loads). Stdlib only (sovereign, no deps).

PREREQS (one-time, in your LinkedIn app at linkedin.com/developers/apps):
  1. Products tab: request "Share on LinkedIn" (w_member_social) + "Sign In with LinkedIn using OpenID Connect".
  2. Auth tab: add an authorized redirect URL EXACTLY:  http://localhost:8765/callback
  3. Auth tab: copy your Client ID + Primary Client Secret into ~/.secrets/linkedin_credentials.env as:
        LINKEDIN_CLIENT_ID=...
        LINKEDIN_CLIENT_SECRET=...
Then:  python3 scripts/dist_scheduler/linkedin_auth.py
"""
from __future__ import annotations

import http.server
import json
import secrets
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

SECRETS = Path.home() / ".secrets" / "linkedin_credentials.env"
REDIRECT = "http://localhost:8765/callback"
PORT = 8765
SCOPE = "openid profile w_member_social"
AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"

_result: dict = {}


def _load_env() -> dict:
    d = {}
    if SECRETS.exists():
        for ln in SECRETS.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, _, v = ln.partition("=")
                d[k.strip()] = v.strip().strip('"').strip("'")
    return d


def _save_env(updates: dict):
    """Merge updates into the env file, preserving comments + other keys."""
    lines, seen = [], set()
    existing = SECRETS.read_text(encoding="utf-8").splitlines() if SECRETS.exists() else []
    for ln in existing:
        s = ln.strip()
        if s and not s.startswith("#") and "=" in s:
            k = s.split("=", 1)[0].strip()
            if k in updates:
                lines.append(f"{k}={updates[k]}"); seen.add(k); continue
        lines.append(ln)
    for k, v in updates.items():
        if k not in seen:
            lines.append(f"{k}={v}")
    SECRETS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    SECRETS.chmod(0o600)


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        q = urllib.parse.urlparse(self.path)
        if q.path != "/callback":
            self.send_response(404); self.end_headers(); return
        params = urllib.parse.parse_qs(q.query)
        _result.update({k: v[0] for k, v in params.items()})
        self.send_response(200)
        self.send_header("Content-Type", "text/html"); self.end_headers()
        msg = "✓ Authorized — you can close this tab and return to the terminal."
        if "error" in _result:
            msg = f"✗ LinkedIn returned an error: {_result.get('error_description', _result['error'])}"
        self.wfile.write(f"<html><body style='font-family:sans-serif;padding:40px'>{msg}</body></html>".encode())

    def log_message(self, *a):  # silence
        pass


def _post_form(url: str, data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"},
                                method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main() -> int:
    env = _load_env()
    cid, csec = env.get("LINKEDIN_CLIENT_ID"), env.get("LINKEDIN_CLIENT_SECRET")
    if not cid or not csec:
        print(f"✗ Add LINKEDIN_CLIENT_ID + LINKEDIN_CLIENT_SECRET to {SECRETS} first (app Auth tab).")
        return 2
    state = secrets.token_hex(8)
    auth = AUTH_URL + "?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": cid, "redirect_uri": REDIRECT,
        "scope": SCOPE, "state": state})

    srv = http.server.HTTPServer(("127.0.0.1", PORT), _Handler)
    threading.Thread(target=srv.handle_request, daemon=True).start()  # serve exactly one callback
    print("\n1. Approve in your browser (opening now; if it doesn't, paste this URL):\n")
    print("   " + auth + "\n")
    try:
        webbrowser.open(auth)
    except Exception:
        pass
    print("2. Waiting for the redirect to http://localhost:8765/callback …")
    # block until the handler fills _result (handle_request returns after one request)
    import time
    for _ in range(300):
        if _result:
            break
        time.sleep(1)
    if "error" in _result:
        print(f"✗ LinkedIn error: {_result.get('error_description', _result['error'])}"); return 1
    code = _result.get("code")
    if not code:
        print("✗ No auth code received (timed out)."); return 1
    if _result.get("state") != state:
        print("✗ State mismatch — aborting (possible CSRF)."); return 1

    tok = _post_form(TOKEN_URL, {"grant_type": "authorization_code", "code": code,
                                 "redirect_uri": REDIRECT, "client_id": cid, "client_secret": csec})
    access = tok.get("access_token")
    if not access:
        print(f"✗ Token exchange failed: {tok}"); return 1
    info = _get(USERINFO_URL, access)
    sub = info.get("sub")
    if not sub:
        print(f"✗ Could not read member id from /userinfo: {info}"); return 1
    urn = f"urn:li:person:{sub}"
    _save_env({"LINKEDIN_ACCESS_TOKEN": access, "LINKEDIN_AUTHOR_URN": urn})
    name = info.get("name", "your profile")
    exp = tok.get("expires_in", 0)
    print(f"\n✓ Done. Authorized as {name}.")
    print(f"  LINKEDIN_AUTHOR_URN = {urn}")
    print(f"  token written to {SECRETS} (expires in ~{exp // 86400} days).")
    print("  The scheduler picks it up automatically — LinkedIn is now live-ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
