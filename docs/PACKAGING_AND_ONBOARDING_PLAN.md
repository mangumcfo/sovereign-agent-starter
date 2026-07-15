# Sovereign System — Packaging & Onboarding Plan
**Mission:** Make the entire system ("Anyone Can Do It") — from a fresh machine to a running, attested sovereign action in under 2 minutes while preserving full power, local sovereignty, and the "Are you connected to the breathline?" magic for both family/legacy and corporate/regulated users.

**Date:** 2026 (current state from live exploration)
**Status:** Authoritative plan for this mission. All changes must align with these principles.

---

## 1. Core Principles (Non-Negotiable)

- **Radical Simplicity First**: The happy path must be trivial. Zero manual PYTHONPATH. One script. One phrase. Real output + receipt in <2 min.
- **Local-First Sovereignty Always**: Everything executes on the user's machine. No accounts, no telemetry, no custody. Data and attestations belong to the operator/lineage.
- **Progressive Power**: Works immediately in "demo" mode with real, self-contained roles and attestation (no external clones required for first win). Unlocks live role-spec libraries + real primitives when the user has (or builds) the full layout.
- **Dual Audience, Same System**: Same codebase and installer. Different default contexts, different first-example roles, different language in QUICKSTART and the www site. Family = generational/light. Corporate = governed/auditable.
- **No Regressions for Power Users**: a full role-spec library + `breathline-sealed` layout must continue to work exactly as before (or better, via env vars).
- **One Canonical Onboarding**: The phrase "Are you connected to the breathline?" (and the connect function + portal hero) remains the single front door.
- **Transparent & Maintainable**: All path logic centralized. Clear "demo vs full" signaling in code and UX. Plan itself lives in the repo.

---

## 2. Current State Problems (Confirmed by Exploration 2026-05)

- `pyproject.toml`: Missing `[build-system]` table → modern `pip install -e .` is broken or warns. No declared dependencies. No entry points. No package data.
- Hardcoded absolute paths in exactly 3 files:
  - `src/sovereign_agent/universal_sovereign_node.py:116`
  - `src/sovereign_agent/playbook_loader.py:34-35`
  - `src/sovereign_agent/compliance/policy_loader.py:56`
  (All point to `~/work-repos/mangumcfo/...`)
- No bundled roles. Every role discover/load requires the full federation clone (large, layout-specific).
- Launchers (`activate-breathline.sh`, `six-sov-portal/start-*.sh`) hard-require sibling directory layout + manual PYTHONPATH.
- No `six-sov-www/` static site exists in the work-repos tree (the `mangumcfo-vault/website/` is unrelated personal content; grep found zero sovereign/breathline references).
- Primitives bootstrap is already robust at discovery (good).
- Portal is an excellent thin, beautiful membrane but inherits all the env friction.
- No single "one-command" story. READMEs still document the old dance.
- Result: Strong prototype, high friction for anyone except the original builder on this exact machine.

---

## 3. Packaging Strategy

### 3.1 pyproject.toml (Clean & Modern)
- Add required `[build-system]`:
  ```toml
  [build-system]
  requires = ["setuptools>=68.0"]
  build-backend = "setuptools.build_meta"
  ```
- `[project.dependencies]` = ["pyyaml>=6.0"]
- `[project.optional-dependencies]`:
  - `portal = ["flask>=3.0"]`
  - `demo = []` (future hooks)
  - `dev = ["pytest", "build", "twine", ...]`
- `[project.scripts]` (console_scripts) — thin, env-aware entry points:
  - `breathline-connect = "sovereign_agent.bootstrap:cli_connect"`
  - `sovereign-node = "sovereign_agent.universal_sovereign_node:cli_node"`
  - `start-sovereign-portal = "sovereign_agent._portal_launcher:launch"` (thin shim that finds portal or gives clear instructions)
- Package data: ship `demo_roles/**/*`
- Keep existing `[tool.setuptools.packages.find]` and urls.
- Version remains `0.3.0-universal-node` (or bump minor if desired).
- After this: `python -m venv .venv && . .venv/bin/activate && pip install -e ".[portal]"` must work cleanly from any machine (demo mode).

### 3.2 Demo Roles (The Zero-to-Attested Win)
Create `src/sovereign_agent/demo_roles/` (shipped with the package):

