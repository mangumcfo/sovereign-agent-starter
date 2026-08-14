#!/usr/bin/env python3
"""node_agent.py — Sovereign Agent v0: the node's node-local MIND (loopback model only).

(Named node_agent.py, NOT sovereign_agent.py, so it never shadows the `sovereign_agent` package on sys.path.)

Reads node state with READ-FIRST tools and answers/advises via a loopback completion (same pattern as
compute_share's model-url). It PROPOSES consequential acts as text blocks the operator runs — it has NO code path
that mutates state, so there is no silent execute. Consequential change stays behind KM's keyboard / the existing
HumanApprovalGate / grant / mandate. Compose-only: no new admission logic, no cloud brain, no hub.

  status              read-first tools only (node · grant/units · GPU · peers · transport) — no model call
  ask --prompt "…"    gather that context → loopback model → local answer + any PROPOSE block → exit 0

good > perfect: this is v0, a thin working mind. Spiral-improve. Integrity-only — no channel-secrecy claims.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pathlib
import re
import subprocess
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent

MODEL_URL_DEFAULT = "http://127.0.0.1:11434/api/generate"
SHARE_DIR = os.environ.get("SHARE_ROOT", os.path.expanduser("~/.sovereign_share"))

SYSTEM = """You are the Sovereign Agent — a node-local mind running on the operator's OWN iron via a loopback model.
You READ node state and ADVISE the operator (KM-1176). Objective: LGP — help the node earn and operate.
You have NO ability to execute anything. If a consequential action is warranted (issue/renew/revoke a grant,
change units/capacity, start/stop a service, send anything over a Port), you MUST NOT claim to do it. Instead emit:
  PROPOSE: <one-line intent>
  RUN: <the exact command KM would run>
  GATE: <the human gate/approval or keyboard act that authorizes it>
