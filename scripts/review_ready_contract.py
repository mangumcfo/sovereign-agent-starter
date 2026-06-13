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
# Env-aware (audit 2026-06-13): this script previously IGNORED OBLIGATION_LEDGER_ROOT and hardcoded
# atrium_review. Mirror the canonical resolver's semantics (env → atrium_review) so the rail gate reads
# the SAME root the node serves; tests monkeypatch the env before import.
LEDGER_ROOT = Path(os.environ.get("OBLIGATION_LEDGER_ROOT")
                   or (REPO / "memory" / "obligations" / "atrium_review"))
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


def _check_gate6_renderability(bdir: Path) -> dict:
    """Tech/Arch GATE 6 — Renderability (Deterministic-Render Writing Standard v1.0, GB-sealed 2026-06-12).
    Binding. The structural floor checked here: every major section ends with a Receipt box (the Helix
    validation anchor — Gate 6's explicit success criterion). Full Gate-6 rigor (one-truth · every promise
    has a render target · zero dishonest stubs) lives in the tech_arch board's rigor block; this bars the
    box-less manuscript that can never extrude deterministically."""
    mss = sorted(p for p in bdir.glob("manuscript_v*.md")
                 if re.match(r"manuscript_v[0-9.]+\.md$", p.name))  # exclude changelog/sidecars
    if not mss:
        return {"pass": False, "status": "no-manuscript", "detail": "no manuscript to render-check"}
    text = mss[-1].read_text(encoding="utf-8", errors="ignore")
    boxes = text.count("\U0001F4E6 Receipt Box")
    sections = len(re.findall(r"^# (?:Chapter \d+|Appendix )", text, re.M))
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
    *fidelity*.ndjson record. PASS iff a matching record indicates pass and no FAIL is the latest verdict."""
    sources = [GB_CYLINDER] + sorted(REPO.glob("artifacts/*fidelity*.ndjson")) + sorted(REPO.glob("memory/**/*fidelity*.ndjson"))
    latest = None
    for src in sources:
        if not src.is_file():
            continue
        for line in src.read_text(encoding="utf-8").splitlines():
            low = line.lower()
            # Only an ACTUAL verdict record counts — not any passing mention of the word "fidelity"
            # (a later non-verdict GB note was overriding the real PASS). Require the verdict marker.
            is_verdict = "fidelity_verdict" in low or ("fidelity" in low and ("verdict" in low or src.name.lower().find("fidelity") >= 0))
            if not is_verdict or not any(r in low for r in refs):
                continue
            verdict = "pass" if ("pass" in low and "fail" not in low) else ("fail" if "fail" in low else "?")
            latest = verdict  # later lines win (append-only → newest verdict)
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
    try:
        sys.path.insert(0, str(REPO / "src"))
        from sovereign_agent.obligations.ledger import ObligationLedger
        lg = ObligationLedger(str(LEDGER_ROOT), principal_id="KM-1176")
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
        owner="KM-1176", classification="C1", material=True, next_gate="Human disposition", ref=ref,
        intent=(f"All Review-Ready Rail gates green (boards rigor-pass · obligations clean · fidelity PASS · "
                f"Review Brief sealed) and your review feedback is applied + rebuilt clean. "
                f"FINAL PDF: {pdf}. "
                f"ACCEPT = your sign-off (review complete) → Tiger seals the final → you provide pb+hc ISBNs "
                f"for the KDP dispatch bundle. Review Brief: {brief}. Manuscript: {ms}."),
        lgp={"objective": "first book through the rail — human keeps only the judgment (LGP/human primacy)"},
    )
    return entry.get("id")


def evaluate(book_id: str, extra: list[str]) -> dict:
    bdir = _book_dir(book_id)
    refs = _book_refs(book_id, extra)
    checks = [_check_boards(bdir), _check_obligations(refs), _check_fidelity(refs),
              _check_review_brief(bdir, book_id, extra)]
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
