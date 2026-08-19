# -*- coding: utf-8 -*-
"""node_binding — the ONLY module in this app that touches the node.

∞Δ∞ Law: the Universal Sovereign Node IS the ERP. This app only DRIVES it. ∞Δ∞

Posture, enforced here and nowhere else:

  * **Library-direct.** Every call below is an in-process call into `sovereign_agent.*`.
    There is no HTTP client, no call to `breathline-node-api` on :8421, no daemon requirement,
    no bearer credential.
  * **No second ledger.** This app owns no store. Every durable write goes through
    `economy.income.attribute_income` (directly or via its contribution / tax-event composers),
    which appends to the node's own `ObjectRegistry`. Every read replays that registry. There is
    no app-side database, cache file, or config file — session state lives in memory and dies
    with the process.
  * **The fences are the module's, not ours.** `MONEY_PATH_BREACH_FIELDS`, the tax fence, and the
    human gate all live inside the functions we call. We do not re-implement them, and we do not
    route around them.
  * **No Port.** v0 never opens or sanctions a crossing. `port_ref` may be *recorded* as a
    reference to a directive the operator created elsewhere; recording a reference is not crossing.
  * **No statutory act.** A tax event is a RECORD. There is no file, pay, remit, form, or
    represent path anywhere in this app. On a tax event the module's own TAX-FENCE refuses such a
    field; on a plain income or contribution it does not, so this app narrows further and refuses
    the same vocabulary on EVERY act it submits (`STATUTORY_FENCE_FIELDS`). That narrowing is
    labelled as ours — it is not a claim about what the module refuses.

The one piece of app-side state is the `HumanApprovalGate` instance, which is in-memory by design
(the node's own gate is too). Pending approvals are session-scoped and are reported as such.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple

# --- the node ------------------------------------------------------------------------------------
from sovereign_agent.compliance.human_approval_gate import ApprovalRequest, HumanApprovalGate
from sovereign_agent.economy.compliance import (
    TAX_CATEGORIES,
    TAX_FENCE_BREACH_FIELDS,
    record_tax_event,
    reporting_package,
)
from sovereign_agent.economy.contribution import (
    CONTRIBUTION_CLASSES,
    SOURCE_DEFAULT_CLASS,
    record_contribution,
)
from sovereign_agent.economy.income import (
    IncomeRefused,
    attribute_income,
    verify_income,
)
from sovereign_agent.keystore.node_keystore import KeystoreError, load_node_key
from sovereign_agent.objects.manifest import cut_manifest
from sovereign_agent.objects.proofs import replay_root
from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.obligations import projection as obligation_projection
from sovereign_agent.obligations.evidence import EvidenceTier, classify_evidence
from sovereign_agent.obligations.ledger import AlreadyClosedError, ObligationLedger

APP_NAME = "USN ERP Operator Surface"
APP_VERSION = "0.1.0"

REGISTRY_FILENAME = "objects.ndjson"
LEDGER_FILENAME = "obligations.ndjson"
KEYFILE_SUFFIX = ".nodekey.json"
RECEIPT_LOG_FILENAME = "onboard_receipts.ndjson"
INCOME_KIND = "income"

#: Governance postures, expressed in the gate's own vocabulary. `requires_approval` returns False
#: for any mode other than "corporate_regulated" — so "sovereign" is genuinely the module's ungated
#: path, not a weakened gate.
MODE_SOVEREIGN = "live"
MODE_REGULATED = "corporate_regulated"

#: The three action classes this vertical performs. Under the regulated posture every one is
#: declared high-materiality, so the gate engages on all of them.
RECORD_ACTION_CLASSES = ("attribute_income", "record_contribution", "record_tax_event")

#: The obligation lifecycle acts this app drives. Every one is an existing `ObligationLedger`
#: method — no new engine, no new verb.
OBLIGATION_ACTION_CLASSES = ("obligation_open", "obligation_approve", "obligation_close",
                             "obligation_attest", "obligation_veto", "obligation_clear_veto")

ACTION_CLASSES = RECORD_ACTION_CLASSES + OBLIGATION_ACTION_CLASSES
REGULATED_POLICY = {"high_materiality_classes": list(ACTION_CLASSES)}

#: Classifications the ledger accepts. Free-form in the module; offered as a short list here so the
#: UI does not invent one.
CLASSIFICATIONS = ("C1", "C2", "C3")

#: Payload keys that `income_record` / `_tax_extra` / `_contribution_extra` generate themselves.
#: Anything else in a stored payload is operator-supplied `extra` and must be handed back to the
#: verifier as such, or the round-trip will not reproduce the record.
_DERIVED_KEYS = frozenset({
    "id", "earner", "work_ref", "amount", "unit", "port_ref",
    "tax_event", "tax_category", "reportable", "references_income",
})

#: A registry with nothing in it. Used only to label an empty node honestly.
EMPTY_MERKLE_ROOT = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

#: An app-level NARROWING, and named as one. The module's tax fence
#: (`TAX_FENCE_BREACH_FIELDS`) is applied by `_tax_extra`, so it guards tax events but NOT a plain
#: income or contribution record — a field like `file_return` on a plain income passes the module's
#: money-path fence untouched. This app therefore refuses statutory-act fields on EVERY act it
#: submits. It is a narrowing of what the app will pass through, never a claim that the module
#: refuses it, and it reuses the module's own vocabulary rather than inventing a second list.
STATUTORY_FENCE_FIELDS = frozenset(TAX_FENCE_BREACH_FIELDS)


class SurfaceError(Exception):
    """An operator-actionable failure. Carries text meant to be shown in the UI verbatim."""


class GateRequired(Exception):
    """The act is gated and no human disposition has been recorded. Carries the pending request id."""

    def __init__(self, req_id: str, action_class: str, summary: str):
        super().__init__(f"human approval required for {action_class}")
        self.req_id = req_id
        self.action_class = action_class
        self.summary = summary


def utc_now() -> str:
    """The single place this app stamps a time. Modules take `at` explicitly and never call now()
    themselves, so the stamp is always the operator's act time, recorded once."""
    return datetime.now(timezone.utc).isoformat()


