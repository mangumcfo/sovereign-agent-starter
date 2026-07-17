#!/usr/bin/env python3
"""seed_adversary.py — P2 of the Press: the panel runs on the SEED, before drafting/extrusion.

Contract: CONTRACTS_P2_P4.md (frozen 2026-07-16).
  seed_adversary.py <volume-id> --level L0|L1 [--chapter N] [--seeds DIR]

Levels built this increment (L2 frontier panel = contract only, not built):
  L0 — deterministic, no model: weasel lexicon · ungated present-tense accomplishment
       (the "hopeful verb" that launders a plan into an achievement) · promise-coverage
       (every locked beat's tokens present in the prose — the deterministic ceiling) ·
       claims discipline (evidence_grade + source; roadmap citations resolved against
       the golden record — drift fails).
  L1 — one chapter per call on the local model host (gemma4:31b prose lane, temperature 0,
       schema-strict JSON): judgment the lints can't make — is a named beat actually
       SERVED, not just name-dropped? Rental law honored: GPU must be idle (>=20GB
       free) before any local call; orders are single-model (batching law).

Output (contract): artifacts/adversary/<volume>/<ts>_L<level>.json
  {volume, level, verdicts[]{chapter, lens, refuted, reason}, result: PASS|KILL,
   killed_back_to, record_sha256}
Floor law: gates never relax by model class — L0 is identical for everyone.
Refuter identity != builder identity is enforced at the phase level (builder hand
does not validate this build) and recorded in each record's "refuter" field.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import yaml

REPO = Path(os.environ.get("PRESS_DATA_ROOT") or Path.cwd())
ROADMAP = REPO / "artifacts" / "series_roadmap.yaml"
OUT_ROOT = REPO / "artifacts" / "adversary"

LOCAL_HOST = os.environ.get("PRESS_LOCAL_MODEL_HOST", "")  # the node sets this; no default network
LOCAL_SSH = os.environ.get("PRESS_LOCAL_GPU_SSH", "")  # ssh target for the GPU-idle check
OLLAMA = f"http://{LOCAL_HOST}:11434" if LOCAL_HOST else ""
L1_MODEL = os.environ.get("ADVERSARY_L1_MODEL", "gemma4:31b")
GPU_FREE_MIN_MB = 20000  # never interrupt a rental of the shared GPU (operator law)

WEASEL = [
    "seamlessly", "effortlessly", "best-in-class", "world-class", "revolutionary",
    "just works", "trivially", "obviously", "will simply", "simply works",
    "state-of-the-art", "cutting-edge", "game-chang", "frictionless",
]
# Present-tense accomplishment: the hopeful verb that launders a plan into a fact.
ACCOMPLISHMENT = re.compile(
    r"\b(already|now)\s+(runs|works|ships|serves|handles|scales|supports)\b"
    r"|\bruns today\b|\bis live\b|\bin production\b", re.I)
STOP = set("the a an of to in for and or with your you will that this is are be on any".split())

# Placeholder markers that mean a beat is scaffolding, not a locked promise.
PLACEHOLDER_BEAT = re.compile(r"\b(tbd|todo|placeholder|tktk|xxx|lorem)\b", re.I)

# Typesetting furniture a full chapter may lawfully END with: \newpage, horizontal
# rules, headings, bold-only lines, blank lines. Furniture stays IN the prose — it
# is chapter content — but the end-of-chapter check reads the last PROSE line
# beneath it. (Shared rule with the seed generation side; found by whole-pipeline
# verification: a genuine full chapter ending in furniture was falsely refused.)
FURNITURE = re.compile(r"^(\\newpage|-{3,}|#+\s.*|\*\*[^*]+\*\*|\s*)$")


def _tokens(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP}


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def validate_seed_unit(card):
    """THE SEED-UNIT LAW (A4, operator-ruled): the adversary's seed unit is the
    FULL CHAPTER plus LOCKED beats — enforced here, at the one choke point every
    node's cards pass through, never by convention. The law exists because the
    model judges inputs literally: placeholder beats get judged as real beats,
    and chapter excerpts produce honest false-kills ("cuts off mid-sentence").
    Returns a refusal reason, or None for a lawful card."""
    if card.get("seed_unit") != "full_chapter":
        return ("seed-unit law (A4): card must attest seed_unit: full_chapter — "
                "excerpts are refused at load, not judged")
    if card.get("beats_locked") is not True:
        return ("seed-unit law (A4): beats_locked: true required — "
                "unlocked beats are scaffolding, not promises")
    beats = card.get("beats") or []
    if not beats:
        return "seed-unit law (A4): no beats — nothing promised, nothing to adversary"
    placeholders = [b for b in beats if PLACEHOLDER_BEAT.search(str(b))]
    if placeholders:
        return f"seed-unit law (A4): placeholder beats refused: {placeholders}"
    prose = (card.get("prose") or "").strip()
    if len(_sentences(prose)) < 3:
        return ("seed-unit law (A4): prose too short to be a full chapter "
                "(fewer than 3 sentences)")
    lines = [ln for ln in prose.splitlines() if not FURNITURE.match(ln.strip())]
    last_prose = lines[-1].strip() if lines else ""
    if not re.search(r"[.!?][\"'”’)\]`]*\s*$", last_prose):
        return ("seed-unit law (A4): prose ends mid-sentence — excerpt refused "
                "(the false-kill class the law exists to prevent; trailing "
                "typesetting furniture is skipped, not judged)")
    return None


def load_cards(seeds_dir: Path, chapter=None):
    cards = []
    for p in sorted(seeds_dir.glob("*.yaml")):
        c = yaml.safe_load(p.read_text(encoding="utf-8"))
        c["_file"] = str(p)
        if chapter is None or c.get("chapter") == chapter:
            reason = validate_seed_unit(c)
            if reason:
                sys.exit(f"ADVERSARY FAIL: {p.name}: {reason}")
            cards.append(c)
    if not cards:
        sys.exit(f"ADVERSARY FAIL: no seed cards in {seeds_dir} (default-deny)")
    return cards


def _resolve_record(path_expr):
    """Resolve 'series[<number>].<field>' or 'series[<n>].titles[<i>].<field>'
    against the golden record. Returns the value or raises KeyError."""
    r = yaml.safe_load(ROADMAP.read_text(encoding="utf-8"))
    m = re.fullmatch(r"series\[(\d+)\](?:\.titles\[(\d+)\])?\.(\w+)", path_expr.strip())
    if not m:
        raise KeyError(f"unsupported record path: {path_expr}")
    ser = next(s for s in r["series"] if s.get("series_number") == int(m.group(1)))
    node = ser["titles"][int(m.group(2))] if m.group(2) is not None else ser
    return node[m.group(3)]


def l0_check(card):
    """Deterministic lenses. Returns list of verdicts (refuted=True kills)."""
    verdicts, ch = [], card.get("chapter")
    prose = card.get("prose", "")

    hits = [w for w in WEASEL if w in prose.lower()]
    verdicts.append({"chapter": ch, "lens": "L0:weasel", "refuted": bool(hits),
                     "reason": f"weasel language: {hits}" if hits else "clean"})

    runs_today = " ".join(card.get("runs_today") or []).lower()
    bad = []
    for s in _sentences(prose):
        if ACCOMPLISHMENT.search(s):
            key = _tokens(s)
            if not key or len(key & _tokens(runs_today)) / max(len(key), 1) < 0.2:
                if "designed-toward" not in s.lower() and "designed toward" not in s.lower():
                    bad.append(s[:90])
    verdicts.append({"chapter": ch, "lens": "L0:ungated_accomplishment", "refuted": bool(bad),
                     "reason": ("present-tense accomplishment with no runs_today backing: "
                                + " | ".join(bad)) if bad else "clean"})

    missing = []
    pt = _tokens(prose)
    for beat in card.get("beats") or []:
        bt = _tokens(beat)
        if bt and len(bt & pt) / len(bt) < 0.5:
            missing.append(beat)
    verdicts.append({"chapter": ch, "lens": "L0:promise_coverage", "refuted": bool(missing),
                     "reason": f"beats with no textual presence: {missing}" if missing
                     else "all beats textually present (NOTE: presence != served — L1's lens)"})

    bad_claims, drift = [], []
    for cl in card.get("claims") or []:
        if cl.get("evidence_grade") not in ("MEASURED", "DERIVED", "DIRECTIONAL") or not cl.get("source"):
            bad_claims.append(cl.get("text", "?")[:60])
        src = cl.get("source", "")
        if src.startswith("roadmap:"):
            try:
                val = str(_resolve_record(src[len("roadmap:"):]))
                quoted = cl.get("value_quoted")
                if quoted is not None and quoted not in val:
                    drift.append(f"{src} record={val[:40]!r} != quoted={quoted!r}")
            except (KeyError, StopIteration, IndexError) as e:
                drift.append(f"{src} unresolvable: {e}")
    verdicts.append({"chapter": ch, "lens": "L0:claims_discipline", "refuted": bool(bad_claims),
                     "reason": f"claims missing grade/source: {bad_claims}" if bad_claims else "clean"})
    verdicts.append({"chapter": ch, "lens": "L0:record_drift", "refuted": bool(drift),
                     "reason": f"drift vs golden record: {drift}" if drift else "clean"})
    return verdicts


def _gpu_idle():
    if not (LOCAL_HOST and LOCAL_SSH):
        sys.exit("L1 requires PRESS_LOCAL_MODEL_HOST + PRESS_LOCAL_GPU_SSH (unconfigured — refusing, never guessing a network)")
    """Rental law: never interrupt a Vast.ai rental. GPU counts as ours if >=20GB
    free, OR the VRAM is held by our own resident Ollama lane model (batching law:
    one model resident at a time — our own lane is not a rental)."""
    try:
        out = subprocess.run(["ssh", "-o", "ConnectTimeout=5", LOCAL_SSH,
                              "nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=15).stdout.strip()
        if int(out.splitlines()[0]) >= GPU_FREE_MIN_MB:
            return True
        with urllib.request.urlopen(f"{OLLAMA}/api/ps", timeout=10) as r:
            loaded = [m.get("name") for m in json.loads(r.read()).get("models", [])]
        return loaded == [L1_MODEL]  # exactly our lane model resident, nothing else
    except Exception:
        return False


L1_WORK_ORDER = """You are an adversarial reviewer for a book chapter SEED. Try to REFUTE it.
A seed is a CHAPTER-LEVEL summary, not an implementation. The bar: a beat is SERVED if the
prose states what the thing IS and the design principle behind it, at chapter scope. Do NOT
refute for missing implementation detail, code, or how-to depth — every beat here will be a
summary. REFUTE only when: (a) a beat is merely name-dropped — mentioned in passing with zero
statement of what it is or why ("later sections also touch on X" with nothing more), or (b) a
sentence claims a capability as existing/live that the runs_today list does not back.

