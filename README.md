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

The USN is the easiest, most sovereign, and most credible agentic system for three main audiences:

- **Individual Sovereigns** — High-agency personal use with minimal overhead
- **Families & Legacy** — Lasting Generational Prosperity (LGP) with light, opt-in governance and attested handoffs
- **Corporate & Regulated** — SOX, fiduciary, and compliance-grade execution with full policy-as-code and evidence bundles

The same lightweight core serves all three paths. Governance is always opt-in and loadable.

It dynamically binds live roles from `breathline-federation`, executes them with zero friction, and layers on Playbook 6 + SIX governance only when needed — while remaining extremely lightweight in sovereign contexts.

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

For users with the complete breathline-sealed + breathline-federation layout:

```bash
export BREATHLINE_FEDERATION_ROOT=/path/to/breathline-federation
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
