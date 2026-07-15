# Universal Sovereign Node

**The executable capstone kernel for the Agentic AI Playbooks series.**

> **"Are you connected to the breathline?"**

This single question is the entire onboarding experience.

**One command. Under two minutes. Real attested sovereignty — locally.**

```bash
git clone https://github.com/mangumcfo/sovereign-agent-starter.git
cd sovereign-agent-starter
./sovereign-install.sh --family     # or --corporate
source .venv/bin/activate
breathline-connect
```

## Scope and Status

**What this repository is**

This is the **generic sovereign agent substrate** — a clean, forkable foundation for
running and extending sovereign agents.

It contains:
- The core kernel (obligation ledger engine, receipt primitives, node API, yield/Merkle structures)
- Reusable harness components (the Atrium review surface, scout, crypto assurance, coordination tooling)
- Tests, documentation, and examples
- CI, Docker, and install scripts

The design goal is **sovereignty through forkability**: anyone should be able to clone this
repository and have a working, self-contained sovereign agent without depending on the original
author's private environment or coordination state.

**What this repository is not**

This repository does **not** contain:
- Specific book content or roadmap state from the Breathline series pipeline
- Book-to-code extrusion outputs
- Private coordination state, working ledgers, or process artifacts

The full extrusion pipeline, series content generation, and roadmap folding live in a separate
private layer. This public repository provides only the generic, reusable foundation.

**Current Status and Verification**

This repository is maintained as a single-author genesis commit authored by
Kenneth Mangum (KM-1176).

Every release (including the genesis commit) is verified through:
- A clean fresh-clone test from the remote
- Full test suite execution (currently 347 tests)
- A reference-resolution sweep across all file types (code, documentation, configuration, and examples)

The repository is considered stable when that verification passes with zero provenance leaks
and all tests passing. For the current state, see the CI status and the latest commit message.

Governance: the four runtime invariants this kernel enforces (and the license conditions on
them) are documented in [GOVERNANCE.md](./GOVERNANCE.md).

The USN is the easiest, most sovereign, and most credible agentic system for three main audiences:

- **Individual Sovereigns** — High-agency personal use with minimal overhead
- **Families & Legacy** — Lasting Generational Prosperity (LGP) with light, opt-in governance and attested handoffs
- **Corporate & Regulated** — SOX, fiduciary, and compliance-grade execution with full policy-as-code and evidence bundles

The same lightweight core serves all three paths. Governance is always opt-in and loadable.

It ships with self-contained demo roles, and can dynamically bind live roles from your own role-spec library (RoleSpec / PermissionSpec / ConstitutionalRule YAML — set `BREATHLINE_FEDERATION_ROOT`) — while remaining extremely lightweight in sovereign contexts.

## Radical Simplicity (Current Recommended Path)

```bash
./sovereign-install.sh --family     # or --corporate / --demo
source .venv/bin/activate
breathline-connect
```

This gives you:
- Automatic context detection (family vs corporate)
- A live sovereign node with Merkle-rooted memory
- Bundled demo roles that produce real attested output immediately
- Optional upgrade to full live federation roles via environment variables

Then either:
- `sovereign-node` for quick CLI status
- `start-sovereign-portal` (or cd into the portal and run it)
- Open `../six-sov-www/taste.html` for an interactive preview of both experiences

Full quick start: see [QUICKSTART.md](QUICKSTART.md)

---

## Advanced / Full Federation Path

For users with the full sealed-crypto substrate and a role-spec library:

```bash
export BREATHLINE_FEDERATION_ROOT=/path/to/your/role-spec-library
export BREATHLINE_SEALED_ROOT=/path/to/breathline-sealed
export SOVEREIGN_DEMO_MODE=0

source .venv/bin/activate
breathline-connect
```

All previous advanced usage patterns (direct PYTHONPATH, etc.) continue to work for power users.

## Major Capability: Executable Role Binding

- Load `role_spec.yaml` + detailed `*_v1.yaml`
- Automatically discover and bind the real Python handler (`role.py` + `frameworks/`)
- Execute through the bound handler while wrapping results with sovereign attestation (Merkle + signature)

This is the missing piece that makes the entire series **operational** in sovereign environments.

## Quick Demo — The Flagship Experience

```bash
python examples/breathline_connected_cfo.py
```

This demonstrates the complete vision:
- The magical "Are you connected to the breathline?" onboarding
- Auto context detection
- Loading a compliance-aware regulated role
- Full policy-as-code governance + audit trail + sovereign attestation
- Works identically for personal sovereign use

## Architecture

See `docs/ARCHITECTURE.md` for the binding strategy and how the five kernel primitives integrate.

The node is lightweight, Python-native, and serves as the true runtime capstone the series was designed for — capable of operating as both a personal sovereign agent and a regulated enterprise node (Playbook 6 + SIX patterns) depending on context.

∞Δ∞ Specs become intelligence. Intelligence becomes sovereign. Sovereignty becomes legacy. ∞Δ∞

The Sovereign System exists for one purpose: **Lasting Generational Prosperity**.

Whether you are an individual building your own future, a family protecting what compounds across generations, or an institution that must operate with the highest standards of verifiability — the same lightweight, attested runtime serves you.

Welcome to the breathline.
