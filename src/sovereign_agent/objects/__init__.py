"""sovereign_agent.objects — the Sovereign Object Model (S5-05 extrusion).

Book→code extrusion of S5-05 "Sovereign Object Model — Registry, Manifests &
Merkle Integrity". Every module below lands against a seal-blocking HOLD on the
volume's extrusion ledger; the ledger row cites the acceptance test that proves it.

Implemented slices (each backed by its cited acceptance test):
  identity.py     stable object identity; versions carry author + resolvable
                  source_ref (R22-3 provenance law reused, never duplicated)   E2-2
  registry.py     append-only version store; one integrity root over the
                  whole population, recomputable byte-identical               E2-1
  lifecycle.py    value-at-date with approver · append-only change · close-as-
                  version · envelope refusal with the rule cited      E1-2 E5-1/2/4
  manifest.py     manifest cut over the registry, verifies by recompute;
                  period-end manifests chain to their predecessors        E3-1 E3-3
  proofs.py       Merkle membership proofs (same tree convention as
                  evidence.export_packet, cross-checked) · replay vs
                  proof-only agreement                                    E4-1 E4-4
  scope.py        exactly-one-mandate scoping · per-mandate roots ·
                  scoped-sharing grants nothing wider                     E6-1 E6-4
  migrate.py      origin-asserted cutover stamps · unsourced never seals ·
                  attestation reconciliation                              E7-1 E7-3
  inheritance.py  successor packet verifying offline · unsourced always
                  disclosed                                               E8-1 E8-4

Substrate reused (Step-0 dig law — never re-implement what exists):
  evidence.export_packet   _sha/_canon/_merkle_root (canonical bytes + tree convention)
  obligations.provenance   _assert_source_ref_resolves (a citation is never written false)

Money-path and any live-host claim remain OUT of scope: this package is the object
model's mechanics. runs_today posture is governed by the volume ledger, not by this file.
"""
