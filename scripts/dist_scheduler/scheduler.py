#!/usr/bin/env python3
"""scheduler.py — self-hosted, sovereign dispatch scaffold (cron + per-platform API clients; NO Buffer/Publer).
Reads the v1 assets for a launched book and dispatches them to the api_headless channels via the post-clients.
DEFAULT DRY-RUN: the full pipeline runs WITHOUT credentials — live posting (--live) is the only step that needs
the OAuth keys (the one-time KM credential step). Mirrors the CHANNEL_TRACKER state machine:
staged → gated → dispatched → live | failed (loud).

Usage:
  python3 scripts/dist_scheduler/scheduler.py 01_strategic_finance            # dry-run, X + LinkedIn
  python3 scripts/dist_scheduler/scheduler.py 01_strategic_finance --live     # needs creds (flags if missing)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "clients"))
from x_client import XClient          # noqa: E402
from linkedin_client import LinkedInClient  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DIST = REPO / "artifacts" / "distribution"
STANDARD = Path("/home/kmangum/work-repos/mangumcfo/breathline-books-vault/book_standards/distribution_standard.yaml")

# channel → (asset file, client). X + LinkedIn FIRST per [445]; Substack staged-next (client pending).
CHANNEL_ASSET = {"x": "x_thread", "linkedin": "linkedin_carousel", "substack": "substack_excerpt"}
CLIENTS = {"x": XClient(), "linkedin": LinkedInClient()}


def _load_standard() -> dict:
    import yaml
    return yaml.safe_load(STANDARD.read_text(encoding="utf-8"))


def _v1_headless_channels(std: dict) -> list[str]:
    ch = std.get("channels", {})
    return [k for k, v in ch.items() if v.get("v1") and v.get("automation") == "api_headless"]


def _drip_schedule(std: dict) -> list[dict]:
    drip = (std.get("cadence", {}) or {}).get("drip", [])
    today = _dt.date.today()
    out = []
    for token in drip:
        days = 0
        for w in str(token).replace("-", " ").split():
            if w.isdigit():
                days = int(w)
        out.append({"slot": token, "date": (today + _dt.timedelta(days=days)).isoformat()})
    return out


def dispatch(book_id: str, dry_run: bool = True) -> dict:
    std = _load_standard()
    bdir = DIST / book_id
    if not bdir.exists():
        raise SystemExit(f"no generated assets for {book_id} (run the generators first)")
    channels = _v1_headless_channels(std)
    results, state = [], {}
    log = bdir / "dispatch_log.ndjson"
    for ch in channels:
        asset_name = CHANNEL_ASSET.get(ch)
        asset_path = bdir / f"{asset_name}.json"
        if not asset_path.exists():
            results.append({"channel": ch, "ok": False, "detail": "asset missing"}); continue
        asset = json.loads(asset_path.read_text(encoding="utf-8"))
        client = CLIENTS.get(ch)
        if client is None:
            r = {"channel": ch, "ok": True, "live": False, "detail": "client pending (Substack next) — staged"}
        else:
            r = dict(client.post(asset, dry_run=dry_run))
            if not dry_run and not client.available():
                r["detail"] = f"NEEDS CREDS: set {', '.join(client.missing_creds())}"
        results.append(r)
        state[ch] = {"state": ("dispatched" if (r.get("live")) else "staged"),
                     "ts": r.get("ts"), "detail": r.get("detail")}
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"book_id": book_id, **r}) + "\n")
    (bdir / "channel_state.json").write_text(
        json.dumps({"book_id": book_id, "channels": state, "drip": _drip_schedule(std),
                    "mode": "dry_run" if dry_run else "live"}, indent=2), encoding="utf-8")
    return {"book_id": book_id, "mode": "dry_run" if dry_run else "live", "results": results}


def main() -> int:
    ap = argparse.ArgumentParser(description="Sovereign distribution dispatch scaffold (X + LinkedIn first)")
    ap.add_argument("book_id")
    ap.add_argument("--live", action="store_true", help="post for real (needs platform OAuth env keys)")
    args = ap.parse_args()
    res = dispatch(args.book_id, dry_run=not args.live)
    print(f"dispatch [{res['mode']}] — {res['book_id']}")
    for r in res["results"]:
        print(f"  {'✓' if r.get('ok') else '✗'} {r['channel']:9} {r.get('detail', '')}")
    # creds flag
    need = {ch: c.missing_creds() for ch, c in CLIENTS.items() if c.missing_creds()}
    if need:
        print("  ⚠ credentials needed for live posting (one-time KM step):")
        for ch, keys in need.items():
            print(f"      {ch}: {', '.join(keys)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
