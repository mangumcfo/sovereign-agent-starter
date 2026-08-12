# Builder Patterns v0 — recipes over the sovereign node

Ten patterns for building an app on the node. Each composes **only the nine capability cards**
(`docs/CAPABILITY_CARDS/`) — a real, callable surface, nothing designed-toward. Each pattern names its intent,
the cards it uses, the steps, the kill-targets it must hold, and the anti-patterns that break it.

**Standing invariants across every pattern:** the Port is the only blessed path to anything external · the
money-path is off (the node moves and holds no value) · a human gate cannot be removed from an act the operator
chose to gate · every pattern that creates a relationship also names how to **leave** it (refuse / clean exit),
non-hostage. Nothing here is a token, a coin, a yield, or a security.

---

## 1 · OAuth-shaped Port attach
**Intent:** an app that logs users in and calls resource servers with OAuth tokens instead uses local, receipted
authorization — no central IdP holds authority. (Full mapping: `docs/OAUTH_TO_PORT.md`.)
**Cards:** `onboard-gate` · `receipt-verify` · `port-crossing`.
**Steps:** (1) the user mints a self-held key at onboard — identity replaces "sign in with…"; (2) an action the
user gates is default-deny — a human-approved, receipted grant replaces the bearer token; (3) any reach to an
external resource server is a **Port crossing** (open → declared boundary → named-human sanction → receipt); (4)
revoke = refuse / grant expiry / clean exit.
**Kill-targets:** no hosted IdP · no long-lived ambient token · Port-only external reach · no custody of user authority.
**Anti-patterns:** issuing an internet-facing bearer token · a refresh secret that lives forever · calling the
resource server directly without a crossing.

## 2 · Compliance evidence pack
**Intent:** hand an auditor a bundle they can verify without trusting the vendor — because there is no vendor in
the verification path.
**Cards:** `object-model` · `receipt-verify` · `identity-keystore`.
**Steps:** (1) every governed act is already an authored, hash-chained version under one mandate; (2) derive one
integrity root over the object population (`ObjectRegistry.population_root`); (3) the auditor recomputes the root
from the object list alone and checks each receipt's signature offline (`verify_node_act`); (4) provenance and
mandate on every version make the trail self-describing.
**Kill-targets:** verification is the auditor's, never "verified by us" · no central attestation authority · no
value in the pack (evidence, not money).
**Anti-patterns:** a compliance dashboard that asserts state instead of replaying the chain · a signature the
examiner must call your API to check · mutating a record in place.

## 3 · Internal ERP-ish app, propose-only
**Intent:** an internal line-of-business app records and moves governed business objects, but **proposes** — it
never holds the mandate root, and material changes need a human hand.
**Cards:** `object-model` · `onboard-gate` · `receipt-verify`.
**Steps:** (1) model business objects as governed versions under a mandate (`ObjectRegistry.append`); (2) the app
proposes a change; (3) an act the operator marked gated is default-deny until a named human approves; (4) the
result is a receipt anyone can verify. Cross-mandate reads need a declared `SharingRule` or are refused.
**Kill-targets:** the app never holds the mandate root · no cross-mandate access without a declared rule · no
silent state change · money-path off (record a directive, never move value in-node — settlement is Port-only).
**Anti-patterns:** an app service account with unlimited authority · reading another mandate's objects with no
rule · treating a "current value" cache as truth over the replayed chain.
**Exit & non-hostage:** the mandate holder can export the full object chain and walk; nothing is held for them.

## 4 · P2P receipted message
**Intent:** two nodes exchange messages that are receipts, validated by each side independently — no hub.
(Runnable: `examples/p2p_messaging/`.)
**Cards:** `identity-keystore` · `peer-recognition` · `messaging` · `clean-exit`.
**Steps:** (1) each node holds its own key; (2) mutual recognition, verified public-only; (3) `send_message`
registers a provenance-carrying, integrity-bound message; (4) `carry_to_peer` → `receive_from_peer` — the far
side validates over the packet's own bytes; a wrong stated root or a tampered payload is refused.
**Kill-targets:** no broker/hub takes custody · no central validator · fail-closed on any failed check.
**Anti-patterns:** routing messages through a server that can read or alter them · trusting a central "valid"
verdict · accepting a packet whose root you did not check.
**Exit & non-hostage:** `refuse_recognition` ends the relationship with no residual claim; `clean_exit` severs
every grant and the node walks with its keys and records.

## 5 · Integrity file share
**Intent:** store a file as the owner's object and share it only through a governed path — no silent public
bucket. (Runnable: `examples/file_storage/`.)
**Cards:** `storage-integrity` · `object-model`.
**Steps:** (1) `store_datum` writes an owner-scoped datum with a Merkle root over its bytes; (2) the owner reads
it whole; (3) another party with no rule is refused (deny-by-default); (4) the owner declares a `SharingRule`
naming exactly this datum and party; (5) altered bytes fail integrity on read.
**Kill-targets:** no central store owns the data · no standing trust across data · no silent public bucket · no
altered data served.
**Anti-patterns:** uploading to a bucket a central service controls · serving bytes without checking the root ·
widening access without the owner declaring a rule.
**Exit & non-hostage:** the datum is the owner's object; revoking a share is simply not presenting the rule
again — no grant stands on its own.