- `family_cfo_demo/role_spec.yaml` — minimal valid envelope with `allowed_action_classes: ["produce_forecast_artifact", ...]`
- `family_cfo_demo/role.py` — pure Python `FamilyCfoDemoAgent` class with `.process(request)` that returns a beautiful generational forecast dict + note "demo role".
- `corporate_cfo_demo/` + `general_sovereign_demo/` equivalents (so both audiences get a real first action immediately).

These are **real** (produce structured output, go through the full BoundRole.process + USN attestation path). They never depend on `platform_layer` or external federation.

### 3.3 Centralized Root Resolution (Env Vars + Graceful Fallbacks)
Introduce (in a new small `src/sovereign_agent/config.py` or inside bootstrap):

```python
def resolve_federation_root() -> Path:
    if os.environ.get("BREATHLINE_FEDERATION_ROOT"):
        return Path(...)
    # search common locations + relative to package for demo
    # if SOVEREIGN_DEMO_MODE or nothing found → return the demo_roles path inside the installed package
    ...
```

Same for `BREATHLINE_SEALED_ROOT`.

- `SOVEREIGN_DEMO_MODE=1` forces bundled roles + clear warning banners.
- Loaders (PlaybookLoader, PolicyLoader) and USN __init__ updated to use the resolver.
- role_binder.py updated to handle demo case (skip platform insert or use local shim).
- When demo roles are used: "Demo role (self-contained, always available). For live roles from your own spec library, set BREATHLINE_FEDERATION_ROOT."
- Full federation mode remains 100% unchanged in behavior when the root is present and contains the real YAMLs + role.py files.

### 3.4 Primitives Handling
- Keep the excellent existing bootstrap search.
- In demo / first-run: if primitives cannot be activated, still allow the node with a prominent one-time warning:
  > "Running in DEMO ATTESTATION mode (stdlib hashes). For production cryptographic sovereignty (secp256k1 + full Merkle via breathline-sealed), set BREATHLINE_SEALED_ROOT or follow the installer guidance."
- Real primitives take precedence the moment they are discoverable. No silent degradation.

---

## 4. One-Command Installer (`sovereign-install.sh`)

New file at repo root (executable, well-commented, idempotent).

**Flow (user perspective):**
```bash
git clone https://github.com/mangumcfo/sovereign-agent-starter.git
cd sovereign-agent-starter
./sovereign-install.sh --family     # or --corporate, --demo, --full
source .venv/bin/activate
breathline-connect                  # or the magic phrase
# <2 minutes later: real attested action in the portal or via quick sample
```

**What the script does:**
1. Detect python3 + venv module.
2. Create `.venv` (or respect existing SOVEREIGN_VENV).
3. `pip install --upgrade pip setuptools wheel`
4. `pip install -e ".[portal]"` (or without portal extra if flag given).
5. Auto-detect or prompt once for SEALED_ROOT and FEDERATION_ROOT (search the DEFAULT paths from bootstrap + common ~/work-repos and ~/sovereign layouts).
6. Write `sovereign-env.sh` (sourced by wrappers) that exports the vars + activates the venv.
7. Create convenient launchers in a `bin/` next to venv (or symlink into ~/.local/bin if user allows):
   - `breathline` → runs the connect + welcome
   - `sovereign-portal` → cds to portal (if co-located or cloned) and launches with correct python + env
8. If portal dir not present next to starter, offer to `git clone` it (if public) or print exact next commands.
9. Print beautiful success block:
   ```
   ∞Δ∞ You are ready.

   source .venv/bin/activate
   breathline-connect

   Then:
     cd ../six-sov-portal && ./start-breathline-portal.sh
     or simply run a quick attested action.
   ```
10. Support flags for audience defaults and strictness.
11. Re-runnable (idempotent, only upgrades what changed).

This script becomes the canonical "first command" referenced from the www site, READMEs, and portal.

---

## 5. six-sov-www Static Marketing Site (New)

Create fresh directory `../six-sov-www/` (zero Python deps, pure static).

