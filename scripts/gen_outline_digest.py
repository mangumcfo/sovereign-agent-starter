#!/usr/bin/env python3
"""Generate a human-readable chapter-outline digest from series_roadmap.yaml.

WHY: KM wants to SEE the planned chapter outlines without tracking raw YAML.
This emits a scannable drill-down view (public series -> volume -> chapters).
Single source of truth = series_roadmap.yaml (GB lane); this file is derived,
so it never drifts. The Atrium Series Pipeline card drill-down link points at
the per-volume anchors (book_id) in the generated SERIES_OUTLINES_DIGEST.md.

Run:  python3 scripts/gen_outline_digest.py
"""
import sys
import pathlib

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required:  pip install pyyaml")

ART = pathlib.Path(__file__).resolve().parent.parent / "artifacts"
SRC = ART / "series_roadmap.yaml"
OUT = ART / "SERIES_OUTLINES_DIGEST.md"

STAGE = {
    "published": "published",
    "sealed": "sealed",
    "handoff": "handoff",
    "outline_locked": "outline locked",
    "outline_partial": "outline partial",
    "concept": "concept",
    "stub": "STUB (not written yet)",
}


def mark(stage):
    return STAGE.get(stage, stage or "-")


def main():
    data = yaml.safe_load(SRC.read_text())
    series = data.get("series", [])
    out = [
        "# Series Outlines - Drill-Down Digest",
        "",
        "_Derived from `series_roadmap.yaml` (single source of truth). "
        "Regenerate with `python3 scripts/gen_outline_digest.py` - do not hand-edit._",
        "",
    ]
    counts = {"volumes": 0, "chapters": 0, "stubs": 0}
    for s in series:
        if s.get("visibility") == "private":
            continue
        out.append(f"## Series {s.get('series_number')} - {s.get('name','')}")
        out.append("")
        for t in s.get("titles", []):
            counts["volumes"] += 1
            out.append(f'<a id="{t.get("book_id","")}"></a>')
            out.append(f"### {t.get('title','')}  -  _{mark(t.get('stage'))}_")
            if t.get("one_line"):
                out.append(f"{t['one_line']}")
            out.append("")
            chapters = t.get("chapters")
            if chapters:
                for c in chapters:
                    counts["chapters"] += 1
                    if c.get("stage") == "stub":
                        counts["stubs"] += 1
                    line = f"- **Ch {c.get('n')}. {c.get('title','')}**  ({mark(c.get('stage'))})"
                    out.append(line)
                    if c.get("promise"):
                        out.append(f"    - {c['promise']}")
            else:
                out.append("- _(chapters not yet outlined)_")
            out.append("")
    out.append("---")
    out.append(
        f"_Public volumes: {counts['volumes']} · chapters outlined: "
        f"{counts['chapters']} · still stubbed: {counts['stubs']}._"
    )
    OUT.write_text("\n".join(out) + "\n")
    print(f"Wrote {OUT}")
    print(
        f"Public volumes: {counts['volumes']} | "
        f"chapters: {counts['chapters']} | stubs: {counts['stubs']}"
    )


if __name__ == "__main__":
    main()
