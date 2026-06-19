#!/usr/bin/env python3
"""x_client.py — X (Twitter) API v2 thread client. Posts the x_thread asset as a chained reply thread.
Live wiring needs an OAuth2 user token (env X_ACCESS_TOKEN). Default dry-run runs without it."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base import Client, PostResult  # noqa: E402

API = "https://api.twitter.com/2/tweets"


class XClient(Client):
    name = "x"
    env_keys = ["X_ACCESS_TOKEN"]   # OAuth2 user-context bearer (also accepts X_API_KEY/SECRET upstream)

    def build_payload(self, asset: dict) -> dict:
        posts = asset.get("content", []) or []
        return {"units": len(posts), "posts": posts,
                "summary": (posts[0] if posts else "")[:80]}

    def _post_live(self, payload: dict) -> PostResult:
        import os
        token = os.environ["X_ACCESS_TOKEN"]
        headers = {"Authorization": f"Bearer {token}"}
        prev = None
        for text in payload["posts"]:
            body = {"text": text}
            if prev:
                body["reply"] = {"in_reply_to_tweet_id": prev}
            resp = self._http_post(API, headers, body)
            prev = (resp.get("data") or {}).get("id", prev)
        return PostResult.ok(self.name, f"posted thread of {payload['units']} tweets (head={prev})", live=True)
