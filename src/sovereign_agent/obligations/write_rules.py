"""Policy-at-the-write (S4-G1) — write_rules documents, the 6-predicate vocabulary, refusal records.

Spec: docs/specs/S4-G1_policy_at_the_write_v0.1.md. Design rule §1: the rule fires AT the write, or
it isn't a rule — every rule binds to the existing write points (open / approve / close) and its
only power is refusal with the rule cited. Rules constrain writes; they never author writes.

Module idiom mirrors quorum_guard / mandate_guard: pure, stateless, crypto-free, no ledger import
(projection + token_schema only — no cycle). Lives in obligations/ (not compliance/) because the
ledger's write points import it; pulling compliance/__init__ (-> compliance_engine) into the
ledger's import path would be a heavier, cycle-prone graph. The document SHAPE is the existing
policy-document shape extended with a `write_rules:` top-level key (legacy documents stay valid),
and load_write_policy accepts a PolicyLoader-loaded Policy object (duck-typed on .raw_content), a
dict, a YAML path, or a WritePolicy — so documents still travel the existing PolicyLoader path.

Enforcement semantics (§4, mirrors AH-1 exactly): first failing rule in DOCUMENT ORDER refuses;
the refusal is BOTH raised (WriteRefused — PermissionError family, the EconomicActionRefused
posture: loud, fail-closed, proposed entries left open) AND appended as a ledger fact (the §4
record: refused_at / write_point / rule_id / policy_id / policy_version / message / entry_ref).
Raise-and-record, never raise-only — the record of the "no" is as durable as any "yes" (TRUTH-2).

DECLARED-CONFIG-NEVER-CONSTANTS: every threshold / cap / floor lives in the policy document; the
only literals here are the vocabulary names and the POLICY-0 fallback the spec itself fixes (§5).
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

import yaml

from . import projection as _proj
from . import token_schema as _token_schema
from ._util import _now, _entry_id


class WritePolicyLoadError(ValueError):
    """A write_rules document refused to LOAD — fail-closed at load, not at first use (§2).

    Unknown predicate name, malformed args, empty applies_to, duplicate rule id, missing file:
    the document does not become governance. Mirrors the A4 unattested-card refusal (addendum).
    """


class WriteRefused(PermissionError):
    """Fail-closed refusal of a write, rule cited — the EconomicActionRefused posture (loud,
    PermissionError family, proposed entries left open on the chain). Always paired with an
    appended refusal record (§4): raise-and-record, never raise-only."""


@dataclass(frozen=True)
class Violation:
    """One rule's refusal verdict — everything the §4 refusal record and the raise must cite."""
    rule_id: str
    policy_id: str
    policy_version: str
    message: str


@dataclass(frozen=True)
class WriteRule:
    id: str
    applies_to: dict            # {"kind": glob} and/or {"classification": exact} — >=1 required
    predicate: str              # vocabulary name (§3)
    args: dict                  # parsed args (Decimals already exact)
    effect: str                 # "refuse" | "require_second_approver"
    message: str


@dataclass(frozen=True)
class WritePolicy:
    id: str
    version: str
    rules: tuple                # tuple[WriteRule, ...] in document order (§4: deterministic)
    token_registry: Optional[dict]   # optional S4-G2 registry riding the policy document
    document_sha256: str        # content hash over the canonical document (§6 attestation hook)


# predicate -> (write points it fires at, exact arg-key set). threshold_second_approver's §3 point
# is approve(); per the addendum it is NOT a third intercept — it acts as the quorum-floor raise
# stamped at open() (quorum_guard path) and is CITED at close() when the raised floor is unmet.
_PREDICATES = {
    "amount_ceiling":            (("open",), frozenset({"max"})),
    "supply_cap":                (("close",), frozenset({"cap"})),
    "require_evidence":          (("close",), frozenset({"floor"})),
    "require_gate":              (("approve",), frozenset({"gate"})),
    "forbid_class":              (("open",), frozenset({"class"})),
    "threshold_second_approver": (("open", "close"), frozenset({"above"})),
}
_EFFECTS = frozenset({"refuse", "require_second_approver"})
_E_ORDER = {"E0": 0, "E1": 1, "E2": 2}

