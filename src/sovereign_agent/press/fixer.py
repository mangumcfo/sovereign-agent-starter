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
import re
import os
import sys
import urllib.request
from pathlib import Path

import yaml

LOCAL_HOST = os.environ.get("PRESS_LOCAL_MODEL_HOST", "")  # the node sets this; no default network
OLLAMA = f"http://{LOCAL_HOST}:11434" if LOCAL_HOST else ""
MODEL = os.environ.get("ADVERSARY_L1_MODEL", "gemma4:31b")

ORDER = """You are fixing a book chapter SEED that an adversarial review KILLED.
FIRST LAW: read the kill_reasons list and SATISFY EVERY ONE OF THEM explicitly — the
rewrite fails if any listed reason would still be true of the new prose. Kill-reason
classes and their required repairs:
- beat not served → serve it: state what it is and the design principle in 2-3 sentences.
- unqualified live claim → requalify to design voice unless runs_today backs it.
- banned voice / template frame / canon drift → remove or replace the exact phrasing named.
- concreteness_floor items → ADD the missing element named: 'no question' → work at least
  one genuine question into the prose (a reader's or a named actor's, not rhetorical
  filler); missing numerals → thread real numbers from the card's worked_example; missing
  named actor → let a named person from the card act. These are additions, not deletions —
  a floor kill can NEVER be satisfied by re-emitting the same prose.
- duplicated sentence / repeated span → rewrite one occurrence away entirely.
Also: (a) every beat in the beats list stays SERVED at chapter scope; (b) no sentence
claims a capability as existing/live unless the runs_today list backs it; (c) keep the
original voice, length within +-30%, and everything that already works.

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
    # D-3: only THIS card's refutations drive the repair — reasons harvested from other
    # chapters would steer the rewrite at prose that was never refuted.
    ch = str(card.get("chapter"))
    kill_reasons = [v["reason"] for v in rec.get("verdicts", [])
                    if v.get("refuted") and (str(v.get("chapter")) == ch or v.get("chapter") is None)]
    if not kill_reasons:
        sys.exit(f"SEED_FIX FAIL: record has no refuted verdicts for chapter {ch} — "
                 "nothing to repair for this card (D-3 targeting)")

    # think:false — ollama>=0.20 thinking-default regression (pilot-2 blocker, 2026-07-27)
    payload = {"model": MODEL, "stream": False, "think": False, "format": "json",
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
            # gemma (ollama>=0.20, think:false) wraps format:json output in a ```json fence —
            # strip before parse (Wall-1 defect, pilot-2 launch-2, 2026-07-27)
            content = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", content.strip())
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
