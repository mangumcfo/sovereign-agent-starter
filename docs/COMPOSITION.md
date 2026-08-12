# Composition — how the primitives interoperate

One page. How an app and the node's primitives compose, and the invariants that hold no matter which primitives
you combine. The primitives are small on purpose: they compose, they do not entangle.

## The one rule of interop

**Apps propose · the node governs and receipts · a human disposes material acts · the Port is the only door
out · nobody takes custody.** Every composition below is an instance of that rule.

## The five primitives and how they snap together

| primitive | what it is | composes with | card / path |
|---|---|---|---|
| **identity** | a self-held key on the user's machine; signs and verifies | signs every other primitive's act; verifies any receipt | `identity-keystore` |
| **gate** | a human hand over the acts the operator chose to gate | wraps any act; default-deny until a named human approves | `onboard-gate` |
| **object** | a governed, hash-chained record under one mandate | messages, data, crossings, ERP records are all objects; cross-mandate needs a declared `SharingRule` | `object-model` |
| **message / Port** | node-to-node delivery (no hub) · the governed door to anything external | a message is an object; a Port crossing gates and receipts every external reach | `messaging` · `port-crossing` |
| **peer / exit** | mutual recognition, and a clean, non-hostage way to leave | recognition rides on identity; exit severs every grant | `peer-recognition` · `clean-exit` |

They snap together in one direction: **identity signs → the object model records → the gate holds material acts →
the message/Port moves things (in-network or out) → peer/exit governs the relationship.** No primitive reaches
around another; a message is an object, an external reach is a crossing, a share is a declared scope.

## What an app may and may not do

- **May:** propose acts (create objects, send messages, store data, open crossings); read its own mandate; verify
  any receipt offline; surface a gate decision to the user.
- **May not:** hold the mandate root or another user's key; widen its own scope; approve a gated act on the user's
  behalf; call an external service directly (that is a Port crossing); move or hold value in-node.

## The interop invariants (true for every composition)

1. **Apps propose, the node disposes.** The app never holds the root and cannot self-approve a gated act.
2. **The node receipts everything.** Every act yields an authored, integrity-bound receipt verifiable offline
   against a public key — no account, no callback to us.
3. **A human gates material acts.** Which acts are gated is configuration; that gated acts need a hand is not
   removable.
4. **Port-only external.** Any reach outside the node is a declared, sanctioned, receipted crossing —
   deny-by-default, named-human sanction, a receipt, never the value. Money-path is off.
5. **No custody.** No key, no funds, no data is held for the user. Every relationship has an exit
   (`refuse_recognition` / `clean_exit`) that leaves no residual claim.

## A minimal composed flow

```
identity.sign  →  objects.append (a governed record)  →  [gate: named human, if the act is gated]
                                                          →  messaging.send  OR  port.open+sanction_crossing
                                                          →  a receipt  →  verify offline (you / peer / auditor)
   … and at any time: peer.refuse or clean_exit — walk with your keys and records, no hostage.
```

Every arrow is a real callable — see `docs/CALLABLE_MAP.md` for the paths and `docs/PATTERNS.md` for worked
recipes. This page is the contract the patterns obey; it is not folded into the generated CALLABLE_MAP.