# The §5 loud fallback: rule id fixed by the spec; message verbatim.
POLICY0_RULE_ID = "POLICY-0"
POLICY0_MESSAGE = "policy declared but not loadable — fail-closed"
PLACEHOLDER_VERSION = "PLACEHOLDER"


def document_sha256(document: dict) -> str:
    """Canonical content hash of a policy document — the §6 amendment-evidence / attestation hook."""
    return hashlib.sha256(json.dumps(document, sort_keys=True, default=str).encode()).hexdigest()


def _parse_decimal_arg(rule_id: str, name: str, raw) -> Decimal:
    if isinstance(raw, float):
        raise WritePolicyLoadError(f"rule {rule_id!r}: arg {name!r} is a float ({raw!r}) — declare "
                                   f"Decimal strings, never floats")
    try:
        d = Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise WritePolicyLoadError(f"rule {rule_id!r}: arg {name!r} = {raw!r} does not parse as a "
                                   f"Decimal") from exc
    if not d.is_finite():
        raise WritePolicyLoadError(f"rule {rule_id!r}: arg {name!r} = {raw!r} is not finite")
    return d


def _parse_applies_to(rule_id: str, raw: dict) -> dict:
    applies_to = raw.get("applies_to")
    if not isinstance(applies_to, dict) or not applies_to:
        raise WritePolicyLoadError(f"rule {rule_id!r}: empty/missing applies_to — a rule that "
                                   f"selects nothing is a load failure (§2)")
    unknown_sel = set(applies_to) - {"kind", "classification"}
    if unknown_sel:
        raise WritePolicyLoadError(f"rule {rule_id!r}: unknown applies_to selectors {sorted(unknown_sel)} "
                                   f"— v0.1 selects on kind and/or classification only")
    for sel, val in applies_to.items():
        if not val or not isinstance(val, str):
            raise WritePolicyLoadError(f"rule {rule_id!r}: applies_to.{sel} must be a non-empty string")
    return dict(applies_to)


def _parse_predicate_args(rule_id: str, name: str, got_args: dict) -> dict:
    """Per-predicate arg validation — malformed args refuse to load (§2)."""
    if name in ("amount_ceiling", "supply_cap", "threshold_second_approver"):
        key = next(iter(_PREDICATES[name][1]))
        return {key: _parse_decimal_arg(rule_id, key, got_args[key])}
    if name == "require_evidence":
        floor = got_args["floor"]
        if floor not in ("E1", "E2"):
            raise WritePolicyLoadError(f"rule {rule_id!r}: require_evidence floor must be E1|E2, "
                                       f"got {floor!r}")
        return {"floor": floor}
    if name == "require_gate":
        if got_args["gate"] != "human":
            raise WritePolicyLoadError(f"rule {rule_id!r}: require_gate v0.1 knows only gate: human, "
                                       f"got {got_args['gate']!r}")
        return {"gate": "human"}
    cls = got_args["class"]   # forbid_class — the only name left in the v0.1 vocabulary
    if not cls or not isinstance(cls, str):
        raise WritePolicyLoadError(f"rule {rule_id!r}: forbid_class class must be a non-empty string")
    return {"class": cls}


