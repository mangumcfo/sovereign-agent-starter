#!/usr/bin/env python3
"""fixer.py — the TARGETED-PATCH repair lane (KM ruling 2026-07-27).

History: the original fixer rewrote the WHOLE prose per round. The ch6 arc proved that
churns at temperature 0 — every full rewrite re-samples the model's stylistic attractor,
re-introducing violations previous rounds cleared (a banned frame literally came back).
Local repairs converged (ch5's floor heal); global rewrites oscillated.

THE PATCH LAW now enforced here:
  1. Each kill reason's offending spans are located MECHANICALLY — with the SAME regexes
     the gate kills with (imported from prescreen: single source, never copied).
  2. ONLY those spans are rewritten (one tiny model call per span, temp 0).
  3. Patches are spliced back DETERMINISTICALLY (exact-string replacement).
  4. Every other byte of the existing prose is untouched — a violation cannot be
     re-introduced into text that is never rewritten.
  5. Additive classes (concreteness_floor, unserved beats) INSERT a generated passage
     at a deterministic point; they rewrite nothing.
Fail-closed: a span that cannot be located or a patch that cannot splice is a loud
SEED_FIX FAIL, never a silent whole-prose fallback (that would be the churn again).
Writes a NEW card (<name>_fixed.yaml) — never overwrites the source; never self-certifies.

Usage: fixer.py <card.yaml> <record.json> [--out DIR]
Env:   PRESS_LOCAL_MODEL_HOST / ADVERSARY_L1_MODEL (shared with the adversary)
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import yaml

from .prescreen import BANNED, BUDGET_PATTERNS, CANON, VP_BAN

LOCAL_HOST = os.environ.get("PRESS_LOCAL_MODEL_HOST", "")
OLLAMA = f"http://{LOCAL_HOST}:11434" if LOCAL_HOST else ""
MODEL = os.environ.get("ADVERSARY_L1_MODEL", "gemma4:31b")


def _call(system, user, key):
    """One tiny patch call. Returns the JSON field `key`. Fail-loud, schema-strict."""
    payload = {"model": MODEL, "stream": False, "think": False, "format": "json",
               "options": {"temperature": 0, "num_predict": 1024},
               "messages": [{"role": "system", "content": system},
                            {"role": "user", "content": user}]}
    req = urllib.request.Request(f"{OLLAMA}/api/chat", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    for attempt in (1, 2):
        with urllib.request.urlopen(req, timeout=600) as r:
            content = json.loads(r.read())["message"]["content"]
        content = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", content.strip())
        try:
            return json.loads(content)[key].strip()
        except (json.JSONDecodeError, KeyError):
            if attempt == 2:
                sys.exit(f"SEED_FIX FAIL: non-schema patch output twice: {content[:160]}")


def _sentences_matching(prose, pattern):
    """Sentences (in order) containing a match of pattern."""
    out = []
    for s in re.split(r"(?<=[.!?])\s+", prose):
        if s.strip() and re.search(pattern, s, re.I):
            out.append(s.strip())
    return out


REWRITE_SYS = ("You rewrite ONE sentence from a book chapter. Return ONLY JSON "
               '{"sentence": "<rewritten>"}. Keep the meaning and the surrounding voice; '
               "obey the constraint exactly; no new claims, no new named capabilities.")
INSERT_SYS = ("You write a SHORT insertion (1-3 sentences) for a book chapter. Return ONLY "
              'JSON {"passage": "<insertion>"}. Ground it in the chapter card material given; '
              "no new claims of live capability; match the surrounding voice.")


def _patch_sentence(prose, sentence, constraint):
    if sentence not in prose:
        sys.exit(f"SEED_FIX FAIL: located span not spliceable (drifted?): {sentence[:90]!r}")
    new = _call(REWRITE_SYS, json.dumps({"sentence": sentence, "constraint": constraint},
                                        ensure_ascii=False), "sentence")
    if not new or new == sentence:
        sys.exit(f"SEED_FIX FAIL: patch returned unchanged/empty for: {sentence[:90]!r}")
    return prose.replace(sentence, new, 1)


def main():
    if not LOCAL_HOST:
        sys.exit("fixer requires PRESS_LOCAL_MODEL_HOST (unconfigured — refusing)")
    card_p, rec_p = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else card_p.parent
    card = yaml.safe_load(card_p.read_text(encoding="utf-8"))
    rec = json.loads(rec_p.read_text())
    ch = str(card.get("chapter"))
    verdicts = [v for v in rec.get("verdicts", [])
                if v.get("refuted") and (str(v.get("chapter")) == ch or v.get("chapter") is None)]
    if not verdicts:
        sys.exit(f"SEED_FIX FAIL: record has no refuted verdicts for chapter {ch}")

    prose = card["prose"]
    patches = 0
    for v in verdicts:
        lens, reason = v.get("lens", ""), v.get("reason", "")

        if "template_frame" in lens:
            for s in _sentences_matching(prose, VP_BAN):
                prose = _patch_sentence(prose, s, "Remove the banned template frame; open the "
                                        "thought a different, concrete way.")
                patches += 1

        elif "template_budget" in lens:
            m = re.match(r"(.+?): (\d+) > budget (\d+)", reason)
            if not m or m.group(1) not in BUDGET_PATTERNS:
                sys.exit(f"SEED_FIX FAIL: unlocatable budget reason: {reason[:100]!r}")
            name, n, cap = m.group(1), int(m.group(2)), int(m.group(3))
            pat = BUDGET_PATTERNS[name][0]
            spans = _sentences_matching(prose, pat)
            excess = max(n - cap, 1)
            for s in spans[-excess:]:  # rewrite the LAST excess occurrences
                prose = _patch_sentence(prose, s, f"Express this WITHOUT the construction "
                                        f"({name}); vary the sentence shape.")
                patches += 1

        elif "voice_" in lens:
            cls = lens.split("voice_")[-1]
            pat = BANNED.get(cls)
            if not pat:
                sys.exit(f"SEED_FIX FAIL: unknown voice class {cls!r}")
            for s in _sentences_matching(prose, pat):
                if cls == "empty_transition":
                    # DETERMINISTIC: an empty transition is empty by definition — strip the
                    # connective mechanically, no model call (temp-0 echo made model patching
                    # of this class unreliable; observed live ch7 2026-07-27).
                    new_s = re.sub(r"^(?:Furthermore|Moreover|Additionally|In conclusion|"
                                   r"In summary|To summarize|That said|Indeed|Notably|"
                                   r"Importantly|Ultimately),\s*", "", s.strip())
                    if new_s and new_s != s.strip():
                        new_s = new_s[0].upper() + new_s[1:]
                        if s not in prose:
                            sys.exit(f"SEED_FIX FAIL: span not spliceable: {s[:90]!r}")
                        prose = prose.replace(s, new_s, 1)
                        patches += 1
                        continue
                prose = _patch_sentence(prose, s, "Remove the banned phrasing entirely; say it "
                                        "plainly in the house voice. You MUST NOT return the "
                                        "sentence unchanged — the banned wording must be gone.")
                patches += 1

        elif "canon_drift" in lens:
            term = next((t_ for t_ in CANON if t_ in reason), None)
            if term is None:
                sys.exit(f"SEED_FIX FAIL: unlocatable canon reason: {reason[:100]!r}")
            spans = _sentences_matching(prose, r"\b" + term + r"\b")
            if not spans:
                sys.exit(f"SEED_FIX FAIL: canon term {term!r} not found in prose")
            prose = _patch_sentence(prose, spans[0],
                                    f"On this first use, expand {term} to its full canonical "
                                    f"phrase: '{CANON[term].title()} ({term})'. Change nothing else.")
            patches += 1

        elif "text_integrity" in lens:
            m = re.search(r"repeated 12-gram x\d+: '(.{10,90})'", reason)
            gram = m.group(1).strip() if m else None
            if gram:
                spans = [s for s in _sentences_matching(prose, re.escape(gram.split()[0]))
                         if all(w in s.lower() for w in gram.split()[:6])]
            else:
                m2 = re.search(r"duplicated sentence x\d+: '(.{10,90})'", reason)
                key = m2.group(1).strip()[:60] if m2 else ""
                spans = [s for s in re.split(r"(?<=[.!?])\s+", prose)
                         if key and key[:40].lower() in re.sub(r"\W+", " ", s).strip().lower()]
            if len(spans) < 2:
                sys.exit(f"SEED_FIX FAIL: duplicate span not locatable twice: {reason[:100]!r}")
            prose = _patch_sentence(prose, spans[-1], "Rephrase completely so it repeats no "
                                    "long word-sequence from earlier in the chapter.")
            patches += 1

        elif "live_claim" in lens:
            m = re.search(r": '(.+?)'$", reason) or re.search(r': "(.+?)"$', reason)
            target = None
            if m:
                frag = m.group(1)[:60]
                hits = [s for s in re.split(r"(?<=[.!?])\s+", prose) if frag[:40] in s]
                target = hits[0].strip() if hits else None
            if not target:
                sys.exit(f"SEED_FIX FAIL: live-claim sentence not locatable: {reason[:100]!r}")
            prose = _patch_sentence(prose, target, "Requalify to design voice — this "
                                    "capability is designed-toward, not live.")
            patches += 1

        elif "concreteness_floor" in lens:
            ctx = json.dumps({"worked_example": card.get("worked_example"),
                              "need": reason}, ensure_ascii=False)[:2000]
            passage = _call(INSERT_SYS, ctx, "passage")
            paras = prose.split("\n\n")
            idx = 1 if len(paras) > 1 else 0
            paras.insert(idx + 1, passage)
            prose = "\n\n".join(paras)
            patches += 1

        else:
            # L1 verdicts NAME their spans in structured tails: "| overclaims: [..]" and
            # "| unserved: [..]" (adversary reason format). Overclaim sentences are
            # REWRITE targets (requalify); unserved beats are ADDITIVE. Never whole-prose.
            over, unserved = [], []
            mo = re.search(r"overclaims:\s*(\[.*?\])", reason)
            mu = re.search(r"unserved:\s*(\[.*?\])", reason)
            try:
                over = json.loads(mo.group(1)) if mo else []
            except json.JSONDecodeError:
                over = []
            try:
                unserved = json.loads(mu.group(1)) if mu else []
            except json.JSONDecodeError:
                unserved = []
            for oc in over:
                frag = str(oc)[:60]
                hits = [s for s in re.split(r"(?<=[.!?])\s+", prose) if frag[:40] in s]
                if not hits:
                    # locate by longest common fragment: fall back to token overlap
                    toks = [w for w in re.findall(r"[A-Za-z_./]{5,}", str(oc))][:4]
                    hits = [s for s in re.split(r"(?<=[.!?])\s+", prose)
                            if toks and all(tk in s for tk in toks[:2])]
                if not hits:
                    sys.exit(f"SEED_FIX FAIL: L1 overclaim not locatable: {str(oc)[:90]!r}")
                prose = _patch_sentence(prose, hits[0].strip(),
                                        "Requalify: this capability/binding is designed-toward, "
                                        "not live — keep the design content, drop the live claim.")
                patches += 1
            if unserved or not over:
                passage = _call(INSERT_SYS, json.dumps({
                    "kill_reason": reason[:400], "unserved_beats": unserved or None,
                    "beats": card.get("beats"),
                    "worked_example": card.get("worked_example")}, ensure_ascii=False)[:2500],
                    "passage")
                paras = prose.split("\n\n")
                paras.insert(max(len(paras) - 1, 1), passage)
                prose = "\n\n".join(paras)
                patches += 1

    card["prose"] = prose
    card.pop("_file", None)
    out = out_dir / (card_p.stem + "_fixed.yaml")
    out.write_text(yaml.safe_dump(card, sort_keys=False, allow_unicode=True))
    print(f"[FIXED-TARGETED] {card_p.name} -> {out}  patches={patches}  model={MODEL}@local "
          f"(spans only; all other bytes preserved)")


if __name__ == "__main__":
    main()
