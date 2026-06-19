#!/usr/bin/env python3
"""base.py — sovereign self-hosted post-client interface (no SaaS). Each platform client reads its OAuth/API
creds FROM ENV (the one-time KM credential step), builds the real API request, and posts. Default is dry-run:
the full pipeline (generate → gate → schedule → staged dispatch) runs WITHOUT credentials; live posting is the
only thing that needs the keys. Error Voice: failures are loud, never silent (CONSTITUTION §4)."""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cred_store import load_secrets  # noqa: E402  (named to avoid shadowing stdlib `secrets`)


class PostResult(dict):
    @classmethod
    def ok(cls, channel, detail, live=False):
        return cls(channel=channel, ok=True, live=live, detail=detail,
                   ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    @classmethod
    def fail(cls, channel, detail):
        return cls(channel=channel, ok=False, live=False, detail=detail,
                   ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


class Client:
    name = "base"
    env_keys: list[str] = []          # cred keys that must be present to go live
    secrets_file: str | None = None   # ~/.secrets/<file> the keys live in (env vars override)

    def creds(self) -> dict:
        return load_secrets(self.secrets_file) if self.secrets_file else dict(__import__("os").environ)

    def available(self) -> bool:
        c = self.creds()
        return all(c.get(k) for k in self.env_keys)

    def missing_creds(self) -> list[str]:
        c = self.creds()
        return [k for k in self.env_keys if not c.get(k)]

    def build_payload(self, asset: dict) -> dict:
        raise NotImplementedError

    def _http_post(self, url: str, headers: dict, body: dict) -> dict:
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 (sovereign, known hosts)
            return json.loads(r.read().decode() or "{}")

    def post(self, asset: dict, dry_run: bool = True) -> PostResult:
        """Build the platform payload; dry-run logs the intended post; live posts via the official API."""
        payload = self.build_payload(asset)
        if dry_run:
            n = payload.get("units", 1)
            return PostResult.ok(self.name, f"DRY-RUN — would post {n} unit(s): {payload.get('summary', '')}"[:160])
        if not self.available():
            return PostResult.fail(self.name, f"missing creds: {', '.join(self.missing_creds())}")
        try:
            return self._post_live(payload)
        except Exception as e:  # loud Error Voice
            return PostResult.fail(self.name, f"live post failed: {e}")

    def _post_live(self, payload: dict) -> PostResult:
        raise NotImplementedError
