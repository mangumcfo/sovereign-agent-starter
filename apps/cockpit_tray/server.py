#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cockpit_tray — the six-desk factory tray, honest by construction.

∞Δ∞ Desks = lanes · belt = board · center = the human gate. ∞Δ∞

One local page. Six seats (AA / Tiger / GB / Grok Bot / No1 / KM), a center tile
showing the pending HumanApprovalGate queue and the last receipt hash, and an OUT
strip naming what was NOT live at the P0 inventory.

Honesty is structural, not stylistic:

  * Every tile is bound to a live read executed DURING the page render, or carries
    a painted OUT mark. Nothing is cached between renders, so a tile whose source
    dies renders DEAD on the next refresh — a probe that cannot fail proves
    nothing, and every probe here can fail visibly.
  * A tile never claims more certainty than its source: if the node API answers
    401, the tile says AUTH-REQUIRED and how to fix it; it does not show a fake
    zero. If a source is absent on this iron, the tile says so.
  * The sources-answering figure is derived from the probes of THIS render.
    It cannot read "all answering" unless every probed source answered.

Binds loopback only and refuses any other host (same posture as the ERP surface:
reach from another machine is a Port-governed crossing, not a bind flag).

Launch:
    python apps/cockpit_tray/server.py               # http://127.0.0.1:8479
    NODE_API_BEARER='<principal_id>:<secret>' python apps/cockpit_tray/server.py

Environment:
    NODE_API_BEARER   bearer for the node API (contract auth model
                      "principal_id-bearer"); without it the node-fed tiles
                      render AUTH-REQUIRED — visibly, in the painted UI.
    NODE_API_URL      default http://127.0.0.1:8421
    SURFACE_URL       default http://127.0.0.1:8477
