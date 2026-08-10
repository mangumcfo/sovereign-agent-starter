# -*- coding: utf-8 -*-
"""estate.venture_continuity — Generational Transfer (Series 12, Vol 3:
Forkable Ventures, Business Continuity & Verifiable Handoff).

Most family businesses fail the generational test — operational context is lost, a key person leaves, the
records are fragmented, a dispute captures the whole thing. This volume designs ventures heirs can **cleanly
inherit, fork, and continue** rather than rebuild: a venture captured as a governed record with a versioned,
forkable governance skin and its inheritable material estate, a verifiable operational handoff package, and a
continuation that **re-attributes** the venture to the heir — and it does so by **composing** the sealed layers
below it and **re-implementing none of them.** It re-attributes the venture through the sealed opener
(`execute_transfer` / `inheritance_package`, S12 V1), forks governance through the sealed policy-as-code skin
(`fork_governance_skin`, S11 V4), and homes the **material-estate handoff** (the F2 fold) through the sealed
material covenant (`verify_under_covenant`, S9) — physical goods as inheritable governed objects.

**The SUCCESSION-FENCE holds:** business continuity is **re-attribution of owned records**, not an escrowed
handoff a firm releases. `VENTURE_BREACH_FIELDS` refuses any escrow, custodian, second/venture succession
authority, handoff firm, or recovery engine — and (seal-key-closed) any press/seal key field. KILL-TARGET: the
succession firm / business broker that owns the venture handoff and rations the continuity — refused. Heirs
fork the governance and continue operating; nobody stands between them and the venture they inherited.
Weakest-party: an heir continues the business from receipts they hold. NO TOKEN · no yield · holds no value ·
money-path OFF · rolls no cryptography.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .generational_transfer import execute_transfer, verify_transfer, TransferStatus, EstateRefused  # S12 V1
from ..risk.governance import GovernanceSkin, fork_governance_skin                       # S11 V4 (governance skin)
from ..material.provision_covenant import verify_under_covenant                          # S9 material (F2 fold)

__all__ = ["VentureState", "capture_venture_state", "fork_venture", "VentureHandoff", "handoff_package",
           "VentureStatus", "continue_venture", "VENTURE_BREACH_FIELDS"]


# THE SUCCESSION-FENCE for the venture volume: business continuity is re-attribution of owned records — NOT a
# handoff an escrow or a broker holds and releases. Any escrow, custodian, second/venture succession authority,
# handoff firm, or recovery engine is a breach; and (seal-key-closed) no press/seal key field.
VENTURE_BREACH_FIELDS = frozenset({
    "escrow", "standing_escrow", "escrowed_venture", "custodian", "handoff_firm", "business_broker",
    "second_authority", "succession_authority", "venture_authority", "recovery_engine", "release_authority",
    "held_value", "seal_key", "press_key", "sealing_key",
})


def _vfence(mapping: Optional[Mapping[str, Any]], where: str) -> None:
    for k in (mapping or {}):
        kl = str(k).lower()
        if kl in ("seal_key", "press_key", "sealing_key"):
            raise EstateRefused(
                f"venture continuity must carry no press/seal key field ('{k}') — a venture passes as the "
                f"family's OWN governed records, never the press seal key")
        if kl in VENTURE_BREACH_FIELDS:
            raise EstateRefused(
                f"venture continuity must carry no escrow/custodian/handoff-firm field ('{k}') — business "
                f"continuity is RE-ATTRIBUTION of owned records; no firm holds the handoff and releases it "
                f"(composition, not a succession-firm engine)")


# --- Forkable business architecture & state capture (Ch 2 / Ch 3) ------------------------------------------

@dataclass(frozen=True)
class VentureState:
    """A venture captured as a governed record heirs can inherit and fork: its versioned, forkable governance
    skin (S11 V4), its inheritable material estate (S9 provision receipts — the F2 material-estate handoff), any
    livelihood streams (S10), and receipted relationships/contracts. It holds no value; it is the venture's
    inheritable *records*, not the venture's assets in escrow."""
    venture_id: str
    governance: GovernanceSkin
    material: tuple = ()
    livelihood: tuple = ()
    relationships: tuple = ()


def capture_venture_state(venture_id: str, governance: GovernanceSkin, *, material: Sequence[Mapping[str, Any]] = (),
                          livelihood: Sequence[Mapping[str, Any]] = (),
                          relationships: Sequence[Mapping[str, Any]] = (),
                          extra: Optional[Mapping[str, Any]] = None) -> VentureState:
    """Capture a venture's inheritable state as a forkable governed record: its governance skin (S11 V4), its
    material estate (S9 receipts), its livelihood streams (S10), and its receipted relationships. Deny-by-
    default: a venture needs an id and a governance skin (a venture with no governance cannot be forked or
    continued); an escrow/custodian/handoff-firm field is refused (the SUCCESSION-FENCE)."""
    _vfence(extra, "a venture state")
    if not str(venture_id).strip():
        raise EstateRefused("a venture state needs an id")
    if not isinstance(governance, GovernanceSkin):
        raise EstateRefused("a venture state needs a governance skin (S11 V4) — a venture with no governance "
                            "cannot be cleanly forked or continued")
    return VentureState(venture_id=str(venture_id), governance=governance, material=tuple(material),
                        livelihood=tuple(livelihood), relationships=tuple(relationships))


