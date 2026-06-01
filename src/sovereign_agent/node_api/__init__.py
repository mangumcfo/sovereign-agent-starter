"""
sovereign_agent.node_api — HTTP/JSON Node API per `contract_v1.yaml`.

The Node API is the **thin-waist** seam Atrium (and any other UI or agent) talks
to. It is a pure translation layer over the existing Python core:

    UniversalSovereignNode  ──┐
    ComplianceEngine          ├── wrapped by node_api routes (no business logic)
    RoleBinder / BoundRole    │
    PlaybookLoader            ┘

Architectural posture (G's 2026-05-30 correction, KM-1176-ratified):

    "Atrium is the reference visual surface for the sovereign harness defined
     in Series 2 and implemented in the sovereign-agent-starter. The UI is
     replaceable. The contract (receipts, breath-gates, K1-K4 server-side,
     Node API shapes) is sovereign."

Shapes flow OUT OF this module into `contract_v1.yaml` / the consuming UI.
Atrium's `api.js` will eventually `fetch()` from `127.0.0.1:8421/api/v1/...`.

This is the minimal viable shell (Track A1 of the post-Series-2 plan).
Endpoints A (node identity/health/ladder) + C (roles list/get/invoke) implement
real handlers wrapping the Python core. Endpoints B/D/E/F return informative
501 placeholders so consumers can probe the surface immediately while the
remaining handlers are filled in.

Embodies (from SERIES_1_PRINCIPLES_TO_EMBODY_IN_THE_HARNESS.md):
    Principle 7 — Thin-Waist, Separability, Replaceability
    Principle 1 — Human Primacy & Sovereign Agency (every request carries
                  principal_id; no hardcoded principals; auth at boundary).
    Principle 4 — Default-Deny + Constitutional Boundaries (missing token,
                  unknown principal, or RED-class action without breath-gate
                  all fail-closed loudly).
"""

__version__ = "0.1.0"  # follows contract_v1.yaml version line; bump alongside it
