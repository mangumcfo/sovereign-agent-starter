#!/usr/bin/env python3
"""
Atrium autonomous PRODUCER (Step C-full, final piece).

Watches the live node's obligation ledger for new captured review sessions and, for each one,
invokes a headless Claude to read the session transcript + the manuscript and emit grouped diffs,
then POSTs them as a /proposals entry. The operator still accepts/rejects in the Atrium diff-review
(see-before-write) — the producer NEVER applies or seals. Proposals only.

Bounds / safety:
- Produces PROPOSALS only. No file writes, no apply, no seal. KM's accept in the diff-review is the gate.
- Idempotent: a per-session state file prevents reprocessing; also skips sessions that already have a proposal.
- Defensive: if generation yields no valid JSON, it marks the session processed with an empty result + logs.
- Killable: systemctl --user stop/disable atrium-producer.service.

Usage:
    atrium_producer.py --once     # single pass (for testing / timer)
    atrium_producer.py            # poll loop (POLL_SECONDS)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request

NODE = "http://127.0.0.1:8421/api/v1"
STATE = os.path.expanduser("~/.breathline/atrium_producer_state.json")
LOG = os.path.expanduser("~/.breathline/atrium_producer.log")
CLAUDE = os.path.expanduser("~/.local/bin/claude")
POLL_SECONDS = 45

# Map a book tag → manuscript path the generator reads to ground exact before-text.
_VAULT = "/home/kmangum/work-repos/mangumcfo/breathline-books-vault/kdp/agentic_playbooks"
BOOK_PATHS = {
    "Book 10": f"{_VAULT}/10_scaling_enterprise/v1.0/manuscript_v1.5.md",
    "Book 11": f"{_VAULT}/11_ma_due_diligence/v1.0/manuscript_v1.5.md",
    "Book 12": f"{_VAULT}/12_agentic_enterprise/v1.0/manuscript_v1.5.md",
}


def _log(msg: str) -> None:
    line = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + "  " + msg
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    print(line, flush=True)


def _get(path: str):
    with urllib.request.urlopen(NODE + path, timeout=10) as r:
        return json.loads(r.read().decode())


def _post(path: str, body: dict):
    req = urllib.request.Request(NODE + path, data=json.dumps(body).encode(),
                                 method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def _state() -> dict:
    try:
        return json.loads(open(STATE, encoding="utf-8").read())
    except (OSError, ValueError):
        return {"processed": []}


def _save_state(s: dict) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    open(STATE, "w", encoding="utf-8").write(json.dumps(s, indent=2))


def _book_of(intent: str) -> str:
    # Page-tag forms: "[Book 11 · p14]" (review session) or "Page: Book 11 · p3" (pdf-edit / hopper
    # packet). Anchored on '[' or 'Page:' so a "Book 12" mention inside the seed prose isn't mistaken
    # for the target book.
    m = re.search(r"\[(Book \d+)", intent or "") or re.search(r"Page:\s*(Book \d+)", intent or "")
    return m.group(1) if m else "Book 11"


PROMPT = """You are the Atrium diff-review PRODUCER. A human (KM) recorded this book-review session as a page-tagged transcript. Decide whether it asks for concrete BOOK edits, then output ONLY a JSON object (no prose, no markdown fences).

TRANSCRIPT:
{transcript}

MANUSCRIPT FILE (read the WHOLE file to ground exact text): {manuscript}

