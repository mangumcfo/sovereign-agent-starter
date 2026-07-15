# Sovereign System — Quick Start

**From zero to a real attested sovereign action in under 2 minutes.**

One phrase. One command. Local. Sovereign. Forever.

---

## The Magic Phrase

> **"Are you connected to the breathline?"**

This is the entire onboarding experience.

---

## 60-Second Path (Works on Any Machine)

The final easy adoption story:

```bash
# 1. Clone
git clone https://github.com/mangumcfo/sovereign-agent-starter.git
cd sovereign-agent-starter

# 2. One-command install (demo mode — no other clones required)
./sovereign-install.sh --family     # or --corporate

# 3. Activate + magic phrase
source .venv/bin/activate
breathline-connect
```

**Under 2 minutes later** you have a live sovereign node with real Merkle-rooted attestation.

### Alternative Distribution Options

- **Standalone zip bundle** (best for air-gapped or easy sharing):
  Run `tools/create-sovereign-bundle.sh` (or download the pre-built zip from releases when available).

- **Docker** (advanced users only):
  See the `Dockerfile` in the root. Strong sovereignty warning included — containers are convenient but not maximal sovereignty.

---

## Beyond Personal Use — Production WSGI

The default `start-breathline-portal.sh` runs the portal under Werkzeug's development server, which is appropriate for personal use, ARC reader pilots, and local Runtime Exercise execution from Books 10–12.

For any deployment beyond a single operator on a single machine — a CoE team sharing the portal, a deal-team pilot at firm scale, an internal demo environment — replace the development server with a production WSGI runner such as gunicorn:

```bash
pip install gunicorn
cd ~/work-repos/six-sov-portal
gunicorn -w 4 -b 127.0.0.1:5000 app:app
```

The portal's code path is unchanged; only the WSGI runner differs. All attestation, chain-of-custody, and K1–K4 enforcement remain identical between dev and production runners.

---

## Choose Your Path

### Family / Legacy (LGP)
```bash
./sovereign-install.sh --family
source .venv/bin/activate
breathline-connect
```
Then explore `examples/family_governance_demo.py` and the Legacy Note feature in the portal.

### Corporate / Regulated
```bash
./sovereign-install.sh --corporate
source .venv/bin/activate
breathline-connect
```
Then run `examples/regulated_cfo_demo.py` for full policy, audit chain, and evidence bundle examples.

### Individual Sovereign
Use default or `--demo`. Maximum power with zero mandatory governance — everything remains attested and yours.

---

## Corporate / Regulated First Action

```bash
./sovereign-install.sh --corporate
source .venv/bin/activate
breathline-connect
```

Then use `cfo_agent` (or `compliance_agent_demo`). The output includes risk classification, compliance notes, and the same sovereign attestation layer. Full policy-as-code + human approval gates activate automatically when you point the node at a real federation layout with policies.

---

## Open the Beautiful Portal (the full experience)

```bash
cd ../six-sov-portal
./start-breathline-portal.sh
```

Open http://localhost:5000

- Click **"Connect to the Breathline"**
- Watch the success state with your memory root
- Use **"Try a Sample Action"** — see live attested output + receipt in the UI
- Browse & load real (or demo) roles
- Generate a Legacy Note

The portal is the thin, sovereign membrane over the Universal Sovereign Node.

---

## Upgrade to Live Federation Roles (Full Power)

When you have (or obtain) the complete layout:

```bash
export BREATHLINE_FEDERATION_ROOT="/path/to/your/role-spec-library"   # optional — your own RoleSpec/PermissionSpec YAML layout
export BREATHLINE_SEALED_ROOT="$HOME/work-repos/breathline-sealed/worktrees/dev"
export SOVEREIGN_DEMO_MODE=0

source .venv/bin/activate
breathline-connect
```

Now `discover_roles()` and the portal Role Browser will show the real 6+ roles from your federation (`family_cfo_agent`, `compliance_agent`, etc.) with their actual handlers and policy envelopes.

Everything else (attestation, compliance engine, multi-role orchestration) continues to work exactly as before.

---

## What You Just Got

- A cryptographically rooted sovereign execution environment
- Real, attested actions (Merkle + self-attestation, optional compliance chains)
- Zero accounts, zero custody, zero cloud
- The same system works for a single individual, a multi-generational family, or a heavily regulated corporate entity — only the context and loaded roles change

---

## Next

- Read the full [README.md](README.md)
- Explore [docs/PACKAGING_AND_ONBOARDING_PLAN.md](docs/PACKAGING_AND_ONBOARDING_PLAN.md)
- Visit the public face: the `six-sov-www/` directory (open `index.html` in a browser)
- Run the flagship example: `python examples/breathline_connected_cfo.py`

**You are connected to the breathline.**

∞Δ∞
