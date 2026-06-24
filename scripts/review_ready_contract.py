#!/usr/bin/env python3
"""
review_ready_contract.py — R1 of the Review-Ready Rail (GB spec v1.0, sealed 2026-06-10).

Machine-checkable contract: NO book reaches KM's review queue unless ALL gates pass. No vibes-gates —
each check resolves against a real artifact / the live obligation ledger / the fidelity record.

  A book is REVIEW-READY iff:
    1. Boards executed     — Editorial + UX + Technical board artifacts present (each = an enhancement list)
    2. Obligations closed   — every book obligation closed (credit) or open-with-explicit-defer-reason
    3. Fidelity gate passed — GB witness trace recorded PASS for the book (semantic, not just hash)
    4. Review Brief sealed  — one-page brief present with 3–7 genuine judgment calls

Usage:
  python3 scripts/review_ready_contract.py 12_agentic_enterprise --match B12 "Agentic Enterprise"
  → prints the per-gate table + gap-list; writes artifacts/review_ready/<book>.json; exit 0 ready / 1 not.

The gap-list IS the work between a book and KM's queue — each gap is a candidate B32 obligation.

∞Δ∞ The rail earns the volume; the gates earn the trust; the human keeps only the judgment. ∞Δ∞
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KDP = Path("/home/kmangum/work-repos/mangumcfo/breathline-books-vault/kdp")
AGENTIC = KDP / "agentic_playbooks"
# Route through THE canonical resolver (audit 2026-06-13d #31): this script once IGNORED
# OBLIGATION_LEDGER_ROOT; now it shares the exact resolver the node serves (env → atrium_review),
# single-sourced + boundary-checked. Tests monkeypatch the env before import.
def _resolve_ledger_root() -> Path:
    src = str(REPO / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from sovereign_agent.obligations.ledger import get_ledger_root
    return get_ledger_root(default=REPO / "memory" / "obligations" / "atrium_review")


LEDGER_ROOT = _resolve_ledger_root()
GB_CYLINDER = REPO / "artifacts" / "GB_KM_Aligned_Interaction_Cylinder.ndjson"
# Canonical Series-Pipeline boards (WORKFLOW.md), RATIFIED mapping (GB [207] + [209], 2026-06-11):
#   Editorial R1/R2/R3 (editorial_board_review_v*_round{1,2,3}.md) — each carries an embedded ```rigor```
#       block (board_rigor.rigor_check_md); the Cold Reader is the 7th LENS inside the rounds, not a board.
#   Book-to-UX (virality_to_ux_translation_v*.md, step 17.5) — presence (prescriptive board, not prose-rigor).
#   Tech/Arch 5-gate (tech_arch_review_v*.md, step 17.6) — MANDATORY, fires right after Book-to-UX; review_ready
#       NEVER flips without its green (GB [209]). It is NOT deferred — an un-run Tech/Arch reads NOT-RUN
#       (honest red), never a false green. Its docket (what it will check) is surfaced when not-yet-run.
REQUIRED_EDITORIAL_ROUNDS = ("round1", "round2", "round3")
TECH_ARCH_DOCKET = "bl-verify repo liveness · receipt-YAML hash-checks · '(planned)'-spec real status · co-extruded-code↔book coherence"


def _book_roots() -> list[Path]:
    """Where a book's artifact dir can live: the S1 agentic_playbooks vault AND each Series-N folder
    (Wave 1 brought S2 onto the rail — vols live under series_02_…/<vol_id>/v*). runs_anywhere-friendly."""
    return [AGENTIC] + sorted(KDP.glob("series_*"))


def _book_dir(book_id: str) -> Path | None:
    for root in _book_roots():
        for v in sorted((root / book_id).glob("v*"), reverse=True):
            if v.is_dir():
                return v
    return None


def _vkey(p: Path) -> tuple:
    """Numeric version sort key so manuscript_v1.10 > v1.9 (string sort gets this wrong)."""
    return tuple(int(n) for n in re.findall(r"\d+", p.name))


def _check_gate6_renderability(bdir: Path) -> dict:
    """Tech/Arch GATE 6 — Renderability (Deterministic-Render Writing Standard v1.0, GB-sealed 2026-06-12).
    Binding. The structural floor checked here: every major section ends with a Receipt box (the Helix
    validation anchor — Gate 6's explicit success criterion). Full Gate-6 rigor (one-truth · every promise
    has a render target · zero dishonest stubs) lives in the tech_arch board's rigor block; this bars the
    box-less manuscript that can never extrude deterministically."""
    mss = sorted((p for p in bdir.glob("manuscript_v*.md")
                 if re.match(r"manuscript_v[0-9.]+\.md$", p.name)), key=_vkey)  # exclude changelog/sidecars
    if not mss:
        return {"pass": False, "status": "no-manuscript", "detail": "no manuscript to render-check"}
    text = mss[-1].read_text(encoding="utf-8", errors="ignore")
    # Receipt-box marker (Tiger fix 2026-06-19, ref THREAD [440]/[442]): count the letters-only
    # "**RECEIPT —" header the manuscripts ACTUALLY use. The ▣ (U+25A3) marker GB's 2026-06-18 reconcile
    # counted was REMOVED in V3 v1.8 — ▣ forced a stray DejaVu font fallback (KM's render-fidelity "multiple
    # fonts" bug) and is now HARD-BANNED by the render_fidelity gate (book_standard.yaml#render_fidelity
    # .banned_source_glyphs). Counting ▣ left Gate 6 UNSATISFIABLE against render_fidelity — the two gates
    # contradicted. The R8-safe "**RECEIPT —" header is letters-only by construction => no fallback possible.
    boxes = len(re.findall(r"\*\*RECEIPT\b", text))
    sections = len(re.findall(r"^#{1,2} (?:Chapter \d+|Appendix )", text, re.M))  # match ## chapter headers too
    if boxes == 0:
        return {"pass": False, "status": "no-receipt-boxes",
                "detail": "Gate 6 RED — manuscript has no Receipt boxes (Helix anchor missing)"}
    if sections and boxes < sections:
        return {"pass": False, "status": f"partial({boxes}/{sections})",
                "detail": f"Gate 6 PARTIAL — {boxes} Receipt boxes for {sections} sections"}
    return {"pass": True, "status": f"green({boxes}-boxes)", "detail": ""}


def _check_boards(bdir: Path | None) -> dict:
    """The canonical Series-Pipeline boards (ratified mapping GB [207]+[209]): Editorial R1/R2/R3 each
    rigor-pass via their embedded ```rigor``` block; Book-to-UX present; Tech/Arch present + rigor-pass.
    Tech/Arch is MANDATORY — un-run reads NOT-RUN (honest red) with its docket, never a false green."""
    if not bdir:
        return {"check": "boards_executed", "pass": False, "detail": "book dir not found",
                "gap": "locate book artifact dir"}
    try:
        sys.path.insert(0, str(REPO / "scripts"))
        from board_rigor import rigor_check_md
    except Exception:  # noqa: BLE001
        rigor_check_md = None

    ok, issues, statuses = [], [], {}

    # 1) Editorial R1/R2/R3 — each round .md present + rigor-pass (Cold Reader is a lens within, flagged in block)
    for rnd in REQUIRED_EDITORIAL_ROUNDS:
        files = sorted(bdir.glob(f"*editorial_board_review*{rnd}.md"))
        label = f"editorial_{rnd}"
        if not files:
            issues.append(f"{label}: not run"); statuses[label] = "not-run"; continue
        if rigor_check_md:
            r = rigor_check_md(str(files[0]))
            if r.get("pass"):
                ok.append(label); statuses[label] = "rigor-pass"
            else:
                issues.append(f"{label}: RIGOR FAIL ({len(r.get('gaps', []))})"); statuses[label] = "rigor-fail"
        else:
            ok.append(label); statuses[label] = "present"

    # 2) Book-to-UX Translation (17.5) — presence (prescriptive board)
    if sorted(bdir.glob("*virality_to_ux_translation*.md")):
        ok.append("book_to_ux"); statuses["book_to_ux"] = "present"
    else:
        issues.append("book_to_ux: not run"); statuses["book_to_ux"] = "not-run"

    # 3) Tech/Arch (17.6) — MANDATORY green; un-run is honest red (never a false green), docket surfaced
    ta = sorted(bdir.glob("*tech_arch_review*.md"))
    if not ta:
        issues.append(f"technical: NOT RUN (mandatory, fires after Book-to-UX) — docket: {TECH_ARCH_DOCKET}")
        statuses["technical"] = "not-run"
    elif rigor_check_md:
        r = rigor_check_md(str(ta[0]))
        if r.get("pass"):
            ok.append("technical"); statuses["technical"] = "rigor-pass"
        else:
            # a tech_arch .md without an embedded rigor block still counts as run if it states a verdict;
            # but a rigor-fail is honest red, not green.
            issues.append(f"technical: present but RIGOR FAIL/no-block ({len(r.get('gaps', []))})")
            statuses["technical"] = "present-no-rigor"
    else:
        ok.append("technical"); statuses["technical"] = "present"

    # 4) Tech/Arch GATE 6 — Renderability (Deterministic-Render Standard v1.0). Binding: review_ready never
    #    flips without the Receipt-box anchor. Only enforced once a Tech/Arch board exists (Gate 6 lives in it).
    if ta:
        g6 = _check_gate6_renderability(bdir)
        statuses["renderability_gate6"] = g6["status"]
        if g6["pass"]:
            ok.append("renderability_gate6")
        else:
            issues.append(f"renderability_gate6: {g6['detail']}")

    return {"check": "boards_executed", "pass": not issues,
            "detail": " · ".join(f"{k}={v}" for k, v in statuses.items()),
            "statuses": statuses,
            "gap": ("; ".join(issues) if issues else "")}


def _book_refs(book_id: str, extra: list[str]) -> list[str]:
    toks = [book_id, book_id.replace("_", " ")] + [book_id.split("_", 1)[-1].replace("_", " ")] + list(extra or [])
    return [t.lower() for t in toks if t]


def _check_obligations(refs: list[str]) -> dict:
    """Every obligation referencing the book is closed (credit) or open-with-defer-reason."""
    try:
        sys.path.insert(0, str(REPO / "src"))
        from sovereign_agent.obligations.ledger import ObligationLedger
        lg = ObligationLedger(str(LEDGER_ROOT))
        open_obs = lg.open_obligations()
    except Exception as e:  # noqa: BLE001 — ledger optional; report honestly
        return {"check": "obligations_closed", "pass": False, "detail": f"ledger error: {e}",
                "gap": "repair obligation ledger access"}

    def _matches(o: dict) -> bool:
        # The review packet itself IS the human gate (ref=review_ready:<book>), not an unresolved board
        # finding — never count it against the book's own readiness (it stays open until KM dispositions).
        if (o.get("ref") or "").startswith("review_ready:"):
            return False
        hay = f"{o.get('intent', '')} {o.get('title', '')} {o.get('ref', '')}".lower()
        return any(r in hay for r in refs)

    def _deferred(o: dict) -> bool:
        hay = f"{o.get('intent', '')} {o.get('title', '')} {o.get('ref', '')}".lower()
        return "defer" in hay

    book_open = [o for o in open_obs if _matches(o)]
    blocking = [o for o in book_open if not _deferred(o)]
    return {"check": "obligations_closed", "pass": not blocking,
            "detail": f"{len(book_open)} open for book ({len(blocking)} blocking, {len(book_open) - len(blocking)} deferred)",
            "gap": ("close or defer-with-reason: " + ", ".join(o.get("id", "?") for o in blocking[:6]) if blocking else ""),
            "blocking_ids": [o.get("id") for o in blocking]}


def _check_fidelity(refs: list[str]) -> dict:
    """GB witness trace recorded a PASS for the book (semantic gate). Scans the GB meta-cylinder + any
    *fidelity*.ndjson record. PASS iff the latest verdict record for the book is PASS.

    Robustness fix (GB-flagged 2026-06-23): parse the explicit `fidelity_verdict` FIELD VALUE, not the whole
    line. The old check (`"pass" in low and "fail" not in low`) flipped a genuine PASS to '?' whenever the
    record's prose legitimately contained the word 'fail' (e.g. a trace describing 'fail-closed' gate behavior) —
    the same gate-brittleness class as the earlier brand/markup false-REDs. Now the verdict is value-scoped."""
    import json as _json  # noqa: PLC0415
    # One-truth ordering fix (GB-flagged 2026-06-24): select the latest verdict by the record's DATE — the
    # filename date (YYYY-MM-DD) → an in-file ts field → file mtime — NOT by filename sort order. The old code
    # iterated `sorted(glob())` and let the last file win, so a stale 'vol_..._2026-06-14' (PASS) out-sorted a
    # fresh 'GB_vol_..._2026-06-24' (HOLD) alphabetically and propped a false-green. Now a fresh verdict wins.
    sources = [GB_CYLINDER] + list(REPO.glob("artifacts/*fidelity*.ndjson")) + list(REPO.glob("memory/**/*fidelity*.ndjson"))
    candidates = []  # (date_key, mtime, verdict)
    for src in sources:
        if not src.is_file():
            continue
        verdict = None
        ts_in_file = ""
        for line in src.read_text(encoding="utf-8").splitlines():
            low = line.lower()
            if not any(r in low for r in refs):
                continue
            # explicit fidelity_verdict field — read its VALUE only (scoped); recognize pass/fail/HOLD/superseded
            try:
                obj = _json.loads(line)
            except (ValueError, TypeError):
                obj = None
            if isinstance(obj, dict):
                for k, v in obj.items():
                    kl = str(k).lower()
                    if "fidelity_verdict" in kl or ("fidelity" in kl and "verdict" in kl):
                        sv = str(v).lower()
                        verdict = ("pass" if "pass" in sv else "fail" if "fail" in sv
                                   else "hold" if "hold" in sv else "superseded" if "supersed" in sv else verdict)
                    if kl in ("ts", "date", "timestamp", "sealed_at", "when") and v:
                        ts_in_file = str(v)
            if verdict is None:
                m = re.search(r"fidelity[_ ]verdict\W+(pass|fail|hold|superseded)", low)
                if m:
                    verdict = m.group(1)
        if not verdict:
            continue
        fnm = re.search(r"(\d{4}-\d{2}-\d{2})", src.name)
        date_key = (fnm.group(1) if fnm else (ts_in_file[:10] if ts_in_file else ""))
        candidates.append((date_key, src.stat().st_mtime, verdict))
    if not candidates:
        latest = None
    else:
        candidates.sort(key=lambda c: (c[0], c[1]))  # by date, then mtime — fresh out-truths stale
        latest = candidates[-1][2]
    passed = latest == "pass"
    return {"check": "fidelity_passed", "pass": passed,
            "detail": (f"verdict: {latest}" if latest else "no fidelity record for book"),
            "gap": ("" if passed else "GB fidelity trace must record PASS (semantic source-trace)")}


def _check_review_brief(bdir: Path | None, book_id: str, extra: list[str] | None = None) -> dict:
    """One-page Review Brief present with 3–7 genuine judgment calls (framed as decisions). GB seals it in
    artifacts/ — match by book_id or any short token (e.g. 'B12') so the contract finds it wherever it lives."""
    tokens = [book_id] + [t for t in (extra or []) if t]
    cands = []
    if bdir:
        cands += list(bdir.glob("*review_brief*")) + list(bdir.glob("*Review_Brief*")) + list(bdir.glob("REVIEW_BRIEF*"))
    art = REPO / "artifacts"
    for tok in tokens:
        cands += [p for p in art.glob("*[Rr]eview_[Bb]rief*") if tok.lower() in p.name.lower()]
        cands += [p for p in art.glob(f"*{tok}*") if "review" in p.name.lower() and "brief" in p.name.lower()]
        cands += [p for p in art.glob(f"*{tok}*[Ff]old*[Rr]eview*")]
    cands = list(dict.fromkeys(cands))  # dedupe, keep order
    if not cands:
        return {"check": "review_brief_sealed", "pass": False, "detail": "no Review Brief found",
                "gap": "GB seals one-page Review Brief w/ 3–7 judgment calls"}
    text = cands[0].read_text(encoding="utf-8", errors="replace")
    calls = len(re.findall(r"(?im)^\s*(?:\d+[.)]|[-*])\s+.*\b(decision|judg(e)?ment|call|approve|choose|whether|should we)\b", text)) \
        or len(re.findall(r"(?i)judg(e)?ment call", text))
    ok = 3 <= calls <= 7
    return {"check": "review_brief_sealed", "pass": ok, "detail": f"{cands[0].name}: {calls} judgment calls",
            "gap": ("" if ok else f"Review Brief needs 3–7 judgment calls (found {calls})")}


def _brief_path(book_id: str, extra: list[str]) -> str:
    bdir = _book_dir(book_id)
    chk = _check_review_brief(bdir, book_id, extra)
    # chk.detail is "<name>: N judgment calls"; recover the artifact path if it lives in artifacts/
    for tok in [book_id] + (extra or []):
        for p in (REPO / "artifacts").glob("*[Rr]eview_[Bb]rief*"):
            if tok.lower() in p.name.lower():
                return str(p.relative_to(REPO))
    return chk.get("detail", "")


def mint_review_packet(book_id: str, label: str, extra: list[str]) -> str | None:
    """On READY, mint the human-gate packet so the book APPEARS in the Awaiting-KM view with its Brief
    one click away (pilot finding #2, GB [171]). Idempotent: skip if a review packet already exists."""
    # Node owner derived from env, not a hardcoded literal (audit 2026-06-13c #24, CONSTITUTION §1) — so
    # the packet attributes correctly on any node, matching the runs-anywhere LEDGER_ROOT fix beside it.
    owner = (os.environ.get("BREATHLINE_NODE_OWNER") or os.environ.get("BREATHLINE_NODE_LOOPBACK_OWNER")
             or "KM-1176").strip()
    try:
        sys.path.insert(0, str(REPO / "src"))
        from sovereign_agent.obligations.ledger import ObligationLedger
        lg = ObligationLedger(str(LEDGER_ROOT), principal_id=owner)
    except Exception:  # noqa: BLE001
        return None
    ref = f"review_ready:{book_id}"
    for o in lg.open_obligations():
        if (o.get("ref") or "") == ref:
            return o.get("id")  # already minted — idempotent
    brief = _brief_path(book_id, extra)
    bdir = _book_dir(book_id)
    ms, pdf = "", ""
    if bdir:
        cands = sorted(bdir.glob("manuscript_v*.md"))
        ms = str(cands[-1].relative_to(REPO.parent)) if cands else ""
        pdfs = sorted((bdir / "final").glob("*.pdf"))
        pdf = str(pdfs[0]) if pdfs else ""
    entry = lg.open(
        title=f"✍ Sign off {label} — review-ready; Accept to seal",
        owner=owner, classification="C1", material=True, next_gate="Human disposition", ref=ref,
        intent=(f"All Review-Ready Rail gates green (boards rigor-pass · obligations clean · fidelity PASS · "
                f"Review Brief sealed) and your review feedback is applied + rebuilt clean. "
                f"FINAL PDF: {pdf}. "
                f"ACCEPT = your sign-off (review complete) → Tiger seals the final → you provide pb+hc ISBNs "
                f"for the KDP dispatch bundle. Review Brief: {brief}. Manuscript: {ms}."),
        lgp={"objective": "first book through the rail — human keeps only the judgment (LGP/human primacy)"},
    )
    return entry.get("id")


def _check_artifact_package(bdir: Path | None, book_id: str) -> dict:
    """Artifact-package gate (KM 2026-06-18, GB [414]): review_ready CANNOT flip without the human-reviewable
    package — a formatted PDF + figures + cover + /seeit pages + KDP structure. Closes the rail gap that let
    V3 reach review_ready on .md + brief alone, with no readable book for KM to actually review."""
    import os  # noqa: PLC0415
    name = "artifact_package"
    if not bdir:
        return {"check": name, "pass": False, "detail": "book dir not found", "gap": "no book dir"}
    final = bdir / "final"
    pdfs = [p for p in (final.glob("*.pdf") if final.exists() else []) if "wrap" not in p.name.lower()]
    # canonical S2+ figures live in figures/approved/ (SVG two-tier renders); fall back to figures/ then images/ (S1)
    figs = (list((bdir / "figures" / "approved").glob("figure_*_book.png"))
            or list((bdir / "figures" / "approved").glob("*.png"))
            or list((bdir / "figures").glob("*.png"))
            or list((bdir / "images").glob("fig*.png")))
    covers = (list(final.glob("cover*wrap*")) + list(final.glob("cover*.png")) + list(final.glob("cover*.jpg"))) if final.exists() else []
    seeit_root = Path(os.environ.get("BREATHLINE_SEEIT_ROOT", os.path.expanduser("~/six-sov-www/seeit")))
    seeit_ok = False
    ex = seeit_root / "exercises.py"
    if ex.exists():
        txt = ex.read_text(encoding="utf-8", errors="ignore").lower()
        seeit_ok = any(tok in txt for tok in ("helix", "s3v3", "vol_03_helix"))
    issues = []
    if not pdfs:    issues.append("no formatted PDF in final/")
    if not figs:    issues.append("figures/ empty")
    if not covers:  issues.append("no cover in final/")
    if not seeit_ok: issues.append("no /seeit pages for this book")
    detail = f"pdf={'Y' if pdfs else 'N'} · figures={len(figs)} · cover={'Y' if covers else 'N'} · seeit={'Y' if seeit_ok else 'N'}"
    return {"check": name, "pass": not issues, "detail": detail,
            "gap": ("artifact package incomplete: " + "; ".join(issues)) if issues else None}


# Calibrated S2 FLOOR — measured from the FULL S2 set 2026-06-18 (GB [422] catch: a gate must PASS S2, not
# exceed it). S2 totals: v01 14,484 · v02 17,312 · v04 10,589 · v05 15,046 → S2 MIN = vol_04 (10,589w, 12ch
# avg 882, min 480). The floor sits at/just below that minimum so NO real S2 volume is RED-blocked; the
# blocking Cold-Reader/quality verdict (GB-owned) enforces the *target* above this regression floor.
_S2_BAR = {"total_words": 10500, "avg_chapter_words": 850, "min_chapter_words": 450,
           "seeit_pages_min_ratio": 1.0}  # >= one /seeit page per chapter (GB floor; S2 runs ~1.2/ch)


def _check_substance(bdir: Path | None, book_id: str) -> dict:
    """Substance gate (KM 2026-06-18, the V3 regression): a volume must match the calibrated S2 DEPTH bar —
    chapter depth + total words + /seeit coverage — not just pass structural gates. Thresholds are MEASURED
    from the S2 V1 anchor so the gate could not fail S2 itself (its min chapter is 874w; appendices count to
    total, not to the per-chapter floor). Closes the hole that let a ~6.8k-word volume reach review_ready."""
    import os  # noqa: PLC0415
    name = "substance_s2_bar"
    if not bdir:
        return {"check": name, "pass": False, "detail": "book dir not found", "gap": "no book dir"}
    mss = sorted((p for p in bdir.glob("manuscript_v*.md") if re.match(r"manuscript_v[0-9.]+\.md$", p.name)), key=_vkey)
    if not mss:
        return {"check": name, "pass": False, "detail": "no manuscript", "gap": "no manuscript"}
    text = mss[-1].read_text(encoding="utf-8", errors="ignore")
    # split chapters vs appendices: depth bars on chapters; total over all sections (S2's own shape)
    pieces = re.split(r"(?m)^(#{1,2} (?:Chapter|Appendix)[^\n]*)", text)
    chap_words, appx_words = [], []
    for k in range(1, len(pieces), 2):
        head = pieces[k]; w = len(pieces[k + 1].split()) if k + 1 < len(pieces) else 0
        (appx_words if "Appendix" in head else chap_words).append(w)
    chap_words = chap_words or [0]
    nch = len(chap_words)
    total = sum(chap_words) + sum(appx_words)
    avg = sum(chap_words) // nch
    thin = [i + 1 for i, w in enumerate(chap_words) if w < _S2_BAR["min_chapter_words"]]
    seeit_root = Path(os.environ.get("BREATHLINE_SEEIT_ROOT", os.path.expanduser("~/six-sov-www/seeit")))
    seeit_n = 0
    ex = seeit_root / "exercises.py"
    if ex.exists():
        _seeit_txt = ex.read_text(encoding="utf-8", errors="ignore")
        # Prefer the book's OWN /seeit pages (sX vY derived from the dir), fall back to the s3v3 proxy so volumes
        # that have not authored their own pages keep their prior (lenient) behaviour. max() => never regresses.
        _proxy = len(re.findall(r'"id":"s3v3-', _seeit_txt))
        _own = 0
        if bdir is not None:
            _sm = re.search(r"series_0*(\d+)", str(bdir))
            _vm = re.search(r"vol_0*(\d+)", str(bdir))
            if _sm and _vm:
                _own = len(re.findall(rf'"id":"s{_sm.group(1)}v{_vm.group(1)}-', _seeit_txt))
        seeit_n = max(_own, _proxy)
    issues = []
    if total < _S2_BAR["total_words"]:
        issues.append(f"total {total}w < S2 floor {_S2_BAR['total_words']}w")
    if avg < _S2_BAR["avg_chapter_words"]:
        issues.append(f"chapter avg {avg}w < S2 floor {_S2_BAR['avg_chapter_words']}w")
    if thin:
        issues.append(f"{len(thin)} chapters under {_S2_BAR['min_chapter_words']}w (ch {thin})")
    if seeit_n < int(_S2_BAR["seeit_pages_min_ratio"] * nch):
        issues.append(f"/seeit {seeit_n} < {int(_S2_BAR['seeit_pages_min_ratio']*nch)} (≈ one per chapter)")
    detail = f"total={total}w · chapters={nch}@avg{avg}w · appx={len(appx_words)} · seeit={seeit_n}/{nch}ch"
    return {"check": name, "pass": not issues, "detail": detail,
            "gap": ("below S2 bar: " + "; ".join(issues)) if issues else None}


# canonical_toolchain gate (GB spec 2026-06-18): a volume must be built with the proven S1/S2 tools, not
# per-volume ad-hoc scripts. Verified mechanically via the volume's toolchain.json provenance.
_CANON_ALLOW = {"build_v1.0.py", "generate_svg_v1.0.py", "svg_toolkit.py", "generate_images.py", "chartgen.py",
                "generate_wraps_standard.py", "build_pages.py"}  # generate_svg + svg_toolkit = the ratified SVG figure tool (Visual Standard v2.0, S2+)
_CANON_ADHOC = {"build_pdf.py", "gen_cover.py", "gen_figures.py", "gen_figures_more.py"}


def _check_canonical_toolchain(bdir: Path | None, book_id: str) -> dict:
    """canonical_toolchain (GB 2026-06-18): the production package was built with the canonical S1/S2 chain,
    not per-volume ad-hoc scripts. Reads toolchain.json provenance; RED if missing, if any producer is not in
    the allowlist, or if an ad-hoc producer script is present in the volume. No provenance -> RED (honest)."""
    import json as _json  # noqa: PLC0415
    name = "canonical_toolchain"
    if not bdir:
        return {"check": name, "pass": False, "detail": "book dir not found", "gap": "no book dir"}
    tj = bdir / "toolchain.json"
    if not tj.exists():
        return {"check": name, "pass": False, "detail": "no toolchain.json",
                "gap": "no build provenance — record toolchain.json (canonical producers per artifact)"}
    try:
        prov = (_json.loads(tj.read_text(encoding="utf-8")) or {}).get("producers", {})
    except ValueError:
        return {"check": name, "pass": False, "detail": "toolchain.json invalid", "gap": "toolchain.json not valid JSON"}
    issues = []
    non_allow = [f"{k}={v}" for k, v in prov.items() if v not in _CANON_ALLOW]
    if non_allow:
        issues.append("non-canonical producer(s): " + ", ".join(non_allow))
    for need in ("pdf", "figures", "cover", "seeit"):
        if need not in prov:
            issues.append(f"missing provenance: {need}")
    adhoc_present = sorted(p.name for p in bdir.glob("*.py") if p.name in _CANON_ADHOC)
    if adhoc_present:
        issues.append("ad-hoc production script(s) present: " + ", ".join(adhoc_present))
    detail = "producers=" + ",".join(f"{k}:{v}" for k, v in prov.items())
    return {"check": name, "pass": not issues, "detail": detail[:90],
            "gap": ("canonical_toolchain: " + "; ".join(issues)) if issues else None}


# book_structure gate (KM 2026-06-18, the V3 'same pen' regression): a volume must follow the established
# S1/S2 manuscript convention — front matter + per-chapter scaffolding + back matter — not a per-book shape.
# Required sections measured from the S2 V1 template.
_STRUCT_FRONT = ["About This Series", "Table of Contents", "Preflight", "Executive Brief"]
_STRUCT_BACK = ["See It Work", "Reader Resources", "About the Author", "Also by Kenneth Mangum", "Connect"]


def _check_book_structure(bdir: Path | None, book_id: str) -> dict:
    """book_structure (KM 2026-06-18; hardened 2026-06-18 eve after GB's rendered-PDF read): the manuscript must
    carry the S1/S2 book convention — front matter (copyright/ISBN page, About This Series, Table of Contents,
    Preflight, Executive Brief), per-chapter scaffolding (all THREE convention elements: Worked Example +
    Industry Signal + Your Next Steps), and back matter (See It Work, Reader Resources, About the Author, Also by
    Kenneth Mangum, Connect). Closes the 'not from the same pen' gap.

    GB's PDF read caught that the gate passed V3 on 2 of the 3 elements (Industry Signal + Your Next Steps) while
    Worked Example was wholly absent (0 boxes) — the metric-based gate missed what an eye on the rendered artifact
    saw. The fix adds the Worked Example floor. CALIBRATION (pass-S2-not-exceed-it): measured Worked Example
    counts across the S2 anchor are V1=4/9ch, V2=1/12ch, V4=2/12ch, V5=5/10ch — so the absolute S2 minimum is 1
    (V2). The floor is therefore Worked Example >= 1: high enough to catch a whole missing element type (V3's old
    0), low enough never to block a real S2 volume. A per-chapter floor would FAIL three of four S2 volumes — the
    recurring over-strict-gate mistake. The craft target (match the chosen V1 pen, ~4) is separate from this floor."""
    name = "book_structure"
    if not bdir:
        return {"check": name, "pass": False, "detail": "book dir not found", "gap": "no book dir"}
    mss = sorted((p for p in bdir.glob("manuscript_v*.md") if re.match(r"manuscript_v[0-9.]+\.md$", p.name)), key=_vkey)
    if not mss:
        return {"check": name, "pass": False, "detail": "no manuscript", "gap": "no manuscript"}
    t = mss[-1].read_text(encoding="utf-8", errors="ignore")
    n_chap = len(re.findall(r"(?m)^# Chapter \d+", t)) or len(re.findall(r"(?m)^#{1,2} Chapter \d+", t))
    miss = []
    miss += [f"front:{s}" for s in _STRUCT_FRONT if s not in t]
    if "Copyright" not in t or "ISBN" not in t:
        miss.append("front:copyright/ISBN page")
    n_signal = t.count("## Industry Signal")
    n_steps = t.count("## Your Next Steps")
    n_worked = len(re.findall(r"(?m)^#{1,2} Worked Example", t))
    # threshold = n_chap - 1: measured to pass the S2 anchor (S2 V1 carries 8 Industry Signals across 9 chapters)
    floor = max(1, n_chap - 1)
    if n_chap and n_signal < floor:
        miss.append(f"per-chapter:Industry Signal ({n_signal}/{n_chap} chapters)")
    if n_chap and n_steps < floor:
        miss.append(f"per-chapter:Your Next Steps ({n_steps}/{n_chap} chapters)")
    # Worked Example floor = 1 (the measured S2 minimum, V2=1/12). Catches a whole missing element type (V3's old
    # 0) without blocking a real S2 volume; a per-chapter floor would fail 3 of 4 S2 volumes.
    if n_chap and n_worked < 1:
        miss.append(f"convention-element:Worked Example absent ({n_worked} labeled boxes; need >=1, S2 floor)")
    miss += [f"back:{s}" for s in _STRUCT_BACK if s not in t]
    detail = f"chapters={n_chap} · worked={n_worked} · signal={n_signal} · steps={n_steps} · front+back present"
    return {"check": name, "pass": not miss, "detail": detail[:90],
            "gap": ("missing S1/S2 sections: " + "; ".join(miss)) if miss else None}


def _check_render_fidelity(bdir: Path | None, book_id: str) -> dict:
    """render_fidelity (KM-ratified 2026-06-18): the BUILT PDF must match the S2 'pen' at the rendered-page
    level — approved font families only (no stray DejaVu/emoji), no raw markdown leaking to the reader, no
    source glyph that forces a font fallback. Closes the root cause of the V3 render drift: every other gate
    reasoned at the .md/marker level; this one validates what the page actually renders (pdffonts + pdftotext).
    Criteria load from book_standards/book_standard.yaml#render_fidelity (the machine source of truth)."""
    name = "render_fidelity"
    if not bdir:
        return {"check": name, "pass": False, "detail": "book dir not found", "gap": "no book dir"}
    fin = bdir / "final"
    pdfs = sorted(p for p in fin.glob("*.pdf")) if fin.exists() else []
    pdfs = [p for p in pdfs if not re.search(r"wrap|cover", p.name, re.I)]
    if not pdfs:
        return {"check": name, "pass": False, "detail": "no built PDF in final/", "gap": "no PDF to lint"}
    pdf = max(pdfs, key=lambda p: p.stat().st_size)  # the manuscript PDF (largest non-cover)
    mss = sorted((p for p in bdir.glob("manuscript_v*.md")
                 if re.match(r"manuscript_v[0-9.]+\.md$", p.name)), key=_vkey)
    source = str(mss[-1]) if mss else None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import pdf_parity_lint
        r = pdf_parity_lint.lint(str(pdf), source)
    except Exception as e:  # poppler missing or import error — surface, don't silently pass
        return {"check": name, "pass": False, "detail": f"lint error: {e}"[:90], "gap": f"render lint failed: {e}"}
    fails = [c for c in r["checks"] if not c["pass"]]
    detail = f"{pdf.name}: " + (" · ".join(c["detail"] for c in r["checks"]))
    return {"check": name, "pass": r["pass"], "detail": detail[:90],
            "gap": ("render divergence vs S2 pen: " + "; ".join(c["detail"] for c in fails)) if fails else None}


def _check_enforcement_claims(bdir: Path | None, book_id: str) -> dict:
    """enforcement_claims (KM Call-3, 2026-06-24): the mechanical exists_is_not_wired backstop. Every RECEIPT
    RUNS-TODAY claim that asserts ENFORCEMENT must cite a live code trace or be marked DESIGNED-TOWARD; known-unwired
    phrasings HARD-fail. Closes the recurring class (S3-V2 SOD + S4-V2 'YAML enforced at the write') so a board
    forgetting to trace can no longer let an overclaim ship. Advisory flags pass-with-note; HARD flags block."""
    name = "enforcement_claims"
    if not bdir:
        return {"check": name, "pass": False, "detail": "book dir not found", "gap": "no book dir"}
    mss = sorted((p for p in bdir.glob("manuscript_v*.md")
                 if re.match(r"manuscript_v[0-9.]+\.md$", p.name)), key=_vkey)
    if not mss:
        return {"check": name, "pass": True, "detail": "no manuscript to scan", "gap": None}
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import enforcement_claim_lint
        r = enforcement_claim_lint.lint_text(mss[-1].read_text(encoding="utf-8"))
    except Exception as e:  # surface, never silently pass
        return {"check": name, "pass": False, "detail": f"lint error: {e}"[:90], "gap": f"enforcement lint failed: {e}"}
    hard, adv = len(r["hard"]), len(r["flags"]) - len(r["hard"])
    detail = f"{r['n_units']} runs-today claims scanned · {hard} HARD · {adv} advisory"
    gap = None
    if r["hard"]:
        gap = "exists != wired overclaim(s): " + "; ".join(f"{f['where']}:{f['hit']}" for f in r["hard"])
    return {"check": name, "pass": r["pass"], "detail": detail, "gap": gap}


def _check_production_standards(bdir: Path | None, book_id: str) -> dict:
    """production_standards (KM-ratified 2026-06-18): the manuscript matches the S2 'pen' as enforceable layout
    rules — no editing artifacts, S2-style flat clickable TOC, chapter-end order (receipt closes the chapter),
    no clumped callout/back-matter lists, figures placed beside their prose. Criteria load from
    book_standards/book_standard.yaml#production_standards. Delegates to scripts/book_lint.py."""
    name = "production_standards"
    if not bdir:
        return {"check": name, "pass": False, "detail": "book dir not found", "gap": "no book dir"}
    mss = sorted((p for p in bdir.glob("manuscript_v*.md") if re.match(r"manuscript_v[0-9.]+\.md$", p.name)), key=_vkey)
    if not mss:
        return {"check": name, "pass": False, "detail": "no manuscript", "gap": "no manuscript"}
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import book_lint
        r = book_lint.lint(str(mss[-1]))
    except Exception as e:
        return {"check": name, "pass": False, "detail": f"lint error: {e}"[:90], "gap": f"book_lint failed: {e}"}
    fails = [c for c in r["checks"] if not c["pass"]]
    detail = " · ".join(f"{c['check']}={'ok' if c['pass'] else 'RED'}" for c in r["checks"])
    return {"check": name, "pass": r["pass"], "detail": detail[:90],
            "gap": ("S2-pen layout divergence: " + "; ".join(c["detail"] for c in fails)) if fails else None}


BOOK_STANDARD = Path("/home/kmangum/work-repos/mangumcfo/breathline-books-vault/book_standards/book_standard.yaml")


def _book_standard() -> dict:
    import yaml  # noqa: PLC0415
    try:
        return yaml.safe_load(BOOK_STANDARD.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _latest_ms_text(bdir: Path | None) -> tuple[str, str]:
    if not bdir:
        return "", ""
    mss = sorted((p for p in bdir.glob("manuscript_v*.md")
                  if re.match(r"manuscript_v[0-9.]+\.md$", p.name)), key=_vkey)
    return (mss[-1].read_text(encoding="utf-8", errors="ignore"), mss[-1].name) if mss else ("", "")


def _check_forward_reference(bdir: Path | None, book_id: str) -> dict:
    """forward_reference (KM 6-call D2, book_standard.yaml#forward_reference): MINIMIZE forwards; anything
    deliverable this season is BUILT IN, not deferred; every genuine cross-series forward NAMES its closing
    series + a closure plan. RED if a forward lacks a named closing series, or this-season work is labeled
    'forward'. Criteria load from the machine source of truth."""
    name = "forward_reference"
    crit = _book_standard().get("forward_reference", {})
    text, msname = _latest_ms_text(bdir)
    if not text:
        return {"check": name, "pass": False, "detail": "no manuscript", "gap": "no manuscript to scan"}
    fwd_pat = re.compile(r"\[current\s*·\s*forward\]|\bforward edge\b|deferred to v\d|in a (?:later|future) series", re.I)
    ser_pat = re.compile(r"Series\s+\d|\bS\d\b")
    # SECTION-level check (D2 intent): a forward must name its closing series somewhere in the SAME section
    # (between ## headings) — not on the literal same line. The section names the closure once.
    sections = re.split(r"(?m)^#{1,3}\s", text)
    total, unclosed = 0, []
    for sec in sections:
        fwds = fwd_pat.findall(sec)
        if fwds:
            total += len(fwds)
            if not ser_pat.search(sec):
                head = sec.strip().split("\n", 1)[0][:48]
                unclosed.append(head)
    ok = (not crit) or not unclosed
    return {"check": name, "pass": ok,
            "detail": f"{total} forward refs · {len(unclosed)} sections without a named closing series ({msname})"[:90],
            "gap": None if ok else f"D2 — forward sections lack a named closing series/closure plan: {unclosed[:2]}"}


def _check_keyword_discipline(bdir: Path | None, book_id: str) -> dict:
    """keyword_discipline (KM 6-call D5, book_standard.yaml#keyword_discipline): RECONCILE the volume to its
    locked-outline keyword targets, anchor chapters on them, FLAG any deviation. RED if target keywords are
    unreconciled/dropped. Targets = the book's metadata chapter_kw (the locked-outline keywords)."""
    name = "keyword_discipline"
    crit = _book_standard().get("keyword_discipline", {})
    text, msname = _latest_ms_text(bdir)
    if not text:
        return {"check": name, "pass": False, "detail": "no manuscript", "gap": "no manuscript to scan"}
    # resolve keyword targets from the book's metadata (locked-outline keywords)
    targets: list[str] = []
    cands = []
    if bdir:
        cands = list(bdir.glob("metadata*.y*ml")) + list(bdir.parent.glob("v*/metadata*.y*ml"))
    for mp in cands:
        try:
            import yaml  # noqa: PLC0415
            m = yaml.safe_load(mp.read_text(encoding="utf-8")) or {}
            targets = m.get("chapter_kw") or m.get("keywords") or m.get("keyword_targets") or []
            if targets:
                break
        except Exception:
            continue
    if not targets:
        return {"check": name, "pass": False, "detail": "no keyword targets found",
                "gap": "D5 — locked-outline keyword targets not found (metadata chapter_kw)"}
    low = text.lower()
    missing = [k for k in targets if k.lower() not in low]
    ok = (not crit) or not missing
    return {"check": name, "pass": ok,
            "detail": f"{len(targets) - len(missing)}/{len(targets)} target keywords anchored"[:90],
            "gap": None if ok else f"D5 — keyword drift; targets not anchored: {missing}"}


def _check_cover_standard(bdir: Path | None, book_id: str) -> dict:
    """cover_standard (KM 2026-06-20, book_standard.yaml#cover_standard): the cover must match the S1/S2 pen —
    a real HERO illustration, the BREATHLINE BOOKS imprint, the series/volume tag, the author, navy/gold palette,
    and the full KDP wrap set. CRITICAL: this inspects the RENDERED output (verify_output_not_just_provenance) —
    pixel complexity for the hero, OCR for the text — so a flat cover with the right toolchain.json still FAILS
    (closes the canonical_toolchain provenance-vs-output gap)."""
    name = "cover_standard"
    crit = (_book_standard().get("cover_standard") or {}).get("must_have", {})
    if not bdir or not crit:
        return {"check": name, "pass": False, "detail": "no book dir / no cover_standard spec",
                "gap": "no cover_standard criteria"}
    fin = bdir / "final"
    cover = fin / "cover_KDP.png"
    if not cover.exists():
        return {"check": name, "pass": False, "detail": "no cover_KDP.png", "gap": "build the cover"}
    fails = []
    from PIL import Image, ImageOps  # noqa: PLC0415
    im = Image.open(cover).convert("RGB")
    # 1) HERO present — flat text covers have ~6k unique colours; a rich hero has 100k+ (calibrated vs S2 V1).
    if crit.get("hero_image"):
        upper = im.crop((0, 0, im.width, int(im.height * 0.55)))
        cols = upper.getcolors(maxcolors=400000)
        uniq = len(cols) if cols else 400000
        if uniq < 25000:
            fails.append(f"no hero image (flat: {uniq} colours < 25000)")
    # 2) OCR the render (white-on-dark → OCR the inverted grayscale too) for the required text
    need_text = {}
    if crit.get("imprint_line"):
        need_text["imprint"] = str(crit["imprint_line"]).lower()
    if crit.get("author"):
        need_text["author"] = str(crit["author"]).lower()
    if crit.get("series_volume_tag"):
        need_text["volume tag"] = f"volume {book_id_vol(book_id)}"
    if need_text:
        try:
            import pytesseract  # noqa: PLC0415
            small = im.resize((1200, int(im.height * 1200 / im.width)))
            g = small.convert("L")
            txt = (pytesseract.image_to_string(g) + " " + pytesseract.image_to_string(ImageOps.invert(g))).lower()
            txt = re.sub(r"\s+", " ", txt)
            for label, needle in need_text.items():
                if needle not in txt and not all(w in txt for w in needle.split()):
                    fails.append(f"{label} '{needle}' not found in render (OCR)")
        except Exception as e:  # noqa: BLE001
            fails.append(f"OCR unavailable: {e}"[:60])
    # 3) palette — navy + gold both present (brand)
    if crit.get("palette"):
        px = list(im.resize((120, 180)).getdata())
        navy = sum(1 for r, g, b in px if b > r and b < 130 and r < 90)
        gold = sum(1 for r, g, b in px if r > 150 and 120 < g < 200 and b < 130)
        if navy < len(px) * 0.15:
            fails.append("navy not dominant")
        if gold < 3:
            fails.append("no gold accent")
    # 4) full wrap set
    for w in (crit.get("wrap_set") or []):
        if not any((fin / f"{w}{ext}").exists() for ext in (".png", ".pdf", ".jpg")):
            fails.append(f"missing wrap: {w}")
    ok = not fails
    return {"check": name, "pass": ok,
            "detail": ("hero+imprint+tag+author+palette+wraps verified in the render" if ok
                       else f"{len(fails)} cover issue(s): {fails[0]}")[:90],
            "gap": None if ok else f"cover diverges from S2 pen: {'; '.join(fails[:3])}"}


def book_id_vol(book_id: str) -> str:
    """Best-effort volume number from a book_id (vol_03_… → 3; else the leading digits)."""
    m = re.search(r"vol[_-]?0*(\d+)", book_id, re.I) or re.match(r"0*(\d+)", book_id)
    return m.group(1) if m else "1"


def evaluate(book_id: str, extra: list[str]) -> dict:
    bdir = _book_dir(book_id)
    refs = _book_refs(book_id, extra)
    checks = [_check_boards(bdir), _check_obligations(refs), _check_fidelity(refs),
              _check_review_brief(bdir, book_id, extra), _check_artifact_package(bdir, book_id),
              _check_substance(bdir, book_id), _check_canonical_toolchain(bdir, book_id),
              _check_book_structure(bdir, book_id), _check_render_fidelity(bdir, book_id),
              _check_production_standards(bdir, book_id), _check_enforcement_claims(bdir, book_id),
              _check_forward_reference(bdir, book_id), _check_keyword_discipline(bdir, book_id),
              _check_cover_standard(bdir, book_id)]
    ready = all(c["pass"] for c in checks)
    return {
        "book_id": book_id, "review_ready": ready,
        "checks": checks,
        "gaps": [c["gap"] for c in checks if c.get("gap")],
        "meta": {"contract": "Review-Ready Rail R1 v1.0",
                 "spec": "artifacts/GB_ReviewReady_Rail_Spec_2026-06-10.md",
                 "book_dir": str(bdir) if bdir else None,
                 "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Review-Ready Contract checker (R1)")
    ap.add_argument("book_id")
    ap.add_argument("--match", nargs="*", default=[], help="extra book-reference tokens (e.g. B12 'Agentic Enterprise')")
    ap.add_argument("--json", action="store_true", help="print full JSON")
    args = ap.parse_args()
    result = evaluate(args.book_id, args.match)
    out_dir = REPO / "artifacts" / "review_ready"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{args.book_id}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2)); return 0 if result["review_ready"] else 1
    flag = "✅ REVIEW-READY" if result["review_ready"] else "⛔ NOT READY"
    print(f"{flag} — {args.book_id}")
    if result["review_ready"]:
        label = (args.match[0] if args.match else args.book_id)
        pid = mint_review_packet(args.book_id, f"{label} ({args.book_id})", args.match)
        if pid:
            print(f"  📖 review packet on the human gate: {pid} (appears in Awaiting-KM)")
    for c in result["checks"]:
        print(f"  {'✓' if c['pass'] else '✗'} {c['check']:20} {c['detail']}")
    if result["gaps"]:
        print("  gaps (each → a B32 obligation):")
        for g in result["gaps"]:
            print(f"    • {g}")
    return 0 if result["review_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