"""

from __future__ import annotations

import argparse
import html
import ipaddress
import json
import os
import re
import sys
import urllib.error
import urllib.request

from flask import Flask, Response

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))

NODE_API_URL = os.environ.get("NODE_API_URL", "http://127.0.0.1:8421")
SURFACE_URL = os.environ.get("SURFACE_URL", "http://127.0.0.1:8477")
BOARD_PATH = os.path.join(_REPO_ROOT, "coordination", "TURN_BOARD.md")

# Both suite locations, by name (USN_ERP_SURFACE_BAR.md L6) — existence
# live-checked at render (zoom targets must resolve to real objects; a listed
# suite that is missing renders as missing).
SUITE_LOCATIONS = [
    "tests/test_cash_application.py",
    "tests/test_billing.py",
    "apps/usn_erp_surface/tests",
]

app = Flask(__name__)


# ---------------------------------------------------------------- live reads --
# Each returns a dict with "state" in {"LIVE", "DEAD", "AUTH-REQUIRED"} plus
# payload/detail. They are called inside the request handler — once per render,
# never cached — so killing a source changes the very next paint.

def _http_json(url: str, bearer: str | None, timeout: float = 3.0) -> dict:
    req = urllib.request.Request(url)
    if bearer:
        req.add_header("Authorization", f"Bearer {bearer}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"state": "LIVE", "payload": json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return {"state": "AUTH-REQUIRED",
                    "detail": f"{url} → 401. Set NODE_API_BEARER='<principal_id>:<secret>' "
                              f"(token file: ~/.breathline/credentials/<principal_id>.token)."}
        # Carry the contract error's own words onto the tile when the body has them —
        # a DEAD mark should say what refused, not just a status code.
        said = ""
        try:
            body = json.loads(exc.read().decode("utf-8"))
            said = " · " + str(body.get("what") or body.get("error") or "")[:140]
        except Exception:  # noqa: BLE001
            pass
        return {"state": "DEAD", "detail": f"{url} → HTTP {exc.code}{said}"}
    except Exception as exc:  # noqa: BLE001 — every failure class must paint, not raise
        return {"state": "DEAD", "detail": f"{url} → {type(exc).__name__}: {exc}"}


def read_board() -> dict:
    """Last board row per seat, read from coordination/TURN_BOARD.md at render."""
    try:
        with open(BOARD_PATH, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        return {"state": "DEAD", "detail": f"{BOARD_PATH} → {type(exc).__name__}: {exc}"}
    rows: dict[str, dict] = {}
    for line in text.splitlines():
        m = re.match(r"^\|\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}Z)\s*\|\s*([A-Za-z0-9-]+)\s*\|(.*)$", line)
        if not m:
            continue
        when, seat, rest = m.group(1), m.group(2).upper(), m.group(3)
        cells = [c.strip() for c in rest.strip().strip("|").split("|")]
        rows[seat] = {"when": when, "headline": cells[0] if cells else "", "full": line}
    return {"state": "LIVE", "rows": rows, "path": BOARD_PATH}


def read_node(bearer: str | None) -> dict:
    """Node API: status + pending breath gates + receipt tail. One dict, three reads."""
    out = {
        "status": _http_json(f"{NODE_API_URL}/api/v1/status", bearer),
        "pending": _http_json(f"{NODE_API_URL}/api/v1/breath_gate/pending", bearer),
        "receipts": _http_json(f"{NODE_API_URL}/api/v1/inference/receipts?limit=1000", bearer),
    }
    tail = None
    if out["receipts"]["state"] == "LIVE":
        items = out["receipts"]["payload"].get("receipts", [])
        if items:
            last = items[-1]
            for key in ("receipt_hash", "version_hash", "record_hash"):
                if last.get(key):
                    tail = {"field": key, "value": last[key], "seq": len(items) - 1}
                    break
            if tail is None:
                tail = {"field": None, "value": None,
                        "detail": "tail record carries no hash-named field; keys: "
                                  + ", ".join(sorted(last.keys()))}
        else:
            tail = {"field": None, "value": None, "detail": "receipt store is empty on this node"}
    else:
        # Inherit the read's own failure words — the tile must say what refused.
        tail = {"field": None, "value": None,
                "detail": out["receipts"].get("detail", "receipts read did not return LIVE")}
    out["tail"] = tail
    return out


def read_surface() -> dict:
    """Is the v1.1 ERP surface answering on loopback?"""
    try:
        with urllib.request.urlopen(SURFACE_URL, timeout=2.0) as resp:
            resp.read(200)
            return {"state": "LIVE", "detail": SURFACE_URL}
    except Exception as exc:  # noqa: BLE001
        return {"state": "DEAD", "detail": f"{SURFACE_URL} → {type(exc).__name__}"}


# ------------------------------------------------------------------- painting --

CHIP = {
    "LIVE": '<span class="chip live">LIVE</span>',
    "DEAD": '<span class="chip dead">SOURCE DEAD</span>',
    "AUTH-REQUIRED": '<span class="chip auth">AUTH-REQUIRED</span>',
    "OUT": '<span class="chip out">OUT</span>',
}

# The OUT strip: facts as they stood at the P0 inventory (2026-08-29), verbatim
# class, past tense on purpose — these are inventory facts, not live claims.
OUT_STRIP = [
    "Dragon was 198 behind origin/main at P0",
    "apps/usn_erp_surface was 0 entries on that tree",
    "operator console vintage UNKNOWN (not a git repo, probed routes 404)",
    "WP4 not durable (gate queue was process-local)",
    "v1.2 unmerged (verified GREEN on branch, FF is KM's keyboard)",
    "ollama was *:11434 (all interfaces) at inventory",
]

SEAT_ORDER = ["AA", "TIGER", "GB", "GROK BOT", "KM-NO1", "KM"]
BOARD_SEAT_KEY = {"AA": "AA", "TIGER": "TIGER", "GB": "GB", "KM-NO1": "KM-NO1"}


def _esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def _seat_tile(name: str, board: dict, node: dict) -> str:
    """One desk. Every branch paints its own state chip."""
    if name == "GROK BOT":
        return f"""<div class="tile seat">
  <h3>Grok Bot {CHIP['OUT']}</h3>
  <p class="mark">OUT — no Grok Bot process runs on this iron. Frames arrive as
  worktree deposits carried over PR #21; the Bot profile paste is at KM's keyboard.
  This tile binds to nothing and says so.</p>
