# -*- coding: utf-8 -*-
"""economy.income — The Income Primitive (Series 10 Sovereign Economy, Vol 1, the opener).

`attribute_income` records an earned unit of economic value as a **governed, attributed object owned by the
earner** — the economy **records and attributes, it never moves or settles**. The value itself rides the
sealed **Port** (S6 Vol 7): a value edge is a Port directive the record *references* (`port_ref`), so value
crosses the external rail and the record holds none. The record may state an **amount** as an attribution
(what was earned), but it is never a balance the node holds, moves, custodies, or settles, and it never
mints a bearer instrument — those are the money-path breaches this primitive refuses in code.

Money-fence (KM-1176 S10 rigor, GB arm carve-outs, enforced here from line 1): **permitted** — record an
amount, reference a Port directive (value crosses through; the record carries no held/settled value), split
credit as records; **breach → refused** — any in-node field that holds/moves/custodies/settles value or
mints a bearer instrument (balance, custody, settle, wallet, token, mint, bearer, yield, apy). Kill-target:
**the intermediary that owns your income stream for holding your money — refused**; there is no in-node
custodian, because the record is owned by the earner (its mandate) and no held balance exists to be the
hook. Weakest-party lens: an earner with no second device verifies **ownership** from a receipt they hold —
not a balance a platform shows them. NO TOKEN · no yield language · rolls no cryptography (composes the
sealed floors' hashing). The earned value's downstream livelihood and attribution home to S10 Vols 2–5.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from ..objects.identity import object_id, make_version   # Object Model (S5 Vol 5)
from ..material.provision_local import (                  # s9_01 — the S9→S10 bridge (types + shared object mechanism)
    ProvisionStatus,
    ProvisionRefused,
)

__all__ = ["attribute_income", "verify_income", "income_record",
           "IncomeRefused", "IncomeStatus", "MONEY_PATH_BREACH_FIELDS"]

IncomeRefused = ProvisionRefused        # a money-path breach or a malformed attribution is refused
IncomeStatus = ProvisionStatus          # the weakest-party ownership verdict (composed from the bridge)

# In-node MONEY-PATH breach fields: a record carrying any of these would hold/move/custody/settle value or
# mint a bearer instrument — refused. (An `amount` attribution + a `port_ref` directive are PERMITTED.)
MONEY_PATH_BREACH_FIELDS = frozenset({
    "balance", "custody", "custodied", "settle", "settled", "settlement", "escrow",
    "wallet", "token", "tokens", "mint", "minted", "bearer", "yield", "apy", "apr",
    "hold_funds", "held_funds", "transfer_funds", "move_funds",
})


def income_record(earner: str, work_ref: str, *, amount: Any = None, unit: str = "credits",
                  port_ref: Optional[str] = None, extra: Optional[Mapping[str, Any]] = None) -> dict:
    """The canonical income record: an earning attributed to an earner for a unit of work, owned by them.
    PERMITTED: an `amount` (attribution) + a `port_ref` (a directive reference to the sealed Port, where the
    value crosses the external rail) + `extra` attribution fields (e.g. splitting credit as records).
    REFUSED: any in-node money-path field. The record never holds, moves, custodies, or settles value."""
    if not str(earner).strip():
        raise IncomeRefused("income requires an earner — the owner of the record")
    if not str(work_ref).strip():
        raise IncomeRefused("income requires a work reference — the unit of value that was earned")
    rec = {"id": f"{earner}:{work_ref}", "earner": str(earner), "work_ref": str(work_ref)}
    if amount is not None:
        try:
            rec["amount"] = float(amount)            # PERMITTED — an attribution figure, not a held balance
        except (TypeError, ValueError):
            raise IncomeRefused("income amount, if recorded, must be a number (an attribution figure)")
        rec["unit"] = str(unit)
    if port_ref:
        rec["port_ref"] = str(port_ref)              # PERMITTED — value rides the sealed Port (S6 Vol 7)
    if extra:
        for k, v in dict(extra).items():             # PERMITTED — split credit as records (attribution fields)
            rec[str(k)] = v
    for k in rec:
        if k.lower() in MONEY_PATH_BREACH_FIELDS:
            raise IncomeRefused(
                f"income record must carry no in-node money-path field ('{k}') — the economy records and "
                f"attributes, it never holds, moves, custodies, or settles value; value rides the sealed Port")
    return rec


def attribute_income(earner: str, work_ref: str, *, mandate: str, author: str, source_ref: str, at: str,
                     registry: Any, amount: Any = None, unit: str = "credits",
                     port_ref: Optional[str] = None, extra: Optional[Mapping[str, Any]] = None,
                     approver: Optional[str] = None, approval_ref: Optional[str] = None, gate: Any = None,
                     action_class: str = "attribute_income",
                     role_spec: Optional[Mapping[str, Any]] = None, mode: str = "live") -> dict:
    """Record an earned unit of economic value as a governed object OWNED BY the earner (its mandate), into
    the earner's own registry, and return its receipt. The economy records/attributes; it never moves or
    settles — value rides the sealed Port via `port_ref`. Human primacy: a gated attribution passes a human
    approval. There is no in-node custodian to own the earner's income stream. Rolls no cryptography."""
    if gate is not None and gate.requires_approval(action_class, dict(role_spec or {}), mode):
        if not (approver and approval_ref):
            raise IncomeRefused(
                "a gated income attribution requires a human approval (HumanApprovalGate, S5 Vol 16) — none supplied")
    rec = income_record(earner, work_ref, amount=amount, unit=unit, port_ref=port_ref, extra=extra)
    obj_id = object_id("IncomeEvent", rec["id"])
    # composes the Object Model (S5 Vol 5): hash-chained, mandate-scoped (= owned by the earner), provenance-checked
    receipt = registry.append(obj_id, rec, author=author, source_ref=source_ref, at=at, mandate=mandate,
                              kind="income", approver=approver, approval_ref=approval_ref)
    return receipt