Consequential state stays behind KM's keyboard. Be concise, practical, income/ops-useful. Integrity-only —
claim no channel secrecy. If you are unsure, say so and propose a read-only check."""


# ── read-first tools (all read-only; no mutation anywhere in this file) ──────────
def _node():
    try:
        from sovereign_agent.keystore.node_keystore import load_node_key
        k = load_node_key(os.environ.get("NODE_KEYSTORE_DIR"),
                          os.environ.get("BREATHLINE_NODE_NAME", "UniversalSovereignNode"))
        return {"have_key": True, "fingerprint": k.fingerprint, "public_hex": k.public_hex[:16] + "…"}
    except Exception as e:  # noqa: BLE001
        return {"have_key": False, "note": f"no durable key ({type(e).__name__})"}


def _grant():
    grants = []
    for f in sorted(glob.glob(os.path.join(SHARE_DIR, "grant_*.json"))):
        try:
            g = json.load(open(f, encoding="utf-8"))
            d = (g.get("grant", {}).get("delegation", {}) or {}).get("payload", {})
            grants.append({"file": os.path.basename(f), "to": d.get("delegate_to"),
                           "models": g.get("models"), "expires": d.get("expires_at")})
        except Exception:  # noqa: BLE001
            grants.append({"file": os.path.basename(f), "note": "unreadable"})
    units = None
    reg_dir = os.path.join(SHARE_DIR, "registry")
    if os.path.exists(os.path.join(reg_dir, "objects.ndjson")):
        try:
            from sovereign_agent.objects.registry import ObjectRegistry   # the ONE chain gateway (§1)
            cur = ObjectRegistry(reg_dir).current()
            cap = next((v for k, v in cur.items() if k.startswith("capacity:")), None)
            if cap:
                units = (cap.get("payload") or {}).get("units")
        except Exception:  # noqa: BLE001
            pass
    return {"grants": grants, "offered_units_remaining": units}


def _loopback(url: str) -> str:
    """M1: the mind is loopback by structure. Refuse a non-loopback URL — do not even probe it."""
    host = re.sub(r"^https?://", "", url).split("/")[0].split(":")[0]
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit(f"refused: the mind is loopback-only (got host {host!r}) — no cloud brain, not even to probe")
    return url


def _gpu():
    import shutil
    if not shutil.which("nvidia-smi"):        # three-state: absent
        return {"state": "no-check", "note": "nvidia-smi not installed — GPU not checkable on this iron"}
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.free,utilization.gpu",
                                       "--format=csv,noheader,nounits"], text=True, timeout=8)
        free, util = (x.strip() for x in out.strip().splitlines()[0].split(","))
        return {"state": "ok", "free_mib": int(free), "util_pct": int(util)}   # found
    except Exception as e:  # noqa: BLE001
        return {"state": "error", "note": f"nvidia-smi present but failed ({type(e).__name__})"}   # could-not-read


def _peers():
    pb = os.environ.get("SOVEREIGN_PEER_BOOK", os.path.expanduser("~/.sovereign_peer_book.jsonl"))
    if not os.path.exists(pb):
        return {"count": 0}
    rows = [json.loads(raw) for raw in open(pb, encoding="utf-8") if raw.strip()]  # local .jsonl (peer_book idiom)
    return {"count": len(rows), "labels": [r.get("label") for r in rows]}


def _reachable(url):
    try:
        urllib.request.urlopen(url, timeout=3); return True
    except Exception:  # noqa: BLE001
        return False


def _transport(model_url=MODEL_URL_DEFAULT):
    tags = re.sub(r"/api/.*$", "/api/tags", model_url)
    puller = False
    try:
        puller = subprocess.call(["pgrep", "-f", "compute_share_pull"], stdout=subprocess.DEVNULL) == 0
    except Exception:  # noqa: BLE001
        pass
    return {"model_loopback_up": _reachable(tags), "puller_running": puller}


def gather(model_url=MODEL_URL_DEFAULT) -> dict:
    return {"node": _node(), "grant": _grant(), "gpu": _gpu(), "peers": _peers(),
            "transport": _transport(model_url)}


# ── exact, node-filled action templates (v0.1) — copy-paste-ready RUN text, still nothing executes ──
def _action_templates() -> dict:
    """Build the EXACT renew/revoke command for each present grant, filled from the node's own state so a proposal
    is copy-paste-ready — never a model-invented flag. Read-only: reads grant JSON + registry, prints, runs nothing."""
    node = os.environ.get("BREATHLINE_NODE_NAME", "UniversalSovereignNode")
    reg = os.path.join(SHARE_DIR, "registry")
    units = _grant().get("offered_units_remaining") or "100"
    ks = os.environ.get("NODE_KEYSTORE_DIR", "~/.sovereign_keystore")
    tpls = []
    for f in sorted(glob.glob(os.path.join(SHARE_DIR, "grant_*.json"))):
        try:
            g = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        d = (g.get("grant", {}).get("delegation", {}) or {}).get("payload", {})
        to = d.get("delegate_to", "<peer>")
        rpub = g.get("requester_public_hex", "<PEER_PUBLIC_HEX>")
        models = " ".join(g.get("models") or ["<model>"])
        renew = (f"NODE_KEYSTORE_DIR={ks} python3 scripts/compute_share_offer.py --node {node} --units {units} "
                 f"--renew-days 7 --approver KM-1176 --approval-ref km-renew-{to.lower()} "
                 f"--requester-name {to} --requester-public-hex {rpub} --models {models} "
                 f"--registry {reg} --emit-grant {f} --min-gpu-free-mib 20000")
        tpls.append({"peer": to, "expires": d.get("expires_at"), "grant_file": f,
                     "renew_run": renew, "revoke_run": f"rm {f}",
                     "revoke_effect": "standing puller reloads each poll → denies the next job within ~5s (live revoke)"})
    return {"node": node, "grants": tpls}


def _templates_text(t: dict) -> str:
    if not t["grants"]:
        return "  (no grant files present — nothing to renew/revoke; use compute_share_offer.py to issue a first offer)"
    out = []
    for g in t["grants"]:
        out.append(f"  peer {g['peer']} (expires {g['expires']}):")
        out.append(f"    RENEW 7d — RUN: {g['renew_run']}")
        out.append(f"    REVOKE  — RUN: {g['revoke_run']}   ({g['revoke_effect']})")
        out.append("    GATE: KM keyboard (issue/renew/revoke is a human act)")
    return "\n".join(out)


# ── loopback model call (same fence as compute_share: 127.0.0.1 only) ───────────
def _complete(model_url: str, model: str, prompt: str) -> str:
    host = re.sub(r"^https?://", "", model_url).split("/")[0].split(":")[0]
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit(f"refused: the mind is loopback-only (got host {host!r}) — no cloud brain")
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(model_url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:      # noqa: S310 (loopback-enforced above)
        data = json.loads(r.read().decode("utf-8"))
    return data.get("response") or data.get("message", {}).get("content", "") or json.dumps(data)[:400]


def cmd_status(a) -> int:
    _loopback(getattr(a, "model_url", MODEL_URL_DEFAULT))     # M1: refuse a non-loopback session before any probe
    ctx = gather(getattr(a, "model_url", MODEL_URL_DEFAULT))
    print("∞Δ∞ Sovereign Agent v0 · node status (read-only) · integrity-only, observable in transit")
    n = ctx["node"]
    print(f"  node        : {'fp ' + n['fingerprint'] if n.get('have_key') else n.get('note')}")
    g = ctx["grant"]
    print(f"  grant(s)    : {len(g['grants'])} · units offered (latest capacity): {g['offered_units_remaining']}")
    for gr in g["grants"]:
        print(f"                - {gr.get('file')} → {gr.get('to')} · models {gr.get('models')} · expires {gr.get('expires')}")
    gp = ctx["gpu"]
    print(f"  gpu         : {gp['free_mib']} MiB free · {gp['util_pct']}% util" if gp.get("state") == "ok" else f"  gpu         : {gp.get('note')} [{gp.get('state')}]")
    print(f"  peers       : {ctx['peers']['count']} known {ctx['peers'].get('labels', [])}")
    t = ctx["transport"]
    print(f"  transport   : model-loopback {'UP' if t['model_loopback_up'] else 'down'} · puller {'running' if t['puller_running'] else 'stopped'}")
    return 0


def cmd_propose(a) -> int:
    """Deterministic, model-free: print the EXACT copy-paste-ready renew/revoke for every present grant."""
    t = _action_templates()
    print("∞Δ∞ Sovereign Agent v0 · EXACT proposals (nothing executed — KM's keyboard authorizes)\n")
    print(_templates_text(t))
    print("\n(read-only: the agent printed exact command text; it ran nothing. Consequential change stays behind KM.)")
    return 0


def cmd_ask(a) -> int:
    _loopback(a.model_url)                                    # M1: refuse a non-loopback session before any probe
    ctx = gather(a.model_url)
    tpl = _templates_text(_action_templates())
    prompt = (f"{SYSTEM}\n\nNODE CONTEXT (read-only tools):\n{json.dumps(ctx, indent=2)}\n\n"
              f"EXACT ACTION TEMPLATES — if you propose a renew or revoke, COPY the RUN line VERBATIM from here; "
              f"never invent flags:\n{tpl}\n\nOPERATOR (KM-1176) ASKS:\n{a.prompt}\n\n"
              f"Answer concisely. Propose (do not execute) any consequential act, quoting the exact RUN line above.")
    try:
        ans = _complete(a.model_url, a.model, prompt)
    except urllib.error.URLError:
        print(f"✗ loopback model not answering at {a.model_url} — start it (e.g. `ollama serve`), then ask again.")
        return 3
    print("∞Δ∞ Sovereign Agent v0 · local answer (loopback mind · propose-only)\n")
    print(ans.strip())
    props = re.findall(r"PROPOSE:.*?(?=\n\s*\n|\Z)", ans, re.S)
    if props:
        print("\n— PROPOSED ACTS (NOT executed — KM's keyboard / gate authorizes) —")
        for p in props:
            print("  " + p.strip().replace("\n", "\n  "))
    print("\n(agent v0 read state and advised; it executed nothing. Consequential change stays behind KM.)")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Sovereign Agent v0 — node-local mind, read-first + propose-only.")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status"); s.add_argument("--model-url", default=MODEL_URL_DEFAULT); s.set_defaults(fn=cmd_status)
    pr = sub.add_parser("propose"); pr.set_defaults(fn=cmd_propose)   # deterministic exact renew/revoke, no model
    q = sub.add_parser("ask")
    q.add_argument("--prompt", required=True)
    q.add_argument("--model", default="llama3.2:1b")
    q.add_argument("--model-url", default=MODEL_URL_DEFAULT)
    q.set_defaults(fn=cmd_ask)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
