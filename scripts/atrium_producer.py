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
BOOK_PATHS = {
    "Book 11": "/home/kmangum/work-repos/mangumcfo/breathline-books-vault/kdp/agentic_playbooks/11_ma_due_diligence/v1.0/manuscript_v1.5.md",
    "Book 12": "/home/kmangum/work-repos/mangumcfo/breathline-books-vault/kdp/agentic_playbooks/12_agentic_enterprise/v1.0",
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
    m = re.search(r"\[(Book \d+)", intent or "")
    return m.group(1) if m else "Book 11"


PROMPT = """You are the Atrium diff-review PRODUCER. A human (KM) recorded this book-review session as a page-tagged transcript. Decide whether it asks for a concrete BOOK edit, then output ONLY a JSON object (no prose, no markdown fences).

TRANSCRIPT:
{transcript}

MANUSCRIPT FILE (read it to ground exact text): {manuscript}

RULES:
- If the transcript requests a concrete manuscript change: read the file, locate the EXACT current text, and produce minimal grouped diffs. `before` MUST be exact lines copied from the file; `after` is the minimal change. Prefer 1-3 groups; never invent edits not asked for.
- If it is a question, an observation, a tooling/UI note, or not a book edit: return an empty groups list with a classifying note. Do NOT fabricate a book diff.
- Output EXACTLY this JSON shape and nothing else:
{{"session_ref":"<book + page>","book":"<book>","note":"<short classification or summary>","groups":[{{"id":"g1","title":"...","kind":"prose|code","scope":"GREEN","rationale":"...","file":"...","before":["exact line"],"after":["changed line"]}}]}}
"""


def _generate(transcript: str, book: str) -> dict | None:
    manuscript = BOOK_PATHS.get(book, BOOK_PATHS["Book 11"])
    prompt = PROMPT.format(transcript=transcript, manuscript=manuscript)
    cwd = os.path.dirname(manuscript) if os.path.isfile(manuscript) else manuscript
    try:
        out = subprocess.run([CLAUDE, "-p", prompt], cwd=cwd, capture_output=True,
                             text=True, timeout=300).stdout
    except (subprocess.TimeoutExpired, OSError) as exc:
        _log(f"  generation error: {exc}")
        return None
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


def main() -> int:
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