def _parse_rule(raw: dict) -> WriteRule:
    rule_id = raw.get("id")
    if not rule_id or not isinstance(rule_id, str):
        raise WritePolicyLoadError(f"a write_rule is missing its stable, citable id: {raw!r}")
    applies_to = _parse_applies_to(rule_id, raw)
    predicate = raw.get("predicate")
    if not isinstance(predicate, dict) or "name" not in predicate:
        raise WritePolicyLoadError(f"rule {rule_id!r}: predicate must be {{name: <vocab §3>, ...args}}")
    name = predicate["name"]
    if name not in _PREDICATES:
        raise WritePolicyLoadError(f"rule {rule_id!r}: unknown predicate {name!r} — v0.1 vocabulary "
                                   f"is {sorted(_PREDICATES)} (unknown => the document refuses to load)")
    got_args = {k: v for k, v in predicate.items() if k != "name"}
    if set(got_args) != _PREDICATES[name][1]:
        raise WritePolicyLoadError(f"rule {rule_id!r}: predicate {name!r} takes exactly args "
                                   f"{sorted(_PREDICATES[name][1])}, got {sorted(got_args)} — "
                                   f"malformed args refuse to load (§2)")
    args = _parse_predicate_args(rule_id, name, got_args)
    effect = raw.get("effect")
    if effect not in _EFFECTS:
        raise WritePolicyLoadError(f"rule {rule_id!r}: effect must be one of {sorted(_EFFECTS)} "
                                   f"(v0.1 has exactly two), got {effect!r}")
    # Effect/predicate pairing is fixed in v0.1 — a mismatch is ambiguous governance: refuse to load.
    if (name == "threshold_second_approver") != (effect == "require_second_approver"):
        raise WritePolicyLoadError(f"rule {rule_id!r}: predicate {name!r} pairs with effect "
                                   f"{'require_second_approver' if name == 'threshold_second_approver' else 'refuse'!r} "
                                   f"only, got {effect!r}")
    message = raw.get("message")
    if not message or not isinstance(message, str):
        raise WritePolicyLoadError(f"rule {rule_id!r}: message (the human sentence shown with the id) "
                                   f"is required")
    return WriteRule(id=rule_id, applies_to=applies_to, predicate=name, args=args,
                     effect=effect, message=message)


def _coerce_document(source) -> dict:
    """Accept a PolicyLoader Policy (duck-typed on .raw_content — the existing loader path), a
    dict document, or a YAML file path; return the document dict or refuse to load."""
    raw_content = getattr(source, "raw_content", None)   # PolicyLoader Policy object
    if isinstance(raw_content, dict):
        return raw_content
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise WritePolicyLoadError(f"write policy document not found: {path}")
        try:
            source = yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            raise WritePolicyLoadError(f"write policy document {path} is not valid YAML: {exc}") from exc
    if not isinstance(source, dict):
        raise WritePolicyLoadError(f"write policy document must be a mapping, got {type(source).__name__}")
    return source


def _document_head(document: dict) -> tuple[str, str]:
    """(id, version) — both required (§2/§6: versions are monotonic and citable)."""
    policy_id = document.get("id")
    if not policy_id or not isinstance(policy_id, str):
        raise WritePolicyLoadError(f"write policy document has no id: {document!r}")
    version = document.get("version")
    if version is None:
        raise WritePolicyLoadError(f"write policy {policy_id!r} has no version — versions are "
                                   f"monotonic and citable (§2/§6)")
    if isinstance(version, float):
        raise WritePolicyLoadError(f"write policy {policy_id!r}: version {version!r} parsed as a "
                                   f"float — quote it in the YAML (version: \"1.0\")")
    return policy_id, str(version)


def load_write_policy(source) -> WritePolicy:
    """Load a write_rules policy from: a WritePolicy (as-is) · a PolicyLoader Policy · a dict
    document · a YAML file path. Missing file, unparseable YAML, or any §2 violation =>
    WritePolicyLoadError (fail-closed at load, not at first use)."""
    if isinstance(source, WritePolicy):
        return source
    document = _coerce_document(source)
    policy_id, version = _document_head(document)
    raw_rules = document.get("write_rules") or []   # legacy documents (no write_rules key) stay valid
    if not isinstance(raw_rules, list):
        raise WritePolicyLoadError(f"write policy {policy_id!r}: write_rules must be a list")
    rules = tuple(_parse_rule(r) for r in raw_rules)
    seen: set = set()
    for rule in rules:
        if rule.id in seen:
            raise WritePolicyLoadError(f"write policy {policy_id!r}: duplicate rule id {rule.id!r} "
                                       f"— ids are unique per document (§2)")
        seen.add(rule.id)
    registry = document.get("token_registry")
    if registry is not None and not isinstance(registry, dict):
        raise WritePolicyLoadError(f"write policy {policy_id!r}: token_registry must be a mapping")
    return WritePolicy(id=policy_id, version=version, rules=rules,
                       token_registry=dict(registry) if registry else None,
                       document_sha256=document_sha256(document))


