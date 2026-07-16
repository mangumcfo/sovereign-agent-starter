#!/usr/bin/env python3
"""seed_fix.py — P3 draft-fix work order on the local model host (prose lane, zero frontier).

Takes a seed card + its KILL adversary record, asks the local prose model to rewrite
ONLY the prose so every beat is served at chapter scope and no claim outruns
runs_today. Writes a NEW card (<name>_fixed.yaml) — never overwrites the source.
30B rule honored: self-contained order, schema-strict JSON out, exemplared,
deterministically verified afterward by seed_adversary (the fixer never self-certifies).

Usage: seed_fix.py <card.yaml> <adversary_record.json> [--out DIR]
Env:   PRESS_LOCAL_MODEL_HOST / ADVERSARY_L1_MODEL (shared with the adversary)
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

import yaml

LOCAL_HOST = os.environ.get("PRESS_LOCAL_MODEL_HOST", "")  # the node sets this; no default network
OLLAMA = f"http://{LOCAL_HOST}:11434" if LOCAL_HOST else ""
MODEL = os.environ.get("ADVERSARY_L1_MODEL", "gemma4:31b")

ORDER = """You are fixing a book chapter SEED that an adversarial review KILLED.
Rewrite ONLY the prose so that: (a) every beat in the beats list is SERVED at chapter
scope — state what it is and the design principle behind it in 2-3 sentences (no
implementation detail needed); (b) no sentence claims a capability as existing/live
unless the runs_today list backs it — prospective design stays in future/design voice;
(c) keep the original voice, length within +-30%, and everything that already works.

Return ONLY a JSON object: {"prose": "<the full rewritten prose>"}

Example of serving a beat that was only name-dropped: instead of "later sections also
touch on honest rendering guarantees", write "The honest rendering guarantee is the
constitutional piece: a lens may hide fields, but never invent values or reorder
history, and every lens declares what it omits." """


def main():
    if not LOCAL_HOST:
        sys.exit("fixer requires PRESS_LOCAL_MODEL_HOST (unconfigured — refusing)")
    card_p, rec_p = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else card_p.parent
    card = yaml.safe_load(card_p.read_text(encoding="utf-8"))
    rec = json.loads(rec_p.read_text())
    kill_reasons = [v["reason"] for v in rec.get("verdicts", []) if v.get("refuted")]

    payload = {"model": MODEL, "stream": False, "format": "json",
               "options": {"temperature": 0},
               "messages": [{"role": "system", "content": ORDER},
                            {"role": "user", "content": json.dumps({
                                "promise": card.get("promise"), "beats": card.get("beats"),
                                "runs_today": card.get("runs_today"),
                                "kill_reasons": kill_reasons,
                                "prose": card.get("prose")}, ensure_ascii=False)}]}
    req = urllib.request.Request(f"{OLLAMA}/api/chat", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    for attempt in (1, 2):
        with urllib.request.urlopen(req, timeout=900) as r:
            content = json.loads(r.read())["message"]["content"]
        try:
            fixed_prose = json.loads(content)["prose"]
            break
        except (json.JSONDecodeError, KeyError):
            if attempt == 2:
                sys.exit(f"SEED_FIX FAIL: non-schema output twice: {content[:200]}")
    card["prose"] = fixed_prose
    card.pop("_file", None)
    out = out_dir / (card_p.stem + "_fixed.yaml")
    out.write_text(yaml.safe_dump(card, sort_keys=False, allow_unicode=True))
    print(f"[FIXED] {card_p.name} -> {out}  model={MODEL}@local")


if __name__ == "__main__":
    main()