def fork_venture(state: VentureState, new_id: str, *, add_gated: Sequence[str] = (),
                 remove_gated: Sequence[str] = (), extra: Optional[Mapping[str, Any]] = None) -> VentureState:
    """Fork a venture for an heir — a clean fork that preserves momentum (composes the sealed
    `fork_governance_skin`, S11 V4). The heir gets a new venture id with a forked, version-controlled governance
    skin (adding or removing gated decision classes) over the same inheritable material, livelihood, and
    relationships. History is preserved by keeping both ventures. A pricing/underwriting rule is refused by the
    inherited governance fence; an escrow/handoff-firm field is refused here."""
    _vfence(extra, "a venture fork")
    if not str(new_id).strip():
        raise EstateRefused("a venture fork needs a new id — heirs fork into their own venture")
    forked = fork_governance_skin(state.governance, f"{state.governance.skin_id}:{new_id}",
                                  add_gated=add_gated, remove_gated=remove_gated)
    return VentureState(venture_id=str(new_id), governance=forked, material=state.material,
                        livelihood=state.livelihood, relationships=state.relationships)


# --- Verifiable operational handoff package (Ch 3) — with the S9 material-estate fold (F2) ------------------

@dataclass(frozen=True)
class VentureHandoff:
    """A verifiable operational handoff package: the venture's governance is a genuine forkable skin, and its
    material estate verifies under the sealed material covenant (S9 — the F2 material-estate handoff). Complete
    only when the governance governs something and every inherited good is genuinely provisioned; it holds no
    value and files nothing."""
    venture_id: str
    complete: bool
    governed: bool
    material_ok: bool
    goods: int
    reason: str = ""


def handoff_package(state: VentureState) -> VentureHandoff:
    """Assemble a verifiable operational handoff package. It is complete iff (a) the venture's governance skin
    governs at least one decision class (a forkable skin, not decoration) and (b) every good in the venture's
    material estate is genuinely provisioned under the sealed material covenant (`verify_under_covenant`, S9 —
    the material-estate handoff fold). Deny-by-default: a governance-less or unverified material estate is not a
    complete handoff. Composition-not-engine; holds no value."""
    governed = bool(state.governance.gated_classes)
    material_ok = all(verify_under_covenant(m["receipt"], m["good"]).provisioned for m in state.material)
    complete = governed and material_ok
    reason = ("a verifiable operational handoff — governance forkable, material estate genuine" if complete
              else "; ".join(x for x in [
                  "" if governed else "governance governs nothing (not forkable)",
                  "" if material_ok else "a good in the material estate is not genuinely provisioned",
              ] if x))
    return VentureHandoff(venture_id=state.venture_id, complete=complete, governed=governed,
                          material_ok=material_ok, goods=len(state.material), reason=reason)


# --- Business continuity as a living covenant (Ch 8) -------------------------------------------------------

@dataclass(frozen=True)
class VentureStatus:
    """The one honest indicator an heir reads over an inherited venture: *this venture is mine to continue.*
    Continued iff the handoff package is complete and the venture's estate re-attributed to the heir through the
    sealed opener. Holds no value; continuity is re-attribution of owned records, not a released escrow."""
    continued: bool
    heir: str
    venture_id: str
    transfer: Optional[TransferStatus] = None
    reason: str = ""


def continue_venture(decedent: str, heir: str, state: VentureState, work_ref: str, *, at: str, author: str,
                     source_ref: str, registry: Any, gate: Any = None, approver: Optional[str] = None,
                     approval_ref: Optional[str] = None, extra: Optional[Mapping[str, Any]] = None) -> VentureStatus:
    """Continue a venture into the next generation — heirs continue operating rather than rebuild. It verifies
    the operational handoff package is complete, then RE-ATTRIBUTES the venture's estate (its material and
    livelihood streams) to the heir by composing the sealed `execute_transfer` (S12 V1). Deny-by-default: an
    incomplete handoff package does not continue; an empty/unverified estate does not transfer. Composition-not-
    engine: it composes the sealed opener + governance + material layers and invents no succession-firm engine.
    Returns the honest indicator the heir reads."""
    _vfence(extra, "a venture continuation")
    pkg = handoff_package(state)
    if not pkg.complete:
        return VentureStatus(continued=False, heir=heir, venture_id=state.venture_id, transfer=None,
                             reason=f"the operational handoff is not complete — {pkg.reason}")
    estate: Dict[str, Any] = {}
    if state.material:
        estate["material"] = list(state.material)
    if state.livelihood:
        estate["livelihood"] = list(state.livelihood)
    st = execute_transfer(decedent, heir, estate, work_ref, at=at, author=author, source_ref=source_ref,
                          registry=registry, gate=gate, approver=approver, approval_ref=approval_ref, extra=extra)
    reason = ("this venture is mine to continue — governance forkable, estate re-attributed to the heir"
              if st.transferred else f"the venture estate did not re-attribute — {st.reason}")
    return VentureStatus(continued=st.transferred, heir=heir, venture_id=state.venture_id, transfer=st,
                         reason=reason)
