"""local_mind.py — read-first tools + a LOOPBACK completion + propose-only templates for the node's mind.

Composed by the CLI and by the node_api chat route. Everything here is READ-ONLY and loopback-only; it has no
code path that mutates state. Consequential acts (issue/renew/revoke a grant) are returned as PROPOSE text that
goes to KM's keyboard / the Gate Inbox — never executed here. The model call is OpenAI-compatible
(/v1/chat/completions — Ollama today, vLLM/Qwen-MoE tomorrow) with an Ollama-native fallback.
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import urllib.error
import urllib.request

SHARE_DIR_DEFAULT = os.path.expanduser("~/.sovereign_share")
CHAT_URL_DEFAULT = os.environ.get("BREATHLINE_MIND_URL", "http://127.0.0.1:11434/v1/chat/completions")

SYSTEM = (
    "You are the Sovereign Agent — a node-local mind on the operator's OWN iron via a loopback model. You READ "
    "node state and ADVISE KM-1176 (objective: LGP — help the node earn and operate). You have NO ability to "
    "execute anything. For any consequential act (issue/renew/revoke a grant, change units, start/stop a service, "
    "send over a Port) do NOT claim to do it — emit:\n  PROPOSE: <intent>\n  RUN: <exact command>\n  GATE: <the "
    "human gate / keyboard act>\nConsequential state stays behind KM's keyboard. Be concise and income/ops-useful. "
    "Integrity-only; claim no channel secrecy. When you propose renew/revoke, quote the exact RUN line you are given."
)


def _loopback_or_die(url: str) -> str:
    host = re.sub(r"^https?://", "", url).split("/")[0].split(":")[0]
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError(f"the mind is loopback-only (got host {host!r}) — no cloud brain")
    return url


def _share_dir() -> str:
    return os.environ.get("SHARE_ROOT", SHARE_DIR_DEFAULT)


def _gpu():
    import shutil
    if not shutil.which("nvidia-smi"):
        return {"state": "no-check", "note": "nvidia-smi not installed"}
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.free,memory.total,utilization.gpu",
                                       "--format=csv,noheader,nounits"], text=True, timeout=8)
        free, total, util = (x.strip() for x in out.strip().splitlines()[0].split(","))
        return {"state": "ok", "free_mib": int(free), "total_mib": int(total), "util_pct": int(util)}
    except Exception as e:  # noqa: BLE001
        return {"state": "error", "note": f"nvidia-smi failed ({type(e).__name__})"}


def _grants():
    node = os.environ.get("BREATHLINE_NODE_NAME", "UniversalSovereignNode")
    ks = os.environ.get("NODE_KEYSTORE_DIR", os.path.expanduser("~/.sovereign_keystore"))
    reg = os.path.join(_share_dir(), "registry")
    units = None
    if os.path.exists(os.path.join(reg, "objects.ndjson")):
        try:
            from ..objects.registry import ObjectRegistry
            cur = ObjectRegistry(reg).current()
            cap = next((v for k, v in cur.items() if k.startswith("capacity:")), None)
            if cap:
                units = (cap.get("payload") or {}).get("units")
        except Exception:  # noqa: BLE001
            pass
    out = []
    for f in sorted(glob.glob(os.path.join(_share_dir(), "grant_*.json"))):
        try:
            g = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        d = (g.get("grant", {}).get("delegation", {}) or {}).get("payload", {})
        to = d.get("delegate_to", "<peer>")
        rpub = g.get("requester_public_hex", "<PEER_PUBLIC_HEX>")
        models = " ".join(g.get("models") or ["<model>"])
        renew = (f"NODE_KEYSTORE_DIR={ks} python3 scripts/compute_share_offer.py --node {node} --units {units or 100} "
                 f"--renew-days 7 --approver KM-1176 --approval-ref km-renew-{str(to).lower()} --requester-name {to} "
                 f"--requester-public-hex {rpub} --models {models} --registry {reg} --emit-grant {f} --min-gpu-free-mib 20000")
        out.append({"file": os.path.basename(f), "peer": to, "expires": d.get("expires_at"), "models": g.get("models"),
                    "renew_run": renew, "revoke_run": f"rm {f}"})
    return {"node": node, "units": units, "grants": out}


def _node_fp():
    try:
        from ..keystore.node_keystore import load_node_key
        k = load_node_key(os.environ.get("NODE_KEYSTORE_DIR", os.path.expanduser("~/.sovereign_keystore")),
                          os.environ.get("BREATHLINE_NODE_NAME", "UniversalSovereignNode"))
        return k.fingerprint
    except Exception:  # noqa: BLE001
        return None


def _puller_running():
    try:
        return subprocess.call(["pgrep", "-f", "compute_share_pull"], stdout=subprocess.DEVNULL) == 0
    except Exception:  # noqa: BLE001
        return False


def facts() -> dict:
    g = _grants()
    return {"node_fp": _node_fp(), "gpu": _gpu(), "grants": g["grants"], "units_offered": g["units"],
            "puller_running": _puller_running()}


def pick_model(tags_url: str = "http://127.0.0.1:11434/api/tags"):
    """Largest installed local tag that fits the card (budget on TOTAL VRAM; never a <3B if bigger fits)."""
    try:
        data = json.loads(urllib.request.urlopen(_loopback_or_die(tags_url), timeout=5).read().decode())
    except Exception:  # noqa: BLE001
        return None
    total = _gpu().get("total_mib")
    cands = []
    for m in data.get("models", []):
        name = m.get("name")
        if not name:
            continue
        pm = re.search(r"([\d.]+)\s*B", (m.get("details") or {}).get("parameter_size", ""), re.I)
        pb = float(pm.group(1)) if pm else 0.0
        size_mib = (m.get("size", 0) or 0) / 1048576
        if total and size_mib > total * 0.92:
            continue
        cands.append((pb, size_mib, name))
    if not cands:
        return None
    cands.sort(reverse=True)
    big = [c for c in cands if c[0] >= 3.0]
    return (big or cands)[0][2]


def complete(prompt: str, *, model: str, chat_url: str = CHAT_URL_DEFAULT, system: str = SYSTEM) -> str:
    """OpenAI-compatible chat completion over a LOOPBACK endpoint (Ollama or vLLM); Ollama-native fallback."""
    _loopback_or_die(chat_url)
    if "/v1/" in chat_url or chat_url.endswith("/chat/completions"):
        body = {"model": model, "messages": [{"role": "system", "content": system},
                                              {"role": "user", "content": prompt}], "stream": False}
        req = urllib.request.Request(chat_url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=180) as r:  # noqa: S310 (loopback-enforced)
            data = json.loads(r.read().decode())
        return (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
    # Ollama-native /api/generate fallback
    body = {"model": model, "prompt": f"{system}\n\n{prompt}", "stream": False}
    req = urllib.request.Request(chat_url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:  # noqa: S310
        return json.loads(r.read().decode()).get("response", "")


def proposals_text(f: dict) -> str:
    if not f["grants"]:
        return "(no grant files present — nothing to renew/revoke)"
    out = []
    for g in f["grants"]:
        out.append(f"peer {g['peer']} (expires {g['expires']}):")
        out.append(f"  RENEW 7d — RUN: {g['renew_run']}")
        out.append(f"  REVOKE  — RUN: {g['revoke_run']}   (puller reloads each poll → denies next job ~5s)")
        out.append("  GATE: KM keyboard (issue/renew/revoke is a human act)")
    return "\n".join(out)
