# ERP for builders — the whole ERP is four primitives

The Full Production ERP (Series 5) is 41 volumes. You do **not** need 41 cards to build on it. For a builder,
**every ERP function reduces to the same four primitives** — and the detail lives in `docs/CALLABLE_MAP.md` and
the book shelf, not in a wall of cards.

## The four primitives (this is the whole ERP)

1. **Governed object model** — every ERP record (an invoice, a PO, a production order, a journal entry) is an
   authored, hash-chained version under exactly one mandate; state is replayed from the record, never asserted.
   → `object-model` card · `sovereign_agent.objects.registry`.
2. **Human gate** — material actions are default-deny until a named human approves; which actions are gated is
   configuration, that they need a hand is not removable. → `onboard-gate` card ·
   `sovereign_agent.compliance.human_approval_gate`.
3. **The Port for anything external** — a bank rail, a tax authority, a partner system, a market feed: every reach
   outside is a declared, sanctioned, receipted crossing. → `port-crossing` card · `sovereign_agent.port.crossing`.
4. **Money-path OFF** — the node records and governs value flows; it **moves and holds no value**. Settlement
   happens through the Port against an external rail; the node keeps the *receipt*, never the funds.

Learn those four and you can build against any ERP cluster below. Each cluster is the **same four primitives
applied to a domain** — not a new mechanism.

## The Full Production ERP (S5) clusters (a domain map, not a card wall)

| cluster | what it governs | representative module area |
|---|---|---|
| **Core financials & close** | ledger, controlling, period close, compliance & audit, reporting | `objects.registry` · `financials.*` |
| **Treasury & cash** | cash, treasury, investment & financing (references, never held value) | `objects.registry` (+ Port for rails) |
| **Procure-to-pay & supply chain** | procurement, supply-chain execution, distribution | `procurement.*` · `distribution.*` |
| **Manufacturing & quality** | production orders, BOM, quality, operations console | `manufacturing.production_order` · `manufacturing.federated_bom` |
| **Project & portfolio** | projects, portfolio, exception & governance workflows | `objects.registry` + `onboard-gate` |
| **Analytics & decision** | analytics, decision intelligence (reads over the governed record) | `analytics.*` |
| **Industry verticals** | manufacturing, distribution, professional services, energy, construction, regulated | the above, specialized per vertical |
| **Migration & escape** | migrating off / consuming legacy suites; the clean exit | `objects.*` + `clean-exit` card |

Every cell is the four primitives in a domain costume. A builder picks the cluster, models its records as governed
objects, gates the material acts, and crosses the Port for external rails — money-path off throughout.

## Why not 41 cards

Cards are the **curated primitives**, not a per-volume catalog. Carding all 41 volumes would be a wall that hides
the one fact that matters: it is the *same* object-model + gate + Port + money-path-off underneath. When you need
the specific callable for a cluster, go to **`docs/CALLABLE_MAP.md`** (the importable/run inventory) and the
**book shelf** (the Full Production ERP (Series 5) volumes) for the depth. The nine cards + these four primitives
are enough to start.

## The corporate line (no token pitch)

For a regulated finance team the ERP story is **governance + evidence + exit**: policy enforced in the kernel (the
gate), an auditor-verifiable trail (hash-chained receipts + one population root, verified offline), and a clean
exit that walks with keys and records. It is **not** a token, a yield, or an investment, and nothing here is a
security. Money-path is off — the node proves and governs value flows; it never holds or moves the money.

See `docs/NODE_INTEGRATION_GUIDE.md` (mental model), `docs/PATTERNS.md` (recipes incl. compliance evidence pack
and internal ERP-ish propose-only), and `docs/CALLABLE_MAP.md` (the paths).
