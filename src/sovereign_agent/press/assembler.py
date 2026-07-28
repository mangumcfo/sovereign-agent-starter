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
  front matter (title/subtitle/series line + a build-state table single-sourced from the
  ledger) · frame declaration ("About the Worked Scenario") · chapters (settled prose
  VERBATIM + a GENERATED four-field receipt box) · Cast & Canon (plain-name rendering of
  the continuity facts — no dotted config keys) · Do-It-Yourself worksheets (each
  chapter's verify affordances) plus an assembly receipt JSON: sha256 of every piece.

PS-5 generation (2nd production board): the reader receipt is DERIVED, per chapter, from
the live extrusion ledger + the chapter — never hand-maintained, never identical across
chapters. 'What runs today' lists that chapter's PRESENT claims (plain-English ledger
data); 'What is designed' names the deployment form derived from the title; 'How you
check' is the affordance worksheet. Chapter PROSE is still placed verbatim; the module
still writes no prose and still refuses on any missing piece. The fixed scaffolding it
contributes is declared once in SCAFFOLD below.
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
    "verify_heading":  "## Do It Yourself — Chapter Worksheets",
    "verify_note":     "*(each chapter's checks, to run against your own records)*",
    "receipt_title":   "Receipt — Chapter {n}",
    "receipt_claim":   "**Claim.**",
    "receipt_runs":    "**What runs today.**",
    "runs_frame":      ("These mechanisms are implemented in the platform's object library and "
                        "checked by their own tests — what is proven is the mechanism, not a live "
                        "deployment (Ridgeline is a worked scenario):"),
    "receipt_designed": "**What is designed, not yet running.**",
    "designed_frame":  ("Deploying the {form} over your own records is the design this chapter "
                        "equips you to build."),
    "receipt_disclosure": (
        "> **About these receipts.** Each chapter closes with a receipt. \"Implemented + "
        "test-checked\" means the mechanism runs in the platform's object library and passes its "
        "own tests — it is **not** deployed as a live system for any business. Ridgeline is a "
        "worked scenario; building the deployed model is your work. This note is printed once; "
        "the per-chapter receipts carry only what is specific to that chapter."),
    "receipt_check":   "**How you check.**",
    "check_frame":     "Run these against your own records:",
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
        # PS-5 generation: the reader receipt is GENERATED from the extrusion ledger +
        # continuity, not hand-maintained. The seed supplies only the one editorial thesis
        # line (`claim`); runs-today / designed / how-to-check are derived below.
        rb = c.get("receipt_box") or {}
        if not str(rb.get("claim", "")).strip():
            gaps.append(f"{f}: receipt_box.claim (the chapter thesis) missing — "
                        "the reader receipt cannot be generated")
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


def _deployed_form(title):
    """Derive a chapter's 'deployed form' noun phrase from its title, so the 'what is
    designed' line varies per chapter without a hand-maintained field. Preserves proper
    capitalization (Merkle, Object); problem chapters ('… Fail …') fall back to the volume
    noun; comparison/appendage tails ('vs …', '& …') are dropped."""
    t = str(title).strip()
    if re.search(r"\bFail\b", t):
        return "sovereign object model"
    t = re.sub(r"^(?:The|A|An)\s+", "", t)
    t = re.split(r"\s+(?:vs|versus|&)\s+", t)[0].strip()
    return t or "object model"


def _receipt_box_md(n, c):
    """GENERATED reader receipt (PS-5, N-3 scaffold variation — S5-05 O-7 proof board). The
    standing disclosure ('these are implemented mechanisms, not a live deployment') and the
    'how you check' worksheets are printed ONCE elsewhere (front matter + the Do-It-Yourself
    section) — never repeated in every box, which trained the reader to skip them. Each box
    carries ONLY its varied per-chapter content: the thesis, this chapter's PRESENT claims,
    and this chapter's designed deployment form. No two boxes are identical."""
    S = SCAFFOLD
    rb = c["receipt_box"]
    present = [e for e in c["extrusion"] if str(e.get("status", "")).upper() == "PRESENT"]
    holds = [e for e in c["extrusion"]
             if str(e.get("status", "")).upper() in ("HOLD", "DOWNGRADED")]
    lines = [f"> **{S['receipt_title'].format(n=n)}**", ">",
             f"> {S['receipt_claim']} {str(rb['claim']).strip()}", ">",
             f"> {S['receipt_runs']} Implemented + test-checked in the platform's object library:"]
    for e in present:  # plain-English claim text from the ledger — no E-ID, no path, no test
        lines.append(f"> - {str(e.get('claim', '')).strip()}")
    lines += [">", f"> {S['receipt_designed']} "
              + S["designed_frame"].format(form=_deployed_form(c["title"]))]
    for e in holds:
        lines.append(f"> - {str(e.get('claim', '')).strip()}")
    return "\n".join(lines)


