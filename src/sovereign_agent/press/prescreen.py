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

GATE_REV = 6  # rev-6 (2026-07-27, 2nd production board — connective-tissue register): the
              # boards proved the tissue is generatively bad. New voice/pacing budgets, each
              # calibrated 0-fire across 9,180 published paragraphs: (1) "This X allows [Name]
              # to Y" frame KILLED on sight; (2) pronominalize — a full "First Last" name twice
              # in one paragraph kills (name once per scene); (3) cast-as-decoration — 2+ named
              # characters as reaction-verb subjects in one paragraph kills; (4) near-verbatim
              # restatement backstop (Jaccard>=0.6 within a paragraph). Class-shape pins (R-4):
              # possessive owner forms + name+managed-verb proximity. rev-5: bare-numeral +
              # apparatus-leak + pinned continuity. rev-4: spec-leak + duplicate-shingle.
              # scan + continuity-facts ledger check (volume mode). rev-3 = shape-aware exception.
              # Old rev-3 note: # rev-3 (2026-07-27, KM narrow ruling): shape-aware exception — comparison-led
              # chapters (card shape.name) get chiasmus cap 2->4 and 12-gram dup tolerance
              # >=2 -> >=3 (one twin-entity repeat allowed). EVERYTHING else unchanged.
              # Pack-level shape/budget reconciliation deferred to post-pilot design.
              # rev-2: + text-integrity kill. Bump on ANY kill-set change; never reuse a rev

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

# Template frames + budget locators — MODULE-LEVEL so the targeted-patch fixer locates
# spans with the SAME regexes that kill them (single source; KM ruling 2026-07-27).
VP_BAN = r"The fundamental failure of|The fundamental problem|The design calls for|The design principle here is"
BUDGET_PATTERNS = {
    "sentence-initial 'The design'": (r"(?m)(?:^|[.!?]\s)The design\b", 2),
    "'This ensures/…' frame": (r"\bThis (?:ensures|creates|prevents|eliminates|transforms|allows)\b", 3),
    "'ensures' family": (r"\bensur(?:es|e|ing)\b", 4),
    "not-X-but-Y chiasmus": (r"\bnot (?:a|an|the) [^,.;]{2,40}, but (?:a|an|the)\b", 2),
    "'The result is a'": (r"\bThe result is a\b", 1),
    "'structural'": (r"\bstructural\b", 2),
}

# House canon: term -> the ONLY lawful expansion. The drafter is fed the glossary
# (prevention); this gate is the backstop (detection). Extend deliberately + bump rev.
CANON = {"LGP": "lasting generational prosperity"}

# APPARATUS-LEAK (rev-5, production board §Stage-3): internal build/coordination language
# that must NEVER reach reader-facing text — body OR receipt boxes (PS-5: receipts are the
# product now). MODULE-LEVEL so the fixer strips with the same patterns that kill.
#   HARD  — kill on sight anywhere reader-facing (paths, pytest node ids, test-fn names,
#           schema nouns used as apparatus, internal agent/coordination phrasings).
#   STALE_RUNS — a post-extrusion volume may not print the pre-extrusion "nothing runs
#           today" absolute; the honest form names present foundations. Kills on sight.
APPARATUS_HARD = (
    r"(?:src|tests|tools|kdp|artifacts)/[A-Za-z0-9_./-]+\.(?:py|yaml|md|json)"
    r"|\btest_[A-Za-z0-9_]{3,}\b|::test_[A-Za-z0-9_]+"
    r"|\bblocks_seal\b|\bseed_rev\b|\bgate_rev\b|\bdraft_status\b|\bsettled_cycle\b"
    r"|\bwrite_rules\b|\bco_extrude\w*\b|\bacceptance_test\b|\bextrusion ledger\b"
    r"|\bstays? in (?:its|their|his|her) lane\b|\bobligation-granularity\b"
    r"|\bcontinuity ledger\b|\bcalibration bank\b|\bc-?extrusion\b"
    r"|\brendered from the volume's continuity\b")
APPARATUS_STALE_RUNS = (
    r"[Nn]othing in this volume'?s? object model runs today"
    r"|[Nn]othing .{0,30}runs today.{0,30}design only")


