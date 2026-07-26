#!/usr/bin/env python3
"""prescreen.py — the deterministic quality gate wired into the cycle (gate_rev law).

Born from the D4 pilot escalation (2026-07-26): ch3 reached an adversary PASS while
carrying a fabricated house term ("LGP = Ledger-General-Purpose") and design-voice
violations ("Furthermore") — GATE-BLINDNESS. The adversary judges weasel/claims/beat
service; it has no canon or voice eyes. This module is those eyes, and it is
DETERMINISTIC BY LAW (pure pattern/vocab checks, zero model calls): every verdict
replays identically, forever.

GATE KILL SET (binding conditions, G/KM 2026-07-26):
  CHECK1  — unqualified live-capability claims in a runs_today:[] volume
  CHECK5  — banned voice (empty transitions · consultant-speak · throat-clearing · hedges)
  CANON   — house-term drift (LGP means 'Lasting Generational Prosperity', nothing else)
Advisory (recorded, never gating here): rhythm bands (CHECK8) and beat service (CHECK9)
— beat service is the adversary L1's judgment lane; rhythm is a style band, not a law.

Every record and receipt carries GATE_REV. A PASS without a gate version is invalid —
that is how gate-blindness hid. Bumping the gate = bump GATE_REV; metrics epoch-split.

Gate mode writes an adversary-format record (verdicts name the chapter) so the cycle's
fixer targeting (D-3) works unchanged: a prescreen KILL repairs exactly like an L1 KILL.
"""
from __future__ import annotations

import collections
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path

import yaml

GATE_REV = 2  # rev-2 (2026-07-26): + dup-n-gram / text-integrity kill (garbled duplicated
              # spans escaped rev-1). Bump on ANY kill-set change; never reuse a rev

LIVE = (r"\b(runs today|is live|are live|is running|are running|ships today|available today"
        r"|you can run (it|this) today|in production|is enforced|are enforced|enforces"
        r"|blocks at the write|code-traced|built \+ tested|already runs)\b")
QUAL = r"(designed.toward|\(planned\)|is the build|not built|structurally OFF|forward.arc|closes in|when built|the design calls for)"

BANNED = {
    "empty_transition": r'(?m)(?:^|[.!?"]\s)(Furthermore|Moreover|Additionally|In conclusion|In summary|To summarize|That said|Indeed|Notably|Importantly|Ultimately),',
    "consultant": r'(?i)\bleverag(?:e|es|ed|ing) (?:the|our|your|a|an|these|this)\b|\butiliz(?:e|es|ed|ing)\b|\b(?:seek|strive) to\b|\bholistic\b|\bparadigm shift\b|\bcutting.edge\b|\bgame.chang|\bsyner(?:gy|gies|gistic)\b|\brobust solution\b',
    "throat_clearing": r"(?i)in today's (?:fast.paced|rapidly|digital)|it is worth noting|it should be noted|let's dive|in this chapter, we will|as we have seen|at the end of the day|the bottom line is|unlock the power|harness the power|navigate the complexities|ever.evolving|delve into|tapestry|myriad|plethora",
    "hedged": r"(?i)\bcan help you\b|\bmay be able to\b|\bmight be able to\b|\bcould potentially\b",
}

# House canon: term -> the ONLY lawful expansion. The drafter is fed the glossary
# (prevention); this gate is the backstop (detection). Extend deliberately + bump rev.
CANON = {"LGP": "lasting generational prosperity"}


def _w(s):
    return len(re.findall(r"[A-Za-z'’]+", s))


