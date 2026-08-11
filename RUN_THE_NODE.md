# Run the node yourself — honest path (seeit → clone → install → onboard → verify)

This is the **honest, no‑overclaim** path a person follows to run a sovereign node from this repo and verify a
receipt **without trusting us**. It is the source copy for **six‑sov.com/seeit** and the in‑repo quickstart.

> **Book ≠ module.** The *books* (Series 0–14) **teach**; **this repository is the running node**. Series 0–4 are
> **teaching‑only** — reading, not runtime. The executable node is the code here (Series 5–14 sealed runtime).
> Reading a book does not run anything; running the node does not require a book.

## 1 · Clone
```bash
git clone https://github.com/mangumcfo/sovereign-agent-starter.git
cd sovereign-agent-starter
```

## 2 · Install (one‑liner)
```bash
python3 -m venv --system-site-packages .venv && ./.venv/bin/pip install -e .
```

**Honest scope — the durable identity works from a fresh clone.** The cryptographic substrate (ECDSA secp256k1
+ Merkle) **ships in this repository** under `src/primitives/sealed/` (git‑tracked — it is in every clone). A
fresh clone therefore **mints, signs, verifies, and reloads a real durable self‑held key with no extra
download** — verified: on a clean checkout, `generate_node_key` → `sign_node_act` → `verify_node_act` →
`load_node_key` all succeed and the fingerprint is stable across reload. (Deeper federation/role features may
pull in more, and the node **fails loud** — never stubs — if a substrate it needs is genuinely absent; but the
core self‑held identity, the 5‑turn onboard, and offline receipt verification below all run from the clone
itself.)

## 3 · Onboard — the 5‑turn human ceremony (no key until you accept)
```bash
export NODE_KEYSTORE_DIR=~/.sovereign_keystore     # your key lives here, on your own machine
./.venv/bin/python -c "from sovereign_agent.onboarding.onboard import cli_onboard; cli_onboard()"
```
The five turns, in order: **1** key ceremony (key on this machine only · no passphrase · no recovery service ·
lose the file = lose the identity → you accept → **only then** is a key written) · **2** name this node · **3**
which acts always need your hand (a safe default set you can edit) · **4** approve or deny your first gated act ·
**5** a signed receipt + how to verify it. **No key is written before your turn‑1 accept.** Nothing phones home;
turns 1–5 need no cloud, no account.

## 4 · Verify the receipt — without us
Turn 5 prints an exact snippet you run yourself: it loads **your** public key and checks the receipt signature.
If it returns `True`, the receipt is genuinely yours — verified with no AI, no cloud, no account, and no trust in
us.

## What this is / is not
- **Is:** a self‑held cryptographic node identity on your own iron; a human‑gated first act; a receipt you verify
  offline. **No custodian, no recovery service, no passphrase claim** (the key is a file under your control).
- **Is not:** a token, a coin, a yield product, or an investment. **Nothing here is a security and no return is
  promised.** No account, no signup, no telemetry.

Live surface: **six‑sov.com/seeit** · Code: **github.com/mangumcfo/sovereign-agent-starter**