def _abs(p: Optional[str]) -> Optional[str]:
    return os.path.abspath(os.path.expanduser(str(p))) if p else None


def _canonical(obj: Any) -> str:
    """Canonical JSON — sorted keys, no incidental whitespace. The basis of the export's determinism."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _d(obj: Any) -> Any:
    return asdict(obj) if is_dataclass(obj) and not isinstance(obj, type) else obj


# ==================================================================================================
# The binding
# ==================================================================================================

class NodeBinding:
    """One open node. Holds paths, the process gate, and nothing else.

    Deliberately holds no records: every read below replays the node's registry or ledger from disk,
    so the app cannot drift from the node and cannot become a second source of truth.
    """

    def __init__(self, keystore_dir: Optional[str], registry_root: Optional[str],
                 ledger_root: Optional[str], *, regulated: bool = True,
                 operator: str = "operator", mandate: Optional[str] = None):
        self.keystore_dir = _abs(keystore_dir)
        self.registry_root = _abs(registry_root)
        self.ledger_root = _abs(ledger_root)
        self.regulated = bool(regulated)
        self.operator = str(operator or "operator").strip() or "operator"
        self.mandate = (mandate or self.operator).strip() or self.operator
        self.gate = HumanApprovalGate(REGULATED_POLICY if self.regulated else {})
        #: req_id -> the pending act, so an approval can be replayed into the module call verbatim.
        self._staged: Dict[str, Dict[str, Any]] = {}
        #: req_id -> the recorded disposition, kept only so the UI can show what happened.
        self._disposed: Dict[str, Dict[str, Any]] = {}

        if not self.registry_root:
            raise SurfaceError(
                "No registry root configured. Set SUBSTRATE_STORAGE_ROOT, or enter the path when "
                "opening the node. This is where the node keeps objects.ndjson — its own store, the "
                "one this app writes through."
            )

    # -- classmethod ------------------------------------------------------------------------------
    @classmethod
    def from_env(cls, **overrides: Any) -> "NodeBinding":
        """Open from the environment, with per-field overrides from the UI. No config file is read
        or written — the app persists no settings of its own."""
        return cls(
            keystore_dir=overrides.get("keystore_dir") or os.environ.get("NODE_KEYSTORE_DIR"),
            registry_root=overrides.get("registry_root") or os.environ.get("SUBSTRATE_STORAGE_ROOT"),
            ledger_root=overrides.get("ledger_root") or os.environ.get("OBLIGATION_LEDGER_ROOT"),
            regulated=overrides.get("regulated", True),
            operator=overrides.get("operator") or os.environ.get("USN_OPERATOR") or "operator",
            mandate=overrides.get("mandate") or os.environ.get("USN_MANDATE"),
        )

    @property
    def mode(self) -> str:
        return MODE_REGULATED if self.regulated else MODE_SOVEREIGN

    # -- node handles -----------------------------------------------------------------------------
    def _registry(self) -> ObjectRegistry:
        """The node's own object registry. Constructing it creates objects.ndjson if the node has
        never written — that is the node's store coming into existence, not a store of ours."""
        os.makedirs(self.registry_root, exist_ok=True)
        return ObjectRegistry(self.registry_root)

    def _ledger(self) -> Optional[ObligationLedger]:
        """The node's obligation ledger for READS, if one exists. Never created by a read — an absent
        ledger is reported, not conjured. Reads touch no bytes (verified: opening for read creates
        no file)."""
        if not self.ledger_root:
            return None
        if not os.path.isfile(os.path.join(self.ledger_root, LEDGER_FILENAME)):
            return None
        return ObligationLedger(root=self.ledger_root)

    def _ledger_gate(self, disposition: Optional[Mapping[str, Any]]):
        """The ledger's `gate` seam, fed the operator's ACTUAL disposition.

        `ObligationLedger.approve` consults an injected callable and records its verdict on the
        chain; with no gate injected, AH-1 fail-closes a MATERIAL approval. The repo ships one
        adapter for this seam, `obligations.node_integration.make_gate` — but that one hardcodes
        `status="approved"` on the assumption that reaching `approve()` already implies an
        authenticated human. This app supplies its own adapter instead, for one reason: **it cannot
        mint an approval the operator did not give.** With no recorded disposition it returns a
        DENY, so a code path that reaches `approve()` without a human behind it fails closed rather
        than passing.

        This is using the documented seam, not adding a verb. The verdict handed back is the very
        `record_disposition` result the operator produced by clicking.
        """
        def gate(action: str, obligation: Mapping[str, Any]) -> Dict[str, Any]:
            if not disposition:
                return {"status": "denied", "real": False,
                        "reason": ("no human disposition was recorded for this act — this app never "
                                   "synthesises one, so the ledger fails closed")}
            return dict(disposition)
        return gate

    def _ledger_for_write(self, disposition: Optional[Mapping[str, Any]] = None) -> ObligationLedger:
        """The node's obligation ledger, wired to write. Creating it on first use is the node's own
        store coming into existence, exactly as the object registry does — not a store of ours."""
        if not self.ledger_root:
            raise SurfaceError(
                "No obligation ledger root configured. Set OBLIGATION_LEDGER_ROOT, or enter the path "
                "when opening the node. Obligations live in the node's own obligations.ndjson."
            )
        os.makedirs(self.ledger_root, exist_ok=True)
        return ObligationLedger(root=self.ledger_root, principal_id=self.operator,
                                gate=self._ledger_gate(disposition))

    # ============================================================================================
    # 1 · Open the node — status
    # ============================================================================================

    def status(self) -> Dict[str, Any]:
        """Everything the operator needs to trust what they are looking at, read from disk each
        call. Absent stores are reported with a reason rather than faked."""
        out: Dict[str, Any] = {
            "app": {"name": APP_NAME, "version": APP_VERSION,
                    "binding": "library-direct (sovereign_agent imported in-process)",
                    "second_ledger": False, "port_crossings": 0, "statutory_acts": 0},
            "operator": self.operator,
            "mandate": self.mandate,
            "governance": {
                "posture": "regulated · human-gated" if self.regulated else "sovereign · ungated",
                "mode": self.mode,
                "gated_action_classes": list(ACTION_CLASSES) if self.regulated else [],
                "note": (
                    "Every recording act passes HumanApprovalGate.requires_approval and is refused "
                    "until you approve it yourself."
                ) if self.regulated else (
                    "The module's own ungated path: HumanApprovalGate.requires_approval returns False "
                    "for any mode other than corporate_regulated. Switch to regulated to gate acts."
                ),
            },
            "paths": {"keystore_dir": self.keystore_dir, "registry_root": self.registry_root,
                      "ledger_root": self.ledger_root},
        }

        # identity — public material only
        ident: Dict[str, Any] = {"present": False}
        if self.keystore_dir and os.path.isdir(self.keystore_dir):
            ids = sorted(n[: -len(KEYFILE_SUFFIX)] for n in os.listdir(self.keystore_dir)
                         if n.endswith(KEYFILE_SUFFIX))
            if ids:
                try:
                    k = load_node_key(self.keystore_dir, ids[0])
                    ident = {"present": True, "node_id": k.node_id, "fingerprint": k.fingerprint,
                             "public_hex": k.public_hex, "created_at": k.created_at,
                             "sig_scheme": k.sig_scheme, "other_node_ids": ids[1:]}
                except KeystoreError as exc:
                    ident = {"present": False, "note": str(exc)}
            else:
                ident = {"present": False, "note": (
                    f"No *{KEYFILE_SUFFIX} in '{self.keystore_dir}'. This node has not been onboarded "
                    f"here. Run the onboard ceremony yourself — this app cannot mint a key.")}
        else:
            ident = {"present": False, "note": (
                "No keystore configured or the path does not exist. Identity is optional for "
                "recording, but without it there is no fingerprint to show and no receipt log to verify.")}
        out["identity"] = ident

        # receipt log
        rl: Dict[str, Any] = {"present": False, "count": 0}
        if self.keystore_dir:
            rp = os.path.join(self.keystore_dir, RECEIPT_LOG_FILENAME)
            rl["path"] = rp
            if os.path.isfile(rp):
                try:
                    rl = {"path": rp, "present": True, "count": len(self._read_ndjson(rp))}
                except SurfaceError as exc:
                    rl = {"path": rp, "present": False, "note": str(exc)}
        out["receipt_log"] = rl

        # registry
        log = os.path.join(self.registry_root, REGISTRY_FILENAME)
        if os.path.isfile(log):
            reg = self._registry()
            entries = reg.entries()
            stated, replayed = reg.population_root(), replay_root(reg)
            kinds: Dict[str, int] = {}
            for e in entries:
                kinds[str(e.get("kind"))] = kinds.get(str(e.get("kind")), 0) + 1
            income = [e for e in entries if e.get("kind") == INCOME_KIND]
            out["registry"] = {
                "present": True, "log_file": log,
                "entries": len(entries), "objects": len(reg.current()),
                "population_root": stated, "replay_root": replayed,
                "roots_match": stated == replayed,
                "empty": stated == EMPTY_MERKLE_ROOT,
                "kinds": kinds,
                "income_events": len(income),
                "tax_events": sum(1 for e in income if (e.get("payload") or {}).get("tax_event")),
                "contributions": sum(1 for e in income
                                     if (e.get("payload") or {}).get("contribution_class")),
            }
        else:
            out["registry"] = {"present": False, "log_file": log, "entries": 0, "objects": 0,
                               "income_events": 0, "tax_events": 0, "contributions": 0,
                               "note": (f"No {REGISTRY_FILENAME} yet at '{self.registry_root}'. "
                                        f"It is created by the node's own store on your first record.")}

        # obligation ledger — read-only in this vertical
        led = self._ledger()
        if led is None:
            out["obligations"] = {"present": False, "note": (
                "No obligation ledger configured or none exists at that path. This vertical opens no "
                "obligations; the panel is read-only and stays empty until the node has one.")}
        else:
            mf = led.manifest()
            out["obligations"] = {
                "present": True, "ledger_file": mf.get("file"),
                "chain_valid": led.verify_chain(), "chain_entries": mf.get("chain_entries"),
                "by_status": led.by_status(), "by_owner": led.by_owner(),
                "open_count": len(led.open_obligations()),
                "last_entry": {"type": mf.get("last_type"), "ref": mf.get("last_ref"),
                               "at": mf.get("last_ts"), "hash": mf.get("last_hash")},
            }

        out["gate"] = self.gate_state()
        return out

    @staticmethod
    def _read_ndjson(path: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise SurfaceError(
                        f"Malformed NDJSON at {path}:{n} — {exc}. The log is corrupt; this app "
                        f"refuses to guess at its contents."
                    ) from exc
        return rows

    # ============================================================================================
    # 4 · The human gate
    # ============================================================================================

    def gate_state(self) -> Dict[str, Any]:
        """Pending and recently disposed approvals. In-memory and session-scoped by design — the
        node's own gate is too — and labelled as such so nobody mistakes it for durable record."""
        pending = []
        for req_id, req in self.gate.get_pending().items():
            staged = self._staged.get(req_id, {})
            pending.append({
                "req_id": req_id, "action_class": req.action_class,
                "principal_id": req.principal_id, "risk_level": req.risk_level,
                "rationale": req.rationale, "required_approvers": list(req.required_approvers),
                "summary": staged.get("summary", req.rationale),
            })
        return {
            "engaged": self.regulated,
            "pending": sorted(pending, key=lambda p: p["req_id"]),
            "pending_count": len(pending),
            "disposed": [dict(d) for d in list(self._disposed.values())[-10:]],
            "durable": False,
            "note": ("Pending approvals live in this process only and are lost on restart. Nothing is "
                     "written to the node until you approve — a denial writes nothing at all."),
        }

    def _requires_gate(self, action_class: str) -> bool:
        return bool(self.gate.requires_approval(action_class, {}, self.mode))

    def _stage(self, action_class: str, summary: str, call: Dict[str, Any]) -> str:
        """Open a real approval request and hold the act until a human disposes of it. Uses
        `request_approval` — never `simulate_approval`, which the repo marks TEST-ONLY."""
        req = ApprovalRequest(
            action_class=action_class, role_id="usn_erp_surface",
            principal_id=self.operator, risk_level="material",
            rationale=summary, required_approvers=[self.operator],
        )
        req_id = self.gate.request_approval(req)
        self._staged[req_id] = {"action_class": action_class, "summary": summary, "call": call}
        return req_id

    def dispose(self, req_id: str, approve: bool, *, approver: Optional[str] = None,
                reason: str = "") -> Dict[str, Any]:
        """Record a REAL human disposition and, on approval, perform the held act.

        There is no auto-approve path in this app: `dispose` is only ever reached from an explicit
        operator click, and a denial performs no write of any kind.
        """
        staged = self._staged.get(req_id)
        if staged is None:
            raise SurfaceError(
                f"No pending approval '{req_id}'. It may have been disposed already, or the app was "
                f"restarted — pending approvals are session-scoped and nothing was written."
            )
        who = (approver or self.operator).strip() or self.operator
        disposition = self.gate.record_disposition(
            req_id, status="approved" if approve else "denied", approver=who, reason=reason)
        self._staged.pop(req_id, None)

        record: Dict[str, Any] = {
            "req_id": req_id, "action_class": staged["action_class"], "summary": staged["summary"],
            "status": disposition.get("status"), "approver": disposition.get("approver"),
            "at": disposition.get("timestamp"), "real": disposition.get("real", False),
            "reason": reason or None, "receipt": None,
        }
        if not approve:
            record["note"] = "Refused. Nothing was written to the node — the refusal is the act."
            self._disposed[req_id] = record
            return record

        # The operator's real, recorded disposition is what the ledger's gate seam receives — the
        # app never manufactures one. For an economy act it rides as approver + approval_ref; for an
        # obligation act it IS the gate verdict the chain records.
        receipt = self._perform(staged["call"], approver=who, approval_ref=req_id,
                                disposition=dict(disposition, req_id=req_id))
        record["receipt"] = receipt
        record["note"] = "Approved by you. The act was then performed through the node's own module."
        self._disposed[req_id] = record
        return record

    # ============================================================================================
    # 2 & 3 · Recording acts — every one goes through the module that owns the fence
    # ============================================================================================

    #: Every act this app can perform, mapped to the module method that owns it. There is no other
    #: write path, and nothing here is a verb the node does not already expose.
    _ECONOMY_ACTS = ("income", "contribution", "tax_event")
    _OBLIGATION_ACTS = ("obl_open", "obl_approve", "obl_close", "obl_attest", "obl_veto",
                        "obl_clear_veto")

    def _perform(self, call: Mapping[str, Any], *, approver: Optional[str] = None,
                 approval_ref: Optional[str] = None,
                 disposition: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        """Dispatch a staged (or ungated) act to its module. This is the ONLY place this app writes."""
        kind = call["kind"]
        kw = dict(call["kwargs"])

        if kind in self._ECONOMY_ACTS:
            kw.update(registry=self._registry(), gate=self.gate, mode=self.mode,
                      approver=approver, approval_ref=approval_ref)
            try:
                if kind == "income":
                    return attribute_income(**kw)
                if kind == "contribution":
                    return record_contribution(**kw)
                return record_tax_event(**kw)
            except IncomeRefused as exc:
                raise SurfaceError(f"The node refused this record: {exc}") from exc

        if kind in self._OBLIGATION_ACTS:
            return self._perform_obligation(kind, kw, disposition=disposition)

        raise SurfaceError(f"Unknown act '{kind}'.")

    def _perform_obligation(self, kind: str, kw: Dict[str, Any],
                            *, disposition: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
        """Every obligation act, through the ledger's own method. The ledger owns the rules — AH-1,
        the evidence floor, the attestation and veto guards — and this app surfaces its refusals
        verbatim rather than pre-empting or softening them."""
        led = self._ledger_for_write(disposition)
        try:
            if kind == "obl_open":
                return led.open(**kw)
            if kind == "obl_approve":
                return led.approve(kw["obligation_id"], approved_by=self.operator,
                                   rationale=kw.get("rationale", ""))
            if kind == "obl_close":
                return led.close(kw["obligation_id"], evidence=kw["evidence"],
                                 require_e1=bool(kw.get("require_e1", True)),
                                 rejected=bool(kw.get("rejected", False)),
                                 closed_by=self.operator, method=kw.get("method") or None)
            if kind == "obl_attest":
                return led.attest(kw["obligation_id"], role=kw["role"], attested_by=self.operator)
            if kind == "obl_veto":
                return led.veto(kw["obligation_id"], role=kw["role"], reason=kw["reason"],
                                vetoed_by=self.operator)
            if kind == "obl_clear_veto":
                return led.clear_veto(kw["obligation_id"], role=kw["role"], cleared_by=self.operator)
        except AlreadyClosedError as exc:
            raise SurfaceError(f"That obligation is already closed: {exc}") from exc
        except KeyError as exc:
            raise SurfaceError(f"No such obligation on this ledger: {exc}") from exc
        except PermissionError as exc:
            # The ledger's own fail-closed guards: AH-1, the breath-gate-before-execute rule, a
            # standing veto, or missing attestation. Surfaced as the ledger wrote it.
            raise SurfaceError(f"The ledger refused this act: {exc}") from exc
        except ValueError as exc:
            # Evidence floor (E0), an unresolvable path-like reference, or a missing veto reason.
            raise SurfaceError(f"The ledger refused this act: {exc}") from exc
        raise SurfaceError(f"Unknown obligation act '{kind}'.")

    def _fence_extra(self, extra: Optional[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
        """App-level narrowing: refuse a statutory-act field on ANY act, not just a tax event.

        The module's own tax fence only runs inside `_tax_extra`, so a plain income record would
        otherwise accept a field like `file_return`. This app declines to pass one through. It
        narrows what the app submits; it does not weaken or re-implement any module fence.
        """
        if not extra:
            return None
        for k in extra:
            if str(k).lower() in STATUTORY_FENCE_FIELDS:
                raise SurfaceError(
                    f"This app refuses the field '{k}' on any record. Filing, paying, remitting, "
                    f"forming an entity and representing you are your own statutory acts — never the "
                    f"node's, and never this app's. Record the event; do the act yourself."
                )
        return dict(extra)

    def _guard_object_collision(self, work_ref: str, wanted: str) -> None:
        """Refuse to shadow an existing object with a different kind of event.

        Object identity is `IncomeEvent:<earner>:<work_ref>`, so a tax note filed under the same
        work_ref as an earning becomes a NEW VERSION of that earning rather than its own record.
        Nothing is lost — both versions stay in the chain — but the current state would read as the
        tax note and quietly shadow the income. Better to say so than to let it happen silently.
        """
        oid = f"IncomeEvent:{self.operator}:{work_ref}"
        for e in self._income_entries():
            if e.get("object_id") != oid:
                continue
            p = dict(e.get("payload") or {})
            existing = "tax note" if p.get("tax_event") else (
                "contribution" if p.get("contribution_class") else "earning")
            if existing != wanted:
                raise SurfaceError(
                    f"A {existing} is already recorded under the reference '{work_ref}'. Recording a "
                    f"{wanted} under the same reference would append a new version of that same "
                    f"object and shadow it. Give this one its own reference — e.g. "
                    f"'tax:{work_ref}' — and use 'references income' to link them."
                )

    def _submit(self, kind: str, action_class: str, summary: str,
                kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Either stage for approval or perform now — decided by the gate, never by us."""
        call = {"kind": kind, "kwargs": kwargs}
        if self._requires_gate(action_class):
            req_id = self._stage(action_class, summary, call)
            return {"gated": True, "req_id": req_id, "action_class": action_class,
                    "summary": summary, "receipt": None,
                    "note": ("Held at the gate. Nothing has been written. Approve it yourself to "
                             "record it, or deny it and nothing happens.")}
        # Ungated (sovereign posture): the operator's click IS the disposition, so it is minted as a
        # real one — a named approver and a real UTC timestamp — and handed to the ledger's gate.
        # Not an auto-approval: nothing reaches here without an explicit act by the operator.
        receipt = self._perform(call, disposition=self._click_disposition(action_class, summary))
        return {"gated": False, "req_id": None, "action_class": action_class, "summary": summary,
                "receipt": receipt, "note": "Recorded through the node's own module."}

    def _click_disposition(self, action_class: str, summary: str) -> Dict[str, Any]:
        """Mint a REAL disposition for an ungated act — the operator's own click, on their own iron,
        recorded with `record_disposition` (never `simulate_approval`, which the repo marks
        TEST-ONLY). Used only for the ledger's gate seam, which requires a verdict to exist."""
        req = ApprovalRequest(action_class=action_class, role_id="usn_erp_surface",
                              principal_id=self.operator, risk_level="operator_click",
                              rationale=summary, required_approvers=[self.operator])
        req_id = self.gate.request_approval(req)
        res = self.gate.record_disposition(req_id, status="approved", approver=self.operator,
                                           reason="operator acted directly (sovereign posture)")
        return dict(res, req_id=req_id)

    def record_income(self, *, work_ref: str, amount: Optional[float] = None,
                      unit: str = "credits", port_ref: Optional[str] = None,
                      extra: Optional[Mapping[str, Any]] = None,
                      at: Optional[str] = None) -> Dict[str, Any]:
        """Record an earning as a governed object the operator owns.

        The amount is an *attribution figure*, not a held balance: the node records that value was
        earned, it never holds or moves it. `port_ref` records a reference to a Port directive the
        operator created elsewhere — recording a reference is not crossing.
        """
        extra = self._fence_extra(extra)
        self._guard_object_collision(work_ref, "earning")
        return self._submit("income", "attribute_income",
                            f"income · {work_ref}" + (f" · {amount} {unit}" if amount is not None else ""),
                            {"earner": self.operator, "work_ref": work_ref, "mandate": self.mandate,
                             "author": self.operator, "source_ref": "usn_erp_surface",
                             "at": at or utc_now(), "amount": amount, "unit": unit,
                             "port_ref": port_ref or None, "extra": dict(extra or {}) or None})

    def record_contribution_event(self, *, source: str, work_ref: str,
                                  contribution_class: Optional[str] = None,
                                  amount: Optional[float] = None, unit: str = "credits",
                                  port_ref: Optional[str] = None,
                                  extra: Optional[Mapping[str, Any]] = None,
                                  at: Optional[str] = None) -> Dict[str, Any]:
        """Record a concrete contribution — proof-graded by its class (computed / metered /
        attested / hybrid). Composes the same income surface; the class and source ride as
        attribution fields."""
        cc = (contribution_class or SOURCE_DEFAULT_CLASS.get(source, "attested")).strip().lower()
        extra = self._fence_extra(extra)
        self._guard_object_collision(work_ref, "contribution")
        return self._submit("contribution", "record_contribution",
                            f"contribution · {source} · {work_ref} · grade {cc}",
                            {"earner": self.operator, "source": source, "work_ref": work_ref,
                             "contribution_class": cc, "mandate": self.mandate,
                             "author": self.operator, "source_ref": "usn_erp_surface",
                             "at": at or utc_now(), "amount": amount, "unit": unit,
                             "port_ref": port_ref or None, "extra": dict(extra or {}) or None})

    def record_tax_note(self, *, work_ref: str, category: str,
                        references_income: Optional[str] = None,
                        amount: Optional[float] = None, unit: str = "credits",
                        extra: Optional[Mapping[str, Any]] = None,
                        at: Optional[str] = None) -> Dict[str, Any]:
        """Record a tax event as a RECORD ONLY.

        This app has no filing, paying, remitting, entity-formation or representation path, and
        cannot acquire one: `_tax_extra` refuses any such field outright (the TAX-FENCE). Filing and
        paying are the principal's own statutory acts — the node records the category and nothing
        more. Because the record carries no statutory-act field, a later green verify is also proof
        the node filed nothing.
        """
        cat = str(category).strip().lower()
        if cat not in TAX_CATEGORIES:
            raise SurfaceError(
                f"Unknown income category '{category}'. Choose one of {sorted(TAX_CATEGORIES)}. "
                f"The node records the category; you or your accountant map it to statutory law."
            )
        extra = self._fence_extra(extra)
        self._guard_object_collision(work_ref, "tax note")
        return self._submit("tax_event", "record_tax_event",
                            f"tax note · {cat} · {work_ref}",
                            {"principal": self.operator, "work_ref": work_ref, "category": cat,
                             "references_income": references_income or None,
                             "mandate": self.mandate, "author": self.operator,
                             "source_ref": "usn_erp_surface", "at": at or utc_now(),
                             "amount": amount, "unit": unit,
                             "extra": dict(extra or {}) or None})

    # ============================================================================================
    # 7 · Obligations — the node's own lifecycle, driven
    # ============================================================================================
    #
    # The obligation ledger is an append-only, hash-chained NDJSON file the node owns. This app
    # opens, approves and closes through `ObligationLedger`'s own methods and reads by replaying the
    # same file. There is no app-side obligation cache: the panel below and the write path above
    # read and write the one set of bytes, so they cannot disagree.

    def obligation_open(self, *, title: str, intent: Optional[str] = None,
                        classification: str = "C2", ref: Optional[str] = None,
                        material: bool = False, next_gate: Optional[str] = None,
                        requires_attestation: Optional[List[str]] = None,
                        mandate: Optional[str] = None) -> Dict[str, Any]:
        """Open an obligation — a draft action-proposal (a `debit` on the chain).

        `material=True` is the consequential setting: a material obligation cannot be closed until it
        has cleared the breath-gate, and the ledger fail-closes any attempt to approve one without a
        human gate behind it (AH-1). Leave it off for routine work.
        """
        if not str(title).strip():
            raise SurfaceError("An obligation needs a title — what is being undertaken.")
        cls = str(classification or "C2").strip().upper()
        if cls not in CLASSIFICATIONS:
            raise SurfaceError(f"Classification must be one of {list(CLASSIFICATIONS)}.")
        roles = [r.strip() for r in (requires_attestation or []) if str(r).strip()]
        return self._submit(
            "obl_open", "obligation_open",
            f"open obligation · {title}" + (" · MATERIAL" if material else ""),
            {"title": str(title).strip(), "owner": self.operator, "classification": cls,
             "intent": (intent or None), "ref": (ref or None), "material": bool(material),
             "next_gate": (next_gate or None),
             "requires_attestation": roles or None,
             "mandate": (mandate or None)})

    def obligation_approve(self, obligation_id: str, *, rationale: str = "") -> Dict[str, Any]:
        """Approve a draft obligation through the breath-gate.

        The disposition recorded on the chain is the one you gave — this app has no path that
        approves on your behalf, and the ledger's gate seam fails closed without a recorded verdict.
        """
        ob = self._obligation(obligation_id)
        return self._submit("obl_approve", "obligation_approve",
                            f"approve obligation · {ob.get('title') or obligation_id}",
                            {"obligation_id": obligation_id, "rationale": rationale or ""})

    def obligation_close(self, obligation_id: str, *, evidence: str, rejected: bool = False,
                         require_e1: bool = True, method: Optional[str] = None) -> Dict[str, Any]:
        """Close an obligation with evidence (a `credit` and a minted receipt), or record a refusal.

        The ledger's evidence floor applies: claim-only text (E0) will not close it — give an
        artifact pointer, a URL, a hash or a receipt id (E1+). A refusal (`rejected=True`) is exempt
        from both the evidence floor's intent and the breath-gate: saying no needs no gate.
        """
        ob = self._obligation(obligation_id)
        if not str(evidence).strip():
            raise SurfaceError("Closing needs evidence — what shows this was done (or why it was refused).")
        tier = classify_evidence(evidence)
        if require_e1 and not rejected and tier == EvidenceTier.E0_CLAIM:
            raise SurfaceError(
                f"That evidence reads as claim-only (tier E0) and will not close an obligation. Give "
                f"something checkable: a file path, a URL, a hash, or a receipt id. "
                f"For example: 'emailed 2026-08-19 · receipt_id rcpt_9f3a2b1c'."
            )
        verb = "reject" if rejected else "close"
        return self._submit("obl_close", "obligation_close",
                            f"{verb} obligation · {ob.get('title') or obligation_id} · evidence {tier.value}",
                            {"obligation_id": obligation_id, "evidence": str(evidence).strip(),
                             "rejected": bool(rejected), "require_e1": bool(require_e1),
                             "method": method or None})

    def obligation_attest(self, obligation_id: str, *, role: str) -> Dict[str, Any]:
        """Attest as one of the roles a joint-attestation obligation requires."""
        ob = self._obligation(obligation_id)
        if not str(role).strip():
            raise SurfaceError("Attesting needs the role you are attesting as.")
        return self._submit("obl_attest", "obligation_attest",
                            f"attest as {role} · {ob.get('title') or obligation_id}",
                            {"obligation_id": obligation_id, "role": str(role).strip()})

    def obligation_veto(self, obligation_id: str, *, role: str, reason: str) -> Dict[str, Any]:
        """Stand a veto against an obligation. Default-deny while it stands: it cannot execute."""
        ob = self._obligation(obligation_id)
        if not str(reason).strip():
            raise SurfaceError("A veto requires a reason — it is recorded loudly, on the chain.")
        return self._submit("obl_veto", "obligation_veto",
                            f"veto as {role} · {ob.get('title') or obligation_id}",
                            {"obligation_id": obligation_id, "role": str(role).strip(),
                             "reason": str(reason).strip()})

    def obligation_clear_veto(self, obligation_id: str, *, role: str) -> Dict[str, Any]:
        """Withdraw a veto — the vetoing role stands down. The chain keeps both acts."""
        ob = self._obligation(obligation_id)
        return self._submit("obl_clear_veto", "obligation_clear_veto",
                            f"clear veto as {role} · {ob.get('title') or obligation_id}",
                            {"obligation_id": obligation_id, "role": str(role).strip()})

    # -- obligation reads -------------------------------------------------------------------------

    def _obligation(self, obligation_id: str) -> Dict[str, Any]:
        """Find one obligation by replaying the ledger. Raises with the ids that do exist."""
        led = self._ledger()
        if led is None:
            raise SurfaceError(
                "There is no obligation ledger at the configured path yet. Open one first — the "
                "node's own store is created on your first obligation."
            )
        state = led.replay()
        for ob in list(state.get("open", [])) + list(state.get("closed", [])):
            if ob.get("id") == obligation_id:
                return ob
        known = [o.get("id") for o in list(state.get("open", []))][:5]
        raise SurfaceError(
            f"No obligation '{obligation_id}' on this ledger. Open ones include: "
            f"{', '.join(known) if known else '(none)'}."
        )

    def obligations(self, *, only: str = "all", limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """The obligations panel — replayed from the node's ledger on every call.

        `chain_valid` is the load-bearing field. If it reads false the append-only chain has been
        altered and every count beneath it should be treated as unreliable.
        """
        led = self._ledger()
        if led is None:
            return {"present": False, "chain_valid": None, "by_status": {"open": 0, "closed": 0, "total": 0},
                    "total": 0, "count": 0, "offset": offset, "has_more": False, "items": [],
                    "note": (f"No obligation ledger yet at "
                             f"'{self.ledger_root or '(no path configured)'}'. It is created by the "
                             f"node's own store when you open your first obligation.")}

        state = led.replay()
        # `iter_entries` is the ledger's public read-gateway over the raw chain, and `projection` is
        # its public replay module — so the panel derives status the same way the write path does,
        # from committed entries, with no private method and no app-side interpretation.
        entries = list(led.iter_entries())
        closed_ids = {o.get("id") for o in state.get("closed", [])}
        rows: List[Dict[str, Any]] = []
        for ob in list(state.get("open", [])) + list(state.get("closed", [])):
            oid = ob.get("id")
            is_closed = oid in closed_ids
            approved = obligation_projection.is_approved(entries, oid)
            status = "closed" if is_closed else ("approved" if approved else "draft")
            if only != "all" and only != ("closed" if is_closed else "open"):
                continue
            att = led.attestation_status(oid) if ob.get("requires_attestation") else None
            rows.append({
                "id": oid, "title": ob.get("title"), "owner": ob.get("owner"),
                "classification": ob.get("classification"), "intent": ob.get("intent"),
                "ref": ob.get("ref"), "material": bool(ob.get("material")),
                "status": status, "closed": is_closed,
                "approved": bool(ob.get("approved")) or status in ("approved", "closed"),
                "approved_by": ob.get("approved_by"),
                "next_gate": ob.get("next_gate"), "mandate": ob.get("mandate"),
                "requires_attestation": ob.get("requires_attestation"),
                "attestation": att,
                "opened_at": ob.get("timestamp"),
                "chain_hash": ob.get("hash"), "prev_hash": ob.get("prev_hash"),
                "can_approve": (not is_closed) and status == "draft",
                "can_close": not is_closed,
            })
        rows.sort(key=lambda r: str(r.get("opened_at") or ""), reverse=True)

        # the terminal acts, read back off the chain so the panel shows what was actually recorded
        terminal: Dict[str, Dict[str, Any]] = {}
        for e in entries:
            if e.get("type") == "credit":
                terminal[str(e.get("closes"))] = {
                    "evidence": e.get("evidence"), "evidence_tier": e.get("evidence_tier"),
                    "closed_by": e.get("closed_by"), "at": e.get("timestamp"),
                    "receipt_id": (e.get("receipt") or {}).get("receipt_id"),
                    "payload_hash": (e.get("receipt") or {}).get("payload_hash")}
        for r in rows:
            r["closure"] = terminal.get(r["id"])

        mf = led.manifest()
        window = rows[offset: offset + limit]
        return {
            "present": True, "ledger_file": mf.get("file"),
            "chain_valid": led.verify_chain(), "chain_entries": mf.get("chain_entries"),
            "by_status": led.by_status(), "by_owner": led.by_owner(),
            "last_entry": {"type": mf.get("last_type"), "ref": mf.get("last_ref"),
                           "at": mf.get("last_ts"), "hash": mf.get("last_hash")},
            "total": len(rows), "count": len(window), "offset": offset,
            "has_more": offset + len(window) < len(rows), "items": window,
        }

    # ============================================================================================
    # 6 · Reads — replayed from the node every time
    # ============================================================================================

    def _income_entries(self) -> List[Dict[str, Any]]:
        if not os.path.isfile(os.path.join(self.registry_root, REGISTRY_FILENAME)):
            return []
        return [e for e in self._registry().entries() if e.get("kind") == INCOME_KIND]

    @staticmethod
    def _verify_args(entry: Mapping[str, Any]) -> Dict[str, Any]:
        """Reconstruct the verifier's inputs from a stored payload, so `verify_income` re-derives the
        record and re-hashes the receipt. Operator-supplied `extra` is whatever the module did not
        generate itself."""
        p = dict(entry.get("payload") or {})
        extra = {k: v for k, v in p.items() if k not in _DERIVED_KEYS}
        if p.get("tax_event"):
            for k in ("tax_event", "tax_category", "reportable", "references_income"):
                extra.pop(k, None)
        return {"earner": p.get("earner", ""), "work_ref": p.get("work_ref", ""),
                "amount": p.get("amount"), "unit": p.get("unit", "credits"),
                "port_ref": p.get("port_ref"), "extra": extra or None,
                "category": p.get("tax_category"), "references_income": p.get("references_income")}

    def _verify_entry(self, entry: Mapping[str, Any]) -> Dict[str, Any]:
        """Verify one recorded event against its own receipt, using the module's verifier."""
        a = self._verify_args(entry)
        if a["earner"] != self.operator:
            return {"verified": False,
                    "reason": f"recorded for '{a['earner']}', not the open operator '{self.operator}'"}
        extra = dict(a["extra"] or {})
        if a["category"]:
            from sovereign_agent.economy.compliance import _tax_extra  # noqa: PLC0415
            extra = _tax_extra(a["category"], a["references_income"], a["extra"])
        st = verify_income(entry, a["earner"], a["work_ref"], amount=a["amount"], unit=a["unit"],
                           port_ref=a["port_ref"], extra=extra or None)
        return {"verified": bool(st.provisioned), "reason": st.reason}

    def events(self, *, only: str = "all", limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """The operator's recorded events, newest first, each verified against its own receipt."""
        rows = []
        for e in self._income_entries():
            p = dict(e.get("payload") or {})
            is_tax = bool(p.get("tax_event"))
            is_con = bool(p.get("contribution_class"))
            etype = "tax" if is_tax else ("contribution" if is_con else "income")
            if only != "all" and only != etype:
                continue
            rows.append({
                "type": etype,
                "object_id": e.get("object_id"), "seq": e.get("seq"), "at": e.get("at"),
                "work_ref": p.get("work_ref"), "amount": p.get("amount"), "unit": p.get("unit"),
                "port_ref": p.get("port_ref"),
                "tax_category": p.get("tax_category"),
                "references_income": p.get("references_income"),
                "contribution_class": p.get("contribution_class"), "source": p.get("source"),
                "author": e.get("author"), "mandate": e.get("mandate"),
                "approver": e.get("approver"), "approval_ref": e.get("approval_ref"),
                "version_hash": e.get("version_hash"), "prev_hash": e.get("prev_hash"),
                "check": self._verify_entry(e),
            })
        rows.reverse()
        window = rows[offset: offset + limit]
        return {"total": len(rows), "count": len(window), "offset": offset,
                "has_more": offset + len(window) < len(rows), "items": window}

    def verify_object(self, object_id: str) -> Dict[str, Any]:
        """Verify one recorded event by object id — the operator's own weakest-party check."""
        for e in self._income_entries():
            if e.get("object_id") == object_id:
                res = self._verify_entry(e)
                res.update(object_id=object_id, version_hash=e.get("version_hash"),
                           at=e.get("at"), approver=e.get("approver"))
                return res
        raise SurfaceError(f"No recorded event with object id '{object_id}'.")

    # ============================================================================================
    # 5 · The portable package — derived from node state, deterministic
    # ============================================================================================

    def export_package(self) -> Tuple[Dict[str, Any], str]:
        """Build the operator's portable compliance package and return `(package, sha256)`.

        Determinism is a property of the design, not a promise: every field below is derived from
        the node's own state, and the manifest is cut `as_of` the newest recorded entry's own
        timestamp rather than the moment of export. Re-running against unchanged state therefore
        reproduces the package byte for byte — which is what makes the hash worth printing.

        It holds no statutory authority and files nothing. It is a bundle you hand to your
        accountant, not a filing the node makes.
        """
        entries = self._income_entries()
        tax_items, tax_rows = [], []
        for e in entries:
            p = dict(e.get("payload") or {})
            if not p.get("tax_event"):
                continue
            a = self._verify_args(e)
            tax_items.append({"receipt": e, "work_ref": a["work_ref"], "category": a["category"],
                              "references_income": a["references_income"], "amount": a["amount"],
                              "unit": a["unit"], "port_ref": a["port_ref"], "extra": a["extra"]})
            tax_rows.append({"object_id": e.get("object_id"), "at": e.get("at"),
                             "work_ref": a["work_ref"], "category": a["category"],
                             "references_income": a["references_income"],
                             "amount": a["amount"], "unit": a["unit"],
                             "approver": e.get("approver"), "approval_ref": e.get("approval_ref"),
                             "version_hash": e.get("version_hash")})

        pkg = _d(reporting_package(self.operator, tax_items)) if tax_items else {
            "principal": self.operator, "complete": False, "event_count": 0,
            "by_category": {c: 0 for c in sorted(TAX_CATEGORIES)},
            "reason": "no tax events recorded yet — nothing to report, and nothing filed",
        }

        reg_present = os.path.isfile(os.path.join(self.registry_root, REGISTRY_FILENAME))
        manifest, root, as_of = None, None, None
        if reg_present:
            reg = self._registry()
            all_entries = reg.entries()
            as_of = str(all_entries[-1]["at"]) if all_entries else "0000-00-00T00:00:00+00:00"
            manifest = cut_manifest(reg, at=as_of)
            root = reg.population_root()

        core = {
            "package_kind": "usn_operator_compliance_package",
            "package_version": 1,
            "principal": self.operator,
            "mandate": self.mandate,
            "as_of": as_of,
            "population_root": root,
            "manifest": manifest,
            "reporting_package": pkg,
            "income_event_count": sum(1 for e in entries
                                      if not (e.get("payload") or {}).get("tax_event")),
            "tax_event_count": len(tax_rows),
            "tax_events": tax_rows,
            "verification": {
                "all_events_verify": all(self._verify_entry(e)["verified"] for e in entries),
                "method": "sovereign_agent.economy.income.verify_income over each stored receipt",
            },
            "declarations": {
                "money_path": "OFF — no balance held, moved, custodied, netted or settled",
                "statutory_acts": "NONE — nothing filed, paid, remitted, formed or represented",
                "port_crossings": "NONE — this package records; it does not cross",
                "authority": "This package holds no statutory authority. It is yours to hand over.",
                "determinism": ("Derived wholly from node state and stamped as_of the newest recorded "
                                "entry — not the export time — so an unchanged node re-exports identically."),
            },
        }
        return core, hashlib.sha256(_canonical(core).encode("utf-8")).hexdigest()

    def export_bytes(self) -> Tuple[bytes, str]:
        """The package exactly as it lands on disk, plus its hash. Canonical JSON, sorted keys —
        the bytes are the artefact, so they must not depend on dict ordering either."""
        core, digest = self.export_package()
        return (json.dumps(core, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8"), digest)


__all__ = [
    "APP_NAME", "APP_VERSION", "ACTION_CLASSES", "CONTRIBUTION_CLASSES", "SOURCE_DEFAULT_CLASS",
    "TAX_CATEGORIES", "STATUTORY_FENCE_FIELDS", "GateRequired", "NodeBinding",
    "SurfaceError", "utc_now", "OBLIGATION_ACTION_CLASSES", "RECORD_ACTION_CLASSES",
    "CLASSIFICATIONS", "EvidenceTier", "classify_evidence",
]
