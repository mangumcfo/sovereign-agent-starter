"""R22-3 source-citation provenance validator — extracted verbatim from ledger.py (audit 2026-06-16 #6).
A path-like source_ref MUST resolve (the file exists; an appended #"text" passage is present) or raise —
a citation is never written false. Path(__file__).parents[3] unchanged (same obligations/ dir)."""
from __future__ import annotations

from pathlib import Path


def _assert_source_ref_resolves(source_ref: str) -> None:
    """R22-3 provenance rule (GB): a path-like `source_ref` MUST resolve — the file exists, and if a
    `#"quoted text"` passage is appended, that text is present — else raise. A citation is never written
    false. Symbolic refs (no path separator + extension, e.g. 'B11:veto-chapter') are accepted as-is
    (not a file claim, so not falsifiable here)."""
    head, _, tail = source_ref.partition("#")
    path_part = head.strip()
    # Compound ref (audit 2026-06-13 W5 #6): GB feed refs are "<path> + <annotation> + …" where the
    # LEADING token is the file claim and the ` + …` tail is symbolic provenance (e.g. 'B51 delta',
    # 'THREAD[67]'). Validate only the leading file token; the annotations are not file claims, so a real
    # compound ref is never falsely rejected.
    path_part = path_part.split(" + ", 1)[0].strip()
    passage = tail.strip().strip('"') if tail else None
    last = path_part.rsplit("/", 1)[-1]
    if "/" not in path_part or "." not in last:
        return  # symbolic ref — not a file claim
    # Runs-anywhere (audit 2026-06-13): resolve against config-derived roots, not hardcoded operator
    # vault literals (a genuinely-resolvable passage failed on any other host). Falls back to cwd +
    # repo-root; config getters return None on a vault-less host (then only cwd/repo are tried).
    from .. import config  # noqa: PLC0415 — lazy to avoid import cycles
    roots = [Path.cwd(), Path(__file__).resolve().parents[3]]
    books = config.get_books_kdp_root()
    if books:
        roots += [Path(books), Path(books).parent]    # kdp root + the vault root above it
    plays = config.get_playbooks_dir()
    if plays:
        roots.append(Path(plays))
    resolved = next((r / path_part for r in roots if (r / path_part).is_file()), None)
    if resolved is None:
        raise ValueError(
            f"R22-3 provenance: source_ref '{path_part}' does not resolve to a file under known "
            f"roots — a citation is never written false."
        )
    if passage and passage not in resolved.read_text(encoding="utf-8", errors="ignore"):
        raise ValueError(
            f"R22-3 provenance: cited passage not present in '{path_part}' — the source must say it."
        )