# ── active-policy fold (§6: amendment is a sealed event; as-of by replay) ────────────────────────

def active_policy(entries: list[dict], declared: Optional[WritePolicy]) -> Optional[WritePolicy]:
    """The policy IN FORCE = the declared document amended by the LAST SEALED policy.amend entry
    (fold over the chain — replay-only, never instance state). An amendment is effective only once
    its obligation is closed-executed (E2 + human gate enforced at the write points); a rejected or
    still-open amendment changes nothing. A sealed amendment whose embedded document no longer
    parses raises WritePolicyLoadError — the caller fail-closes (POLICY-0 posture)."""
    doc = None
    for e in entries:
        if e.get("type") == "debit" and e.get("kind") == "policy.amend" \
                and _proj.is_executed(entries, e.get("id")):
            doc = (e.get("policy_amendment") or {}).get("document")
    if doc is None:
        return declared
    return load_write_policy(doc)


# ── evaluation at the write points (§4: document order, first failing rule refuses) ─────────────

def entry_ctx(entry: dict) -> dict:
    """The evaluation context read off a (would-be) debit entry — committed data only."""
    return {"kind": entry.get("kind"), "classification": entry.get("classification"),
            "material": bool(entry.get("material")), "token": entry.get("token"),
            "lgp": entry.get("lgp"), "debit": entry}


def _matches(rule: WriteRule, ctx: dict) -> bool:
    """ALL listed applies_to conditions must match (§2). kind is a glob; classification is exact."""
    if "kind" in rule.applies_to:
        kind = ctx.get("kind")
        if not kind or not fnmatch.fnmatchcase(kind, rule.applies_to["kind"]):
            return False
    if "classification" in rule.applies_to:
        if ctx.get("classification") != rule.applies_to["classification"]:
            return False
    return True


def _amount(ctx: dict) -> Optional[Decimal]:
    """The entry's amount: token.amount for token legs, else the lgp economic_value attribution
    (B4's pre-schema seam). None => no readable amount (the caller refuses loudly, never skips)."""
    token = ctx.get("token") or {}
    raw = token.get("amount")
    if raw is None:
        raw = (ctx.get("lgp") or {}).get("economic_value")
    if raw is None:
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _violation(policy: WritePolicy, rule: WriteRule, detail: str) -> Violation:
    return Violation(rule_id=rule.id, policy_id=policy.id, policy_version=policy.version,
                     message=f"{rule.message} — {detail}" if detail else rule.message)


_NO_AMOUNT = "rule matched but the entry carries no readable amount (fail loud, never a silent pass)"


def _open_refusal(policy: WritePolicy, rule: WriteRule, ctx: dict) -> Optional[Violation]:
    """One refuse-effect open-point rule against the entry context — Violation or None."""
    if rule.predicate == "amount_ceiling":
        amount = _amount(ctx)
        if amount is None:
            return _violation(policy, rule, _NO_AMOUNT)
        if amount > rule.args["max"]:
            return _violation(policy, rule, f"amount {amount} > declared ceiling {rule.args['max']}")
    elif rule.predicate == "forbid_class":
        if ctx.get("classification") == rule.args["class"]:
            return _violation(policy, rule, f"class {rule.args['class']!r} is charter-forbidden at open")
    return None


