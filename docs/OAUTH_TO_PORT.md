# OAuth → Port — a migration pattern for builders who have OAuth today

You have an app that logs users in with OAuth and calls resource servers with bearer tokens. This shows how the
same needs — authenticate, authorize a scoped action, refresh, revoke — map onto a sovereign node's **local
authorization + attestation**. You keep your UX; you drop the dependency on a central identity provider holding
your users' authority.

> **This is NOT hosting OAuth for the internet.** The node does not run an identity-provider cloud, does not issue
> internet-facing bearer tokens, and does not log anyone in on anyone else's behalf. It performs **local
> authorization**: the user's own key, the user's own gate, and a **receipt** that a specific act was authorized.
> There is no IdP here to point a redirect URI at.

---

## The mapping

| OAuth concept | node equivalent | sealed floor (card) |
|---|---|---|
| IdP login / "sign in with…" | the user's **self-held key** on their own machine; identity is minted at onboard, not granted by a provider | `identity-keystore`, `onboard-gate` |
| access token (bearer, ambient authority) | a **node-scoped, short-lived, receipted grant** for one act — the human approves it, and it is not a reusable ambient credential | `onboard-gate` (human gate) + `receipt-verify` |
| resource server call | the act is **proposed to the node**, human/policy-gated, and returns a **receipt** — your app never wields a standing token against a remote server on its own | `messaging`, `storage-integrity`, `object-model` |
| calling an **external** API / SaaS / model | a **Port crossing**: declared target, node-declared boundary rule, named-human sanction, receipt | `port-crossing` |
| refresh token | **re-approval** — a new human-gated grant; there is no long-lived refresh secret to steal | `onboard-gate` |
| revoke / logout | **refuse peer** / let the grant expire / **clean exit** — severance leaves no residual claim | `peer-recognition`, `clean-exit` |

The through-line: OAuth centralizes authority in a token an app holds and a provider issues. The node keeps
authority with the **user's key and the user's hand**, and replaces the token with a **verifiable receipt**.

---

## Minimal sequence (copy this shape)

Every arrow below lands on either a **measured callable** (named) or a **human turn** — nothing hand-waved.

```
Builder app        Sovereign node (local)                 Human            External service
     |                     |                                  |                    |
     |  (1) propose act    |                                  |                    |
     |-------------------->|  open the act as a governed      |                    |
     |                     |  object under one mandate        |                    |
     |                     |  [messaging.send_message /        |                    |
     |                     |   storage.store_datum /           |                    |
     |                     |   objects.registry.append]        |                    |
     |                     |                                  |                    |
     |                     |  (2) gate: is this act gated?    |                    |
     |                     |--------------------------------->| approve / deny     |
     |                     |     [onboard-gate: default-deny;  | (named human)      |
     |                     |      no key/act before accept]    |                    |
     |                     |<---------------------------------|                    |
     |                     |                                  |                    |
     |                     |  (3) if the act reaches OUTSIDE: a Port crossing      |
     |                     |     [port.open_crossing] then                        |
     |                     |     [port.sanction_crossing] — deny-by-default,      |
     |                     |     needs a declared boundary rule + this human      |
     |                     |------------------------------------------------------>|
     |                     |     (the Port carries a directive/reference,          |
     |                     |      never value; records that it happened)           |
     |  (4) receipt        |                                  |                    |
     |<--------------------|  authored, integrity-bound                            |
     |                     |                                                        |
     |  (5) verify offline |  [keystore.verify_node_act /                          |
     |     (you or a peer  |   onboarding.verify_onboard_receipt /                 |
     |      or an auditor) |   peerhood.verify_recognition] -> bool                |
```

- **(1)** is a real governed act — one of the callable verbs on the capability cards.
- **(2)** is a human turn — the node cannot self-approve a gated act; no key or gated act exists before the
  turn-1 accept.
- **(3)** only happens when the act reaches an external service, and it is the **only** blessed way out.
- **(4)/(5)** replace the bearer token entirely: instead of presenting a token a server trusts, you present a
  receipt anyone verifies from bytes and a public key, offline.

---

## What you gain, and the honest limits

**Gain:** no central IdP dependency; no long-lived bearer secret to leak; authority stays with the user's key and
hand; every authorization is an auditable receipt; a user can revoke by refusing or cleanly exiting, with no
residual claim.

**Limits (stated plainly):** the node does **not** log a user into a third-party website for you — if that site
requires its own OAuth, your app still speaks that site's protocol **through a Port crossing**, and the node
governs and attests the crossing rather than replacing the site's login. The node authorizes and attests **your**
acts; it does not become the world's identity provider. Where the mechanism is thinner than the wish, the wish
scopes down to the mechanism.