# ── plain-name Cast & Canon generation (PS-5: no dotted config keys in the reader doc) ──
_CANON_GROUPS = [  # (canon key path, reader label, value transform)
    ("company", "The company", lambda v: str(v).split(" - ", 1)[-1] if " - " in str(v) else str(v)),
    ("personas.controller", None, None), ("personas.successor", None, None),
    ("personas.auditor", None, None), ("personas.trustee", None, None),
    ("population.total_objects", "Objects in all", str),
    ("population.classes", "Object classes", str),
    ("mandates.operating", None, None), ("mandates.trust", None, None),
    ("mandates.properties", None, None), ("mandates.crossings", "Declared crossings", str),
    ("objects.C-1042", "C-1042", str), ("objects.WO-88214", "WO-88214", str),
    ("integrity.proof_depth", "Proof depth", str),
    ("integrity.proof_size", "Proof size", str), ("integrity.root_size", "Root size", str),
    ("integrity.manifest", "Year-end manifest", str),
    ("integrity.design_target_proof_check", "Proof check (design target)", str),
    ("migration.sourced", "Sourced at cutover", str),
    ("migration.unsourced", "Unsourced at cutover", str),
    ("audit_day.sample", "Audit sample", str),
    ("audit_day.hashes_checked", "Hash checks in the sample", str),
    ("audit_day.design_target_elapsed", "Tie-out (design target)", str),
    ("audit_day.prior_year_actual", "Prior-year tie-out (incumbent)", str),
]


def _dig(canon, path):
    node = canon
    for k in path.split("."):
        if not isinstance(node, dict) or k not in node:
            return None
        node = node[k]
    return node


def _cast_and_canon(canon):
    """Render selected continuity facts with plain reader labels — persons by name, figures by
    a readable label. No dotted snake_case keys reach the page (the 2nd board's worst offender)."""
    rows = []
    for path, label, xform in _CANON_GROUPS:
        val = _dig(canon, path)
        if val is None:
            continue
        if path.startswith(("personas.", "mandates.")):  # "Name - description" -> Name | description
            name, _, desc = str(val).partition(" - ")
            rows.append((name.strip(), desc.strip() or name.strip()))
        else:
            rows.append((label, xform(val)))
    return rows


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
                              f"{series_line}\n\n| | |\n|---|---|\n{counts}\n\n"
                              f"{S['receipt_disclosure']}")

    # frame declaration — ratified text, verbatim
    pieces["frame_declaration"] = f"{S['frame_heading']}\n\n{frame}"

    # chapters — settled prose verbatim + the four-field receipt box
    # The frame declaration is shown ONCE, in the front-matter "About the Worked Scenario"
    # section. Frame-lock still requires it to open ch1 verbatim in the SEED (integrity), but
    # the rendered chapter strips that leading copy so the reader never meets it twice.
    body, receipts = [], []
    for n, c in chapters:
        prose = str(c["prose"]).strip()
        if prose.startswith(frame):
            prose = prose[len(frame):].lstrip()
        box = _receipt_box_md(n, c)
        receipts.append(box)
        body.append(f"# Chapter {n} — {c['title']}\n\n{prose}\n\n" + box)
    # D6 backstop: no two reader receipts may be identical (the ×8 boilerplate the board caught).
    if len(set(receipts)) != len(receipts):
        raise AssemblyRefusal(["receipt boxes are not all distinct — the PS-2 scaffold is "
                               "printing identical apparatus (D6). Vary per chapter from the ledger."])
    pieces["chapters"] = "\n\n---\n\n".join(body)

    # Cast & Canon — PLAIN-NAME rendering (no dotted config keys; the 2nd board's worst offender)
    gl = [f"{S['glossary_heading']}\n", S["glossary_note"], "", "| | |", "|---|---|"]
    for label, val in _cast_and_canon(vol["continuity_canon"]):
        gl.append(f"| **{label}** | {val} |")
    for term, gloss in CANON.items():
        gl.append(f"| **{term}** | {gloss} |")
    pieces["glossary"] = "\n".join(gl)

    # worksheet-style verification index — each chapter's checks, framed to run on your own records
    vi = [f"{S['verify_heading']}\n", S["verify_note"], ""]
    for n, c in chapters:
        vi.append(f"### Chapter {n} — {c['title']}")
        for i, v in enumerate(c["verify_affordance"], 1):
            vi.append(f"- [ ] **{i}.** {str(v).strip()}")
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