def evaluate_open(policy: WritePolicy, ctx: dict):
    """Open-point rules. Returns (violation | None, raised_quorum_floor, floor_rule_id).
    require_second_approver never refuses at open — it raises the quorum floor (addendum: the
    quorum_guard path, no new gate code). First failing rule in document order wins (§4)."""
    floor, floor_rule = 1, None
    for rule in policy.rules:
        if "open" not in _PREDICATES[rule.predicate][0] or not _matches(rule, ctx):
            continue
        if rule.predicate == "threshold_second_approver":
            amount = _amount(ctx)
            if amount is None:
                return _violation(policy, rule, _NO_AMOUNT), floor, floor_rule
            if amount > rule.args["above"] and floor < 2:
                floor, floor_rule = 2, rule.id   # K4: quorum=2 when amount > threshold (§3)
            continue
        violation = _open_refusal(policy, rule, ctx)
        if violation is not None:
            return violation, floor, floor_rule
    return None, floor, floor_rule


def evaluate_close(policy: WritePolicy, ctx: dict, tier_value: str,
                   entries: list[dict], approved: bool) -> Optional[Violation]:
    """Close-point rules: supply_cap (replay INCLUDING the closing entry), require_evidence,
    and the threshold_second_approver citation when the raised floor is unmet. First failing
    rule in document order wins (§4)."""
    for rule in policy.rules:
        if "close" not in _PREDICATES[rule.predicate][0] or not _matches(rule, ctx):
            continue
        if rule.predicate == "supply_cap":
            debit = ctx.get("debit") or {}
            if not (ctx.get("token") or {}).get("token_id"):
                return _violation(policy, rule, "supply_cap rule matched a non-token entry — no "
                                                "supply to bound (fail loud, never a silent pass)")
            prospective = _token_schema.supply_including(entries, debit)
            if prospective > rule.args["cap"]:
                return _violation(policy, rule,
                                  f"sealing would put circulating supply at {prospective} > declared "
                                  f"cap {rule.args['cap']} (replay including the closing entry)")
        elif rule.predicate == "require_evidence":
            if _E_ORDER.get(tier_value, 0) < _E_ORDER[rule.args["floor"]]:
                return _violation(policy, rule, f"evidence tier {tier_value} is below the declared "
                                                f"floor {rule.args['floor']}")
        elif rule.predicate == "threshold_second_approver":
            amount = _amount(ctx)
            if amount is not None and amount > rule.args["above"] and not approved:
                return _violation(policy, rule,
                                  f"amount {amount} > {rule.args['above']} raises the approval floor "
                                  f"to 2 distinct principals (proposer excluded) — floor not met")
    return None


# ── the §4 refusal record + the §5 POLICY-0 fallback ─────────────────────────────────────────────

def refusal_record(violation: Violation, write_point: str, entry_ref: str, principal_id: str) -> dict:
    """The refusal as a LEDGER FACT — the same recorded-disposition pattern as AH-1's DENIED (§4).
    Appended to the hash chain by the caller; replay re-derives the same 'no' forever."""
    now = _now()
    return {
        "type": "refusal",
        "id": _entry_id(),
        "refused_at": now,
        "write_point": write_point,
        "rule_id": violation.rule_id,
        "policy_id": violation.policy_id,
        "policy_version": violation.policy_version,
        "message": violation.message,
        "entry_ref": entry_ref,
        "principal_id": principal_id,
        "timestamp": now,
    }


def policy0_violation(policy_ref: str, detail: Optional[str]) -> Violation:
    """The §5 loud fallback — a green light with no bulb is retired: a declared-but-unloadable
    policy refuses every material write with POLICY-0, never silently permits."""
    message = POLICY0_MESSAGE if not detail else f"{POLICY0_MESSAGE} ({detail})"
    return Violation(rule_id=POLICY0_RULE_ID, policy_id=policy_ref,
                     policy_version="UNLOADABLE", message=message)
