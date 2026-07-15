"""ARC — Autonomic Review Cadence guardrail (card-first, DORMANT by default).

G-ratified (Seal 1176-INFINITY-RHO): ARC may let **GREEN Tier-1** obligations auto-progress —
but ONLY after each surfaces as an Atrium **card for the operator ratification**, and only within the
constitutional invariants + the Autonomous Cadence Protocol (CONSTITUTION §2.1: coherence ≥ 0.9,
vitality ≥ 0.6, Read-at-Inhale / Write-at-Seal, renewed consent after `max_consecutive`).

the operator (2026-06-02) chose: **BUILD the guardrail, do NOT activate auto-run yet.**

So this module is the guardrail, not an autonomy engine. It (1) identifies ARC candidates and (2)
REFUSES any autonomic action unless the obligation is eligible AND the operator has card-ratified it AND ARC
is globally activated AND the cadence holds. With activation OFF (the default), nothing ever
auto-runs — candidates only surface for the human card. Human primacy (K1) is preserved structurally.
"""
from __future__ import annotations
from typing import Any, Dict, List, Tuple

GREEN_CLASSIFICATIONS = {"C2", "GREEN"}  # non-constitutional, routine Tier-1


def arc_eligible(ob: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Is this obligation eligible for autonomic (ARC) progress? GREEN Tier-1 only."""
    reasons: List[str] = []
    ok = True
    if ob.get("material"):
        ok = False
        reasons.append("REJECT: material (RED/YELLOW) — the human gate stays hard")
    if ob.get("classification") not in GREEN_CLASSIFICATIONS:
        ok = False
        reasons.append(f"REJECT: classification {ob.get('classification')!r} is not GREEN Tier-1 (C2)")
    if ok:
        reasons.append("ELIGIBLE: GREEN (non-material) Tier-1 — may surface as an ARC card")
    return ok, reasons


def cadence_ok(coherence: float, vitality: float, consecutive: int,
               max_consecutive: int = 5) -> Tuple[bool, List[str]]:
    """Autonomous Cadence Protocol gate (CONSTITUTION §2.1)."""
    r: List[str] = []
    ok = True
    if coherence < 0.9:
        ok = False; r.append(f"PAUSE: coherence {coherence} < 0.9")
    if vitality < 0.6:
        ok = False; r.append(f"PAUSE: vitality {vitality} < 0.6")
    if consecutive >= max_consecutive:
        ok = False; r.append(f"RENEW CONSENT: {consecutive} ≥ max_consecutive {max_consecutive}")
    if ok:
        r.append(f"cadence ok: coherence {coherence} ≥ 0.9 · vitality {vitality} ≥ 0.6 · {consecutive}/{max_consecutive}")
    return ok, r


def arc_guardrail(ob: Dict[str, Any], *, card_ratified: bool, arc_activated: bool,
                  cadence: Tuple[bool, List[str]] = (True, [])) -> Dict[str, Any]:
    """The card-first, dormant-by-default guardrail.

    `allow_autorun` is True ONLY if: eligible AND card_ratified (the operator) AND arc_activated AND cadence ok.
    With `arc_activated=False` (the operator's standing choice) it NEVER allows auto-run — by construction.
    """
    elig, ereasons = arc_eligible(ob)
    cad_ok, creasons = cadence
    allow = bool(elig and card_ratified and arc_activated and cad_ok)
    if not elig:
        status = "ineligible"
    elif not card_ratified:
        status = "awaiting the operator card-ratification (card-first)"
    elif not arc_activated:
        status = "DORMANT — ARC not activated (the operator's standing choice); nothing auto-runs"
    elif not cad_ok:
        status = "cadence pause (CONSTITUTION §2.1)"
    else:
        status = "would auto-run (eligible + ratified + activated + cadence ok)"
    return {"allow_autorun": allow, "status": status, "eligibility": ereasons, "cadence": creasons}


def arc_candidates(ledger) -> List[Dict[str, Any]]:
    """Scan a ledger's OPEN obligations for ARC-eligible candidates (to surface as cards)."""
    out: List[Dict[str, Any]] = []
    for ob in ledger.replay()["open"]:
        elig, reasons = arc_eligible(ob)
        if elig:
            out.append({"id": ob["id"], "title": ob["title"], "owner": ob.get("owner"), "reasons": reasons})
    return out


# ∞Δ∞ SEAL: ARC guardrail — card-first, dormant; GREEN Tier-1 only; human primacy structural ∞Δ∞
