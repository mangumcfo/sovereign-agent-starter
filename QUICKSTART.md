# Quick Start — run a sovereign node and verify a receipt yourself

This is the honest path from a clean clone to a **self‑held cryptographic identity** and a **receipt you verify
without trusting us**. No account, no signup, no telemetry, no cloud for the core path.

> **Book ≠ module.** The books (Series 0–14) *teach*; **this repository is the running node.** See
> `RUN_THE_NODE.md` for the same path with full scope notes, and `docs/READING_PATH_S0_S4.md` for the reading arc.
> **Nothing here is a token, a coin, a yield product, or an investment, and nothing is a security.**

## 1 · Clone
```bash
git clone https://github.com/mangumcfo/sovereign-agent-starter.git
cd sovereign-agent-starter
```

## 2 · Install
```bash
python3 -m venv --system-site-packages .venv && ./.venv/bin/pip install -e .
```
The cryptographic substrate (ECDSA secp256k1 + Merkle) **ships with this repository** (`src/primitives/sealed/`),
so a fresh clone mints, signs, verifies, and reloads a real durable key with no extra download.

## 3 · Onboard — the 5‑turn human ceremony
```bash
export NODE_KEYSTORE_DIR=~/.sovereign_keystore     # your key lives here, on your own machine
./.venv/bin/python -c "from sovereign_agent.onboarding.onboard import cli_onboard; cli_onboard()"
```
In order: **1** key ceremony (key on this machine only · no passphrase · no recovery service · lose the file =
lose the identity → you accept → **only then** is a key written) · **2** name the node · **3** choose which acts
always need your hand (a safe default set you can edit) · **4** approve or deny your first gated act · **5** a
signed receipt + how to verify it. **No key is written before your turn‑1 accept.**

## 4 · Verify — without us
Turn 5 prints an exact snippet: it loads **your** public key and checks the receipt signature. `True` means the
receipt is genuinely yours — verified with no AI, no cloud, no account.

## What this is / is not
- **Is:** a self‑held key on your own iron · a human‑gated first act · an offline‑verifiable receipt. **No
  custodian, no recovery service, no passphrase claim.**
- **Is not:** a token/coin/yield/investment · a security · an account · a service that phones home.

## Governance
Human primacy is **on** — the first gated act requires your explicit approval, by design. You choose *which* acts
are gated (turn 3); you do not choose to remove the human hand from the ones you gate. That is the point, not a
limitation.

---
Live surface: **six‑sov.com/seeit** · Code: **github.com/mangumcfo/sovereign-agent-starter**
