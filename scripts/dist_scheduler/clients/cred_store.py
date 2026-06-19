#!/usr/bin/env python3
"""secrets.py — sovereign credential loading. Reads ~/.secrets/<name>.env (KEY=VALUE, # comments; perms 600),
the SAME convention KM's six X-bot already uses (x_api_credentials.env). Env vars override the file, so a
systemd unit or a shell export still wins. No SaaS, no plaintext in-repo — keys live only in ~/.secrets."""
from __future__ import annotations

import os
from pathlib import Path

SECRETS_DIR = Path.home() / ".secrets"


def load_secrets(filename: str) -> dict:
    """Merge ~/.secrets/<filename> with os.environ (env wins). Missing file → just the environment."""
    creds: dict = {}
    path = SECRETS_DIR / filename
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            creds[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        if v:
            creds[k] = v
    return creds
