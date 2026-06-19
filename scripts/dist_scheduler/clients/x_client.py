#!/usr/bin/env python3
"""x_client.py — X (Twitter) API v2 thread client, OAuth 1.0a user-context (posting requires user context,
not an app bearer). Reuses KM's EXISTING keys at ~/.secrets/x_api_credentials.env (the six X-bot's creds);
nothing new to provision for X. Self-contained signer (stdlib HMAC-SHA1) modeled on federation/six/x_oauth.py.
Posts the x_thread asset as a chained reply thread. Default dry-run; --live signs + posts for real."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets as _secrets
import sys
import time
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base import Client, PostResult  # noqa: E402

API = "https://api.twitter.com/2/tweets"


def _penc(s) -> str:
    return quote(str(s), safe="")


def _oauth_header(method: str, url: str, creds: dict) -> str:
    """OAuth 1.0a Authorization header. For a JSON-body POST the signature base string EXCLUDES the body
    (X v2 requirement) — so only the oauth_* params are signed (matches six/x_oauth.py)."""
    oauth = {
        "oauth_consumer_key": creds["X_CONSUMER_KEY"],
        "oauth_nonce": _secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": creds["X_ACCESS_TOKEN"],
        "oauth_version": "1.0",
    }
    base_params = "&".join(f"{_penc(k)}={_penc(v)}" for k, v in sorted(oauth.items()))
    base_string = "&".join([method.upper(), _penc(url), _penc(base_params)])
    signing_key = f"{_penc(creds['X_CONSUMER_SECRET'])}&{_penc(creds['X_ACCESS_TOKEN_SECRET'])}"
    sig = hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    oauth["oauth_signature"] = base64.b64encode(sig).decode()
    return "OAuth " + ", ".join(f'{_penc(k)}="{_penc(v)}"' for k, v in sorted(oauth.items()))


class XClient(Client):
    name = "x"
    secrets_file = "x_api_credentials.env"
    env_keys = ["X_CONSUMER_KEY", "X_CONSUMER_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]

    def build_payload(self, asset: dict) -> dict:
        posts = asset.get("content", []) or []
        return {"units": len(posts), "posts": posts, "summary": (posts[0] if posts else "")[:80]}

    def _post_live(self, payload: dict) -> PostResult:
        creds = self.creds()
        prev = None
        for text in payload["posts"]:
            body = {"text": text}
            if prev:
                body["reply"] = {"in_reply_to_tweet_id": prev}
            headers = {"Authorization": _oauth_header("POST", API, creds)}
            resp = self._http_post(API, headers, body)
            prev = (resp.get("data") or {}).get("id", prev)
        return PostResult.ok(self.name, f"posted thread of {payload['units']} tweets (head={prev})", live=True)
