"""publish.py — the docs projection. A projection holds no state and decides nothing.

Rules encoded here (operator rulings, 2026-07-19):

- **Explicit trigger.** Publishing never happens as a side effect of a build. Someone runs
  `press publish <volume>`. A projection that publishes itself is one bad build away from an
  unwanted public change.
- **Public surface carries SEALED only.** Provisional and designed-toward material stays on
  the internal surface. `--surface public` refuses anything without a verifying seal receipt.
- **The grade travels with the content.** Every card states what runs today versus what is
  designed-toward. A spec that loses its grade in projection is a spec that lies politely.
- **Seal status is read from the Press, never asserted by the site.** The card prints the
  receipt id it read; the site displays what the Press said.
- **The site cannot seal.** For an unsealed volume the card renders the exact command for the
  operator to run through their own authenticated channel. Rendering a command is not sealing.
"""
from __future__ import annotations

import os

from . import seal as sealmod


def _grade_line(vol, seal_rec=None):
    """One honest line per card.

    A VERIFIED SEAL RECEIPT OUTRANKS THE MANIFEST STAGE. The stage is the plan; the
    receipt is what happened. A card that printed "Provisional — not sealed" beside a
    valid receipt would be contradicting itself on the one fact that matters most.
    Without a receipt, the stage speaks and the card says designed·building plainly.
    """
    if seal_rec:
        return "Sealed", ("runs today: sealed by receipt, artifact reproduces "
                          "byte-for-byte from frozen sources")
    stage = (vol.get("stage") or "unknown").strip()
    if stage in ("published", "sealed-publication-ready", "sealed-awaiting-author"):
        return ("Built · Awaiting Seal",
                "designed · building: built to a frozen artifact; no seal receipt on file")
    if stage in ("built-in-review", "pre-order"):
        return "Provisional", "designed · building: built and under review; not sealed"
    return "Designed · Building", "designed-toward: not yet built to a frozen artifact"


def render_card(vid, vol, seal_rec, surface):
    """Concise by ruling: a screen per volume, no prose dumps, no code."""
    chip, grade = _grade_line(vol, seal_rec)
    lines = [f"# {vol.get('title', vid)}", "",
             f"**Status:** {chip}  ", f"**Grade:** {grade}", ""]
    if vol.get("series"):
        lines.append(f"- **Series:** {vol['series']}")
    if vol.get("freeze_sha"):
        lines.append(f"- **Frozen artifact:** `{vol['freeze_sha'][:16]}`")
    if vol.get("depends_on"):
        lines.append(f"- **Depends on:** {', '.join(vol['depends_on'])}")
    gates = vol.get("gates") or []
    if gates:
        lines.append(f"- **Gate chain:** {len(gates)} gate(s) enforced at build")
    if seal_rec:
        lines += ["", "## Seal", "",
                  f"- Sealed **{seal_rec['sealed_utc']}** by **{seal_rec['principal']}**",
                  f"- Receipt `{seal_rec['receipt_sha256']}` (verified against the Press ledger)"]
    else:
        lines += ["", "## Seal", "",
                  "- **Not sealed.** The seal is a human act and happens in the operator's own",
                  "  authenticated channel — this page cannot perform it.", "",
                  "```", f"press seal {vid} --word \"<your seal word>\"", "```"]
    lines += ["", "---",
              "*Projection of Press output. The Press is the source of truth; this page holds "
              "no state and can change nothing.*", ""]
    return "\n".join(lines)


def publish(vols, target, runs_root, out_dir, surface="internal", key=None, dry_run=False):
    """Returns (written, refused). Refusals are values, not exceptions — the caller
    prints them; nothing is published silently and nothing is skipped silently."""
    if surface not in ("public", "internal"):
        raise ValueError(f"surface must be public|internal, got {surface!r}")
    targets = sorted(vols) if target == "--all" else [target]
    written, refused = [], []
    for vid in targets:
        vol = vols.get(vid)
        if not vol:
            refused.append((vid, "not in manifest (default-deny)"))
            continue
        ok, rec = sealmod.is_sealed(runs_root, vid, key=key)
        seal_rec = rec if ok else None
        if surface == "public" and not ok:
            refused.append((vid, f"public surface carries SEALED only — {rec}"))
            continue
        card = render_card(vid, vol, seal_rec, surface)
        path = os.path.join(out_dir, f"{vid}.md")
        if not dry_run:
            os.makedirs(out_dir, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(card)
        written.append((vid, path, len(card.split())))
    return written, refused
