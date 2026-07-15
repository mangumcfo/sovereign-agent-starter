"""Cross-mandate authorization guard — pure predicates over an obligation's `debit` + an `approval`
entry (no ledger import; no cycle; crypto-free — this is authorization logic).

DOCTRINE (S2-V4 *Federated Sovereignty*, Ch 2 "Mandate Foundations"):
  "Each mandate is its own constitutional surface. The operator carries the mandates; the federation
   does not aggregate them. Cross-mandate operations require cross-mandate ceremony." (manuscript_v1.4
   §207) — each mandate has its own Charter/node/audit chain (§211-217); a cross-mandate operation is a
   distinct constitutional act (§221-227, the 3-receipt witness pattern). Ch 8 scoped-access reinforces
   the default-deny posture: access is Charter-scoped, structurally enforced, never vigilance-dependent.

RULE (Slice 2.1, graduates the "automated cross-mandate blocking" designed-toward item):
  An approval/action on a MATERIAL obligation SCOPED to mandate M is authorized only if the acting
  principal HOLDS M — or carries an explicitly-declared cross-mandate authorization for M. A principal
  holding mandate A acting on an obligation scoped to mandate B they do not hold is BARRED, fail-closed.
  This is an ADDITIONAL gate composed with AH-1 (opener≠approver); it does not weaken AH-1.

MANDATE-REPRESENTATION ASSUMPTION (stated loudly per the operator discipline #1):
  Obligations did NOT previously carry mandate scope as a first-class field. The minimal honest
  representation adopted here:
    • the obligation's mandate is an OPTIONAL `mandate` field on the debit (ObligationLedger.open(mandate=…));
      absent ⇒ UNSCOPED ⇒ single-mandate sovereign node ⇒ this gate is a no-op and AH-1 governs alone
      (backward-compatible; the sovereign operator carrying one mandate is unaffected).
    • the acting principal's HELD mandates are supplied AT THE ACTION SITE as `held_mandates` on the
      approval entry (ObligationLedger.approve(held_mandates=…)), recorded on the chain so this predicate
      is a pure replay over committed data (same idiom as AH-1's recorded gate). In a full federation
      deployment these resolve from the operator's per-mandate node identity / role-capability config
      ("the operator carries the mandates", §215); here they are supplied explicitly and enforced
      fail-closed. The book's heavier cross-mandate CEREMONY (the 3-receipt witness sealed at BOTH
      chains, §221-227) is the designed-toward form; this guard enforces the authorization GATE itself —
      a declared `cross_mandate_auth` stands in for the ratified ceremony's authorization output.
"""
from __future__ import annotations


def obligation_mandate(debit: dict | None) -> str | None:
    """The mandate an obligation is scoped to (None ⇒ unscoped / single-mandate sovereign)."""
    return debit.get("mandate") if debit else None


def approval_holds_mandate(debit: dict | None, approval: dict) -> bool:
    """True iff `approval` is authorized under the obligation's mandate scope (fail-closed).

    - Unscoped obligation (no `mandate`) ⇒ True: AH-1 governs alone; sovereign single-mandate node.
    - Scoped to M ⇒ the approval must declare `held_mandates` containing M, OR an explicit
      `cross_mandate_auth` = {"authorized": True, "mandate": M, ...} (the book's cross-mandate
      ceremony authorization). Anything else — no declaration, wrong mandate — is BARRED.
    """
    m = obligation_mandate(debit)
    if not m:
        return True  # unscoped: no cross-mandate boundary to cross
    held = approval.get("held_mandates") or []
    if isinstance(held, (list, tuple, set)) and m in held:
        return True
    xm = approval.get("cross_mandate_auth")
    if isinstance(xm, dict) and xm.get("authorized") is True and xm.get("mandate") == m:
        return True  # explicit, declared cross-mandate authorization (Ch 2 ceremony output)
    return False


def resolve_held_mandates(node_identity: dict | None, principal: str,
                          declared: list | None) -> tuple[list, str, list]:
    """Resolve the acting principal's held mandates from NODE IDENTITY (S2-V4 Ch 2 §215: "the
    operator's identity key is shared across mandates... the constitutional surface at each mandate
    is separate" — the operator CARRIES the mandates; identity, not self-declaration, is the source
    of a held mandate). Graduates the designed-toward remainder named in cross_mandate_v0.1.yaml
    ("Held-mandate resolution from per-mandate node identity / role config is designed-toward").

    `node_identity` is the Charter/node-level registry supplied at ledger construction:
      {principal_id: [mandates held], ...} — in a full federation deployment this is derived from
      the operator's per-mandate node identity config; here it is the node's committed declaration.

    Returns (held_mandates, source, overclaimed):
      • registry absent or principal UNKNOWN ⇒ (declared or [], "declared", []) — the 2.1
        action-site declaration flow, unchanged (single-node / pre-federation posture).
      • principal KNOWN ⇒ (registry list, "node_identity", overclaimed) — identity GOVERNS the
        stamped value. `overclaimed` lists any declared mandate identity does NOT grant: a
        self-declaration exceeding identity is a barred act the caller must DENY, fail-closed
        (a principal cannot talk their way into a mandate their node identity does not hold).
    """
    if not node_identity or principal not in node_identity:
        return (list(declared) if declared else [], "declared", [])
    held = node_identity.get(principal) or []
    held = list(held) if isinstance(held, (list, tuple, set)) else []
    overclaimed = [m for m in (declared or []) if m not in held]
    return (held, "node_identity", overclaimed)
