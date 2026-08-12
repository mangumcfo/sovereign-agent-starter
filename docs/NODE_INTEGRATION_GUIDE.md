# Node Integration Guide — plug an app into a sovereign node in minutes

For an AI-app builder. You do **not** need to read the book shelf. In one page you will see what the node is,
the five-minute mental model, and how your app attaches by **proposing, gating, and verifying** — without ever
holding a root key.

> Book ≠ module: the books teach; this repository **is** the running node. Nothing here is a token, a coin, a
> yield, or a security, and no return is promised. Governance is opt-in and always the human's.

---

## What this IS / IS NOT — read this first

**IS**

- **A self-held cryptographic identity on the user's own machine.** The user mints and holds their own key; you
  build on top of an identity you do not own and cannot recover for them.
- **A human gate over actions.** The node proposes; a human disposes. Chosen actions are default-deny until a
  named human approves.
- **A receipt engine.** Every act produces an authored, integrity-bound receipt that anyone can verify **offline**
  against a public key — no account, no callback to us.
- **A boundary (the Port).** Every reach to anything external is a declared, sanctioned, receipted crossing.

**IS NOT**

- **Not "just another agent framework."** An agent framework gives you a model loop, tools, and prompts, and asks
  you to trust its orchestration. This gives you the opposite layer: a **local identity, a human gate, receipts,
  and a governed boundary** the loop must pass through. There is no hosted brain here, no prompt router, no tool
  registry you rent. If you already have an agent framework, this is the **sovereignty layer under it** — it
  governs what your agent may do and proves what it did.
- **Not a custodian.** The node **never holds your users' keys, funds, or data for them.** There is no wallet we
  keep, no bucket we own, no "recover my account" endpoint. Keys live on the user's machine; data is the owner's
  own object; losing the key file loses the identity — by design, because a custodian is the thing this refuses to
  be.
- **Not OAuth-as-a-service.** It does not host an identity provider for the internet. Authorization is **local**:
  the node issues a short-lived, receipted, node-scoped grant for a specific act — it does not run a login cloud.
  See `OAUTH_TO_PORT.md`.

If, after this section, an app builder could still conclude "agent framework" or "custodian," the section has
failed — tell us and it will be fixed.

---

## The node in five minutes: **key → gate → act → receipt → exit**

1. **key** — the user mints a self-held key on their own machine (`identity-keystore` card). No key exists until
   they accept it; no one else can produce it.
2. **gate** — the user chooses which actions always need their hand (`onboard-gate` card). Those actions are
   default-deny. The AI proposes; the human disposes.
3. **act** — the node performs a governed act (send a message, store a datum, open a crossing). Each act is
   scoped to exactly one mandate and appended as an authored version, never mutated in place.
4. **receipt** — the act yields a receipt bound to its own bytes. Anyone with the public key verifies it
   **offline** — no AI, no cloud, no account (`receipt-verify` card).
5. **exit** — the user can recognize and **refuse** peers with no residual claim, and **cleanly exit** — severing
   every grant and walking with their keys and records (`peer-recognition`, `clean-exit` cards). Nothing holds
   them hostage.

Run the two reference examples to watch all five happen on a bare clone:

```bash
python examples/p2p_messaging/run_p2p.py     # key → recognize → send receipt → verify → refuse (non-hostage)
python examples/file_storage/run_storage.py  # store → own-read → deny stranger → governed share → tamper refused
```

---

## How your app attaches — propose · gate · verify (never hold root)

Your app is the UI, the transport, and the model loop. The node is the identity, the gate, the receipt, and the
boundary. The attach pattern is always the same three moves:

- **Propose.** Your app calls a governed act (e.g. `send_message`, `store_datum`) under a mandate. It supplies the
  content and the intent; it does **not** hold the node's root key, and it cannot widen its own scope.
- **Gate.** For any act the user chose to gate — and for **every** external reach — the node requires a human
  hand. Your app surfaces the decision to the user; it does not auto-approve on their behalf.
- **Verify.** Your app (or the far side, or an auditor) checks the receipt against the public key, offline. Trust
  is a signature check, not a promise.

A minimal attach is a few lines composing sealed floors — the two example scripts are the copy-paste templates.
Pick the capability you need from `docs/CAPABILITY_CARDS/` (each names its callable path, verbs, gate, receipt
shape, and the kill-targets you must not violate).

---

## The Port is the ONLY blessed path outward — this is an invariant

Any reach to something **outside** the node — an external AI or model API, a browser tool, a SaaS connector, a
bank or market rail, a legacy system — **MUST** go through a **Port crossing** (`port-crossing` card):

1. `open_crossing` declares the intent to reach a named external target (a directive/reference, **never** value);
2. `sanction_crossing` is **deny-by-default**: it requires a node-declared boundary rule **and** a named human's
   approval before the crossing is allowed;
3. the crossing produces a receipt that it happened — never the value itself. The Port holds and moves nothing.

An app that calls an external service directly, bypassing the Port, is not integrated — it has broken the
boundary. **There is no other blessed way out.**

---

## Kill-targets your app must not violate

| kill-target | what it forbids |
|---|---|
| **custody** | holding a user's key, funds, or data for them; any "we can recover it" path |
| **silent mint** | creating a key or identity without the user's explicit accept |
| **score-as-authority** | using a reputation/rank/score as if it were a permission or a token |
| **no-exit** | any state a user cannot leave — a grant that survives their exit, records you keep, a hostage |
| **bypass-the-Port** | reaching an external service without a sanctioned crossing |
| **money-path** | moving or holding value in-node; settlement is Port-only and is off by default here |

Build patterns and cards on top of these; do not grow past them.

---

## For corporate & regulated teams — governance, evidence, exit

The same lightweight core serves a regulated deployment without a different product and without a token pitch:

- **Governance as code.** The human gate, mandate scoping, and deny-by-default boundary are enforced in the
  kernel, not asserted in a policy PDF. Which acts are gated is your configuration; that gated acts need a human
  is not removable.
- **Evidence packages.** Every act is an authored, hash-chained receipt; a population of objects derives one
  integrity root; receipts verify offline. That is an audit trail an examiner can check without trusting the
  vendor — because there is no vendor in the verification path.
- **Exit and non-hostage.** A regulated node can **cleanly exit** — severing every grant and walking with its
  keys and records. Continuity and generational hand-off run under a family/organization quorum. You are never
  locked in.

The corporate story is **governance + evidence + exit**. It is not an offering of a token, a yield, or an
investment, and nothing here is a security.

---

## Where to go next

- `docs/CAPABILITY_CARDS/` — one card per capability (callable path, verbs, gate, receipt, kill-targets, app patterns).
- `docs/CALLABLE_MAP.md` — the **inventory of importable/run paths** in the repo; the nine cards are the **curated
  subset** of it. Reach here when a card doesn't cover what you need — every listed path imports on a fresh clone.
- `docs/PATTERNS.md` — ten builder recipes composing the cards.
- `examples/p2p_messaging/`, `examples/file_storage/`, `examples/gated_external_send/` — runnable thin-client templates.
- `docs/OAUTH_TO_PORT.md` — migrating an OAuth-based app to node-scoped, receipted grants.
- `docs/HELPER_AGENT_BRIEF.md` — a system brief so a helper AI can answer builder questions honestly.
- `RUN_THE_NODE.md` — clone → install → onboard → verify.