def gate_card(card: dict) -> tuple[list, dict]:
    """Returns (violations, advisory). Violations = adversary-shaped verdict dicts."""
    prose = (card.get("prose") or "")
    ch = card.get("chapter")
    runs_today = [x for x in (card.get("runs_today") or []) if str(x).strip()]
    body_no_code = re.sub(r"```.*?```", "", prose, flags=re.S)
    body_no_bq = re.sub(r"(?m)^>.*$", "", body_no_code)
    v = []

    # CHECK1 — live claims a runs_today:[] volume cannot make
    if not runs_today:
        for s in re.split(r"(?<=[.!?])\s+", body_no_bq):
            if re.search(LIVE, s, re.I) and not re.search(QUAL, s, re.I):
                v.append({"chapter": ch, "lens": "L0:prescreen:live_claim", "refuted": True,
                          "reason": f"unqualified live-capability claim in runs_today:[] volume: {s.strip()[:120]!r}"})

    # CHECK5 — banned voice
    for name, pat in BANNED.items():
        hits = re.findall(pat, prose)
        if hits:
            flat = [h if isinstance(h, str) else next(x for x in h if x) for h in hits[:4]]
            v.append({"chapter": ch, "lens": f"L0:prescreen:voice_{name}", "refuted": True,
                      "reason": f"banned voice ({name}): {flat}"})

    # CANON — house-term drift
    for term, canonical in CANON.items():
        for m in re.finditer(r"([A-Za-z][A-Za-z \-]{5,60})\s*\(" + term + r"\)|" + term + r"\s*\(([^)]{5,60})\)", prose):
            exp = (m.group(1) or m.group(2) or "").strip()
            if exp and canonical not in exp.lower():
                v.append({"chapter": ch, "lens": "L0:prescreen:canon_drift", "refuted": True,
                          "reason": f"{term} expanded as {exp!r} (canon: {canonical!r})"})
        if re.search(r"\b" + term + r"\b", prose) and not re.search(canonical, prose, re.I):
            v.append({"chapter": ch, "lens": "L0:prescreen:canon_drift", "refuted": True,
                      "reason": f"{term} used but never expanded to canonical {canonical!r}"})
    if re.search(r"(?m)^#{1,6}.*agent-to-agent", prose, re.I):
        v.append({"chapter": ch, "lens": "L0:prescreen:canon_drift", "refuted": True,
                  "reason": "heading-level 'agent-to-agent' (canon term is 'peer role')"})

    # TEXT-INTEGRITY (rev-2) — garbled duplication: an identical normalized sentence
    # appearing 2+ times, or any 12-word n-gram repeating, is generation damage, not style.
    sents_n = [re.sub(r"\W+", " ", s).strip().lower()
               for s in re.split(r"(?<=[.!?])\s+", body_no_bq) if len(s.split()) >= 6]
    dup_s = [s for s, n in collections.Counter(sents_n).items() if n >= 2]
    words_l = re.findall(r"[a-z'’]+", body_no_bq.lower())
    g12 = collections.Counter(tuple(words_l[i:i+12]) for i in range(len(words_l) - 11))
    dup_g = [g for g, n in g12.items() if n >= 2]
    if dup_s:
        v.append({"chapter": ch, "lens": "L0:prescreen:text_integrity", "refuted": True,
                  "reason": f"duplicated sentence x{len(dup_s)}: {dup_s[0][:90]!r}"})
    if dup_g:
        v.append({"chapter": ch, "lens": "L0:prescreen:text_integrity", "refuted": True,
                  "reason": f"repeated 12-gram x{len(dup_g)}: {' '.join(dup_g[0])[:90]!r}"})

    # advisory (recorded, never gating)
    paras = [p.strip() for p in re.split(r"\n\s*\n", body_no_code)
             if p.strip() and not p.strip().startswith(("#", ">", "-", "*", "|"))]
    pw = [_w(p) for p in paras] or [0]
    cv = (statistics.pstdev(pw) / statistics.mean(pw)) if pw and statistics.mean(pw) else 0
    advisory = {"prose_words": _w(body_no_code), "para_CV": round(cv, 2)}
    return v, advisory


def main():
    args = sys.argv[1:]
    def opt(flag, default=None):
        return args[args.index(flag) + 1] if flag in args else default
    seeds = Path(opt("--seeds") or args[0])
    gate = "--gate" in args
    rec_dir = opt("--record-dir")
    vol = opt("--volume", "unknown")
    cards = []
    files = sorted(seeds.glob("ch*.yaml")) if seeds.is_dir() else [seeds]
    for p in files:
        if p.name.startswith("_") or p.name.endswith("_fixed.yaml"):
            continue
        c = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not (c.get("prose") or "").strip():
            print(f"prescreen SKIP (undrafted): {p.name}")
            continue
        cards.append(c)
    if not cards:
        sys.exit("PRESCREEN FAIL: no drafted cards to screen")
    verdicts, adv = [], {}
    for c in cards:
        vv, aa = gate_card(c)
        verdicts += vv
        adv[str(c.get("chapter"))] = aa
    result = "KILL" if verdicts else "PASS"
    print(json.dumps({"gate_rev": GATE_REV, "result": result,
                      "violations": len(verdicts), "advisory": adv}, indent=1))
    for x in verdicts:
        print(f"  [{x['lens']}] ch{x['chapter']}: {x['reason'][:140]}")
    if gate and verdicts:
        if rec_dir:
            os.makedirs(rec_dir, exist_ok=True)
            ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            rec = {"volume": vol, "level": "L0-prescreen", "gate_rev": GATE_REV,
                   "verdicts": verdicts, "result": "KILL"}
            Path(rec_dir, f"{ts}_L0prescreen.json").write_text(json.dumps(rec, indent=1))
        sys.exit(1)


if __name__ == "__main__":
    main()
