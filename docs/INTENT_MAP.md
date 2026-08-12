# Intent Map — Human ↔ App ↔ Port ↔ Node ↔ Peer / Exit

One page. Where authority lives, who may cross which boundary, and which card governs each edge. Read it with
`docs/NODE_INTEGRATION_GUIDE.md` (the mental model) and `docs/PATTERNS.md` (the recipes).

```
   ┌─────────┐        ┌──────────┐         ┌──────────┐         ┌────────────┐        ┌──────────────┐
   │  HUMAN  │        │   APP    │         │   NODE   │         │    PORT    │        │  EXTERNAL    │
   │ disposes│        │ proposes │         │ governs  │         │  boundary  │        │  world /     │
   │  (hand) │        │  (UI)    │         │ + attests│         │ deny-by-   │        │  SaaS / rail │
   └────┬────┘        └────┬─────┘         └────┬─────┘         │  default   │        └──────┬───────┘
        │                  │                    │              └─────┬──────┘               │
        │  1. accept key   │                    │                    │                      │
        │  choose gates    │                    │                    │                      │
        │─────────────────────────────────────▶│  key minted        │                      │
        │                  │  2. propose act    │  (self-held)       │                      │
        │                  │───────────────────▶│  governed object   │                      │
        │  3. approve/deny  │                    │  under one mandate │                      │
        │◀───────gate───────────────────────────│  (default-deny)    │                      │
        │─────────approve───────────────────────▶│                    │                      │
        │                  │  4. receipt        │  authored,         │                      │
        │                  │◀───────────────────│  integrity-bound   │                      │
        │  5. verify offline (you, a peer, an auditor) — no AI, no cloud, no account         │
        │                  │                    │                    │                      │
        │                  │  6. reach outside? ONLY via a crossing   │                      │
        │                  │───────────────────▶│──open_crossing────▶│                      │
        │  named-human sanction (deny-by-default, declared boundary)  │                      │
        │◀──────────────────────────────────────│◀─sanction_crossing─│──directive, never───▶│
        │                  │                    │   receipt-not-value │   value; Port holds   │
        │                  │                    │                    │   nothing             │
        │                  │                    │                    │                      │
        │                  │        ┌───────────┴───────────┐        │                      │
        │                  │        │        PEER            │        │                      │
        │                  │        │ recognize · message ·  │        │                      │
        │                  │        │ refuse · clean exit    │        │                      │
        │                  │        │ (no hub, no registry)  │        │                      │
        │                  │        └───────────┬───────────┘        │                      │
        │  EXIT: refuse_recognition (no residual) · clean_exit (sever all, walk with keys)   │
        │◀───────────────────────────────────────────────────────────────────────────────── │
```

## The edges, and the card that governs each

| edge | who acts | rule | card |
|---|---|---|---|
| **Human → Node** (accept key, choose gates) | the human | no key before the turn-1 accept; the human picks the gates | `onboard-gate` · `identity-keystore` |
| **App → Node** (propose an act) | the app | proposes under a mandate; never holds the mandate root | `object-model` · `messaging` · `storage-integrity` |
| **Node → Human** (gate) | the node asks | a gated act is default-deny until a named human approves | `onboard-gate` |
| **Node → App/anyone** (receipt) | the node | every act yields an authored, integrity-bound receipt | `receipt-verify` |
| **anyone → receipt** (verify) | app / peer / auditor | verified offline against a public key — no account | `receipt-verify` |
| **Node → External** (the ONLY way out) | the node, human-sanctioned | deny-by-default crossing; declared boundary + named human; receipt, never value | `port-crossing` |
| **Node ↔ Peer** | two nodes | mutual recognition, receipted messages, each validated independently — no hub, no registry | `peer-recognition` · `messaging` |
| **Exit** | the user / node | refuse leaves no residual claim; clean exit severs every grant, walks with keys + records | `clean-exit` · `peer-recognition` |

## The four laws the map encodes

1. **Authority lives with the human's key and hand** — the app proposes, the human disposes, the node attests.
   The app never holds the root and cannot widen its own scope.
2. **The Port is the only door outward** — every external reach is a declared, sanctioned, receipted crossing.
   No direct call, ever.
3. **Money-path is off** — the node moves and holds no value; a crossing carries a directive, not funds. The Port
   records that a crossing happened, never the value.
4. **Every relationship has an exit** — refuse and clean exit end any peer, share, or membership with no residual
   claim. Nothing holds the user, their key, or their data hostage.