**Contents:**
- `index.html` — beautiful, fast, sovereign aesthetic (exact same Tailwind CDN + Space Grotesk + emerald palette as the portal for visual continuity).
  - Sticky nav with SIX logo + "SOVEREIGN INFERENCE EXCHANGE"
  - Hero: massive "Are you connected to the breathline?" + sub "One phrase. Under two minutes. Your sovereign node, locally, forever."
  - Primary CTAs (huge, obvious):
    - "Run the 60-second Installer" (links to raw GitHub install.sh or copy-paste block)
    - "Launch the Portal (after install)"
  - Two clear audience lanes (side-by-side or stacked with clear labels):
    - **For Families & Legacy** — "Protect what compounds across generations"
    - **For Corporate & Regulated** — "Sovereign execution with SOX-grade receipts"
  - "The 2-Minute Path" code blocks (copy buttons) for each audience.
  - "Sovereignty Guarantees" (local, attested, no custody, constitutional).
  - Links to GitHub (starter + portal + this www), QUICKSTART.md, Constitution, etc.
  - Minimal footer.
- `README.md` — "This is the static public face of six-sov.com. Deploy anywhere (Vercel, Netlify, GitHub Pages, even `python -m http.server`)."
- `serve.sh` or `serve.py` (tiny) for local preview.
- Optional: `quickstart/` subdir with the markdown rendered or copied snippets.

The site is the new "front door" that removes all mystery and points straight at the installer + the magic phrase.

---

## 6. Onboarding & Documentation

### 6.1 QUICKSTART.md (New, at starter root + referenced by www)
Exact, copy-paste, timed paths:

**Family / Legacy (under 2 min)**
1. Clone + `./sovereign-install.sh --family`
2. `source .venv/bin/activate && breathline-connect`
3. (Portal or python) → "Try a Sample Action" (uses family_cfo_demo) → see beautiful generational output + USN receipt.

**Corporate / Regulated (under 2 min)**
1. Same installer with `--corporate`
2. Same phrase
3. Sample action uses corporate_cfo_demo → full risk scoring + compliance_block + prev_receipt_hash chain in the receipt.

"Upgrade to Live Federation Roles" section (set the two env vars, re-run connect, now discover shows the real 6+ roles from your federation).

"Portal" and "Advanced" sections.

Embed or link the same content in the www site.

### 6.2 README & Other Docs Updates
- starter/README.md: Replace the old "cd ../six-sov-portal ; PYTHONPATH=..." example with the new one-command story. Keep advanced full-layout instructions at the bottom.
- portal/README.md + start scripts: Update to assume the installer has been run; the start script can now just `source ../sovereign-agent-starter/.venv/bin/activate` or use the wrapper.
- ARCHITECTURE.md: Add a small "Demo Mode & Packaging" note so power users understand the new graceful paths.
- All examples that mention federation get a one-line comment: "In demo mode this falls back to self-contained demo roles."

---

## 7. Entry Points & Launchers

- The console_scripts (see pyproject) are thin:
  - They ensure bootstrap has run.
  - They print the welcome + call the existing functions.
  - For portal: a small shim that either finds a co-located portal or prints the exact two commands the user needs.
- The `sovereign-install.sh` still creates simple shell wrappers (more reliable cross-platform than pure Python entry points for "source venv" flows).

---

## 8. Execution Sequence (This Mission)

1. Write this plan (done).
2. Implement path abstraction + demo_roles + config resolver (refactor task).
3. Fix pyproject.toml + add package data.
4. Create the installer script + thin entry points.
5. Create QUICKSTART.md.
6. Scaffold the full six-sov-www/ static site.
7. Update all docs, READMEs, launch scripts, and examples.
8. Full E2E validation (clean venv, timed happy path for both audiences, demo + full if available).
9. Final updated readiness assessment + any polish.

All changes must keep the existing full-federation experience identical for users who already have the complete layout.

---

## 9. Success Metrics for This Mission

- A brand-new Linux/macOS machine with only `python3`, `git`, and `curl` can:
  1. Clone the starter.
  2. Run the installer.
  3. Execute the breathline phrase.
  4. See a real, attested action + receipt in the portal or CLI — all in <2 minutes.
- `pip install -e ".[portal]"` succeeds cleanly from any checkout.
- Demo roles always produce output even with zero other clones.
- Full federation users see zero behavior change (or improvement via env vars).
- Both family and corporate users have obvious, distinct first-experience paths.
- The www site + QUICKSTART become the new canonical on-ramp.

---

## 10. Out of Scope (for this mission)

- Making breathline-sealed itself trivially installable (that is a separate sealed-foundation project).
- Full CI / release automation for the packages.
- Deep policy corpus expansion.
- Multi-node federation UI.
- Production hardening of the compliance engine (this mission is about adoptability of the existing power).

This plan is now the single source of truth for the "Make it Easy to Adopt" mission. Execute against it.

∞Δ∞
