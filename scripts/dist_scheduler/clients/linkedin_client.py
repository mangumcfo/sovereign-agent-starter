#!/usr/bin/env python3
"""linkedin_client.py — LinkedIn carousel posting via the Posts API (version 202401, scope w_member_social).
Posts the linkedin_carousel asset as a real MULTI-IMAGE post: for each slide PNG it runs the documented
3-step image flow (initializeUpload -> binary PUT -> reference), then creates the post with content.multiImage.
Reuses KM's token at ~/.secrets/linkedin_credentials.env. Default dry-run; --live uploads + posts for real."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base import Client, PostResult  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
POSTS_API = "https://api.linkedin.com/rest/posts"
IMAGES_API = "https://api.linkedin.com/rest/images?action=initializeUpload"
VERSION = "202401"


class LinkedInClient(Client):
    name = "linkedin"
    secrets_file = "linkedin_credentials.env"
    env_keys = ["LINKEDIN_ACCESS_TOKEN", "LINKEDIN_AUTHOR_URN"]

    def _headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}", "LinkedIn-Version": VERSION,
                "X-Restli-Protocol-Version": "2.0.0"}

    def build_payload(self, asset: dict) -> dict:
        slides = asset.get("content", []) or []
        meta = asset.get("meta", {})
        png_dir = REPO / meta.get("svg_dir", "")
        pngs = sorted(str(p) for p in png_dir.glob("slide_*.png")) if png_dir.exists() else []
        book = meta.get("book", "")
        series = meta.get("series", "")
        cta = meta.get("cta", "")
        # caption (the post text above the carousel) — book + hook + CTA; reader-centered, with a clickable nudge
        hook = next((s.get("body") for s in slides[1:] if s.get("body")), "")
        commentary = (f"{book} — from {series}.\n\n{hook}\n\n{cta}\n\n"
                      "#AgenticAI #CFO #FinanceLeadership #ExecutivePlaybook")
        return {"units": len(pngs), "pngs": pngs, "commentary": commentary,
                "book": book, "summary": f"carousel '{book}' ({len(pngs)} slides)"}

    def _init_image(self, token: str, author: str) -> dict:
        body = json.dumps({"initializeUploadRequest": {"owner": author}}).encode()
        req = urllib.request.Request(IMAGES_API, data=body,
                                     headers={**self._headers(token), "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return (json.loads(r.read().decode()) or {}).get("value", {})

    def _put_bytes(self, upload_url: str, token: str, data: bytes):
        req = urllib.request.Request(upload_url, data=data,
                                     headers={"Authorization": f"Bearer {token}"}, method="PUT")
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status

    def _post_live(self, payload: dict) -> PostResult:
        creds = self.creds()
        token, author = creds["LINKEDIN_ACCESS_TOKEN"], creds["LINKEDIN_AUTHOR_URN"]
        image_urns = []
        for png in payload["pngs"]:
            v = self._init_image(token, author)
            up, urn = v.get("uploadUrl"), v.get("image")
            if not up or not urn:
                return PostResult.fail(self.name, f"image init failed for {Path(png).name}: {v}")
            self._put_bytes(up, token, Path(png).read_bytes())
            image_urns.append(urn)
        if not image_urns:
            return PostResult.fail(self.name, "no images uploaded")
        body = {
            "author": author, "commentary": payload["commentary"], "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
            "content": {"multiImage": {"images": [{"id": u, "altText": f"{payload['book']} — slide"} for u in image_urns]}},
            "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False,
        }
        data = json.dumps(body).encode()
        req = urllib.request.Request(POSTS_API, data=data,
                                     headers={**self._headers(token), "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=45) as r:
            post_id = r.headers.get("x-restli-id") or r.headers.get("x-linkedin-id") or "?"
        return PostResult.ok(self.name, f"posted carousel ({len(image_urns)} slides) id={post_id}", live=True)