</div>"""
    if name == "KM":
        pend = node["pending"]
        if pend["state"] == "LIVE":
            count = pend["payload"].get("count", 0)
            body = (f'<p class="big">{count}</p><p>gated act(s) awaiting the human hand '
                    f'(breath_gate/pending, read this render)</p>')
        else:
            body = f'<p class="mark">{_esc(pend.get("detail", ""))}</p>'
        return f"""<div class="tile seat">
  <h3>KM {CHIP[pend['state']]}</h3>{body}
</div>"""
    # Board-fed seats: AA / TIGER / GB / KM-NO1
    key = BOARD_SEAT_KEY[name]
    label = {"AA": "AA", "TIGER": "Tiger", "GB": "GB", "KM-NO1": "No1"}[name]
    if board["state"] != "LIVE":
        return f"""<div class="tile seat">
  <h3>{label} {CHIP['DEAD']}</h3>
  <p class="mark">{_esc(board.get('detail', 'board unreadable'))}</p>
</div>"""
    row = board["rows"].get(key)
    if row is None:
        return f"""<div class="tile seat">
  <h3>{label} {CHIP['LIVE']}</h3>
  <p class="mark">board readable; no row for seat {key} found in it</p>
</div>"""
    return f"""<div class="tile seat">
  <h3>{label} {CHIP['LIVE']}</h3>
  <p class="when">{_esc(row['when'])}</p>
  <p>{_esc(row['headline'][:160])}</p>
  <details><summary>zoom: full board row</summary><pre>{_esc(row['full'])}</pre></details>
</div>"""


def _center_tile(node: dict) -> str:
    pend, tail = node["pending"], node["tail"]
    if pend["state"] != "LIVE":
        return f"""<div class="tile center">
  <h2>Human gate {CHIP[pend['state']]}</h2>
  <p class="mark">{_esc(pend.get('detail', ''))}</p>
  <p class="mark">This tile reads {_esc(NODE_API_URL)}/api/v1/breath_gate/pending and
  /api/v1/inference/receipts each render. It is dead or unauthenticated right now and
  shows that instead of a number.</p>
</div>"""
    items = pend["payload"].get("pending", [])
    rows = "".join(
        f"<li><code>{_esc(i.get('req_id'))}</code> · {_esc(i.get('provenance', {}).get('source', '?'))}</li>"
        for i in items) or "<li>queue empty this render</li>"
    if tail and tail.get("value"):
        tail_html = (f'last receipt hash (store tail, seq {tail["seq"]}, field '
                     f'<code>{_esc(tail["field"])}</code>):<br><code class="hash">{_esc(tail["value"])}</code>')
    else:
        detail = (tail or {}).get("detail", "receipts read did not return LIVE")
        tail_html = f'<span class="mark">{_esc(detail)}</span>'
    return f"""<div class="tile center">
  <h2>Human gate {CHIP['LIVE']}</h2>
  <p class="big">{pend['payload'].get('count', 0)}</p>
  <p>pending HumanApprovalGate request(s)</p>
  <ul>{rows}</ul>
  <p>{tail_html}</p>
</div>"""


def _zoom_strip(surface: dict, board: dict) -> str:
    suites = "".join(
        f'<li><code>{_esc(p)}</code> — '
        + ("present at this tree" if os.path.exists(os.path.join(_REPO_ROOT, p))
           else '<span class="mark">MISSING at this tree</span>')
        + "</li>"
        for p in SUITE_LOCATIONS)
    if surface["state"] == "LIVE":
        surf = f'<a href="{_esc(SURFACE_URL)}">{_esc(SURFACE_URL)}</a> — answering this render'
    else:
        surf = f'<span class="mark">{_esc(surface["detail"])} — not running on this iron</span>'
    board_line = (_esc(board.get("path", BOARD_PATH))
                  + (" — read this render" if board["state"] == "LIVE"
                     else f' — <span class="mark">{_esc(board.get("detail", ""))}</span>'))
    return f"""<div class="tile zoom">
  <h3>Zoom targets (real objects only)</h3>
  <ul>
    <li>Board: <code>{board_line}</code></li>
    <li>v1.1 loopback surface: {surf}</li>
    <li>Suites, both locations by name:<ul>{suites}</ul></li>
  </ul>
