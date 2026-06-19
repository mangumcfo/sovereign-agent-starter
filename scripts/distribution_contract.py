#!/usr/bin/env python3
"""
distribution_contract.py — the headless quality gates for the Distribution Layer (Tiger lane, thread [445]).

The DISTRIBUTION analog of review_ready_contract.py. NO volume's social/distribution assets reach KM's one
"Launch" gate unless ALL gates pass. No vibes-gates — every criterion LOADS from the machine-readable engine
book_standards/distribution_standard.yaml (change the yaml -> the gate verdict changes; the auto-propagation
proof, mirroring the book rail). Assets are DERIVE-FROM-SEALED: generated from the sealed, human-approved
manuscript, never re-authored; each traces to its source via dist_provenance.json.

  A volume is DISTRIBUTION-READY iff (criteria from distribution_standard.yaml#distribution_ready):
    1. asset_completeness — the v1 asset set exists (x_thread · linkedin_carousel · substack_excerpt)
    2. voice_brand        — voice_match (no consultant-speak) + brand + sovereignty_tone
    3. format_specs       — each asset meets its asset_specs entry (counts / dims / words)
    4. derive_provenance  — dist_provenance.json: every asset traces to the sealed source (sealed_commit)
    5. gb_sample_read     — GB rendered-read verdict PASS recorded on a representative sample (the no-slop catch)

Usage:
  python3 scripts/distribution_contract.py 01_strategic_finance --match "Strategic Finance"
  -> per-gate table + gap-list; writes artifacts/distribution_ready/<book>.json; exit 0 ready / 1 not.
  On all-green: mints ONE distribution_launch:<book> obligation into Awaiting-KM (the single human gate).

∞Δ∞ The engine earns the assets; the gates earn the trust; the human keeps only the Launch. ∞Δ∞
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
DIST_STANDARD = Path("/home/kmangum/work-repos/mangumcfo/breathline-books-vault/book_standards/distribution_standard.yaml")
DIST_ROOT = REPO / "artifacts" / "distribution"          # generated assets: <book_id>/...
READY_ROOT = REPO / "artifacts" / "distribution_ready"   # gate verdicts: <book_id>.json


# ---- ledger (shared resolver, mirrors review_ready_contract) ----
def _resolve_ledger_root() -> Path:
    src = str(REPO / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from sovereign_agent.obligations.ledger import get_ledger_root
    return get_ledger_root(default=REPO / "memory" / "obligations" / "atrium_review")


LEDGER_ROOT = _resolve_ledger_root()


# ---- standard loader (the single source of truth) ----
_STD_CACHE: dict | None = None


def load_standard() -> dict:
    global _STD_CACHE
    if _STD_CACHE is None:
        import yaml
        _STD_CACHE = yaml.safe_load(DIST_STANDARD.read_text(encoding="utf-8"))
    return _STD_CACHE


def v1_asset_set(std: dict) -> list[str]:
    """The asset keys the gates require (asset_specs entries with tier == v1)."""
    return [k for k, v in (std.get("asset_specs") or {}).items() if (v or {}).get("tier") == "v1"]


def _parse_range(spec: str) -> tuple[int, int] | None:
    """'5-9' -> (5, 9); '800-1500' -> (800, 1500). Tolerant of stray text."""
    m = re.search(r"(\d+)\s*-\s*(\d+)", str(spec))
    return (int(m.group(1)), int(m.group(2))) if m else None


# ---- book + asset dir resolvers (resolver fix: KDP root added for S0 titles) ----
def _book_roots() -> list[Path]:
    """Where a sealed book can live: S0 titles at the KDP TOP LEVEL (kdp/01_strategic_finance), the S1
    agentic_playbooks vault, and each Series-N folder. The book-rail _book_dir misses the KDP top level —
    distribution titles include S0, so we add it here (plan: resolver fix)."""
    return [KDP, AGENTIC] + sorted(KDP.glob("series_*"))


def _book_dir(book_id: str) -> Path | None:
    for root in _book_roots():
        d = root / book_id
        vers = sorted((v for v in d.glob("v*") if v.is_dir()), key=_vkey, reverse=True)
        if vers:
            return vers[0]
    return None


def _vkey(p: Path) -> tuple:
    return tuple(int(n) for n in re.findall(r"\d+", p.name)) or (0,)


def _dist_dir(book_id: str) -> Path:
    return DIST_ROOT / book_id


def _read_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _source_text(book_id: str) -> str:
    """The sealed manuscript text — derive-from-sealed means KM's own published prose is his voice by
    definition, so the voice gate must NOT flag phrases that already live in the approved source; it only
    catches consultant-speak the GENERATOR introduced."""
    bdir = _book_dir(book_id)
    if not bdir:
        return ""
    mss = sorted((p for p in bdir.glob("manuscript_v*.md")
                  if re.match(r"manuscript_v[0-9.]+\.md$", p.name)), key=_vkey)
    return mss[-1].read_text(encoding="utf-8", errors="ignore").lower() if mss else ""


# ============================ THE 5 GATES (criteria from the yaml) ============================

def _check_asset_completeness(book_id: str, std: dict) -> dict:
    """The v1 asset set exists per channels[v1:true] + asset_specs (tier v1)."""
    name = "asset_completeness"
    need = v1_asset_set(std)
    dd = _dist_dir(book_id)
    present, missing = [], []
    for a in need:
        # each asset writes <asset>.json (metadata + content) into the dist dir
        if (dd / f"{a}.json").exists():
            present.append(a)
        else:
            missing.append(a)
    ok = not missing
    return {"check": name, "pass": ok,
            "detail": f"{len(present)}/{len(need)} v1 assets: {', '.join(present) or 'none'}",
            "gap": None if ok else f"generate missing v1 assets: {', '.join(missing)}"}


def _check_voice_brand(book_id: str, std: dict) -> dict:
    """voice_match (no consultant-speak) + brand palette + sovereignty_tone (criteria from quality_bar)."""
    name = "voice_brand"
    qb = std.get("quality_bar") or {}
    dd = _dist_dir(book_id)
    texts = []
    for a in v1_asset_set(std):
        j = _read_json(dd / f"{a}.json")
        if j:
            texts.append(json.dumps(j.get("content", j), ensure_ascii=False))
    blob = "\n".join(texts).lower()
    if not blob:
        return {"check": name, "pass": False, "detail": "no asset text to check",
                "gap": "no assets generated yet"}
    # consultant-speak banlist (voice_match: KM's voice, not a consultant deck)
    banned = ["leverage synergies", "circle back", "move the needle", "best-in-class", "paradigm shift",
              "low-hanging fruit", "boil the ocean", "synergize", "thought leader", "value-add",
              "at the end of the day", "going forward,"]
    # derive-from-sealed: a banned phrase only counts if the GENERATOR introduced it (in the asset but NOT in
    # KM's sealed source — his published prose is his approved voice and must never be re-judged here).
    src = _source_text(book_id)
    hits = [b for b in banned if b in blob and b not in src]
    # sovereignty tone tokens (federation voice — Source/Truth/Integrity)
    sov_tokens = ["sovereign", "source", "truth", "integrity", "lgp", "generational", "receipt",
                  "federation", "breath", "constitution"]
    sov_ok = any(t in blob for t in sov_tokens) if qb.get("sovereignty_tone") == "required" else True
    voice_ok = not hits if qb.get("voice_match") == "required" else True
    palette = ((qb.get("brand") or {}).get("palette")) or []
    # brand enforced at generation (svg_toolkit navy/gold); here we confirm a carousel asset carries the palette
    carousel = _read_json(dd / "linkedin_carousel.json") or {}
    brand_ok = bool(palette) and bool(carousel.get("meta", {}).get("palette"))
    ok = voice_ok and sov_ok and brand_ok
    parts = [f"voice={'ok' if voice_ok else 'consultant-speak:'+','.join(hits)}",
             f"sovereignty={'ok' if sov_ok else 'absent'}", f"brand={'ok' if brand_ok else 'palette-unrecorded'}"]
    gap = None
    if not ok:
        g = []
        if not voice_ok: g.append(f"remove consultant-speak: {', '.join(hits)}")
        if not sov_ok: g.append("add sovereignty-tone (Source/Truth/Integrity/LGP)")
        if not brand_ok: g.append("carousel must record brand palette (navy/gold)")
        gap = " · ".join(g)
    return {"check": name, "pass": ok, "detail": " · ".join(parts)[:90], "gap": gap}


def _check_format_specs(book_id: str, std: dict) -> dict:
    """Each asset meets its asset_specs entry (x_thread posts · carousel slides+dims · excerpt words)."""
    name = "format_specs"
    specs = std.get("asset_specs") or {}
    dd = _dist_dir(book_id)
    fails, oks = [], []
    # x_thread: posts in range
    j = _read_json(dd / "x_thread.json")
    rng = _parse_range((specs.get("x_thread") or {}).get("posts", ""))
    if j and rng:
        n = j.get("meta", {}).get("posts", len(j.get("content", []) or []))
        (oks if rng[0] <= n <= rng[1] else fails).append(f"x_thread {n}∉{rng}" if not (rng[0] <= n <= rng[1]) else f"x_thread={n}")
    # linkedin_carousel: slides in range + dims match
    j = _read_json(dd / "linkedin_carousel.json")
    rng = _parse_range((specs.get("linkedin_carousel") or {}).get("slides", ""))
    want_dims = (specs.get("linkedin_carousel") or {}).get("dims", "")
    if j and rng:
        n = j.get("meta", {}).get("slides", len(j.get("content", []) or []))
        dims = j.get("meta", {}).get("dims", "")
        slide_ok = rng[0] <= n <= rng[1]
        dims_ok = (not want_dims) or (dims == want_dims)
        (oks if (slide_ok and dims_ok) else fails).append(
            f"carousel={n}@{dims}" if (slide_ok and dims_ok) else f"carousel {n}∉{rng} or dims {dims}≠{want_dims}")
    # substack_excerpt: words in range
    j = _read_json(dd / "substack_excerpt.json")
    rng = _parse_range((specs.get("substack_excerpt") or {}).get("words", ""))
    if j and rng:
        w = j.get("meta", {}).get("words", 0)
        (oks if rng[0] <= w <= rng[1] else fails).append(f"excerpt={w}w" if rng[0] <= w <= rng[1] else f"excerpt {w}w∉{rng}")
    ok = not fails and bool(oks)
    return {"check": name, "pass": ok, "detail": (" · ".join(oks + fails))[:90] or "no assets",
            "gap": None if ok else f"format out of spec: {', '.join(fails) or 'no assets generated'}"}


def _check_derive_provenance(book_id: str, std: dict) -> dict:
    """dist_provenance.json: every v1 asset traces to the sealed source (source_section + sealed_commit)."""
    name = "derive_provenance"
    dd = _dist_dir(book_id)
    prov = _read_json(dd / "dist_provenance.json")
    if not prov:
        return {"check": name, "pass": False, "detail": "no dist_provenance.json",
                "gap": "generators must write dist_provenance.json (derive-from-sealed)"}
    sealed = prov.get("sealed_commit")
    assets = prov.get("assets") or {}
    missing = [a for a in v1_asset_set(std) if not (assets.get(a) or {}).get("source_section")]
    ok = bool(sealed) and not missing
    detail = f"sealed_commit={(sealed or 'MISSING')[:10]} · {len(assets)} assets traced"
    gap = None
    if not ok:
        g = []
        if not sealed: g.append("record sealed_commit")
        if missing: g.append(f"trace source_section for: {', '.join(missing)}")
        gap = " · ".join(g)
    return {"check": name, "pass": ok, "detail": detail[:90], "gap": gap}


def _check_gb_sample_read(book_id: str, std: dict) -> dict:
    """A GB rendered-read verdict PASS recorded on a representative asset sample (the no-slop catch — the asset
    analog of the figure-quality / fidelity gate). RED until GB records it. Scans the dist sample-read records."""
    name = "gb_sample_read"
    sources = sorted(REPO.glob("artifacts/**/*dist*sample*read*.ndjson")) + \
        sorted(REPO.glob("artifacts/distribution/**/gb_sample_read.ndjson"))
    latest = None
    for src in sources:
        for line in src.read_text(encoding="utf-8", errors="ignore").splitlines():
            low = line.lower()
            if book_id.lower() not in low and book_id.replace("_", " ").lower() not in low:
                continue
            if "sample_read" in low or "gb_sample_read" in low or "no_slop" in low:
                if "pass" in low and "fail" not in low:
                    latest = "pass"
                elif "fail" in low:
                    latest = "fail"
    ok = latest == "pass"
    return {"check": name, "pass": ok,
            "detail": f"GB sample read: {latest or 'not recorded'}",
            "gap": None if ok else "awaiting GB rendered sample-read (PASS) — the no-slop gate"}


# ============================ AGGREGATE + MINT + MAIN ============================

def evaluate(book_id: str) -> dict:
    std = load_standard()
    checks = [_check_asset_completeness(book_id, std), _check_voice_brand(book_id, std),
              _check_format_specs(book_id, std), _check_derive_provenance(book_id, std),
              _check_gb_sample_read(book_id, std)]
    ready = all(c["pass"] for c in checks)
    return {
        "book_id": book_id, "distribution_ready": ready, "checks": checks,
        "gaps": [c["gap"] for c in checks if c.get("gap")],
        "meta": {"contract": "Distribution Rail v1.0", "standard": str(DIST_STANDARD),
                 "standard_version": std.get("version"),
                 "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
    }


def mint_launch_packet(book_id: str, label: str) -> str | None:
    """On all-gates-green, mint the ONE human Launch obligation into Awaiting-KM (idempotent). KM's optional
    voice note + one 'Launch' Accept dispatches the full multi-channel set — no per-asset/per-channel cards."""
    owner = (os.environ.get("BREATHLINE_NODE_OWNER") or os.environ.get("BREATHLINE_NODE_LOOPBACK_OWNER")
             or "KM-1176").strip()
    try:
        sys.path.insert(0, str(REPO / "src"))
        from sovereign_agent.obligations.ledger import ObligationLedger
        lg = ObligationLedger(str(LEDGER_ROOT), principal_id=owner)
    except Exception:
        return None
    ref = f"distribution_launch:{book_id}"
    for o in lg.open_obligations():
        if (o.get("ref") or "") == ref:
            return o.get("id")  # idempotent
    dd = _dist_dir(book_id)
    std = load_standard()
    assets = ", ".join(v1_asset_set(std))
    entry = lg.open(
        title=f"🚀 Launch {label} — distribution-ready; Accept dispatches the multi-channel set",
        owner=owner, classification="C1", material=True, next_gate="Human disposition", ref=ref,
        intent=(f"All distribution gates green (assets complete · voice+brand · format specs · derive-from-sealed "
                f"provenance · GB sample-read PASS). v1 asset set: {assets}. Assets: {dd}. "
                f"ACCEPT = one Launch -> the self-hosted scheduler dispatches the full v1 multi-channel set "
                f"(X · LinkedIn · Substack) per the cadence accordion. Optional voice note to tune before dispatch."),
        lgp={"objective": "existing catalog into the human domains — high quality, minimal human effort, sovereign"},
    )
    return entry.get("id")


def main() -> int:
    ap = argparse.ArgumentParser(description="Distribution-Ready Contract checker")
    ap.add_argument("book_id")
    ap.add_argument("--match", nargs="*", default=[], help="label tokens (e.g. 'Strategic Finance')")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    result = evaluate(args.book_id)
    READY_ROOT.mkdir(parents=True, exist_ok=True)
    (READY_ROOT / f"{args.book_id}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2)); return 0 if result["distribution_ready"] else 1
    flag = "✅ DISTRIBUTION-READY" if result["distribution_ready"] else "⛔ NOT READY"
    print(f"{flag} — {args.book_id}")
    if result["distribution_ready"]:
        label = (args.match[0] if args.match else args.book_id)
        pid = mint_launch_packet(args.book_id, f"{label} ({args.book_id})")
        if pid:
            print(f"  🚀 Launch packet on the human gate: {pid} (appears in Awaiting-KM)")
    for c in result["checks"]:
        print(f"  {'✓' if c['pass'] else '✗'} {c['check']:20} {c['detail']}")
    if result["gaps"]:
        print("  gaps (each → work before the Launch gate):")
        for g in result["gaps"]:
            print(f"    • {g}")
    return 0 if result["distribution_ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