def bare_numeral_ends(body: str) -> list:
    """rev-5: sentences terminating on a BARE cardinal number that stands in for a dropped
    COUNT noun ("limited to a single 16." / "a calculation of 640." — the substitution
    artifacts the production board caught). Three necessary conditions, tuned so published
    prose passes (calibration: 0 fires on 1,098 published paragraphs; the two real garbles
    fire):
      1. the number sits in a NOUN slot — after an article/quantifier/preposition
         (a|an|the|single|only|just|of|to|into), NOT after a copula (is/are/was/were),
         so predicate values like "The proof depth is 16." are spared;
      2. no currency/percent marker ("$412,000." / "40%." are complete);
      3. the SAME number reappears elsewhere in the body immediately followed by a
         lowercase unit word ("16 siblings", "640 hashes") — proof the bare token is a
         lifted count with its noun dropped, not a deliberate rhetorical value
         ("the selling capacity of 7." — 7 carries no unit elsewhere — passes)."""
    # domain count-units: nouns this book counts. A bare sentence-final number whose unit
    # is one of these — dropped — is the artifact; years/scores/ratios never carry these.
    UNIT = (r"sibling|hash|object|proof|version|byte|check|leaf|leaves|node|row|item|"
            r"record|entry|entries|manifest|vendor|facilit|policy|policies|mandate|"
            r"crossing|class|classe|wave|attestation|transition|gate|packet")
    out = []
    for s in re.split(r"(?<=[.!?])\s+", body):
        s = s.strip()
        m = re.search(r"(?i)\b(?:a|an|the|single|only|just|of|to|into)\s+(\d[\d,]*)\.\s*$", s)
        if not m or re.search(r"(?i)\b(?:is|are|was|were|equals?)\s+\d[\d,]*\.\s*$", s):
            continue
        if re.search(r"[$%]\s*\d[\d,]*\.\s*$", s):
            continue
        num = re.escape(m.group(1))
        # the dropped noun is a domain count-unit that this number carries elsewhere
        if re.search(r"\b" + num + r"\s+(?:" + UNIT + r")", body, re.I):
            out.append(s[-70:])
    return out


def apparatus_leaks(texts) -> tuple:
    """rev-5: scan reader-facing strings (body + receipt/verify fields). Returns
    (hard_hits, stale_hits)."""
    blob = "\n".join(t for t in texts if t)
    hard = sorted(set(re.findall(APPARATUS_HARD, blob)))
    stale = re.findall(APPARATUS_STALE_RUNS, blob)
    return hard, stale


# rev-6 connective-tissue register budgets. Cast + reaction-verb vocab kept module-level
# so the drafter order and the fixer share one source. Each calibrated 0-fire on published.
_CAST_FULL = ("Dana Reyes", "Ilse Vogt", "Theo Ridgeline", "Harold Bhatt")
_CAST_ANY = r"(?:Dana|Ilse|Theo|Harold)"
_REACT = (r"(?:sees?|observes?|notes?|views?|watches|watched|recognizes?|relies|relied|"
          r"confirms?|understands?|understood|accepts?|considers?|examines?|monitors?|"
          r"realizes?|feels?|senses?)")
THIS_X_ALLOWS = (r"\b(?:This|The|These|That)\s+\w+(?:\s\w+)?\s+(?:allows?|enables?|lets|permits?)\s+"
                 # the actor: a named character (with optional surname), a role, or a bare
                 # party/organization/reader — the whole "lets them do X" scaffold the board killed
                 r"(?:" + _CAST_ANY + r"(?:\s+(?:Reyes|Vogt|Ridgeline|Bhatt))?"
                 r"|the\s+(?:controller|successor|auditor|trustee|operator|reader)"
                 r"|(?:a|an|the)\s+(?:party|organization|business|successor|auditor|operator|reader))"
                 r"\s+to\b")
_TISSUE_STOP = set("the a an of to in on for and or but is are was were be been that this these "
                   "those it its their his her they them he she we you your our with as at by from "
                   "into than then so not no can will would should could may might each every any "
                   "all one two some such other more most over under about which who whom whose when "
                   "where why how do does did has have had".split())


