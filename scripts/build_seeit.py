#!/usr/bin/env python3
"""
build_seeit.py — generate the `seeit` operator-docs content from the SEALED S2 books (render, not recreate).

seeit is a DERIVED, non-technical training surface (KM + GB aligned 2026-06-10). Every topic pairs a plain-
English operator explanation with the REAL S2 passage it renders from (book↔code: sourced, cited, hashed).
Regenerable → when the books update, re-run and seeit auto-refreshes. Honest by construction: the source
passage ships next to the explanation so any operator can verify it traces to the sealed text.

    python3 scripts/build_seeit.py        # writes artifacts/seeit_content.json

∞Δ∞ Render the living books into operator clarity. Never recreate; always cite. ∞Δ∞
"""
from __future__ import annotations
import hashlib, json, re, time
from pathlib import Path

S2 = "/home/kmangum/work-repos/mangumcfo/breathline-books-vault/kdp/series_02_building_the_agentic_harness"
AGENTIC = "/home/kmangum/work-repos/mangumcfo/breathline-books-vault/kdp/agentic_playbooks"
# S1 B10-12 link to per-chapter seeit walkthroughs (/seeit/<id>-chN). Launch with the republish set.
WALKTHROUGH_BOOKS = [("b10", "10_scaling_enterprise", "Scaling AI Agents"),
                     ("b11", "11_ma_due_diligence", "AI Agents for M&A"),
                     ("b12", "12_agentic_enterprise", "The Agentic Enterprise")]


def _latest(vol_dir: str) -> Path | None:
    cands = sorted(Path(f"{S2}/{vol_dir}/v1.0").glob("manuscript_v*.md"))
    return cands[-1] if cands else None


# Front-matter markers (series blurbs / disclaimers / volume lists / "previously in series"). Paragraphs
# matching these are SKIPPED — they tripped the old loose-anchor extractor into citing boilerplate
# instead of the mechanic (GB fidelity FAIL 2026-06-10). The body is what renders the mechanic.
_FRONTMATTER = re.compile(
    r"about this series|^\s*\*\*disclaimer|this book is the|this volume'?s promise|"
    r"previously in series|reading time|the unique artifact in this volume|"
    r"^\s*[-*]\s*\*\*vol(ume)?\s|where series\s*\d|series\s*\d.*gave\s+(senior|builders|leaders)",
    re.I)


def _clean(p: str) -> str:
    clean = re.sub(r"\s+", " ", p).strip()
    if len(clean) > 720:
        cut = clean[:720]
        clean = cut[: cut.rfind(". ") + 1] if ". " in cut else cut + "…"
    return clean


def _extract(md_path: Path, anchors: list[str], require: list[str]) -> tuple[str, str, int]:
    """Best BODY paragraph for a topic. Skips front-matter, REQUIRES ≥1 load-bearing term (so we render
    the mechanic, never boilerplate), scores by required-term + anchor density and heading match. Returns
    (passage, heading, score). Honest by construction: no required term found in the body → ('', head, 0)
    rather than a wrong citation. This is the fix for the 2026-06-10 fidelity FAIL."""
    if not md_path or not md_path.is_file():
        return "", "", 0
    text = md_path.read_text(encoding="utf-8")
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    last_head, best = "", ("", "", 0)
    for p in paras:
        if p.lstrip().startswith("#"):
            last_head = re.sub(r"^#+\s*", "", p.splitlines()[0]).strip()
            continue
        if _FRONTMATTER.search(p):
            continue
        req_hits = sum(1 for r in require if re.search(r, p, re.I))
        if not req_hits:  # render-not-recreate: the mechanic's own term must be present
            continue
        anc_hits = sum(1 for a in anchors if re.search(a, p, re.I))
        head_bonus = 5 if any(re.search(a, last_head, re.I) for a in (anchors + require)) else 0
        score = req_hits * 10 + anc_hits + head_bonus
        if score > best[2]:
            best = (_clean(p), last_head, score)
    return best


