# Universal Sovereign Node — Architecture (Dynamic Binding Edition)

## Dynamic Role Binding

The USN can load a role in two layers:

1. **Declarative Layer** (RoleSpec / PermissionSpec / ConstitutionalRule YAML — your role-spec library)
   - role_spec.yaml (permission envelope, allowed_action_classes)
   - *_v1.yaml (detailed capabilities, ladder position, constitution reference)

2. **Imperative Layer** (Python)
   - Dynamically imported via `role_binder.py`
   - Looks for `platform/roles/{role_id}/role.py`
   - Falls back gracefully if no handler is present

The `BoundRole` object combines both and exposes a `.process(payload, ...)` method that the node can call under role authority.

## Kernel Primitives (now integrated)

The five kernel primitives (Spec, Constructor, Critic, Auditor, Governor) are wired into the USN via `kernel_integration.py` (loaded from your spec library when present).

- `ConstitutionalGovernor` accepts optional real `kernel_critic` / `kernel_governor`.
- Role execution and `constitutional_check` can run lightweight Critic + Governor elevation-style gates when the primitives are present.
- Auditor usage is recorded through the existing sovereign Merkle + self-attestation path (with a USN-backed adapter in Phase 1).
- Everything degrades gracefully — the original LGP heuristic + Merkle attestation remain fully functional when the kernel tree is not mounted.

This turns the previous "future expansion" note into working, attested capability.

## Sovereign vs Regulated Governance Modes (Hardened Playbook 6 + SIX Integration)

The USN supports two primary operating postures from the same lightweight, constitutionally anchored core:

**Sovereign Mode** (default contexts: personal, family, infrastructure, public)
- Minimal overhead. Full power of breathline_primitives, VerifiableMemory (Merkle), ConstitutionalGovernor, and dynamic role binding.
- Designed for Lasting Generational Prosperity (LGP) and high-agency personal/sovereign use.
- No mandatory audit trails or external gates.

**Regulated Mode** (contexts: corporate_standard, corporate_regulated)
- Hardened enterprise governance layer activated automatically.
- `ComplianceEngine` produces:
  - SOX-style immutable AuditRecords with explicit chain-of-custody (prev_receipt_hash linking records).
  - SIX-style structured cryptographic receipts (node identity signature + compliance_block containing data classification, retention policy, Charter V.7 checks, etc.).
  - Risk scoring + policy-as-code checks (extensible to load Playbook 6-style policies dynamically).
  - HumanApprovalGate with escalation simulation (configurable workflows).
- Compliance-aware roles (`compliance_agent`, `compliance_guardian`, etc.) from your spec library are first-class participants.
- When the full SIX stack is available, the engine can delegate for even stronger external verifiable receipts and mesh settlement.
- All records remain anchored in the node's sovereign Merkle + self-attestation system — nothing bypasses the constitutional foundation.

**Key Design Invariants**
- Verifiability & Auditability first: Every regulated action is timestamped, signed, and chain-linked.
- Flexibility: Policies, approval rules, and classification are data-driven (loadable artifacts), not hardcoded. The same node can serve different statutes and organizational types by changing context + loaded policies.
- Sovereignty preserved: Regulated mode is strictly opt-in via context. The core USN, role binding, and kernel primitives remain unchanged and fully functional for sovereign use cases.
- No unnecessary control: The architecture never forces external frameworks on sovereign operators.

This makes the USN a credible runtime for both personal sovereignty and heavily regulated environments (SOX, fiduciary duty, CAFE, etc.) without compromising its lightweight constitutional character.

### Governance for Regulated Environments (Policy-as-Code + Multi-Role)

The hardened governance layer adds two powerful capabilities on top of the existing constitutional foundation:

**Rich Policy-as-Code Loader (PolicyLoader)**
- Dynamically loads Playbook 6-style policy definitions (YAML) from your spec library (or external paths).
- Policies define data classification rules, Charter V.7 enforcement, retention, approval requirements, and risk overrides.
- `run_policy_compliance_check` is now fully driven by loaded policies (versioned, hot-reloadable).
- Enables the same node to adapt to different statutes and organizational policies simply by loading different policy artifacts.

**Multi-Role Orchestration**
- `load_roles([...])` loads and coordinates multiple BoundRoles simultaneously.
- `request_cross_role_review(reviewer, target, artifact)` provides explicit hand-off with authority gradients (e.g., Compliance can veto or flag CFO outputs per Charter V.7).
- Joint cross-role attestations are produced, creating a complete, verifiable chain of custody across roles.

Together with the hardened `ComplianceEngine` (chain-of-custody AuditTrail + SIX-style receipts), the USN can credibly support SOX, CAFE, fiduciary, and similar regulated environments while remaining a lightweight, constitutionally anchored sovereign runtime.

## Attestation Model

- Module load → Merkle root + node self-attestation
- Role execution → Handler result wrapped with additional USN attestation
- Full chain is verifiable using only the node's public identity and the Merkle roots.

This architecture directly fulfills the "Agentic Harness" vision described in the series planning documents.
