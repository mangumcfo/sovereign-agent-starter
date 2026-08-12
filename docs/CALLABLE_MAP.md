# Callable Map — the inventory of importable / run paths

**One line:** the CALLABLE_MAP is the **inventory of importable/run paths** in this repository — the modules and
callables a builder can actually import and run. The **nine capability cards** (`docs/CAPABILITY_CARDS/`) are the
**curated subset** of this inventory: the primitives most builders reach for first, each with a callable path,
verbs, gate, receipt shape, and kill-targets. This map is the fuller ground the cards are drawn from; the book
shelf (Series 0–14) is where each path is *taught* in depth.

Every path below imports on a fresh public clone (verified). Labels: **RUN** = a callable path you run directly ·
**RUN-partial** = callable here, with a deeper surface taught in the shelf or hosted in the authoring layer ·
**teach** = reading, not runtime.

## Runtime primitives — the areas the cards draw from

| area | module path | key callables | label | card |
|---|---|---|---|---|
| self-held identity | `sovereign_agent.keystore.node_keystore` | `generate_node_key` · `load_node_key` · `sign_node_act` · `verify_node_act` · `node_fingerprint` | RUN | `identity-keystore` |
| onboard + gate | `sovereign_agent.onboarding.onboard` · `sovereign_agent.compliance.human_approval_gate` | `run_onboard` · `cli_onboard` · `verify_onboard_receipt` · `DEFAULT_GATED_ACTS` · `HumanApprovalGate` | RUN | `onboard-gate` |
| receipt verify | (above) `verify_node_act` · `verify_onboard_receipt` · `verify_recognition` | — | RUN | `receipt-verify` |
| peer recognition | `sovereign_agent.peerhood.recognition` | `mutual_recognition` · `verify_recognition` · `refuse_recognition` · `scoped_visibility` | RUN | `peer-recognition` |
| clean exit | `sovereign_agent.peerhood.clean_exit` | `clean_exit` · `exit_green_light` · `walk_with_keys_and_records` | RUN | `clean-exit` |
| messaging | `sovereign_agent.messaging.inter_node` | `send_message` · `carry_to_peer` · `receive_from_peer` | RUN | `messaging` |
| the Port | `sovereign_agent.port.crossing` | `open_crossing` · `sanction_crossing` | RUN | `port-crossing` |
| object model + scope | `sovereign_agent.objects.registry` · `sovereign_agent.objects.scope` | `ObjectRegistry` · `SharingRule` · `check_access` | RUN | `object-model` |
| datum storage | `sovereign_agent.storage.sovereign_store` | `store_datum` · `retrieve_datum` | RUN | `storage-integrity` |

## Wider sealed runtime (not carded — reach via the module path)

| area | module path | key callables | label |
|---|---|---|---|
| obligation ledger | `sovereign_agent.obligations.ledger` | `ObligationLedger` (open/approve/close, hash-chained receipts) | RUN |
| value attribution (Sovereign Livelihood, Series 10) | `sovereign_agent.economy.income` · `sovereign_agent.economy.pool` | `income_record` · `attribute_income` · `verify_income` · `form_pool` · `contribute_to_pool` · `pool_settlement` — **money-path OFF** (`MONEY_PATH_BREACH_FIELDS`); settlement is Port-only | RUN-partial |
| generational transfer (Series 12) | `sovereign_agent.estate.generational_transfer` | key-epoch / family-quorum recovery | RUN-partial |
| ERP modules (Full Production ERP, Series 5) | `sovereign_agent.manufacturing.*` · `.distribution.*` · `.procurement.*` · `.services.*` | production orders, BOM, order lifecycle (governed objects) | RUN-partial — see `docs/ERP_FOR_BUILDERS.md` |

## Reading-path callability (Series 2–4, KM-audited)

Series 2–4 are **not** teach-only — each volume resolves to a real callable path on the public clone:

- **RUN:** Building the Agentic Harness (S2) V1 · Programmable Sovereign ERP (S3) V1, V2 · Sovereign Token & Economic Organism (S4) V1, V2.
- **RUN-partial:** Building the Agentic Harness (S2) V2/V3/V4/V5 · Programmable Sovereign ERP (S3) V3/V4 · Sovereign Token & Economic Organism (S4) V3/V4.
- **teach:** Series 0–1 (the lens and the executive playbooks) are reading, not runtime.
- Series 5–14 are the sealed executable runtime the cards and the wider inventory above are drawn from.

> **T-04:** the Sovereign Token & Economic Organism substrate is *callable* (an obligation ledger + Merkle
> accumulator); it is **not** a public token, coin, yield, or investment offer, and money-path is off.

## How to use this map

1. Start from `docs/NODE_INTEGRATION_GUIDE.md` (the mental model) and the **nine cards** (the curated subset).
2. Need something a card doesn't cover? Find the **module path** here and import it — everything listed runs on a
   fresh clone.
3. Want the depth behind a path? Read its volume on the shelf (`docs/READING_PATH_S0_S4.md` for the reading arc;
   the sealed Series 5–14 for the runtime).
