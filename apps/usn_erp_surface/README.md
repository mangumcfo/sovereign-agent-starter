# USN ERP Operator Surface — v0

∞Δ∞ The Universal Sovereign Node **is** the ERP. This app only drives it. ∞Δ∞

A local app for one operator running their own books on their own node. You open your node, record
what you earned, record a tax note about it, keep a ledger of what you have undertaken to do, and
export a package you can hand to your accountant. Everything you record goes into the node's own
hash-chained stores through the node's own modules. This app keeps no ledger of its own.

**What it does not do, ever:** file, pay, remit, form an entity, represent you, hold a balance,
move value, or cross the Port. Those are your acts, not the node's and not this app's.

---

## Launch

```bash
cd /path/to/sovereign-agent-starter
python3 -m venv --system-site-packages .venv
./.venv/bin/pip install -e .            # brings flask, which is a core dependency of the starter

./apps/usn_erp_surface/launch.sh        # → http://127.0.0.1:8477
```

Or directly, with a browser opened for you:

```bash
./.venv/bin/python apps/usn_erp_surface/server.py --open
```

It binds loopback only and **refuses to start on any other host**. There is no authentication
because there is no remote surface to authenticate — if you ever need reach from another machine,
that is a Port-governed crossing, not a bind flag.

---

## Paths

Three, all optional except the first. Set them in the environment and they prefill the open form,
or just type them into the form. **Nothing is saved** — no config file, no database. Reopening after
a restart means the environment or the form again.

| Variable | Points at | Needed for |
|---|---|---|
| `SUBSTRATE_STORAGE_ROOT` | the registry root holding `objects.ndjson` | **required** — this is where your records live |
| `NODE_KEYSTORE_DIR` | your keystore | your fingerprint and receipt log |
| `OBLIGATION_LEDGER_ROOT` | the obligation ledger root | the obligations panel — reading **and** opening, approving, closing |
| `USN_OPERATOR` | your name | prefills the operator field |

### Point it at a throwaway node

Safest first run. This writes only inside the folder you name:

```bash
mkdir -p /tmp/try_node/keystore
./.venv/bin/python -c "
from sovereign_agent.keystore.node_keystore import generate_node_key
print(generate_node_key('/tmp/try_node/keystore','node',at='2026-08-19T00:00:00+00:00').fingerprint)"

SUBSTRATE_STORAGE_ROOT=/tmp/try_node/registry \
NODE_KEYSTORE_DIR=/tmp/try_node/keystore \
USN_OPERATOR=you \
  ./apps/usn_erp_surface/launch.sh --open
```

Delete `/tmp/try_node` when you are done.

### Point it at your real node

Your keystore is wherever `NODE_KEYSTORE_DIR` pointed when you ran the onboard ceremony (documented
default `$HOME/.sovereign_keystore`). If you have not onboarded, do it yourself — this app cannot
mint a key and will not try:

```bash
export NODE_KEYSTORE_DIR="$HOME/.sovereign_keystore"
./.venv/bin/python -c "from sovereign_agent.onboarding.onboard import cli_onboard; cli_onboard()"
```

To find an existing registry or ledger rather than guess:

```bash
find "$HOME" . -name objects.ndjson     -not -path "*/.git/*" 2>/dev/null
find "$HOME" . -name obligations.ndjson -not -path "*/.git/*" 2>/dev/null
```

Use the **parent directory** of whatever those print. If you have no registry yet, that is fine —
point at where it should live and the node's own store creates it on your first record.

---

## Your first three clicks

1. **Open node.** Fill in your name, check the registry path, leave the posture on
   *Regulated — every recording act needs your explicit approval*. Click **Open node**. The header
   should show your fingerprint. If the registry does not exist yet it says so plainly — that is
   correct, not a failure.

2. **Record an earning.** Reference `consulting-august`, amount `2400`, unit `USD`. Click **Record
   earning**. It does **not** save — it appears under *Human gate* as awaiting you. Nothing has been
   written. Click **Approve**. Now it is on disk, with your name and the approval reference against
   it. (Try **Deny** once, first. Nothing is written at all — the refusal is the act.)

3. **Record a tax note, then export.** Tax note tab → category `self_employment`, references the
   earning you just made, its own reference `tax:consulting-august`. Approve it. Then **Build
   package** → **Download**. That file is yours to hand over. Build it twice against an unchanged
   node and you get the same bytes and the same hash.

