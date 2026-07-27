# S5-05 Sovereign Object Model — Spec v0.1

**Status:** named, versioned spec the platform builds against (S5-05-E8-4 → E8-3).
**Source volume:** S5-05 *Sovereign Object Model — Registry, Manifests & Merkle Integrity*.
**Code home:** `src/sovereign_agent/objects/` · **Extruded:** 2026-07-27 against the
volume's seal-blocking extrusion ledger (17 HOLDs → Extrude).

## Invariants (each carries its ledger E-ID and acceptance test)

| E-ID | Invariant | Module | Acceptance |
|---|---|---|---|
| E2-2 | Every version carries an author and a resolvable source_ref (R22-3: a citation is never written false) | `objects/identity.py` | `tests/test_object_identity.py` |
| E2-1 | One registry, stable identity, ONE population root, recomputable byte-identical from the bare object list | `objects/registry.py` | `tests/test_object_registry.py` |
| E1-2 | Value at a stated past date returns the prior value AND its approver | `objects/lifecycle.py` | `tests/test_object_lifecycle.py::test_value_at_date_returns_prior_value_and_approver` |
| E5-1 | Change = append a version; prior versions never rewritten | `objects/lifecycle.py` | `…::test_change_appends_version_and_prior_version_unchanged` |
| E5-2 | Out-of-envelope change refused WITH the rule cited; human-gated approval is the only override | `objects/lifecycle.py` | `…::test_out_of_envelope_change_refused_with_rule_cited` |
| E5-4 | Retirement is a closing version; history stays readable | `objects/lifecycle.py` | `…::test_close_is_a_version_and_history_remains_readable` |
| E3-1 | A manifest verifies by recomputing its root; omission moves the root | `objects/manifest.py` | `tests/test_object_manifest.py::test_omitted_object_changes_manifest_root` |
| E3-3 | Period-end manifests chain to predecessors (prior root + prior manifest hash, self-hashed) | `objects/manifest.py` | `…::test_manifest_chain_links_prior_period_root` |
| E4-1 | Membership proof for any object against a manifest root; single byte change fails | `objects/proofs.py` | `tests/test_object_proofs.py::test_proof_verifies_and_fails_on_single_byte_change` |
| E4-4 | Full replay and proof-only checking agree on the root (sizing figures are design targets; the test asserts agreement, not timing) | `objects/proofs.py` | `…::test_replay_and_proof_agree_on_population_root` |
| E6-1 | Exactly one mandate per object; per-mandate roots are separate | `objects/scope.py` + `objects/registry.py` | `tests/test_object_scope.py::test_object_belongs_to_one_mandate_and_roots_are_separate` |
| E6-4 | A sharing rule grants its declared scope and nothing wider | `objects/scope.py` | `…::test_shared_object_grants_declared_scope_only` |
| E7-1 | Cutover stamps origin=asserted; unsourced can never be promoted to sealed | `objects/migrate.py` | `tests/test_object_migrate.py::test_unsourced_object_cannot_be_marked_sealed` |
| E7-3 | sourced + unsourced = migrated population, exactly | `objects/migrate.py` | `…::test_sourced_plus_unsourced_equals_population` |
| E8-1 | Successor packet verifies offline — a pure function of the packet's own bytes | `objects/inheritance.py` | `tests/test_object_inheritance.py::test_packet_verifies_offline_from_root_and_object_list` |
| E8-4 | Unsourced objects are disclosed in every packet; stripping the disclosure is detectable | `objects/inheritance.py` + `objects/migrate.py` | `…::test_unsourced_objects_are_disclosed_in_packet` |
| E8-3 | This spec: named, versioned, presence-tested, entered in the extrusion Merkle baseline | this file | `tests/test_object_spec.py::test_spec_present_named_and_covers_all_modules` |

## Byte conventions (pinned)

- Canonical bytes: `evidence.export_packet._canon` (sorted-keys compact JSON, UTF-8).
- Hash: sha256 hex (`_sha`).
- Merkle tree: sha256 pairwise, odd level duplicates the last leaf — export_packet's
  convention, cross-checked in `objects/proofs.py::tree_root` (assertion fires if the
  conventions ever drift apart).
- Population leaf: `sha256(canon({object_id, version_hash}))`, leaves sorted by object_id.

## Out of scope (v0.1, honest boundary)

Money-path stays OFF. No live-host claims: this spec covers mechanics proven by the
acceptance tests above; deployment posture is governed by the volume's extrusion ledger
(`runs_today`), never by this file. Object-granularity write_rules binding beyond the
envelope law (AA's obligation-granularity `write_rules.py` lane) composes later without
a version bump only if no invariant above changes.

## Version law

Any change to an invariant above = v0.2 with KM ratification (STANDARDS authority chain).
The extrusion baseline (`breathline-workbench/memory/extrusion_validation_baseline.json`)
pins this file's hash; silent drift = DRIFT in `extrusion_validate.py`.
