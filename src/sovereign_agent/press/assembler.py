"""assembler.py — PS-2 deterministic assembler (Production Substance Layer, enforcement 2/2).

IT PLACES; IT NEVER WRITES. Every body string in the assembled volume is either
  (a) a VERBATIM placement of ratified material from the volume's seed ledger, or
  (b) a deterministic rendering of ledger VALUES into a table/list (numbers and
      strings copied, never paraphrased).
There is no fallback text, no generated filler, and no model call anywhere in this
module. If any required piece is missing, assembly REFUSES with the full list of
gaps — partial assembly does not exist.

Required inputs (volume seeds dir):
  _volume_input.yaml      title · subtitle · book_id · continuity_canon · chapters
  _continuity_facts.yaml  the volume continuity ledger (the gate-enforced facts)
  _frame_declaration.md   the ratified frame declaration; must ALSO appear verbatim
                          in ch1 prose (frame lock — drift refuses assembly)
  chN.yaml × N            settled:true prose · receipt_box{claim,runs_today} ·
                          verify_affordance[] · extrusion[] (every HOLD blocks_seal)

Assembled output (markdown):
  front matter (title/subtitle/series line + claim-count table) · frame declaration
  ("About the Worked Scenario") · chapters (settled prose VERBATIM + reader-facing
  four-field receipt box: Claim / What runs today / What is designed / How you check) ·
  glossary ("Cast & Canon" rendered from continuity canon + CANON terms) ·
  verification index (every chapter's verify affordances, verbatim)
plus an assembly receipt JSON: sha256 of every placed piece.

The only English this module contributes is the fixed structural scaffolding below —
declared once, visible, and never varied per volume.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import time

import yaml

from .prescreen import CANON

# ── The assembler's own manifest: every fixed string it may emit, declared here. ──
# PS-5 plain-name dialect: the reader-facing apparatus carries NO internal build language
# (no repo paths, no test-function names, no "settled"/tracker vocabulary, no "rendered from
# the continuity ledger" label). Reader receipts say what runs and what is designed in plain
# terms; the code trace lives in the spec + extrusion ledger for auditors, never on the page.
SCAFFOLD = {
    "frame_heading":   "## About the Worked Scenario",
    "glossary_heading": "## Cast & Canon",
    "glossary_note":   "*(the people, figures, and terms this volume holds constant)*",
    "verify_heading":  "## Verification Index",
    "verify_note":     "*(every chapter's reader-runnable checks)*",
    "receipt_title":   "Receipt — Chapter {n}",
    "receipt_claim":   "**Claim.**",
    "receipt_runs":    "**What runs today.**",
    "receipt_designed": "**What is designed, not yet running.**",
    "receipt_check":   "**How you check.**",
    "counts_rows": [
        ("Chapters", "{n_ch}"),
        ("Mechanisms implemented and test-checked in the platform's object library", "{n_present}"),
        ("Deployed as a live system of record", "none yet — the volume is the design you build"),
    ],
    "none_marker": "—",
}


class AssemblyRefusal(Exception):
    """Raised with the FULL list of gaps. Partial assembly does not exist."""
    def __init__(self, gaps):
        self.gaps = list(gaps)
        super().__init__("ASSEMBLY REFUSED (PS-2): " + str(len(self.gaps)) +
                         " required piece(s) missing or unlawful:\n  - " +
                         "\n  - ".join(self.gaps))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _flatten_canon(node, prefix=""):
    """Deterministic walk of continuity_canon → (dotted-key, value) rows."""
    rows = []
    if isinstance(node, dict):
        for k in node:  # yaml dict order preserved — deterministic
            rows.extend(_flatten_canon(node[k], f"{prefix}{k}." if prefix or True else k))
    else:
        rows.append((prefix.rstrip("."), str(node)))
    return rows


def load_volume(seeds_dir):
    """Load + law-check every input. Returns (vol_input, frame, facts, chapters) or
    raises AssemblyRefusal carrying every gap found."""
    gaps = []

    def _read_yaml(name, required_keys=()):
        p = os.path.join(seeds_dir, name)
        if not os.path.exists(p):
            gaps.append(f"{name}: file missing")
            return {}
        data = yaml.safe_load(open(p)) or {}
        for k in required_keys:
            if not (data.get(k) if isinstance(data, dict) else None):
                gaps.append(f"{name}: required key `{k}` missing or empty")
        return data

    vol = _read_yaml("_volume_input.yaml",
                     ("title", "subtitle", "book_id", "continuity_canon", "chapters"))

    facts_p = os.path.join(seeds_dir, "_continuity_facts.yaml")
    facts = []
    if not os.path.exists(facts_p):
        gaps.append("_continuity_facts.yaml: continuity ledger missing")
    else:
        facts = yaml.safe_load(open(facts_p)) or []
        if not facts:
            gaps.append("_continuity_facts.yaml: continuity ledger empty")

    frame_p = os.path.join(seeds_dir, "_frame_declaration.md")
    frame = ""
    if not os.path.exists(frame_p):
        gaps.append("_frame_declaration.md: ratified frame declaration missing")
    else:
        frame = open(frame_p).read().strip()
        if not frame:
            gaps.append("_frame_declaration.md: frame declaration empty")

    chapters = []
    ch_files = sorted((f for f in os.listdir(seeds_dir)
                       if re.fullmatch(r"ch\d+\.yaml", f)),
                      key=lambda f: int(re.search(r"\d+", f).group()))
    if not ch_files:
        gaps.append("no chapter cards (ch*.yaml) found")
    for f in ch_files:
        c = yaml.safe_load(open(os.path.join(seeds_dir, f))) or {}
        n = c.get("chapter", f)
        if c.get("settled") is not True:
            gaps.append(f"{f}: chapter not settled (settled:true required — "
                        "unsettled prose cannot be assembled)")
        if not str(c.get("prose", "")).strip():
            gaps.append(f"{f}: prose missing or empty")
        if not c.get("title"):
            gaps.append(f"{f}: title missing")
        rb = c.get("receipt_box") or {}
        for k in ("claim", "runs_today", "designed"):
            if not str(rb.get(k, "")).strip():
                gaps.append(f"{f}: receipt_box.{k} missing — the reader receipt "
                            "cannot be placed")
        va = c.get("verify_affordance") or []
        if not (isinstance(va, list) and va):
            gaps.append(f"{f}: verify_affordance missing/empty — no reader-runnable check")
        ex = c.get("extrusion")
        if not isinstance(ex, list) or not ex:
            gaps.append(f"{f}: extrusion ledger missing — claims cannot be classified")
        else:
            for e in ex:
                st = str(e.get("status", "")).upper()
                if st not in ("PRESENT", "HOLD", "DOWNGRADED"):
                    gaps.append(f"{f}: extrusion {e.get('id')} unknown status {st!r}")
                if st == "HOLD" and e.get("blocks_seal") is not True:
                    gaps.append(f"{f}: extrusion {e.get('id')} HOLD without "
                                "blocks_seal:true — silent deferral forbidden")
        chapters.append((n, c))

    # frame lock: the declaration must open ch1 verbatim (drift = refuse)
    if frame and chapters:
        ch1 = next((c for n, c in chapters if str(n) == "1"), None)
        if ch1 is not None and frame not in str(ch1.get("prose", "")):
            gaps.append("_frame_declaration.md: declaration NOT found verbatim in ch1 "
                        "prose — frame lock broken (rendered text drifted from the "
                        "ratified declaration)")

    if gaps:
        raise AssemblyRefusal(gaps)
    return vol, frame, facts, chapters


def _receipt_box_md(n, c):
    """Reader-facing four-field receipt box (PS-5 plain-name dialect). Every string is
    PLACED from the seed's receipt_box + verify affordances — no repo paths, no test
    names, no per-row code tracing (that trail lives in the spec + extrusion ledger for
    auditors, never on the reader's page). 'What is designed' is the seed's `designed`
    field, plus any genuine HOLD/DOWNGRADED rows still open."""
    S = SCAFFOLD
    rb = c["receipt_box"]
    holds = [e for e in c["extrusion"]
             if str(e.get("status", "")).upper() in ("HOLD", "DOWNGRADED")]
    lines = [f"> **{S['receipt_title'].format(n=n)}**", ">",
             f"> {S['receipt_claim']} {str(rb['claim']).strip()}", ">",
             f"> {S['receipt_runs']} {str(rb['runs_today']).strip()}", ">",
             f"> {S['receipt_designed']} {str(rb.get('designed', '')).strip()}"]
    for e in holds:  # any still-open hold is named plainly (no E-ID, no path)
        lines.append(f"> - {str(e.get('claim', '')).strip()}")
    lines.append(">")
    lines.append(f"> {S['receipt_check']}")
    for v in c["verify_affordance"]:
        lines.append(f"> - {str(v).strip()}")
    return "\n".join(lines)


def assemble(seeds_dir, out_path, receipt_path=None):
    """Assemble the volume. Refuses (AssemblyRefusal) on any gap; never writes prose."""
    vol, frame, facts, chapters = load_volume(seeds_dir)
    S = SCAFFOLD
    pieces = {}  # name -> text (for the receipt shas)

    n_present = sum(1 for _, c in chapters for e in c["extrusion"]
                    if str(e.get("status", "")).upper() == "PRESENT")
    n_hold = sum(1 for _, c in chapters for e in c["extrusion"]
                 if str(e.get("status", "")).upper() == "HOLD")

    # front matter — title/subtitle placed from the registry record; counts from the ledger
    m = re.match(r"s(\d+)_(\d+)_", str(vol["book_id"]))
    series_line = (f"Series {int(m.group(1))} · Volume {int(m.group(2))}" if m
                   else str(vol["book_id"]))
    counts = "\n".join(f"| {label.format()} | {val.format(n_ch=len(chapters), n_present=n_present, n_hold=n_hold)} |"
                       for label, val in S["counts_rows"])
    pieces["front_matter"] = (f"# {vol['title']}\n\n*{vol['subtitle']}*\n\n"
                              f"{series_line}\n\n| | |\n|---|---|\n{counts}")

    # frame declaration — ratified text, verbatim
    pieces["frame_declaration"] = f"{S['frame_heading']}\n\n{frame}"

    # chapters — settled prose verbatim + the four-field receipt box
    # The frame declaration is shown ONCE, in the front-matter "About the Worked Scenario"
    # section. Frame-lock still requires it to open ch1 verbatim in the SEED (integrity), but
    # the rendered chapter strips that leading copy so the reader never meets it twice.
    body = []
    for n, c in chapters:
        prose = str(c["prose"]).strip()
        if prose.startswith(frame):
            prose = prose[len(frame):].lstrip()
        body.append(f"# Chapter {n} — {c['title']}\n\n{prose}\n\n" + _receipt_box_md(n, c))
    pieces["chapters"] = "\n\n---\n\n".join(body)

    # glossary — continuity canon values + CANON terms, rendered not written
    rows = _flatten_canon(vol["continuity_canon"])
    gl = [f"{S['glossary_heading']}\n", S["glossary_note"], "", "| | |", "|---|---|"]
    for k, v in rows:
        gl.append(f"| {k} | {v} |")
    for term, gloss in CANON.items():
        gl.append(f"| {term} | {gloss} |")
    pieces["glossary"] = "\n".join(gl)

    # verification index — every chapter's affordances, verbatim
    vi = [f"{S['verify_heading']}\n", S["verify_note"], ""]
    for n, c in chapters:
        vi.append(f"### Chapter {n} — {c['title']}")
        for i, v in enumerate(c["verify_affordance"], 1):
            vi.append(f"{i}. {str(v).strip()}")
        vi.append("")
    pieces["verification_index"] = "\n".join(vi).rstrip()

    doc = "\n\n---\n\n".join(pieces[k] for k in
                             ("front_matter", "frame_declaration", "chapters",
                              "glossary", "verification_index")) + "\n"
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    open(out_path, "w").write(doc)

    receipt = {
        "tool": "press.assembler", "law": "places, never writes; refuses on any gap",
        "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "seeds_dir": os.path.abspath(seeds_dir), "out": os.path.abspath(out_path),
        "volume": vol["book_id"], "chapters": len(chapters),
        "claims_present": n_present, "claims_hold": n_hold,
        "piece_sha256_16": {k: _sha(v) for k, v in pieces.items()},
        "doc_sha256_16": _sha(doc), "doc_words": len(doc.split()),
    }
    if receipt_path:
        open(receipt_path, "w").write(json.dumps(receipt, indent=1))
    return receipt
