# BCK — Builder Brief (v0)

**PROPOSE / DRAFT ONLY · KM/owner disposes · own node only · no auto-sanction · no hosted tools.**

That line is the charter. Everything below serves it. The Breathline Composition Kit lets you compose the
sovereign node's **PRESENT** capabilities into one coordinated capability, on **your own node**, without
re-reading the whole shelf and without any claim drifting from what the code does. It is **infrastructure, not
an app**; a **floor with published scope**, never a certification.

Pinned kernel tip: **`710a40f`** (post-confidentiality-shield). Every artifact prints its tip.

## The four parts

| part | file | what it is |
|---|---|---|
| **Graph** (GB) | `bck/compose_graph.yaml` + `compose_graph_generator.py` | the node's routes → verb → owner-gate → fences → test IDs → series cite, **harvested from the tree**, never hand-authored. 78 routes · 61 PRESENT-with-tests · 19 owner-gated. `--check` is the CI drift gate. |
| **Contract** | `bck/coordinated_capacity.schema.yaml` + `.instance.yaml` | how to wire EXISTING routes into ONE capability (coordinated capacity, first domain). A step is **PRESENT only if it cites passing test IDs** (H5). |
| **Verifier** | `bck/fence_verifier.py` (+ `bck/fixtures/`) | run it against **your own node** to check the fences held on the paths you drove. Three states (PASS/FAIL/NOT-DRIVEN), a SCOPE block every run, no credentials, and seeded fixtures that prove each probe can FAIL. |
| **Brief** | this file | the charter + how to use the kit honestly. |

## How to compose one capability (the loop)

1. **Read the graph** for the routes you need — take only rows where `present: true` (they cite tests).
2. **Draft** the composition as a contract instance (copy `coordinated_capacity.instance.yaml`'s shape). For
   every step, cite the **passing test IDs** that prove it. No test → the step is **not PRESENT**; do not ship it.
3. **Run the cited tests** on your node's checkout — all must pass:
   `python3 -m pytest <the test_ids from your instance> -q`
4. **Run the fence-verifier** against your own node and record the SCOPE block:
   `python3 bck/fence_verifier.py --node-url http://127.0.0.1:8421 --tip $(git rev-parse --short HEAD) --store <SUBSTRATE_STORAGE_ROOT>/objects.ndjson`
   For the GET-only boundary probe, also pass `--web-url <your operator web> --access-log <node log>`.
5. **Dispose at the keyboard.** The kit drafts; **you** run every consequential act (store, gate approve/deny,
   Port sanction). The verifier itself holds no credential and its mutating probes exist to be refused.

## Hard fences (HOLD-class — a build that crosses one is not shippable)

- **No landlord / no hosted tool.** The kit is scripts + data on your own node. No shared broker, no daemon,
  no endpoint that holds anyone's node or credential.
- **Owner disposes.** No auto-sanction, no auto-approve. Consequential acts are the owner's keyboard.
- **Value-free.** No `value/amount/funds/balance/held` in any receipt (money-path OFF).
- **No custody.** Storage keeps the integrity root, never the bytes.
- **Own node only.** The verifier and every drive target the URL you pass — your node, not someone else's.
- **Floor, not ceiling.** BCK output and docs never claim a capability is proven-beyond-its-scope or safe by
  blanket assertion — the kit reports what held on the paths named in SCOPE, and nothing more.
- **No platform theater.** `compose_graph.yaml` carries **sealed-series homes only**. A platform≈series map
  ("X ≈ S6/S10") stays in ADR-0001 Appendix A until it passes the four-layer check (substrate → pin → boundary
  → consumer). Never assert it as machine truth.
- **Do not touch a WP4 pilot daily-path file.** BCK is new files under `bck/` only.

## Cold-agent acceptance (the ↔'s test, AA-scored)

A fresh agent, this kit, and its **own node** should be able to draft and run **one thin fence-passing capacity
slice** — with the owner disposing — and the fence-verifier prints a clean SCOPE block. It fails if a hub,
custody, a second authority, or an auto-sanction appears. That test is AA's to score; this brief is what the
cold agent reads first.
