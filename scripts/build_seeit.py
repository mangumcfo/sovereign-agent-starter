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


def _extract(md_path: Path, anchors: list[str]) -> tuple[str, str]:
    """First paragraph matching an anchor (in order). Returns (passage, section_heading_context)."""
    if not md_path or not md_path.is_file():
        return "", ""
    text = md_path.read_text(encoding="utf-8")
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    last_head = ""
    for p in paras:
        if p.lstrip().startswith("#"):
            last_head = re.sub(r"^#+\s*", "", p.splitlines()[0]).strip()
            continue
        for a in anchors:
            if re.search(a, p, re.I):
                # trim a long paragraph to a clean ~700-char excerpt at a sentence end
                clean = re.sub(r"\s+", " ", p).strip()
                if len(clean) > 720:
                    cut = clean[:720]
                    clean = cut[: cut.rfind(". ") + 1] if ". " in cut else cut + "…"
                return clean, last_head
    return "", last_head


# Topic config: each operator explanation RENDERS the sourced passage (faithful, plain-English, non-technical).
TOPICS = [
    dict(id="b32_packets", title="B32 Obligation Packets", icon="🧾",
         vol="vol_03_governed_dev_loop_and_self_building_harness", vol_label="S2 Vol 3 — The Governed Dev Loop",
         anchors=[r"double-entry", r"obligation", r"debit", r"B32", r"JSON.?receipt", r"audit.?chain", r"structural commitment.*receipt", r"verifiable governance receipt"],
         operator="Every commitment is a receipt with two sides: opening it is a DRAFT (nothing happens until you approve), closing it requires EVIDENCE. So every piece of work is tracked, provable, and reversible — you can always see what's open, what's done, and the proof behind it."),
    dict(id="k1_k4", title="K1–K4 Constitutional Invariants", icon="⚖",
         vol="vol_02_the_primacy_cockpit", vol_label="S2 Vol 2 — The Primacy Cockpit",
         anchors=[r"human primacy", r"\bK1\b", r"non-negotiable", r"invariant"],
         operator="Four rules the system ALWAYS enforces, no exceptions. The first and most important — K1, human primacy — means you stay in command: agents propose, you dispose. Nothing material happens without your breath. The others guarantee receipts, fail-closed safety, and honest errors."),
    dict(id="merkle_anchors", title="Merkle Anchors (Receipted Memory)", icon="⛓",
         vol="vol_01_sovereign_inference_and_memory", vol_label="S2 Vol 1 — Sovereign Inference & Memory",
         anchors=[r"merkle", r"hash-chain", r"tamper", r"receipt", r"cylinder"],
         operator="Everything the system does is written to a tamper-evident chain — each entry locked to the one before it by a cryptographic hash. Like a sealed ledger: if anything were altered, the chain breaks visibly. It's how you can PROVE what happened and when, years later."),
    dict(id="governed_loop", title="The Governed Loop", icon="🔁",
         vol="vol_03_governed_dev_loop_and_self_building_harness", vol_label="S2 Vol 3 — The Governed Dev Loop",
         anchors=[r"capture.{0,40}packet", r"propose.{0,30}approve", r"review.{0,30}accept", r"one (human )?gate", r"governed"],
         operator="How a thought becomes a sealed change: capture → packet → validate → ACCEPT (your one gate) → apply → seal. The agents do the work in the background and bring you a single decision; nothing lands without your Accept. One human gate, everything else automated."),
    dict(id="atrium_surfaces", title="Atrium Surfaces (The Cockpit)", icon="🖥",
         vol="vol_02_the_primacy_cockpit", vol_label="S2 Vol 2 — The Primacy Cockpit",
         anchors=[r"the Atrium", r"the cockpit", r"every screen", r"human primacy is visible"],
         operator="The Atrium is your cockpit — one place to see everything: what the agents are doing, what the constitution is enforcing, what's waiting for your breath, and what's already sealed. You never leave it; every part of the system surfaces here so you stay sovereign without touching code."),
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
        passage, heading = _extract(mp, t["anchors"])
        topics.append({
            "id": t["id"], "title": t["title"], "icon": t["icon"],
            "operator_explanation": t["operator"],
            "source": {
                "book": t["vol_label"],
                "manuscript": str(mp.relative_to(S2)) if mp else None,
                "section": heading,
                "passage": passage,
                "passage_sha": hashlib.sha256(passage.encode()).hexdigest()[:16] if passage else None,
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
