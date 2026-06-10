#!/usr/bin/env python3
"""
build_book_code_tree.py — deterministic deriver for the Book↔Code Tree surface.

Implements GB's Book↔Code Tree Derivation Spec v1.0 (artifacts/GB_BookCode_Tree_Derivation_Spec_2026-06-10.md),
Tiger's build contract (§5). RENDER, don't recreate: every node + edge derives from an existing source of
truth — nothing hand-drawn here.

  Book tree   ← series_roadmap.yaml (GB sole-write) + extracted_chapter_outlines*.json
  Code tree   ← git ls-tree -r HEAD src/  (+ module docstring first line for purpose)
  Edges       ← artifacts/book_code_map.yaml  (GB SOLE-WRITE — this script READS it, never writes it)
  Findings    ← orphan code (no edge) + unrendered chapters (no edge, not marked n/a: narrative)

Output: artifacts/book_code_tree.json — {book_tree, code_tree, edges[], findings[], meta{...,hashes,ts}}.
Idempotent + content-hashed (like pipeline_snapshot.py). Drop-off guard on derived-edge count: a DECREASE
vs the prior build exits 2 (loud), same semantics as the pipeline snapshot guard.

  python3 scripts/build_book_code_tree.py            # write the tree; exit 0 ok / 2 drop-off / 1 error

∞Δ∞ The books are the breath, the code is the form; this deriver lets the witness see both at once. ∞Δ∞
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "artifacts" / "book_code_tree.json"
MAP = REPO / "artifacts" / "book_code_map.yaml"
ROADMAP = Path(os.environ.get("SERIES_ROADMAP") or REPO / "artifacts" / "series_roadmap.yaml")


def _yaml():
    import yaml  # local import keeps the deriver yaml-optional at import time
    return yaml


def _chapter_index() -> dict:
    """Newest extracted_chapter_outlines*.json → books-by-id (mirrors series.py _chapter_index)."""
    cands = sorted(REPO.glob("artifacts/extracted_chapter_outlines*.json"), reverse=True)
    for p in cands:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return data.get("books", {}) if isinstance(data, dict) else {}
        except (ValueError, OSError):
            continue
    return {}


def _book_tree(chapter_index: dict) -> tuple[list, list, dict]:
    """Series → titles → chapters from the roadmap (chapters merged from the index, Path B).
    Returns (tree, chapter_node_ids, book_series) — chapter ids are '<book_id>#chN';
    book_series maps book_id → '<series_slug> <series_name>' (lowercased, for silence-matching)."""
    yaml = _yaml()
    text = ROADMAP.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    tree, chapter_ids, book_series = [], [], {}
    for s in data.get("series") or []:
        if not isinstance(s, dict):
            continue
        titles = s.get("titles") or s.get("volumes") or []
        sig = f"{s.get('slug', '')} {s.get('name', '')}".lower()
        snode = {"slug": s.get("slug", ""), "name": s.get("name", ""),
                 "series_number": s.get("series_number"), "visibility": s.get("visibility") or "public",
                 "titles": []}
        for t in titles:
            if not isinstance(t, dict):
                continue
            bid = t.get("book_id", "")
            book_series[bid] = sig
            chs = t.get("chapters") or (chapter_index.get(bid) or {}).get("chapters") or []
            ch_nodes = []
            for c in chs:
                n = c.get("n") if isinstance(c, dict) else None
                cid = f"{bid}#ch{n}"
                chapter_ids.append(cid)
                ch_nodes.append({"id": cid, "n": n,
                                 "title": (c.get("title") if isinstance(c, dict) else str(c)) or ""})
            snode["titles"].append({"book_id": bid, "title": t.get("title", ""),
                                    "publishing_state": t.get("publishing_state"),
                                    "chapter_count": len(ch_nodes), "chapters": ch_nodes})
        tree.append(snode)
    return tree, chapter_ids, book_series


def _docstring_purpose(path: Path) -> str:
    """First non-empty line of the module docstring (best-effort, cheap)."""
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:2000]
    except OSError:
        return ""
    m = re.search(r'"""(.*?)"""', head, re.S) or re.search(r"'''(.*?)'''", head, re.S)
    if not m:
        return ""
    for line in m.group(1).splitlines():
        if line.strip():
            return line.strip()[:160]
    return ""


def _code_tree() -> tuple[list, list]:
    """git ls-tree -r HEAD src/ → module nodes (.py). Returns (nodes, paths)."""
    try:
        out = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "-l", "HEAD", "src/"],
                             capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [], []
    nodes, paths = [], []
    for line in out.splitlines():
        # <mode> blob <sha> <size>\t<path>
        m = re.match(r"^\S+\s+blob\s+(\S+)\s+(\S+)\t(.+)$", line)
        if not m:
            continue
        path = m.group(3)
        if not path.endswith(".py") or path.endswith("__init__.py"):
            continue
        size = int(m.group(2)) if m.group(2).isdigit() else 0
        nodes.append({"path": path, "size": size, "purpose": _docstring_purpose(REPO / path)})
        paths.append(path)
    return nodes, paths


def _load_edges() -> tuple[list, list]:
    """GB's curated map (READ-ONLY, sole-write). Returns (edges, intentional_unrendered-tokens).
    intentional_unrendered silences series with no code form (spec §3 R4) — loudly, in the map."""
    if not MAP.is_file():
        return [], []
    try:
        data = _yaml().safe_load(MAP.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return [], []
    edges = [e for e in (data.get("edges") or []) if isinstance(e, dict)]
    tokens = []
    for x in (data.get("intentional_unrendered") or []):
        bk = x.get("book") if isinstance(x, dict) else x
        if bk:
            tokens.append(str(bk).replace("_", " ").lower())
    return edges, tokens


def _is_edged_code(path: str, edges: list) -> bool:
    """A module is edged if a derived/inspired edge names it — exact file, or a directory edge (trailing /)."""
    for e in edges:
        if e.get("class") not in ("derived", "inspired"):
            continue
        c = e.get("code") or ""
        if c.endswith("/"):
            if path.startswith(c):
                return True
        elif path == c:
            return True
    return False


def _findings(code_paths: list, chapter_ids: list, edges: list, tokens: list, book_series: dict) -> dict:
    """Orphan code (no derived/inspired edge) + unrendered chapters (no edge); chapters in an
    intentional_unrendered series are silenced loudly (counted separately, never hidden)."""
    edged_book = {e.get("book") for e in edges}

    def _ch_edged(cid: str) -> bool:
        return any(cid == b or (b and (b in cid or cid in b)) for b in edged_book)

    def _silenced(cid: str) -> bool:
        sig = book_series.get(cid.split("#", 1)[0], "")
        return any(tok in sig for tok in tokens)

    orphans = sorted(p for p in code_paths if not _is_edged_code(p, edges))
    unrendered, silenced = [], []
    for c in chapter_ids:
        if _ch_edged(c):
            continue
        (silenced if _silenced(c) else unrendered).append(c)
    return {"orphan_code": orphans, "unrendered_chapters": sorted(unrendered),
            "intentional_unrendered": sorted(silenced),
            "orphan_count": len(orphans), "unrendered_count": len(unrendered),
            "intentional_unrendered_count": len(silenced)}


def _content_hash(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]


def _prior_derived_count() -> int | None:
    if not OUT.is_file():
        return None
    try:
        return json.loads(OUT.read_text(encoding="utf-8")).get("meta", {}).get("derived_edge_count")
    except (ValueError, OSError):
        return None


def build() -> dict:
    chapter_index = _chapter_index()
    book_tree, chapter_ids, book_series = _book_tree(chapter_index)
    code_nodes, code_paths = _code_tree()
    edges, tokens = _load_edges()
    findings = _findings(code_paths, chapter_ids, edges, tokens, book_series)
    derived = sum(1 for e in edges if e.get("class") == "derived")
    body = {"book_tree": book_tree, "code_tree": code_nodes, "edges": edges, "findings": findings}
    return {
        **body,
        "meta": {
            "surface": "book_code_tree",
            "kind": "derived-audit (render-not-recreate; sibling-of seeit)",
            "spec": "artifacts/GB_BookCode_Tree_Derivation_Spec_2026-06-10.md",
            "generated_from": [str(ROADMAP.name), "extracted_chapter_outlines*.json",
                               "git ls-tree src/", (MAP.name if MAP.is_file() else f"{MAP.name} (ABSENT — GB sole-write pending)")],
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "n_series": len(book_tree), "n_chapters": len(chapter_ids), "n_modules": len(code_nodes),
            "edge_count": len(edges), "derived_edge_count": derived,
            "orphan_count": findings["orphan_count"], "unrendered_count": findings["unrendered_count"],
            "intentional_unrendered_count": findings["intentional_unrendered_count"],
            "map_present": MAP.is_file(),
            "content_hash": _content_hash(body),
            "note": "Edges READ from book_code_map.yaml (GB sole-write). Absent map → audit shell "
                    "(all code orphan / all chapters unrendered) — findings mode working, not an error.",
        },
    }


def main() -> int:
    prior = _prior_derived_count()
    tree = build()
    derived = tree["meta"]["derived_edge_count"]
    OUT.write_text(json.dumps(tree, indent=2, ensure_ascii=False), encoding="utf-8")
    m = tree["meta"]
    print(f"wrote {OUT.name} — {m['n_series']} series, {m['n_chapters']} chapters, {m['n_modules']} modules, "
          f"{m['edge_count']} edges ({derived} derived), {m['orphan_count']} orphan / {m['unrendered_count']} unrendered, "
          f"hash {m['content_hash']}")
    if not m["map_present"]:
        print("  ⓘ book_code_map.yaml absent (GB sole-write) → audit shell. Run extract_r1_candidates.py to seed it.")
    if prior is not None and derived < prior:
        print(f"  ⚠ DROP-OFF GUARD: derived edges {prior} → {derived} (DECREASED). Investigate before sealing.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