</div>"""


@app.route("/")
def tray() -> Response:
    bearer = os.environ.get("NODE_API_BEARER") or None
    board = read_board()
    node = read_node(bearer)
    surface = read_surface()

    probes = {
        "node API status": node["status"]["state"],
        "node API breath_gate": node["pending"]["state"],
        "node API receipts": node["receipts"]["state"],
        "board file": board["state"],
        "v1.1 surface": surface["state"],
    }
    answering = sum(1 for s in probes.values() if s == "LIVE")
    probe_list = " · ".join(f"{k}: {v}" for k, v in probes.items())

    seats = "".join(_seat_tile(s, board, node) for s in SEAT_ORDER)
    out_items = "".join(f"<li>{_esc(t)}</li>" for t in OUT_STRIP)

    page = f"""<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="5">
<title>Cockpit Tray — six desks, one gate</title>
<style>
body{{background:#0e1116;color:#dfe3e8;font:14px/1.45 system-ui,sans-serif;margin:0;padding:18px}}
h1{{font-size:18px;margin:0 0 2px}} h2{{font-size:15px;margin:0 0 6px}} h3{{font-size:13px;margin:0 0 4px}}
.sub{{color:#8a93a0;font-size:12px;margin-bottom:14px}}
.grid{{display:grid;grid-template-columns:1fr 1fr 1.3fr 1fr 1fr;gap:10px;align-items:start}}
.tile{{background:#161b23;border:1px solid #232a35;border-radius:8px;padding:10px}}
.tile.center{{grid-column:3;grid-row:1 / span 2;border-color:#3d5afe}}
.chip{{font-size:10px;font-weight:700;letter-spacing:.6px;padding:2px 6px;border-radius:3px;vertical-align:middle}}
.chip.live{{background:#124a2b;color:#5ee69a}} .chip.dead{{background:#4a1212;color:#ff7a7a}}
.chip.auth{{background:#4a3a12;color:#ffd75e}} .chip.out{{background:#2a2f38;color:#9aa4b1}}
.big{{font-size:30px;margin:4px 0;font-weight:700}} .when{{color:#8a93a0;font-size:11px;margin:0}}
.mark{{color:#ffd75e;font-size:12px}} .hash{{word-break:break-all;font-size:11px}}
pre{{white-space:pre-wrap;font-size:10px;color:#9aa4b1;max-height:180px;overflow:auto}}
.outstrip{{margin-top:14px;background:#1d1710;border:1px solid #4a3a12;border-radius:8px;padding:10px}}
.outstrip h3{{color:#ffd75e}} .outstrip li{{color:#cbb27a;font-size:12px}}
ul{{margin:6px 0;padding-left:18px}} details summary{{cursor:pointer;color:#7fa3ff;font-size:11px}}
a{{color:#7fa3ff}} code{{font-size:11px}}
.probes{{margin-top:10px;color:#8a93a0;font-size:11px}}
</style></head><body>
<h1>Cockpit Tray</h1>
<p class="sub">Six desks · belt = coordination/TURN_BOARD.md · center = the human gate.
Every tile re-reads its source on this render (auto-refresh 5s); a dead source paints
SOURCE DEAD here, not a stale number. Sources answering <b>this render: {answering} of
{len(probes)} probed</b>.</p>
<div class="grid">
{seats}
{_center_tile(node)}
{_zoom_strip(surface, board)}
</div>
<div class="outstrip">
  <h3>OUT — facts as they stood at the P0 inventory (2026-08-29), not live claims</h3>
  <ul>{out_items}</ul>
</div>
<p class="probes">Probe states this render — {probe_list}. Node API: {_esc(NODE_API_URL)}
(contract auth: principal_id-bearer). This page binds 127.0.0.1 only; it holds no state,
no store, no history — it is a lens, and the node is the truth.</p>
</body></html>"""
    return Response(page, mimetype="text/html")


# ---------------------------------------------------------------------- main --

def main() -> None:
    parser = argparse.ArgumentParser(description="cockpit tray — loopback only")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8479)
    args = parser.parse_args()
    try:
        if not ipaddress.ip_address(args.host).is_loopback:
            raise ValueError
    except ValueError:
        sys.exit("cockpit_tray refuses non-loopback hosts. Reach from another machine "
                 "is a Port-governed crossing, not a bind flag.")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