# Topic config: each operator explanation RENDERS the sourced passage (faithful, plain-English, non-technical).
TOPICS = [
    # Relabeled from "B32 Obligation Packets" (2026-06-10): S2 contains no "B32"/"double-entry" text — that
    # explanation was authored, not rendered (recreate-not-render violation). S2 DOES teach receipts / the
    # verifiable audit chain richly. We render THAT — the faithful concept the books actually carry.
    dict(id="receipts", title="Receipts — the Verifiable Audit Chain", icon="🧾",
         vol="vol_03_governed_dev_loop_and_self_building_harness", vol_label="S2 Vol 3 — The Governed Dev Loop",
         require=[r"receipt"],
         anchors=[r"audit.?chain", r"every act produces", r"chain extension", r"witness", r"verifiable"],
         operator="Every action the agents take produces a receipt — a real, verifiable audit-chain entry. Each receipt extends the chain, and every extension renews your presence in the loop: the system operates WITH your witness, not after a one-time approval. You can always prove what happened, and the book's own claims are checkable against the real receipts."),
    dict(id="k1_k4", title="K1–K4 Constitutional Invariants", icon="⚖",
         vol="vol_02_the_primacy_cockpit", vol_label="S2 Vol 2 — The Primacy Cockpit",
         require=[r"human primacy", r"\bK1\b", r"invariant"],
         anchors=[r"breath-gate", r"constitutional surface", r"approve or deny", r"proposal becomes action"],
         operator="Four rules the system ALWAYS enforces, no exceptions. The first and most important — K1, human primacy — means you stay in command: agents propose, you dispose. Nothing material becomes action without your breath at the gate. The others guarantee receipts, fail-closed safety, and honest errors."),
    dict(id="merkle_anchors", title="Merkle Anchors (Receipted Memory)", icon="⛓",
         vol="vol_01_sovereign_inference_and_memory", vol_label="S2 Vol 1 — Sovereign Inference & Memory",
         require=[r"merkle"],
         anchors=[r"hash", r"audit-chain", r"tamper", r"public anchor", r"SHA-256", r"reproducib"],
         operator="Everything the system does is written to a tamper-evident chain — each entry locked to the one before it by a cryptographic hash (the Merkle layer). Like a sealed ledger: if anything were altered, the chain breaks visibly, verifiable against a public anchor. It's how you can PROVE what happened and when, years later."),
    dict(id="governed_loop", title="The Governed Loop", icon="🔁",
         vol="vol_03_governed_dev_loop_and_self_building_harness", vol_label="S2 Vol 3 — The Governed Dev Loop",
         require=[r"proposal mechanics", r"propose", r"breath-gate"],
         anchors=[r"self-modification", r"cross-role veto", r"gate every", r"structural"],
         operator="How a change is governed: agents propose, and proposal mechanics gate every self-modification through a structural breath-gate review — with cross-role veto authority — before anything becomes action. The agents do the work in the background and bring you a single decision; nothing lands without your gate."),
    dict(id="atrium_surfaces", title="Atrium Surfaces (The Cockpit)", icon="🖥",
         vol="vol_02_the_primacy_cockpit", vol_label="S2 Vol 2 — The Primacy Cockpit",
         require=[r"the Atrium", r"cockpit"],
         anchors=[r"every screen", r"human primacy is visible", r"Stillpoint", r"breath-gate"],
         operator="The Atrium is your cockpit — one place to see everything: what the agents are doing, what the constitution is enforcing, what's waiting for your breath, and what's already sealed. You never leave it; every screen makes human primacy visible, so you stay sovereign without touching code."),
]


def _walkthroughs(slug: str, book_dir: str) -> list[dict]:
    """Extract the per-chapter seeit walkthrough rows the S1 book itself links to (/seeit/<slug>-chN).
    Sourced straight from the manuscript table → the operator pages the published book points readers to."""
    cands = sorted(Path(f"{AGENTIC}/{book_dir}/v1.0").glob("manuscript_v*.md"))
    if not cands:
        return []
    text = cands[-1].read_text(encoding="utf-8")
    rows = []
    # markdown rows: | N | <what> | [/seeit/<slug>-chN](...) | `<demo cmd>` |
    for m in re.finditer(r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*\[?(/seeit/" + re.escape(slug) + r"-ch\d+)\]?[^|]*\|\s*`?([^|`\n]+?)`?\s*\|", text):
        rows.append({"chapter": int(m.group(1)), "title": m.group(2).strip(),
                     "seeit_path": m.group(3).strip(), "demo": m.group(4).strip()})
    # dedupe by path, keep order
    seen, out = set(), []
    for r in rows:
        if r["seeit_path"] in seen:
            continue
        seen.add(r["seeit_path"]); out.append(r)
    return out


def build() -> dict:
    topics = []
    for t in TOPICS:
        mp = _latest(t["vol"])
        passage, heading, score = _extract(mp, t["anchors"], t.get("require", []))
        topics.append({
            "id": t["id"], "title": t["title"], "icon": t["icon"],
            "operator_explanation": t["operator"],
            "source": {
                "book": t["vol_label"],
                "manuscript": str(mp.relative_to(S2)) if mp else None,
                "section": heading,
                "passage": passage,
                "passage_sha": hashlib.sha256(passage.encode()).hexdigest()[:16] if passage else None,
                "match_score": score,
                "required_terms": t.get("require", []),
                "found": bool(passage),
            },
        })
    walkthroughs = []
    for slug, book_dir, title in WALKTHROUGH_BOOKS:
        rows = _walkthroughs(slug, book_dir)
        walkthroughs.append({"book": slug.upper(), "book_id": book_dir, "title": title,
                             "n": len(rows), "chapters": rows})
    body = {"topics": topics, "walkthroughs": walkthroughs}
    return {
        "_meta": {
            "surface": "seeit", "kind": "derived-operator-docs (render-not-recreate)",
            "source_series": "S2 — Building the Agentic Harness (core mechanics) + S1 B10-12 (chapter walkthroughs)",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "content_hash": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16],
            "n_topics": len(topics), "n_sourced": sum(1 for x in topics if x["source"]["found"]),
            "n_walkthrough_chapters": sum(w["n"] for w in walkthroughs),
            "note": "Mechanics RENDER cited S2 passages; walkthroughs are the /seeit/<book>-chN pages S1 B10-12 link to. Book↔code: sourced + hashed; re-run to auto-refresh.",
        },
        **body,
    }


def main():
    reg = build()
    out = Path(__file__).resolve().parents[1] / "artifacts" / "seeit_content.json"
    out.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    m = reg["_meta"]
    print(f"wrote {out.name} — {m['n_topics']} topics, {m['n_sourced']} sourced from S2, hash {m['content_hash']}")
    for t in reg["topics"]:
        print(f"  {'✓' if t['source']['found'] else '✗'} {t['id']:16} ← {t['source']['section'][:46]!r}")


if __name__ == "__main__":
    main()
