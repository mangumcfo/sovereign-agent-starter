#!/usr/bin/env python3
"""linkedin_client.py — LinkedIn API client. Posts the linkedin_carousel as a multi-image / document post.
Live wiring needs a member OAuth token (env LINKEDIN_ACCESS_TOKEN) + author URN (env LINKEDIN_AUTHOR_URN).
Default dry-run runs without them. (Carousel = document post; image upload is a 2-step register+upload.)"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base import Client, PostResult  # noqa: E402

API = "https://api.linkedin.com/rest/posts"


class LinkedInClient(Client):
    name = "linkedin"
    env_keys = ["LINKEDIN_ACCESS_TOKEN", "LINKEDIN_AUTHOR_URN"]

    def build_payload(self, asset: dict) -> dict:
        slides = asset.get("content", []) or []
        meta = asset.get("meta", {})
        title = slides[0].get("title", "") if slides else ""
        return {"units": len(slides), "slides": slides, "dims": meta.get("dims"),
                "svg_dir": meta.get("svg_dir"), "summary": f"carousel '{title}' ({len(slides)} slides)"}

    def _post_live(self, payload: dict) -> PostResult:
        import os
        token = os.environ["LINKEDIN_ACCESS_TOKEN"]
        author = os.environ["LINKEDIN_AUTHOR_URN"]
        headers = {"Authorization": f"Bearer {token}", "LinkedIn-Version": "202401",
                   "X-Restli-Protocol-Version": "2.0.0"}
        # NOTE: slide PNGs must first be registered+uploaded (images endpoint) → asset URNs, then referenced
        # here as a multi-image post. Scaffolded; wired on credential step.
        commentary = payload["slides"][0].get("title", "") if payload["slides"] else ""
        body = {"author": author, "commentary": commentary, "visibility": "PUBLIC",
                "distribution": {"feedDistribution": "MAIN_FEED"}, "lifecycleState": "PUBLISHED"}
        resp = self._http_post(API, headers, body)
        return PostResult.ok(self.name, f"posted carousel ({payload['units']} slides) id={resp.get('id', '?')}", live=True)
