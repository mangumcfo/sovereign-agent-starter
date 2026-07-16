#!/usr/bin/env python3
"""editions.py — P4a: the edition law's last mile (contract: CONTRACTS_P2_P4.md).

Computed changelog, never transcribed: diff two pipeline snapshots -> which titles
advanced a stage, which sealed, which were newly added, which links went live.
Edition stamp = date + catalog-state fingerprint (the snapshot content_hash).
Trigger: when the catalog state has moved past a book's recorded edition stamp,
QUEUE A PROPOSAL at the human wave gate — nothing rebuilds or publishes itself; the
rebuild happens only when a human opens it (press build, new-edition mode).

Usage:
  editions.py changelog <old_snapshot.yaml> <new_snapshot.yaml> [--out FILE]
  editions.py check-trigger <book-id>       # propose if the catalog moved
  editions.py status                        # edition state + pending proposals
State (PRESS_HOME):
  editions_state.json          {book: {edition, catalog_state_hash, snapshot}}
  re_edition_proposals.json    append-only; entries await the human word
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import yaml

REPO = Path(os.environ.get("PRESS_DATA_ROOT") or Path.cwd())
PRESS = Path(os.environ.get("PRESS_HOME") or Path.cwd())
SNAPS = REPO / "artifacts" / "pipeline_snapshots"
STATE_P = PRESS / "editions_state.json"
PROPS_P = PRESS / "re_edition_proposals.json"


def _load_snap(p):
    return yaml.safe_load(Path(p).read_text(encoding="utf-8"))


def _title_map(snap):
    out = {}
    for s in snap.get("series", []):
        key = s.get("number") if s.get("number") is not None else s.get("slug")
        for t in s.get("titles", []) or []:
            out[(key, t.get("title"))] = t
    return out


SEAL_WORDS = ("sealed", "awaiting_seal", "breath_seal")


def compute_changelog(old_p, new_p):
    old, new = _load_snap(old_p), _load_snap(new_p)
    om, nm = _title_map(old), _title_map(new)
    advanced, sealed, added, links_live = [], [], [], []
    for k, nt in nm.items():
        ot = om.get(k)
        label = f"S{k[0]} · {k[1]}"
        if ot is None:
            added.append(label)
            continue
        os_, ns_ = (ot.get("stage") or ""), (nt.get("stage") or "")
        if os_ != ns_:
            advanced.append(f"{label}: {os_ or '—'} → {ns_ or '—'}")
            if any(w in ns_.lower() for w in SEAL_WORDS) and \
               not any(w in os_.lower() for w in SEAL_WORDS):
                sealed.append(label)
        og = json.dumps(ot.get("next_gate") or "")
        ng = json.dumps(nt.get("next_gate") or "")
        if "live" in ng.lower() and og != ng:
            links_live.append(f"{label}: {nt.get('next_gate')}")
    removed = [f"S{k[0]} · {k[1]}" for k in om if k not in nm]
    return {
        "computed_from": {"old": {"file": Path(old_p).name, "hash": old.get("content_hash")},
                          "new": {"file": Path(new_p).name, "hash": new.get("content_hash")}},
        "advanced": sorted(advanced), "sealed": sorted(sealed),
        "added": sorted(added), "links_live": sorted(links_live),
        "removed_or_renamed": sorted(removed),
        "coverage": {"old": old.get("coverage"), "new": new.get("coverage")},
        "law": "computed from the sealed record — no line of this was transcribed by hand",
    }


def render_changelog_md(cl, book):
    L = [f"# Changelog draft — {book} (computed, never transcribed)",
         "",
         f"Catalog state: `{cl['computed_from']['old']['hash'][:16]}` → "
         f"`{cl['computed_from']['new']['hash'][:16]}` "
         f"({cl['computed_from']['old']['file']} → {cl['computed_from']['new']['file']})", ""]
    for section, title in (("added", "Newly added to the catalog"),
                           ("advanced", "Titles that advanced a stage"),
                           ("sealed", "Titles sealed"),
                           ("links_live", "Links gone live"),
                           ("removed_or_renamed", "Removed or renamed (review)")):
        items = cl[section]
        L.append(f"## {title} ({len(items)})")
        L += [f"- {i}" for i in items] or ["- none"]
        L.append("")
    L.append(f"*{cl['law']}.*")
    return "\n".join(L)


def _state():
    return json.loads(STATE_P.read_text()) if STATE_P.exists() else {}


def _proposals():
    return json.loads(PROPS_P.read_text()) if PROPS_P.exists() else []


def _latest_snapshot():
    snaps = sorted(SNAPS.glob("series_pipeline_*.yaml"))
    if not snaps:
        sys.exit("EDITIONS FAIL: no pipeline snapshots exist")
    return snaps[-1]


def cmd_check_trigger(book):
    st = _state()
    if book not in st:
        sys.exit(f"EDITIONS FAIL: {book} has no edition state — seed editions_state.json "
                 "(default-deny: unknown books trigger nothing)")
    latest = _latest_snapshot()
    cur = _load_snap(latest)
    cur_hash = cur.get("content_hash")
    rec = st[book]
    if rec.get("catalog_state_hash") == cur_hash:
        print(f"[quiet] {book} edition {rec['edition']} matches catalog state {cur_hash[:16]} "
              "— no proposal")
        return 0
    pending = [p for p in _proposals()
               if p["book"] == book and p["status"] == "awaiting_operator"
               and p["target_catalog_hash"] == cur_hash]
    if pending:
        print(f"[held] proposal already waiting at the human gate ({pending[0]['id']}) — idempotent")
        return 0
    # Compute the changelog draft for the proposal
    base_snap = rec.get("snapshot")
    note = None
    if not base_snap or not (SNAPS / base_snap).exists():
        candidates = [p for p in sorted(SNAPS.glob("series_pipeline_*.yaml")) if p != latest]
        base = candidates[-1] if candidates else latest
        note = (f"edition {rec['edition']} predates the snapshot-per-edition law — baseline "
                f"{base.name} is the CLOSEST AVAILABLE, not the exact edition state; the "
                "changelog may include earlier movement. Every edition built by the Press "
                "records its exact snapshot going forward.")
    else:
        base = SNAPS / base_snap
    cl = compute_changelog(base, latest)
    draft_dir = PRESS / "changelogs"
    draft_dir.mkdir(exist_ok=True)
    draft = draft_dir / f"{book}_edition{rec['edition'] + 1}_draft.md"
    md = render_changelog_md(cl, book)
    if note:
        md = md.replace("\n\n", f"\n\n> **Baseline honesty note:** {note}\n\n", 1)
    draft.write_text(md, encoding="utf-8")
    prop = {"id": f"prop_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}_{book}",
            "book": book, "current_edition": rec["edition"],
            "proposed_edition": rec["edition"] + 1,
            "reason": f"catalog state moved: {str(rec.get('catalog_state_hash'))[:16]} → {cur_hash[:16]}",
            "target_catalog_hash": cur_hash,
            "changelog_draft": str(draft.relative_to(REPO)),
            "proposed_utc": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
            "status": "awaiting_operator",
            "note": "nothing rebuilds itself — a human opens this via press build (new-edition)"}
    props = _proposals()
    props.append(prop)
    PROPS_P.write_text(json.dumps(props, indent=2))
    prop_sha = hashlib.sha256(json.dumps(prop, sort_keys=True).encode()).hexdigest()[:16]
    print(f"[PROPOSED] {book} Edition {prop['proposed_edition']} queued at the human gate "
          f"({prop['id']}, sha {prop_sha})")
    print(f"  changelog draft: {prop['changelog_draft']}")
    return 3  # awaiting the human word


def cmd_status():
    st, props = _state(), _proposals()
    print("EDITION STATE")
    for b, r in sorted(st.items()):
        print(f"  {b}: edition {r['edition']} @ catalog {str(r.get('catalog_state_hash'))[:16]} "
              f"(snapshot: {r.get('snapshot') or 'MISSING — pre-law edition'})")
    waiting = [p for p in props if p["status"] == "awaiting_operator"]
    print(f"PROPOSALS awaiting the human word: {len(waiting)}")
    for p in waiting:
        print(f"  {p['id']}: {p['book']} → Edition {p['proposed_edition']} ({p['reason']})")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "changelog" and len(args) >= 2:
        out = None
        if "--out" in args:
            i = args.index("--out")
            out = args[i + 1]
            del args[i:i + 2]
        if len(args) != 2:
            sys.exit(f"EDITIONS FAIL: unrecognized argument(s): {args[2:]}")
        cl = compute_changelog(args[0], args[1])
        md = render_changelog_md(cl, "(ad-hoc)")
        if out:
            Path(out).write_text(md, encoding="utf-8")
            print(f"changelog -> {out}")
        else:
            print(md)
        return 0
    if cmd == "check-trigger" and len(args) == 1:
        return cmd_check_trigger(args[0])
    if cmd == "status" and not args:
        return cmd_status()
    sys.exit(f"EDITIONS FAIL: bad usage (see docstring) — argv={sys.argv[1:]}")


if __name__ == "__main__":
    sys.exit(main())
