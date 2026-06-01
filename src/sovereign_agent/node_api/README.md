# sovereign_agent.node_api — Track A1 Minimal Viable Shell

> **The thin-waist HTTP seam Atrium (and any other UI / agent) talks to.**
> Contract: `breathline-federation/specs/node_api/contract_v1.yaml`

## Status

**Track A1 minimal viable shell** — 2026-05-30.

Per the post-Series-2 plan + G's architectural correction (*"Atrium is the
reference visual surface; the contract is sovereign; shapes flow OUT OF the
starter"*), this module gives the starter a real HTTP surface. The Atrium
`api.js` live() helper consumes these routes when MODE flips from "mock" to
"live".

| Contract section | Status | Notes |
|---|---|---|
| **A. Node identity/health/ladder** | ✅ implemented | `routes/node.py` |
| **B. Manifest & Specs**             | ✅ implemented (Track E1) | `routes/placeholders.py` — manifest (node-derived) / specs list+get / validate |
| **C. Roles**                        | ✅ implemented | `routes/roles.py` — discover/get/invoke |
| **D. Invocations & breath-gate**    | ✅ implemented (Track E1) | breath-gate pending/approve/deny (session store) + invocations.get |
| **E. Audit chain & receipts**       | ✅ implemented (Track E1) | audit cylinders + receipts via `ComplianceEngine.get_audit_trail` |
| **F. Federation**                   | ✅ peers real / shards+propagation honest-stub (Track E1) | real mesh deferred to SIX (Vol 4); stubs carry `note` |

> **Track E1 (2026-05-30):** the former B/D/E/F 501 placeholders are now real thin handlers. `routes/placeholders.py` retains its filename for blueprint-registration stability but is no longer placeholder-only. Honest stubs (federation shards/propagation, node-derived manifest) carry a `note` field — never a silent fake (TRUTH).

## Architectural posture (non-negotiable)

Pure **thin translation**. No business logic in the HTTP layer. Every route
wraps the existing Python core:

```
UniversalSovereignNode  ──┐
ComplianceEngine          ├── wrapped by node_api routes
RoleBinder / BoundRole    │
PlaybookLoader            ┘
```

Reuses (don't rewrite):
- `BoundRole.process` — emits the canonical receipt envelope unchanged
- `ComplianceEngine.attest_execution` / `run_policy_compliance_check`
- `RoleBinder.bind_role` / `BoundRole.get_allowed_action_classes`
- `PlaybookLoader.discover_roles` / `load_role` / `load_playbook`

## Run it

```bash
# Dev mode (skips bearer-token check; loudly labelled)
breathline-node-api --dev

# Or directly
PYTHONPATH=src python -m sovereign_agent.node_api.server --dev --port 8421

# Strict mode (requires Authorization: Bearer <principal_id>:<secret> header
# matching ~/.breathline/credentials/<principal_id>.token)
breathline-node-api
```

## Smoke-test

```bash
curl http://127.0.0.1:8421/                       # service envelope
curl http://127.0.0.1:8421/api/v1/node            # identity
curl http://127.0.0.1:8421/api/v1/node/health     # health
curl http://127.0.0.1:8421/api/v1/node/ladder     # ladder rung
curl http://127.0.0.1:8421/api/v1/roles           # discoverable roles
curl http://127.0.0.1:8421/api/v1/roles/cfo_agent # role spec envelope
```

## Tests

```bash
pytest tests/test_node_api.py -v
```

17 tests in the minimal-viable suite. Track A2 will extend with behavioural
parity tests (Python-direct call vs HTTP roundtrip producing identical
receipts for each Series 2 demo script).

## Auth (minimal viable)

Per `contract_v1.yaml` `auth.model = principal_id-bearer`:

- Header: `Authorization: Bearer <principal_id>:<secret>`
- Credential file: `~/.breathline/credentials/<principal_id>.token` (chmod 0600)
- Strict by default; bypass via `--dev` or `BREATHLINE_NODE_API_DEV=1`

The dev bypass injects `principal_id = "dev:anonymous"` and labels every
response with `g.auth_dev_mode = True` so production never confuses a dev
call for real auth.

## TLS

The contract calls for HTTPS with a self-signed cert generated at install.
This minimal shell binds plain HTTP for now with a loud startup warning.
TLS hardening is a Track A3 follow-up; Atrium's `api.js` only needs its
base URL changed when TLS lands (the JSON shape is identical).

## Errors

Every error returns the canonical envelope per CONSTITUTION §4:

```json
{
  "code": "ROLE_NOT_FOUND",
  "what": "Role 'foo' is not registered on this node.",
  "why": "The PlaybookLoader could not discover a role_spec.yaml + handler binding for this role_id.",
  "next_step": "Call GET /api/v1/roles to list discoverable roles, or verify the role lives under the federation primary source.",
  "cylinder_ref": null
}
```

No silent corruption. No bare 500s with stack traces.

## What's next

- **Track A2:** per-demo HTTP smoke verification (Python-direct vs HTTP
  roundtrip → identical receipts for all 10 Series 2 demos)
- **Track A3:** Atrium `api.js` MODE flip → live; `atrium-standalone.html`
  rebuild; surface-by-surface verification
- **Track A2/A3 follow-ups:** real handlers for sections B / D / E / F

Then the api.js seam is sovereign-contract-driven, the Atrium UI is the
**thin replaceable lens** G's correction called for, and the harness's
substrate matches the shape the books describe.

∞Δ∞
