"""Token-typed schema (S4-G2) — pure validators + replay folds over an obligation chain's entries.

Spec: docs/specs/S4-G2_token_typed_schema_v0.1.md. Design rule §1: a token event IS a balanced B32
obligation — one debit entry carrying a `token` block with exactly two legs (dr/cr), on the SAME
hash chain, gate, and replay as every other obligation. No parallel ledger, no balance store: every
derivation here (balance / circulating_supply / checkpoint verify) is a FOLD over sealed entries —
checkpoints never substitute for replay (§3).

Module idiom mirrors quorum_guard / mandate_guard: pure, stateless, crypto-free, no ledger import
(only projection — no cycle). Decimal-exact math ONLY (yield_organism/value_flow.py convention);
no floats anywhere near amounts.

Fences (spec header): private, ledgered, receipt-derived only. Never a coin, never floating, never
exchange-tradeable. money_path stays OFF. Nothing here touches cmd_seal. No token.adjust, no
balance-set, no mutation kind — corrections use the existing reopen/reference pattern (§1).

DECLARED-CONFIG-NEVER-CONSTANTS: the token registry is OPERATOR-DECLARED at ledger construction
(ObligationLedger(token_registry={...})) or via the S4-G1 policy document's `token_registry:` key —
{token_id: {"precision": int (spec default 18), "supply_cap": "<Decimal str>" (optional)}}. An
unregistered token_id refuses at open (rule TOKEN-1). The only literals in this module are the
spec-fixed SCHEMA names (system accounts, kinds, evidence floors) — structure, not thresholds.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from . import projection as _proj

# ── spec-fixed schema names (§1) — structure the spec locks, not operator thresholds ──
IA_ACCOUNT = "issuance_authority"   # contra source: supply enters circulation only by debiting IA
SR_ACCOUNT = "supply_retirement"    # burn sink: supply leaves permanently only by crediting SR
_SYSTEM_ACCOUNTS = frozenset({IA_ACCOUNT, SR_ACCOUNT})
DEFAULT_PRECISION = 18              # spec §2: "precision per token policy (default 18)"
CHECKPOINT_KIND = "token.checkpoint"
# kind -> (dr constraint, cr constraint); "holder" = any NON-system account. Burn-vs-return is
# distinguished BY TARGET ACCOUNT (the book's rule), never by a flag (§1).
_LEG_TABLE = {
    "token.mint":          ("system:" + IA_ACCOUNT, "holder"),
    "token.transfer":      ("holder", "holder"),
    "token.redeem.return": ("holder", "system:" + IA_ACCOUNT),
    "token.redeem.burn":   ("holder", "system:" + SR_ACCOUNT),
}
# Evidence floors at close (§1 table): mint/redeem/checkpoint = E2; transfer = E1+ (per policy;
# v0.1 enforces the E1 floor in the validator so require_e1=False cannot silently duck it).
_E2_FLOOR_KINDS = frozenset({"token.mint", "token.redeem.return", "token.redeem.burn", CHECKPOINT_KIND})
_TOKEN_FIELDS = frozenset({"token_id", "amount", "dr_account", "cr_account", "memo"})
_CHECKPOINT_FIELDS = frozenset({"token_id", "as_of_entry_hash", "balances", "chain_tip", "memo"})


class TokenEventRefused(PermissionError):
    """Fail-closed refusal of a token event — refusal with reason, never a silent drop (spec §2).

    PermissionError family: rides the EconomicActionRefused posture at the adapter surface (G2
    addendum) and the ledger's own refusal idiom. `rule_id` names the citable schema rule (TOKEN-1
    for an unregistered token_id per S4-G1; TOKEN-* for the structural rules) so the recorded
    refusal fact carries the S4-G1 §4 shape.
    """

    def __init__(self, message: str, rule_id: str = "TOKEN-SCHEMA"):
        super().__init__(f"[{rule_id}] {message}")   # rule cited IN the refusal, same as WriteRefused
        self.rule_id = rule_id


class TokenIntegrityBreach(RuntimeError):
    """A LOUD integrity breach in a token derivation — never a quiet drift.

    Raised when the IA/SR identity check disagrees with the holder-sum (§3), or a checkpoint's
    stated balances drift from full-genesis replay ("a drifted checkpoint cannot quietly stand").
    """


def is_token_kind(kind) -> bool:
    """True iff `kind` opts the entry into token-typed validation (fires ONLY on token.* kinds)."""
    return isinstance(kind, str) and kind.startswith("token.")


def _dec(raw, what: str) -> Decimal:
    """Exact-Decimal parse or a loud refusal — no float ever touches an amount."""
    if isinstance(raw, float):
        raise TokenEventRefused(f"{what} {raw!r} is a float — token amounts are Decimal strings, "
                                f"never floats (Decimal-exact math only)", rule_id="TOKEN-AMOUNT")
    try:
        d = Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise TokenEventRefused(f"{what} {raw!r} does not parse as a Decimal",
                                rule_id="TOKEN-AMOUNT") from exc
    if not d.is_finite():
        raise TokenEventRefused(f"{what} {raw!r} is not finite", rule_id="TOKEN-AMOUNT")
    return d


def registry_entry(registry: Optional[dict], token_id) -> tuple[int, Optional[Decimal]]:
    """Resolve (precision, supply_cap) for a token_id from the OPERATOR-DECLARED registry.

    Unregistered / no registry declared => refuse at open, rule TOKEN-1 (spec §2). Malformed
    declared config refuses loudly too — a bad declaration is never silently defaulted over.
    """
    if not registry or token_id not in registry:
        raise TokenEventRefused(
            f"token_id {token_id!r} is not charter-registered on this ledger — declare it in the "
            f"operator token registry (rule TOKEN-1: unregistered id refuses at open)",
            rule_id="TOKEN-1")
    cfg = registry[token_id] or {}
    if not isinstance(cfg, dict):
        raise TokenEventRefused(f"token registry entry for {token_id!r} is not a mapping: {cfg!r}",
                                rule_id="TOKEN-1")
    try:
        precision = int(cfg.get("precision", DEFAULT_PRECISION))
    except (TypeError, ValueError) as exc:
        raise TokenEventRefused(f"token registry precision for {token_id!r} is malformed: "
                                f"{cfg.get('precision')!r}", rule_id="TOKEN-1") from exc
    cap = cfg.get("supply_cap")
    cap_d = _dec(cap, f"registry supply_cap for {token_id!r}") if cap is not None else None
    return precision, cap_d


def _validate_amount(raw, precision: int) -> Decimal:
    """Amount parses as a positive, finite Decimal within precision (§2) — any failure refuses."""
    d = _dec(raw, "token amount")
    if d <= 0:
        raise TokenEventRefused(f"token amount {raw!r} must be > 0 (zero/negative refused; "
                                f"corrections use the reopen/reference pattern, never a negative leg)",
                                rule_id="TOKEN-AMOUNT")
    exponent = d.as_tuple().exponent
    if isinstance(exponent, int) and -exponent > precision:
        raise TokenEventRefused(
            f"token amount {raw!r} exceeds the registered precision ({precision} decimal places) — "
            f"precision overflow refused at open", rule_id="TOKEN-AMOUNT")
    return d


def _validate_account(account, constraint: str, leg: str, kind: str) -> str:
    """One leg against the §1 legs table: 'holder' = any non-system account; 'system:X' = exactly X."""
    if not account or not isinstance(account, str):
        raise TokenEventRefused(f"{kind} {leg} account is missing/malformed: {account!r} — "
                                f"an unbalanced token entry (a missing leg) is refused at open",
                                rule_id="TOKEN-LEGS")
    if constraint == "holder":
        if account in _SYSTEM_ACCOUNTS:
            raise TokenEventRefused(
                f"{kind} {leg} account {account!r} is a system account — this kind's {leg} leg must "
                f"be a holder (system accounts are never 'circulating'; burn-vs-return is chosen by "
                f"kind, and mint's source is only ever {IA_ACCOUNT})", rule_id="TOKEN-LEGS")
        return account
    want = constraint.split(":", 1)[1]
    if account != want:
        raise TokenEventRefused(
            f"{kind} {leg} account must be {want!r} (the §1 legs table), got {account!r} — "
            f"a foreign-leg token entry is refused at open", rule_id="TOKEN-LEGS")
    return account


def validate_open(registry: Optional[dict], kind: str, token: Optional[dict], material: bool) -> None:
    """Validate a token.* entry AT open() (spec §2): legs match the kind's table exactly, amount is
    a positive Decimal within precision, token_id is registered, dr != cr. Any failure = refusal
    with reason (TokenEventRefused), never a silent drop.
    """
    if token is None or not isinstance(token, dict):
        raise TokenEventRefused(f"kind {kind!r} requires a token block (token_id/amount/legs) — "
                                f"none supplied", rule_id="TOKEN-SCHEMA")
    if kind == CHECKPOINT_KIND:
        _validate_checkpoint_open(registry, token, material)
        return
    if kind not in _LEG_TABLE:
        raise TokenEventRefused(
            f"unknown token kind {kind!r} — the schema has exactly {sorted(_LEG_TABLE)} + "
            f"'{CHECKPOINT_KIND}'; there is no token.adjust / balance-set / mutation kind (§1)",
            rule_id="TOKEN-SCHEMA")
    unknown = set(token) - _TOKEN_FIELDS
    if unknown:
        raise TokenEventRefused(f"token block carries unknown fields {sorted(unknown)} — "
                                f"schema fields are {sorted(_TOKEN_FIELDS)} (§2)", rule_id="TOKEN-SCHEMA")
    precision, _cap = registry_entry(registry, token.get("token_id"))
    _validate_amount(token.get("amount"), precision)
    dr_c, cr_c = _LEG_TABLE[kind]
    dr = _validate_account(token.get("dr_account"), dr_c, "dr", kind)
    cr = _validate_account(token.get("cr_account"), cr_c, "cr", kind)
    if dr == cr:
        raise TokenEventRefused(f"{kind} dr_account == cr_account ({dr!r}) — a self-leg entry is "
                                f"refused at open (dr != cr, §2)", rule_id="TOKEN-LEGS")
    if not material:
        # §1 gate classes: mint/redeem are material ALWAYS; transfer defaults material (per-policy
        # relaxation is a future S4-G1 predicate, not invented here). Fail-closed: refuse, never
        # silently upgrade — the opener must declare the materiality the schema demands.
        raise TokenEventRefused(
            f"{kind} must be opened material=True — token events ride the AH-1 human gate "
            f"(§1 gate class; a non-material token write is refused, never silently upgraded)",
            rule_id="TOKEN-GATE")


def _validate_checkpoint_open(registry: Optional[dict], token: dict, material: bool) -> None:
    """Shape-validate a token.checkpoint block (§3). Balance CORRECTNESS is deliberately not judged
    here — verify_checkpoint() recomputes from genesis and names any drift loudly; open only refuses
    malformed shape (the chain may confess a drifted checkpoint later; it can never quietly stand)."""
    unknown = set(token) - _CHECKPOINT_FIELDS
    if unknown:
        raise TokenEventRefused(f"checkpoint block carries unknown fields {sorted(unknown)} — "
                                f"schema fields are {sorted(_CHECKPOINT_FIELDS)} (§3)",
                                rule_id="TOKEN-SCHEMA")
    registry_entry(registry, token.get("token_id"))
    for key in ("as_of_entry_hash", "chain_tip"):
        if not token.get(key) or not isinstance(token.get(key), str):
            raise TokenEventRefused(f"checkpoint {key} is missing/malformed: {token.get(key)!r}",
                                    rule_id="TOKEN-SCHEMA")
    balances_map = token.get("balances")
    if not isinstance(balances_map, dict) or not balances_map:
        raise TokenEventRefused(f"checkpoint balances must be a non-empty {{account: amount}} map, "
                                f"got {balances_map!r}", rule_id="TOKEN-SCHEMA")
    for account, amount in balances_map.items():
        _dec(amount, f"checkpoint balance for {account!r}")   # sign-free: IA is negative by design
    if not material:
        raise TokenEventRefused("token.checkpoint must be opened material=True (E2, material-gated "
                                "attestation, §3)", rule_id="TOKEN-GATE")


def validate_close(registry: Optional[dict], debit: dict, tier_value: str, entries: list[dict]) -> None:
    """Close-time token checks: the §1 evidence floor (E2 for mint/redeem/checkpoint, E1 for
    transfer) + the registry-declared supply cap on a mint, replayed INCLUDING the closing entry
    (§4). Refusal with reason, same shape as a policy refusal (G2 test 7)."""
    kind = debit.get("kind")
    floor = "E2" if kind in _E2_FLOOR_KINDS else "E1"
    order = {"E0": 0, "E1": 1, "E2": 2}
    if order.get(tier_value, 0) < order[floor]:
        raise TokenEventRefused(
            f"{kind} requires evidence tier {floor}+ to close (§1 evidence floor), got {tier_value} — "
            f"a token event never seals on a claim", rule_id="TOKEN-EVIDENCE")
    if kind == "token.mint":
        token = debit.get("token") or {}
        _precision, cap = registry_entry(registry, token.get("token_id"))
        if cap is not None:
            prospective = supply_including(entries, debit)
            if prospective > cap:
                raise TokenEventRefused(
                    f"sealing this mint would put circulating supply at {prospective} > declared "
                    f"supply_cap {cap} for {token.get('token_id')!r} (replay including the closing "
                    f"entry, §4) — refused at close", rule_id="TOKEN-CAP")


# ── derivations: never stored, always replayed (§3) — pure folds, projection.py conventions ──

def _sealed_token_debits(entries: list[dict], token_id: str) -> list[dict]:
    """The token-legged debits (checkpoints excluded — attestations carry no legs) that are SEALED:
    closed by an EXECUTED credit (a rejected close is a recorded 'no', it moves no supply) and not
    reopened. Open/refused entries count 0 (§3)."""
    out = []
    for e in entries:
        if e.get("type") != "debit" or not is_token_kind(e.get("kind")):
            continue
        if e.get("kind") == CHECKPOINT_KIND:
            continue
        token = e.get("token") or {}
        if token.get("token_id") != token_id:
            continue
        if _proj.is_executed(entries, e["id"]):
            out.append(e)
    return out


def balances(entries: list[dict], token_id: str) -> dict[str, Decimal]:
    """{account: balance} by fold over sealed token entries: credit = increase, debit = decrease.
    Deterministic: same entries -> byte-identical map (accounts in first-touch chain order)."""
    out: dict[str, Decimal] = {}
    for e in _sealed_token_debits(entries, token_id):
        token = e["token"]
        amount = Decimal(str(token["amount"]))
        dr, cr = token["dr_account"], token["cr_account"]
        out[dr] = out.get(dr, Decimal("0")) - amount
        out[cr] = out.get(cr, Decimal("0")) + amount
    return out


def balance(entries: list[dict], token_id: str, account: str) -> Decimal:
    """Σ cr − Σ dr for one account over sealed token entries (never stored, always replayed)."""
    return balances(entries, token_id).get(account, Decimal("0"))


def _supply_from_balances(balance_map: dict[str, Decimal], token_id: str) -> Decimal:
    """Circulating supply with the §3 IA/SR identity check — BOTH computed, MUST agree; a
    disagreement is a loud integrity breach, never a quiet drift."""
    holders = sum((v for k, v in balance_map.items() if k not in _SYSTEM_ACCOUNTS), Decimal("0"))
    identity = -(balance_map.get(IA_ACCOUNT, Decimal("0"))) - balance_map.get(SR_ACCOUNT, Decimal("0"))
    if holders != identity:
        raise TokenIntegrityBreach(
            f"IA/SR identity check FAILED for {token_id!r}: Σ holder balances = {holders} but "
            f"−balance(IA) − balance(SR) = {identity} — integrity breach, loud (§3)")
    return holders


def circulating_supply(entries: list[dict], token_id: str) -> Decimal:
    """Σ holder balances == −balance(IA) − balance(SR) (identity-checked), replayed from genesis."""
    return _supply_from_balances(balances(entries, token_id), token_id)


def supply_including(entries: list[dict], closing_debit: dict) -> Decimal:
    """Circulating supply with `closing_debit` treated as sealed — 'replay including the closing
    entry' (§4), the supply-cap gate's math at close()."""
    token = closing_debit.get("token") or {}
    token_id = token["token_id"]
    balance_map = balances(entries, token_id)
    amount = Decimal(str(token["amount"]))
    dr, cr = token["dr_account"], token["cr_account"]
    balance_map[dr] = balance_map.get(dr, Decimal("0")) - amount
    balance_map[cr] = balance_map.get(cr, Decimal("0")) + amount
    return _supply_from_balances(balance_map, token_id)


def checkpoint_block(entries: list[dict], token_id: str) -> dict:
    """Build a §3 checkpoint token-block from the CURRENT replayed state: {as_of_entry_hash,
    token_id, balances, chain_tip}. The block attests replay output — it never substitutes for it."""
    if not entries:
        raise TokenIntegrityBreach("cannot checkpoint an empty chain — nothing to attest")
    tip = entries[-1].get("hash")
    return {
        "token_id": token_id,
        "as_of_entry_hash": tip,
        "balances": {k: str(v) for k, v in balances(entries, token_id).items()},
        "chain_tip": tip,
    }


def verify_checkpoint(entries: list[dict], checkpoint_id: str) -> dict:
    """Verify a sealed token.checkpoint against FULL-GENESIS replay up to its as_of position.

    Recomputes every stated balance by fold over entries[0..as_of] and compares: any drift is a
    named, loud TokenIntegrityBreach — 'a drifted checkpoint cannot quietly stand' (§3). Replay-to-
    date will ride S3-G1's as_of parameter when built; until then this verifies full-genesis only.
    Returns {ok, token_id, as_of_entry_hash, balances} on agreement.
    """
    debit = next((e for e in entries
                  if e.get("type") == "debit" and e.get("id") == checkpoint_id), None)
    if debit is None or debit.get("kind") != CHECKPOINT_KIND:
        raise TokenIntegrityBreach(f"no token.checkpoint entry {checkpoint_id!r} on this chain")
    if not _proj.is_executed(entries, checkpoint_id):
        raise TokenIntegrityBreach(f"checkpoint {checkpoint_id!r} is not sealed — an unsealed "
                                   f"checkpoint attests nothing (§3: checkpoint = a SEALED entry)")
    token = debit.get("token") or {}
    token_id = token.get("token_id")
    as_of = token.get("as_of_entry_hash")
    idx = next((i for i, e in enumerate(entries) if e.get("hash") == as_of), None)
    if idx is None:
        raise TokenIntegrityBreach(f"checkpoint {checkpoint_id!r} cites as_of_entry_hash {as_of!r} "
                                   f"which is not on this chain — loud breach, not a quiet skip")
    replayed = balances(entries[: idx + 1], token_id)
    stated = {k: Decimal(str(v)) for k, v in (token.get("balances") or {}).items()}
    # Compare over the union of accounts (absent == zero) so a dropped or invented account is drift.
    drift = {}
    for account in set(replayed) | set(stated):
        r = replayed.get(account, Decimal("0"))
        s = stated.get(account, Decimal("0"))
        if r != s:
            drift[account] = {"stated": str(s), "replayed": str(r)}
    if drift:
        raise TokenIntegrityBreach(
            f"checkpoint {checkpoint_id!r} DRIFTS from full-genesis replay for {token_id!r}: {drift} "
            f"— a drifted checkpoint cannot quietly stand (§3)")
    return {"ok": True, "token_id": token_id, "as_of_entry_hash": as_of,
            "balances": {k: str(v) for k, v in replayed.items()}}
