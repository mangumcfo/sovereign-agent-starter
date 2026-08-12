# Capability cards — the callable surface, one card each

Each capability is one card: a machine-readable `<id>.yaml` and a human-twin `<id>.md`. Every card names a
**PRESENT, callable** entry point — its `callable_path` and `verbs` import and run on a fresh public clone. There
is no card for a designed-toward or unglued capability. `sealed_home` is series-qualified to the canonical names.

| card | capability | gate | home |
|---|---|:---:|---|
| `identity-keystore` | self-held node identity (mint/sign/verify/reload) | N | Zero-Trust Sovereignty (Series 7) V1 (+ Generational Transfer (Series 12) V1–V2 compose-floors; never D1-as-volume) |
| `onboard-gate` | 5-turn human onboard + gated acts | **Y** | Inter-Node Sovereignty (Series 6) V6 + Full Production ERP (Series 5) V16 gate |
| `receipt-verify` | offline receipt / signature verification | N | Full Production ERP (Series 5) V26 |
| `peer-recognition` | recognize / refuse a peer (no registry) | N | Sovereign Peerhood (Series 14) V02 |
| `clean-exit` | sever grants, walk with keys | N | Sovereign Peerhood (Series 14) V05 |
| `messaging` | receipted inter-node messaging (no hub) | N | Inter-Node Sovereignty (Series 6) V01 |
| `port-crossing` | governed external attach (the only way out) | **Y** | Inter-Node Sovereignty (Series 6) V07 |
| `object-model` | governed object model + mandate scope | N | Full Production ERP (Series 5) V05 + Zero-Trust Sovereignty (Series 7) V05 |
| `storage-integrity` | owner-scoped, Merkle-bound datum storage | N | Zero-Trust Sovereignty (Series 7) V03 |

**Reading a card:** `id · name · sealed_home · callable_path · verbs · inputs/outputs · gate_required ·
receipt_shape · kill_targets · anti_patterns · app_patterns`.

**Two cards gate a human hand** (`onboard-gate`, `port-crossing`) — the onboard ceremony and every external reach.
The rest are governed but not human-gated by default; the object/scope and storage cards are **deny-by-default**
across mandates (a declared `SharingRule` or refusal, never standing trust).

Start with the Integration Guide (`../NODE_INTEGRATION_GUIDE.md`), then pick the cards your app needs, then copy
the matching example in `../../examples/`.
