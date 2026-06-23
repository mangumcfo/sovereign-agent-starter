#!/usr/bin/env python3
"""scheduler.py — self-hosted, sovereign dispatch scaffold (cron + per-platform API clients; NO Buffer/Publer).
Reads the v1 assets for a launched book and dispatches them to the api_headless channels via the post-clients.
DEFAULT DRY-RUN: the full pipeline runs WITHOUT credentials. CONSTITUTIONAL GATE (audit [468], CONSTITUTION §2
Propose→Approve→Execute): a --live post is REFUSED unless the distribution_launch:<book> obligation has been
APPROVED by the human (KM Accepts the Launch card) — and the approving principal is stamped on every dispatch.
State machine: staged → gated (KM-approved launch obligation) → dispatched → live | failed/refused (loud).

Usage:
  python3 scripts/dist_scheduler/scheduler.py 01_strategic_finance            # dry-run, X + LinkedIn
  python3 scripts/dist_scheduler/scheduler.py 01_strategic_finance --live     # refused unless launch APPROVED
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


def launch_approval(book_id: str) -> tuple[bool, str | None, str]:
    """THE GATE (CONSTITUTION §2). Returns (approved, principal, reason). A live post is permitted ONLY if the
    distribution_launch:<book> obligation exists AND has been APPROVED by the human (KM Accept on the Launch
    card sets approved=True via the breath-gate). Minted-not-enforced was the gap. principal = approved_by,
    stamped on the dispatch (provenance)."""
    try:
        sys.path.insert(0, str(REPO / "src"))
        from sovereign_agent.obligations.ledger import ObligationLedger, get_ledger_root
        import os
        root = os.environ.get("OBLIGATION_LEDGER_ROOT") or str(
            get_ledger_root(default=REPO / "memory" / "obligations" / "atrium_review"))
        lg = ObligationLedger(root, principal_id="KM-1176")
    except Exception as e:  # noqa: BLE001 — fail CLOSED (no ledger ⇒ no live post)
        return False, None, f"obligation ledger unavailable — refusing live post: {e}"
    ref = f"distribution_launch:{book_id}"
    found = None
    for o in lg.open_obligations():
        if (o.get("ref") or "") == ref:
            found = o
            break
    if not found:
        return False, None, (f"no {ref} obligation (KM has not been offered/accepted the Launch) — "
                             f"run the contract + KM Accept first")
    if not found.get("approved"):
        return False, None, (f"launch obligation {found.get('id')} exists but is NOT approved — "
                             f"awaiting KM's Accept on the Launch card (Propose→Approve→Execute)")
    return True, (found.get("approved_by") or "KM-1176"), "approved"


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
    # CONSTITUTIONAL GATE: no live post without an APPROVED launch obligation (Propose→Approve→Execute).
    principal = None
    if not dry_run:
        approved, principal, reason = launch_approval(book_id)
        if not approved:
            refusal = {"book_id": book_id, "mode": "live", "refused": True, "reason": reason,
                       "results": [{"channel": ch, "ok": False, "live": False,
                                    "detail": f"REFUSED (ungated): {reason}"} for ch in channels]}
            (bdir / "channel_state.json").write_text(json.dumps(
                {"book_id": book_id, "mode": "live", "refused": True, "reason": reason,
                 "channels": {ch: {"state": "gated", "detail": reason} for ch in channels}}, indent=2),
                encoding="utf-8")
            with log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"book_id": book_id, "event": "live_refused", "reason": reason}) + "\n")
            return refusal   # fail CLOSED — nothing posts
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
        if principal:                       # stamp the approving principal on every live dispatch (provenance)
            r["approved_by"] = principal
        results.append(r)
        state[ch] = {"state": ("dispatched" if (r.get("live")) else "staged"),
                     "ts": r.get("ts"), "detail": r.get("detail"), "approved_by": principal}
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"book_id": book_id, **r}) + "\n")
    (bdir / "channel_state.json").write_text(
        json.dumps({"book_id": book_id, "channels": state, "drip": _drip_schedule(std),
                    "mode": "dry_run" if dry_run else "live", "approved_by": principal}, indent=2), encoding="utf-8")
    return {"book_id": book_id, "mode": "dry_run" if dry_run else "live", "results": results, "approved_by": principal}


def main() -> int:
    ap = argparse.ArgumentParser(description="Sovereign distribution dispatch scaffold (X + LinkedIn first)")
    ap.add_argument("book_id")
    ap.add_argument("--live", action="store_true", help="post for real (needs platform OAuth env keys)")
    args = ap.parse_args()
    res = dispatch(args.book_id, dry_run=not args.live)
    if res.get("refused"):                  # CONSTITUTIONAL GATE — loud refusal (CONSTITUTION §4 Error Voice)
        print(f"⛔ LIVE POST REFUSED — {res['book_id']}")
        print(f"   why: {res['reason']}")
        print(f"   next: KM must Accept the Launch card (distribution_launch:{res['book_id']}) in Atrium first.")
        return 2
    print(f"dispatch [{res['mode']}] — {res['book_id']}" + (f" · approved_by {res['approved_by']}" if res.get('approved_by') else ""))
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