def _content_words(s):
    return {w for w in re.findall(r"[a-z']+", s.lower()) if len(w) > 3 and w not in _TISSUE_STOP}


def _is_narrative(s):
    s = s.strip()
    if not s or not s[0].isupper() or not s.endswith((".", "?", "!")):
        return False
    return not re.search(r"[\[\]\*\|]|^\d|\b\d\.$|\(\d+ points?\)", s)


def tissue_budgets(body: str) -> list:
    """rev-6: return violation dicts for the connective-tissue register budgets."""
    v = []
    paras = re.split(r"\n\s*\n", body)
    # (1) "This X allows [Name] to Y" frame — killed on sight
    allows = re.findall(THIS_X_ALLOWS, body, re.I)
    if allows:
        v.append(("tissue_this_x_allows", f"'This X allows [actor] to Y' frame x{len(allows)}: {allows[:3]}"))
    # (2) pronominalize — a full "First Last" name twice in one paragraph
    pron = []
    for p in paras:
        for full in _CAST_FULL:
            if len(re.findall(re.escape(full), p)) >= 2:
                pron.append(full)
    if pron:
        v.append(("tissue_pronominalize", f"full name repeated in a scene (pronominalize after first): {sorted(set(pron))}"))
    # (3) cast-as-decoration — 2+ named characters as reaction-verb subjects in one paragraph
    for p in paras:
        chars = set()
        for s in re.split(r"(?<=[.!?])\s+", p):
            m = re.match(r"\s*(" + _CAST_ANY + r")(?:\s+\w+)?\s+" + _REACT + r"\b", s)
            if m:
                chars.add(m.group(1))
        if len(chars) >= 2:
            v.append(("tissue_cast_decoration", f"cast-as-decoration: {sorted(chars)} each a reaction-verb subject in one paragraph"))
            break
    # (4) near-verbatim restatement backstop (synonym restatement is the L1's + drafter's job)
    for p in paras:
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", p) if len(s.split()) >= 8 and _is_narrative(s)]
        for i in range(len(sents)):
            for j in range(i + 1, len(sents)):
                a, b = _content_words(sents[i]), _content_words(sents[j])
                if len(a) >= 6 and len(b) >= 6 and len(a & b) / len(a | b) >= 0.6 \
                        and (len(a - b) >= 3 or len(b - a) >= 3):
                    v.append(("tissue_restatement", f"near-verbatim restatement (Jaccard>=0.6): {sents[i][:60]!r}"))
                    return v
    return v


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

    # VARIETY PACK deterministic subset (rev-2, pack v1.0 §1/§3) — template tells + floor
    body_words = _w(body_no_code)
    hits = re.findall(VP_BAN, body_no_bq)
    if hits:
        v.append({"chapter": ch, "lens": "L0:prescreen:template_frame", "refuted": True,
                  "reason": f"banned frame: {sorted(set(hits))}"})
    # rev-3 shape-aware exception (KM 2026-07-27, narrow): a chapter ASSIGNED the
    # comparison-led shape structurally generates comparative constructions — raise ONLY
    # the two colliding caps for that shape; generic template abuse still kills.
    shape_name = str((card.get("shape") or {}).get("name", "")).lower() if isinstance(card.get("shape"), dict) else str(card.get("shape") or "").lower()
    comparison_led = "comparison" in shape_name
    chiasmus_cap = 4 if comparison_led else 2
    budgets = [(pat, (chiasmus_cap if name == "not-X-but-Y chiasmus" else cap), name)
               for name, (pat, cap) in BUDGET_PATTERNS.items()]
    for pat, cap, name in budgets:
        n = len(re.findall(pat, body_no_bq, re.I))
        if n > cap:
            v.append({"chapter": ch, "lens": "L0:prescreen:template_budget", "refuted": True,
                      "reason": f"{name}: {n} > budget {cap}"})
    if body_words >= 600:  # concreteness floor applies at chapter scale only
        floor_fails = []
        if len(re.findall(r"\b\d[\d,.]*\b", body_no_bq)) < 3: floor_fails.append("numerals<3")
        if "?" not in body_no_bq: floor_fails.append("no question")
        if floor_fails:
            v.append({"chapter": ch, "lens": "L0:prescreen:concreteness_floor", "refuted": True,
                      "reason": f"floor: {floor_fails}"})

    # TEXT-INTEGRITY (rev-2) — garbled duplication: an identical normalized sentence
    # appearing 2+ times, or any 12-word n-gram repeating, is generation damage, not style.
    sents_n = [re.sub(r"\W+", " ", s).strip().lower()
               for s in re.split(r"(?<=[.!?])\s+", body_no_bq) if len(s.split()) >= 6]
    dup_s = [s for s, n in collections.Counter(sents_n).items() if n >= 2]
    words_l = re.findall(r"[a-z'’]+", body_no_bq.lower())
    g12 = collections.Counter(tuple(words_l[i:i+12]) for i in range(len(words_l) - 11))
    dup_thresh = 3 if comparison_led else 2  # rev-3: one twin-entity repeat allowed for comparison-led
    dup_g = [g for g, n in g12.items() if n >= dup_thresh]
    if dup_s:
        v.append({"chapter": ch, "lens": "L0:prescreen:text_integrity", "refuted": True,
                  "reason": f"duplicated sentence x{len(dup_s)}: {dup_s[0][:90]!r}"})
    if dup_g:
        v.append({"chapter": ch, "lens": "L0:prescreen:text_integrity", "refuted": True,
                  "reason": f"repeated 12-gram x{len(dup_g)}: {' '.join(dup_g[0])[:90]!r}"})

    # SPEC-LEAK (rev-4, board finding: ch6 shipped repo paths + a HOLD ID as reader prose).
    # Applies to READER prose only (blockquotes = receipt apparatus, exempt by design).
    # Hard leaks (paths, tracking IDs) kill on sight. Schema VOCABULARY kills only in
    # density (>=2 distinct tokens): these books TEACH the system, so a single schema noun
    # in published prose is content, not leakage (recalibration caught BANK-12 using
    # 'draft_status' lawfully — the first over-reach this gate family has had).
    SPEC_HARD = (r"(?:src|tests|tools|kdp|artifacts)/[A-Za-z0-9_./-]+\.(?:py|yaml|md|json)"
                 r"|\bS\d-\d\d-E\d-\d\b|\bHOLD-ID\b|\bbuild-tracker\b")
    SPEC_VOCAB = r"\bblocks_seal\b|\bseed_rev\b|\bgate_rev\b|\bdraft_status\b"
    hard = re.findall(SPEC_HARD, body_no_bq)
    vocab = sorted(set(re.findall(SPEC_VOCAB, body_no_bq)))
    if hard or len(vocab) >= 2:
        v.append({"chapter": ch, "lens": "L0:prescreen:spec_leak", "refuted": True,
                  "reason": f"internal build leakage in reader prose: hard={sorted(set(hard))[:4]} vocab={vocab[:4]}"})

    # BARE-NUMERAL SENTENCE-END (rev-5) — substitution artifacts, reader-facing body only
    bare = bare_numeral_ends(body_no_bq)
    if bare:
        v.append({"chapter": ch, "lens": "L0:prescreen:bare_numeral_end", "refuted": True,
                  "reason": f"sentence terminates on a bare numeral (dropped noun) x{len(bare)}: {bare[0]!r}"})

    # APPARATUS-LEAK (rev-5, PS-5) — internal build/coordination language in reader-facing
    # text. Unlike spec_leak, this INCLUDES the receipt box + verify affordances: PS-5 makes
    # those the product, so a test name or a "stays in its lane" note there is a leak.
    rb = card.get("receipt_box") or {}
    reader_faces = [body_no_bq,
                    str(rb.get("claim", "")), str(rb.get("runs_today", ""))]
    reader_faces += [str(x) for x in (card.get("verify_affordance") or [])]
    ap_hard, ap_stale = apparatus_leaks(reader_faces)
    if ap_hard:
        v.append({"chapter": ch, "lens": "L0:prescreen:apparatus_leak", "refuted": True,
                  "reason": f"internal apparatus in reader-facing text: {ap_hard[:6]}"})
    if ap_stale:
        v.append({"chapter": ch, "lens": "L0:prescreen:apparatus_stale_runs", "refuted": True,
                  "reason": f"stale pre-extrusion 'nothing runs today' claim (volume is post-extrusion): {ap_stale[0][:80]!r}"})

    # rev-6 CONNECTIVE-TISSUE REGISTER budgets (2nd board: voice/pacing failed here)
    for lens_suffix, reason in tissue_budgets(body_no_bq):
        v.append({"chapter": ch, "lens": f"L0:prescreen:{lens_suffix}", "refuted": True, "reason": reason})

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
        if c.get("settled") is True:
            print(f"prescreen SETTLED (pass receipt): {p.name} — not re-screened")
            continue
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

    # rev-4 VOLUME-MODE checks (only when screening a directory of cards)
    if seeds.is_dir() and len(cards) > 1:
        # (a) duplicate-shingle scan: a 10-word shingle in 2+ chapters' reader prose =
        # recycled boilerplate (board: 11 verbatim glossary shingles). Attach to the
        # LATER chapter. The bare canonical expansion itself is lawful (canon law
        # requires it per chapter) — it is < 10 words, so it never trips this.
        seen = {}
        for c in sorted(cards, key=lambda x: int(x.get("chapter", 0))):
            body = re.sub(r"(?m)^>.*$", "", re.sub(r"```.*?```", "", c.get("prose") or "", flags=re.S))
            words = re.findall(r"[a-z'’]+", body.lower())
            mine = set(tuple(words[i:i+10]) for i in range(len(words) - 9))
            for sh in mine:
                if sh in seen and seen[sh] != c.get("chapter"):
                    verdicts.append({"chapter": c.get("chapter"),
                                     "lens": "L0:prescreen:duplicate_shingle", "refuted": True,
                                     "reason": f"10-word shingle recycled from ch{seen[sh]}: "
                                               f"{' '.join(sh)[:80]!r}"})
                    break  # one verdict per chapter-pair is enough to KILL and target
            for sh in mine:
                seen.setdefault(sh, c.get("chapter"))
        # (b) continuity-facts ledger: _continuity_facts.yaml beside the seeds declares
        # canonical facts (must/forbid patterns per chapter scope). Contradictions KILL.
        # rev-5: PINNED facts (pin:true) name their canonical value and get a louder lens —
        # a fact that flipped more than once is pinned so it cannot silently drift again.
        # forbid_pattern may be scoped to certain chapters via `scope` (default: all).
        ledger_p = seeds / "_continuity_facts.yaml"
        if ledger_p.exists():
            ledger = yaml.safe_load(ledger_p.read_text()) or []
            for fact in ledger:
                fpat, mpat = fact.get("forbid_pattern"), fact.get("must_pattern")
                pinned = bool(fact.get("pin"))
                lens = "L0:prescreen:continuity_pin" if pinned else "L0:prescreen:continuity_fact"
                canon = f" (canonical: {fact['canonical']})" if fact.get("canonical") else ""
                scope = [str(x) for x in fact["scope"]] if fact.get("scope") else None
                for c in cards:
                    body = re.sub(r"(?m)^>.*$", "", c.get("prose") or "")
                    in_scope = scope is None or str(c.get("chapter")) in scope
                    if fpat and in_scope and re.search(fpat, body, re.I):
                        verdicts.append({"chapter": c.get("chapter"), "lens": lens, "refuted": True,
                                         "reason": f"contradicts {'PINNED ' if pinned else ''}fact "
                                                   f"{fact.get('name')!r}{canon}: forbidden pattern present"})
                    if mpat and fact.get("required_in") and str(c.get("chapter")) in [str(x) for x in fact["required_in"]]                             and not re.search(mpat, body, re.I):
                        verdicts.append({"chapter": c.get("chapter"), "lens": lens, "refuted": True,
                                         "reason": f"{'PINNED ' if pinned else ''}fact {fact.get('name')!r}{canon} "
                                                   f"missing required statement"})
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
