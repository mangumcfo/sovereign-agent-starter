# scripts/ — operational tooling

Command-line tools around the sovereign-agent node: the Atrium review/apply loop, the crypto
assurance cadence, the obligation-ledger utilities, and the read-only projections. Python tools are
run with `PYTHONPATH=src python3 scripts/<name>.py …`; shell tools are executable directly.

## Atrium review/apply loop
- `atrium_producer.py` — autonomous producer: turns an approved obligation into a grouped-diff proposal.
- `produce_proposal.py` — POST a grouped-diff proposal to the node so it appears in the Atrium queue.
- `atrium_apply.py` — auto-apply agent: on the operator's ACCEPT, land an accepted+tested proposal (re-test, local commit, optional seal, close the obligation).
- `atrium_executor.py` — "the bell": on Accept, spawn execution for a packet and receipt it back.
- `atrium_sittings.py` — "the queue is a query": read-only projection of open work as sittings.
- `atrium_sitting_apply.py` — the sitting write-flow: one Accept disposes a sitting.

## Scout (propose-only anti-slop gate)
- `scout_run.py` — deterministic, propose-only, read-only Scout runner (drift + static-scan derivers).
- `scout_lint.py` — the Scout anti-slop gate: mechanical earned-Green RYG + packet-level auto-reject.

## Crypto assurance cadence
- `crypto_vector_check.py` — deterministic, cheap primitives-assurance (vector cross-check vs the sealed root).
- `crypto_assurance.py` — the daily assurance roll-up over the crypto cadence.
- `crypto_cadence_surface.py` — routes the expensive crypto lanes through Atrium (one human gate).

## Obligation ledger
- `ledger_manifest.py` — manifest/verify/last over the node's ObligationLedger (run after any open/approve/close to see it update).
- `ledger_repair.py` — chain-repair command for an already-forked obligation ledger.

## Projections & gates
- `actions_projection.py` — queryable `.actions[]` projection over the Merkle chain.
- `export_packet.py` — evidence-packet exports.
- `qualification_gate.py` — tiered + qualified-reviewer breath-gates.
- `enforcement_claim_lint.py` — mechanical backstop for the `exists_is_not_wired` standard.
- `open_card_parity.py` — the parity invariant that kills the "view out-truthing the ledger" class.
- `coherence_backfill.py` — safe, non-faking extruder for book↔code anchors + honest narrative classification.
- `coherence_reconciliation_queue.py` — turns harvested gaps (Partial + Missing) into governed queue items.

## Shell utilities
- `run_node_api.sh` — start the node API (Flask) for the Atrium's live mode.
- `mint_node_token.sh` — mint a `principal_id` bearer token for the node API.
- `static_scan.sh` — standing static-analysis pass (ruff + vulture + coverage).