## 6 · Distributed job — propose / gate / receipt (coordination only)
**Intent:** coordinate a unit of work across nodes as receipted proposals and human-gated acceptances. This is
**coordination and attestation only** — it schedules *who agrees to do what* and records receipts. It is **not**
a distributed-compute engine and makes **no** claim to execute, schedule, or run workloads across machines.
**Cards:** `peer-recognition` · `messaging` · `onboard-gate` · `receipt-verify`.
**Steps:** (1) nodes recognize each other; (2) the initiator sends a receipted proposal describing the unit of
work (`send_message`); (3) a receiving node's operator accepts or declines — an act it chose to gate is
default-deny; (4) the acceptance is a receipt each side verifies offline; (5) completion is reported as another
receipted message. The node governs the *agreement and the record*; the actual work runs in each node's own
runtime, outside this surface.
**Kill-targets:** coordination only — **no distributed-compute / no remote-execution claim** · no hub schedules
the work · no central validator of acceptances · Port-only for any external reach the work needs.
**Anti-patterns:** describing this as "distributed computing" or a job runner · a central scheduler that assigns
work · one node executing another's code off this surface.
**Exit & non-hostage:** any node declines a proposal freely; `refuse_recognition` / `clean_exit` leaves no
residual obligation — no node is bound to coordinate.

## 7 · Gated external send
**Intent:** reach an outside relay/webhook/SaaS/model only through a sanctioned Port crossing. (Runnable:
`examples/gated_external_send/`.)
**Cards:** `port-crossing` · `receipt-verify`.
**Steps:** (1) `open_crossing` to a named external target, carrying a directive/reference (never value); (2) an
undeclared boundary is refused; (3) the node declares the boundary rule; (4) a **named human** sanctions →
receipt; (5) the receipt records that the crossing happened, not the payload.
**Kill-targets:** Port-only external reach · deny-by-default · named-human sanction · money-path off (a directive
crosses, never value).
**Anti-patterns:** calling the external API directly · auto-approving with no named human · the Port holding a
balance.

## 8 · Onboard a new user or node
**Intent:** a first-boot ceremony where the user accepts their own key and chooses their gates.
**Cards:** `onboard-gate` · `identity-keystore` · `receipt-verify`.
**Steps:** (1) run the 5-turn onboard — no key is written before the turn-1 accept; (2) the user names the node
and picks which acts always need their hand; (3) they approve or deny a first gated act; (4) a signed receipt is
emitted; (5) the user verifies it offline with the printed snippet.
**Kill-targets:** no key before accept · AI proposes, human disposes · no telemetry / phone-home / default peers.
**Anti-patterns:** auto-accepting the ceremony · shipping a default peer list · removing the human hand from a
gated act.

## 9 · Clean handoff / exit
**Intent:** a user or node leaves — or hands on across a generation — with keys and records intact and no
residual claim.
**Cards:** `clean-exit` · `peer-recognition` · `identity-keystore`.
**Steps:** (1) `clean_exit` severs every recognition, delegation, and membership — an executable act signed with
the peer's own key; (2) prior grants verify DEAD after severance; (3) `walk_with_keys_and_records` — the peer
leaves whole; (4) `exit_green_light` is ON only when every grant is severed, keys are sole-held, and no claim was
retained.
**Kill-targets:** exit is executable, not prose-reversible · no residual grant / escrow / custodian · the peer
walks with its keys and records.
**Anti-patterns:** "deactivation" a central party can undo · keeping a user's records after they leave · an exit
that leaves a grant live.
**Exit & non-hostage:** this pattern *is* the exit guarantee — a hostage anywhere turns the green light off.

## 10 · Recognize-then-collaborate
**Intent:** establish a mutual, verifiable relationship, then exchange scoped, receipted work — and end it
cleanly.
**Cards:** `peer-recognition` · `messaging` · `clean-exit`.
**Steps:** (1) mutual recognition, verified by both parties only; (2) each shares a self-declared, scoped view
(`scoped_visibility`) — not a central lookup; (3) they exchange receipted messages, each validated
independently; (4) either party refuses or cleanly exits to end it.
**Kill-targets:** no central registry/directory/score-as-authority · no hub between the parties · refusal leaves
no residual claim.
**Anti-patterns:** a central directory that ranks peers · using a reputation score as a permission · a "block"
that leaves a lingering claim.
**Exit & non-hostage:** `refuse_recognition` and `clean_exit` both end the relationship with no residue.

---

## Reading the patterns

Every "card" above resolves in `docs/CAPABILITY_CARDS/` to a `callable_path`, its verbs, its `gate_required`, its
receipt shape, and its own kill-targets. Where a pattern has a runnable example, the example is the copy-paste
template and doubles as a regression test. See `docs/NODE_INTEGRATION_GUIDE.md` for the mental model and
`docs/INTENT_MAP.md` for how Human ↔ App ↔ Port ↔ Node ↔ Peer/Exit fit together.