Click any **verified** badge to re-check that receipt against the node right now, rather than
trusting a verdict from page load.

*(Calling `/api/record/tax` directly rather than through the UI: the request field is `category`;
the node's stored record carries it as `tax_category`. The UI handles this for you.)*

---

## Obligations — opening, approving, closing one

An obligation is something you have undertaken to do. It lives on the node's own append-only,
hash-chained `obligations.ndjson`, and the panel you read it in and the acts that change it are the
same file — they cannot drift apart.

**Open one.** *New obligation* → title it (*Send Q3 books to the accountant*), give it an intent and
a reference, and decide the one setting that matters:

> **Material.** A material obligation cannot be closed until it has cleared the breath-gate, and the
> ledger refuses to approve one with no human gate behind it. Leave it off for routine work; turn it
> on for anything you would want a record of having personally authorised.

A reference like `q3-books` is symbolic and always fine. A *path-like* reference — anything with a
slash and a file extension — must actually resolve on this machine, or the ledger refuses it: a
citation is never written false.

**Approve it.** A freshly opened obligation reads `draft`. Click **Approve**, say why, and the
disposition recorded on the chain is yours — this app has no path that approves on your behalf, and
the ledger's gate fails closed if it is ever handed no verdict.

**Close it.** Click **Close** and give evidence. The ledger has a floor here and the field tells you
live which side of it you are on:

| tier | what it means |
|---|---|
| **E0** | claim-only — *"I did it"*. Will **not** close an obligation. |
| **E1** | an artifact pointer: a path, a URL, a hash, or a receipt id. Enough. |
| **E2** | artifact **and** verification — a path plus a hash. The preferred grade. |

Tick *record this as a refusal* to close it as a **no** instead. A refusal needs no gate and no
artifact — saying no is itself the human disposition.

**Joint attestation.** Name roles in *Requires attestation from* (`cfo, counsel`) and each must
attest before the obligation can execute. Any role can stand a **veto**, with a reason, and while it
stands the obligation is default-deny — it cannot close until the veto is cleared. All of that is
the ledger's own rule; the app surfaces its refusals verbatim rather than paraphrasing them.

Under the regulated posture every one of these acts is held at the human gate first, exactly like a
recording act. Deny one and nothing is written at all — not the obligation, not the approval.

What this version deliberately does **not** expose: `reopen` and `repair_chain`. Chain repair is not
an authority an operator surface should hold, and the kill-grep fails RED if either ever appears.

---

## What is where

```
apps/usn_erp_surface/
  node_binding.py   the ONLY module that touches sovereign_agent — every act goes through here
  server.py         loopback Flask shell; a thin JSON translation, no business logic
  ui.html           the whole interface, self-contained: no CDN, no external asset, no telemetry
  killgrep.py       the P6 gate — run it any time; exit 0 GREEN, 1 RED
  tests/            the P2–P6, P8 and O1–O6 proof tests
  launch.sh
```

Verify it before you trust it:

```bash
./.venv/bin/python apps/usn_erp_surface/killgrep.py          # P6
./.venv/bin/python -m pytest apps/usn_erp_surface/tests/ -q  # the rest
```

---

## Remote access

Not built, and not by omission. The surface binds loopback and refuses anything else — including a
private LAN address — because reach from another machine is a Port-governed crossing, not a bind
flag. If that changes it will arrive as an explicit, reviewable decision with its own bar row.

---

## Two things worth knowing

**The gate only engages in the regulated posture.** That is the node's own semantics, not a
weakening: `HumanApprovalGate.requires_approval` returns false for any mode other than
`corporate_regulated`. In the sovereign posture your acts record straight away, and the gate panel
says so rather than pretending to guard. The app defaults to regulated.

**Pending approvals are session-scoped.** They live in this process and are lost if you restart —
exactly like the node's own gate. Nothing pending was ever written, so nothing is lost but the
half-finished intent.

Also: this runs Flask's development server. For one operator on loopback that is the right size of
machinery, and it is what the warning in your terminal is about. It is not a claim to be a
production web service — it is a desktop app that happens to render in a browser.

---

## What v0 deliberately is not

No AR/AP suite, no payroll UI, no bank feeds, no inventory, no multi-entity, no dashboard chrome
beyond these loops. It records income, contributions and tax notes; it gates them; it shows them;
it exports them. That is the whole vertical, and it is complete.

Breath only. ∞Δ∞