RULES:
- If the transcript requests concrete manuscript change(s): read the file and produce grounded diffs. Every `before` MUST be exact text copied verbatim from the file.
- FORMATTING IS A CONCRETE EDIT — never decline it. "bold this", "highlight this piece", "make a callout", "italicize", "make this a bullet" are real, groundable edits. Find the EXACT target text — use the `Seed (human selection): "…"` text in the transcript if present, otherwise the phrase KM names — and produce a diff that formats it: bold = wrap in `**…**`, italic = `*…*`, callout/highlight = make it a `> ` blockquote line or bold lead, bullet = prefix `- `. `before` = the exact current text, `after` = the formatted version. Only return empty groups if the target text genuinely can't be located in the file.
- COMPLETENESS — fix the whole ISSUE, not just the one spot named. If KM signals the issue RECURS ("throughout", "everywhere", "all the…", "same issue", "similar", "keep an eye out"), SWEEP THE ENTIRE MANUSCRIPT and find EVERY instance of that same issue. Group by PATTERN: one group per distinct issue, with a `hunks` array holding EVERY instance (each {{before, after}}). Do NOT make a separate group per instance, and do NOT stop at the first match. Fix the named issue completely in this book. Only the issue(s) KM actually raised — never invent unrelated edits.
- CROSS-BOOK: if KM says the issue also applies to other books (e.g. "books 10-12", "same in 10 and 12"), set top-level "cross_book": ["Book 10","Book 12"]. Do NOT edit other books here; they are processed separately.
- If it is a question / observation / tooling note / not a book edit: return empty groups with a classifying note. Do NOT fabricate.
- Output EXACTLY this JSON (a group uses EITHER `hunks` for one-or-more instances OR a single `before`/`after`):
{{"session_ref":"<book + page>","book":"<book>","note":"<summary; say how many instances per pattern>","cross_book":[],"groups":[{{"id":"g1","title":"<pattern> — N places","kind":"prose|code","scope":"GREEN","rationale":"...","file":"<exact path>","hunks":[{{"before":["exact text"],"after":["changed text"]}}]}}]}}
"""


def _generate(transcript: str, book: str) -> dict | None:
    manuscript = BOOK_PATHS.get(book, BOOK_PATHS["Book 11"])
    prompt = PROMPT.format(transcript=transcript, manuscript=manuscript)
    cwd = os.path.dirname(manuscript) if os.path.isfile(manuscript) else manuscript
    try:
        kb = os.path.getsize(manuscript) // 1024 if os.path.isfile(manuscript) else 0
        _log(f"  reading {book} manuscript ({kb} KB) + your note")
    except OSError:
        pass
    _log("  asking Claude to find the exact text and ground the edit(s)… (a whole-book scan can take 1–5 min)")
    started = time.time()
    try:
        out = subprocess.run([CLAUDE, "-p", prompt], cwd=cwd, capture_output=True,
                             text=True, timeout=600).stdout
    except subprocess.TimeoutExpired:
        _log(f"  Claude timed out after {int(time.time()-started)}s — the request was likely too broad for one pass")
        return None
    except OSError as exc:
        _log(f"  generation error: {exc}")
        return None
    _log(f"  Claude returned in {int(time.time()-started)}s ({len(out)} chars) — parsing the diff JSON…")
    # Extract the last {...} JSON object from the output.
    matches = re.findall(r"\{.*\}", out, re.DOTALL)
    for cand in reversed(matches):
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict) and "groups" in obj:
                return obj
        except ValueError:
            continue
    _log("  no valid JSON in generation output")
    return None


def _existing_proposal_obligations() -> set:
    try:
        props = _get("/proposals").get("proposals", [])
        return {p.get("obligation_id") for p in props if p.get("obligation_id")}
    except Exception:
        return set()


def run_once() -> None:
    st = _state()
    processed = set(st.get("processed", []))
    try:
        log = _get("/obligations/log").get("log", [])
    except Exception as exc:
        _log(f"ledger unreachable: {exc}")
        return
    have_props = _existing_proposal_obligations()
    sessions = [o for o in log
                if o.get("status") == "draft"
                and str(o.get("title", "")).startswith("Review session")
                and o.get("id") not in processed
                and o.get("id") not in have_props]
    if not sessions:
        return
    for o in sessions:
        oid = o["id"]
        intent = o.get("intent", "")
        book = _book_of(intent)
        _log(f"processing {oid} ({book})")
        result = _generate(intent, book)
        groups = (result or {}).get("groups") or []
        if groups:
            try:
                prop = _post("/proposals", {
                    "session_ref": (result or {}).get("session_ref", o.get("ref", "")),
                    "obligation_id": oid,
                    "book": book,
                    "note": (result or {}).get("note", "Auto-produced from your captured session."),
                    "groups": groups,
                })
                _log(f"  posted proposal {prop.get('id')} with {len(groups)} group(s)")
            except Exception as exc:
                _log(f"  post failed: {exc}")
                continue  # leave unprocessed → retry next pass
        else:
            _log(f"  no book edit ({(result or {}).get('note','classified: not a book edit / generation empty')})")
        processed.add(oid)
    st["processed"] = sorted(processed)
    _save_state(st)


def process_one(oid: str) -> None:
    """On-demand: process a single session by id (the Atrium 'Process' button path)."""
    try:
        log = _get("/obligations/log").get("log", [])
    except Exception as exc:
        _log(f"ledger unreachable: {exc}")
        return
    o = next((x for x in log if x.get("id") == oid), None)
    if not o:
        _log(f"on-demand: session {oid} not found")
        return
    if oid in _existing_proposal_obligations():
        _log(f"on-demand: {oid} already has a proposal — skipping (no duplicate)")
        return
    intent = o.get("intent", "")
    book = _book_of(intent)
    _log(f"on-demand processing {oid} ({book})")
    result = _generate(intent, book)
    # Re-check AFTER the (slow) generate: a concurrent run (double-click / auto-process + manual) may
    # have posted in the meantime. Closes the dedupe race so one packet → one card.
    if oid in _existing_proposal_obligations():
        _log(f"  {oid} got a proposal during generation — skipping duplicate post")
        return
    groups = (result or {}).get("groups") or []
    cross = [b for b in ((result or {}).get("cross_book") or []) if b in BOOK_PATHS and b != book]
    if groups:
        try:
            prop = _post("/proposals", {
                "session_ref": (result or {}).get("session_ref", o.get("ref", "")),
                "obligation_id": oid, "book": book, "cross_book": cross,
                "note": (result or {}).get("note", "Produced from your captured session."),
                "groups": groups,
            })
            _log(f"  posted proposal {prop.get('id')} ({len(groups)} group(s){', cross_book='+str(cross) if cross else ''})")
        except Exception as exc:
            _log(f"  post failed: {exc}")
    else:
        note = (result or {}).get("note") or ("Couldn't auto-produce a diff. This usually means the request was too broad for one pass "
                "(e.g. 'scan the whole book') and timed out, or it wasn't a concrete manuscript edit. Point at a specific spot, "
                "or ask Tiger to run a full-book sweep.")
        _log(f"  no diff → info card ({note[:60]})")
        try:
            _post("/proposals", {"session_ref": (result or {}).get("session_ref", o.get("ref", "")),
                                 "obligation_id": oid, "book": book, "info": True, "note": note, "groups": []})
        except Exception as exc:
            _log(f"  info post failed: {exc}")
    # CROSS-BOOK: sweep the same issue in each named book → a separate proposal per book.
    for cb in cross:
        _log(f"  cross-book sweep → {cb}")
        r2 = _generate(intent, cb)
        g2 = (r2 or {}).get("groups") or []
        if g2:
            try:
                p2 = _post("/proposals", {"session_ref": f"cross-book · {cb}", "obligation_id": oid,
                                          "book": cb, "cross_book": [],
                                          "note": f"Cross-book: same issue swept in {cb}. " + (r2 or {}).get("note", ""),
                                          "groups": g2})
                _log(f"    posted {cb} proposal {p2.get('id')} ({len(g2)} group(s))")
            except Exception as exc:
                _log(f"    {cb} post failed: {exc}")


def main() -> int:
    if "--session" in sys.argv:
        i = sys.argv.index("--session")
        oid = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
        if oid:
            process_one(oid)
        return 0
    once = "--once" in sys.argv
    if once:
        run_once()
        return 0
    _log("atrium_producer loop start")
    while True:
        try:
            run_once()
        except Exception as exc:  # never die on a single bad pass
            _log(f"pass error: {exc}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