def verify_income(receipt: Mapping[str, Any], earner: str, work_ref: str, *, amount: Any = None,
                  unit: str = "credits", port_ref: Optional[str] = None,
                  extra: Optional[Mapping[str, Any]] = None) -> IncomeStatus:
    """Weakest-party check: the earner confirms they OWN this income from the receipt alone — no platform, no
    second device, no expertise, no balance shown to them. Re-derives the receipt via the Object Model's
    sealed `make_version` (S5 Vol 5) and confirms the attribution; a tamper flips the light. Ownership is the
    receipt's mandate — an income a platform can revoke is not one this proves. Rolls no cryptography."""
    rec = income_record(earner, work_ref, amount=amount, unit=unit, port_ref=port_ref, extra=extra)
    reasons = []
    if receipt.get("kind") != "income":
        reasons.append("not an income receipt")
    if not receipt.get("mandate"):
        reasons.append("receipt is not mandate-scoped — an unowned income proves no ownership")
    if dict(receipt.get("payload") or {}) != dict(rec):
        reasons.append("the income does not match its receipt")
    try:
        rebuilt = make_version(
            receipt["object_id"], receipt["seq"], dict(receipt["payload"]),
            author=receipt["author"], source_ref=receipt["source_ref"], at=receipt["at"],
            kind=receipt["kind"], approver=receipt.get("approver"),
            approval_ref=receipt.get("approval_ref"), prev_hash=receipt.get("prev_hash"))
        if rebuilt["version_hash"] != receipt.get("version_hash"):
            reasons.append("receipt hash does not verify — the attribution was altered")
    except Exception as e:   # a receipt that will not rebuild fails closed
        reasons.append(f"receipt does not rebuild: {e}")
    return IncomeStatus(provisioned=not reasons, reason="; ".join(reasons) or "provisioned")
