# Example A — P2P receipted messaging

Two sovereign nodes recognize each other, exchange a receipted message, validate it **offline**, and refuse a
peer **without leaving a hostage** — composing sealed floors only. No message bus, no hub, no custodian is built
here; this is a **thin client** over the kernel.

## Run it

```bash
# from the repo root, after `pip install -e .` (see RUN_THE_NODE.md)
python examples/p2p_messaging/run_p2p.py
```

No arguments, no network, no account. It uses a throwaway temp directory and cleans up after itself. It **exits
non-zero if any check fails**, so it doubles as a regression test.

## What it proves (each line asserts)

| step | act | sealed floor | assertion |
|---|---|---|---|
| 1 | mint two self-held keys | `peerhood.genesis.establish_self_held_identity` (Sovereign Peerhood (S14) V01 · D1 keystore) | each node holds its own key on its own iron |
| 2 | mutual recognition | `peerhood.recognition.mutual_recognition` / `verify_recognition` (Sovereign Peerhood (S14) V02) | both parties verify; **a stranger is refused** |
| 3 | send a message | `messaging.inter_node.send_message` (Inter-Node Sovereignty (S6) V01) | the message carries its own integrity hash — a **receipt** the moment it is sent |
| 4 | deliver + validate | `carry_to_peer` → `receive_from_peer` | node B validates the packet **by its own bytes** — no hub, no sender registry |
| 5 | offline root check | `receive_from_peer(expected_root=…)` | the correct peer-stated root matches; **a wrong root is refused** |
| 6 | tamper probe | `receive_from_peer` on a mutated payload | a **tampered** message is refused (fail-closed) |
| 7 | refuse the peer | `refuse_recognition` | a signed act, **`residual_claim=None`, `hostage_free=True`** |

## Kill-targets held (do not violate when you build on this)

- **No custodian / no hub** takes custody of the message — delivery carries nothing in between.
- **No central validator** — each node validates a peer's message for itself.
- **No silent acceptance** — a packet that fails its own checks, or carries a wrong stated root, is refused.
- **Exit is non-hostage** — refusing a peer leaves no residual claim; you can always walk with your key and records.

## How an app attaches

Your app is the transport and the UI; the node is the identity, the receipt, and the gate. Your app **proposes**
a message (calls `send_message` under a mandate it does not own the root of), **carries** the self-verifying
packet over whatever wire you like, and **verifies** on the far side (`receive_from_peer`). The app never holds
another node's key and never becomes the validator. Reaching any *external* service (a push provider, an email
relay) is a **Port crossing** — see `docs/OAUTH_TO_PORT.md`, never a direct call.