Return ONLY a JSON object, no prose, exactly this shape:
{"refuted": <bool>, "unserved_beats": [<entries copied EXACTLY from the beats list>],
 "overclaims": [<sentences claiming more than the evidence>], "weakest_paragraph": "<quote>",
 "reason": "<one sentence>"}

Worked example: beats include "Honest rendering guarantees"; the prose's only mention is
"later sections also touch on honest rendering guarantees" — that is a name-drop, not service:
unserved_beats=["Honest rendering guarantees"], refuted=true. But a beat explained in 2-3
sentences of principle IS served, even with no implementation given.
Judge only from the material below. If every beat is served at chapter scope and no claim
outruns runs_today, then refuted=false and the lists are empty."""


def l1_check(card):
    if not _gpu_idle():
        sys.exit("ADVERSARY FAIL: local GPU not idle (>=20GB free required) — "
                 "rental law: refusing local call; rerun when idle or escalate tier.")
    payload = {
        "model": L1_MODEL, "stream": False, "format": "json",
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": L1_WORK_ORDER},
            {"role": "user", "content": json.dumps({
                "promise": card.get("promise"), "beats": card.get("beats"),
                "runs_today": card.get("runs_today"), "prose": card.get("prose")},
                ensure_ascii=False)},
        ],
    }
    req = urllib.request.Request(f"{OLLAMA}/api/chat", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    for attempt in (1, 2):  # schema-strict: one retry, then fail loud
        with urllib.request.urlopen(req, timeout=600) as r:
            content = json.loads(r.read())["message"]["content"]
        try:
            v = json.loads(content)
            return {"chapter": card.get("chapter"), "lens": f"L1:{L1_MODEL}",
                    "refuted": bool(v.get("refuted")),
                    "reason": (v.get("reason", "") + " | unserved: " + json.dumps(v.get("unserved_beats", []))
                               + " | overclaims: " + json.dumps(v.get("overclaims", [])))[:400]}
        except (json.JSONDecodeError, AttributeError):
            if attempt == 2:
                sys.exit(f"ADVERSARY FAIL: L1 returned non-schema output twice: {content[:200]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("volume")
    ap.add_argument("--level", required=True, choices=["L0", "L1"])
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--seeds", help="seed-card dir (default: seeds/<volume>/ under CWD)")
    a = ap.parse_args()
    seeds = Path(a.seeds) if a.seeds else Path("seeds") / a.volume
    cards = load_cards(seeds, a.chapter)

    verdicts = []
    for c in cards:
        verdicts += l0_check(c) if a.level == "L0" else [l1_check(c)]
    killed = any(v["refuted"] for v in verdicts)
    rec = {"volume": a.volume, "level": a.level, "refuter": f"seed_adversary/{a.level}"
           + (f"+{L1_MODEL}@local" if a.level == "L1" else ""),
           "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
           "verdicts": verdicts, "result": "KILL" if killed else "PASS",
           "killed_back_to": "drafting" if killed else None}
    rec["record_sha256"] = hashlib.sha256(
        json.dumps(rec, sort_keys=True).encode()).hexdigest()
    out = OUT_ROOT / a.volume
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{rec['ts']}_{a.level}.json"
    path.write_text(json.dumps(rec, indent=2))
    for v in verdicts:
        mark = "KILL" if v["refuted"] else "pass"
        print(f"  [{mark}] ch{v['chapter']} {v['lens']}: {v['reason'][:140]}")
    print(f"[{rec['result']}] {a.volume} {a.level} -> {path}  record_sha={rec['record_sha256'][:16]}")
    return 1 if killed else 0


if __name__ == "__main__":
    sys.exit(main())
