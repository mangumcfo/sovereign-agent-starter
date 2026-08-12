# Example B — sovereign file/datum storage

A datum is stored as the **owner's** governed object, integrity-bound by a Merkle root over its own bytes, and
read back only by a **verified, scoped, integrity-checked** access — composing sealed floors only. No store, no
bucket, no cloud host is built here; this is a **thin client** over the kernel.

## Run it

```bash
# from the repo root, after `pip install -e .` (see RUN_THE_NODE.md)
python examples/file_storage/run_storage.py
```

No arguments, no network, no account. It uses a throwaway temp directory and cleans up after itself. It **exits
non-zero if any check fails**, so it doubles as a regression test.

## What it proves (each line asserts)

| step | act | sealed floor | assertion |
|---|---|---|---|
| 1 | store a datum | `storage.sovereign_store.store_datum` (Zero-Trust Sovereignty (S7) V03 · P5 Merkle) | it carries its own **integrity root** over its bytes |
| 2 | owner reads own datum | `retrieve_datum` (own mandate) | returned whole, **integrity verified** — no grant needed |
| 3 | stranger with no rule | `retrieve_datum` (other mandate, no rule) | **refused — deny-by-default** (no silent public bucket) |
| 4 | governed share | `objects.scope.SharingRule` → `retrieve_datum` | owner declares a rule naming **exactly this datum + party**; then that party may read |
| 5 | corruption probe | `retrieve_datum` on altered bytes | **refused** — at-rest integrity fails from the datum's own bytes |
| 6 | phantom read | `retrieve_datum` on a non-existent datum | **refused** (no phantom reads) |

## Kill-targets held (do not violate when you build on this)

- **No central store owns or vouches for the data** — the owner does.
- **No standing trust across data** — every cross-party read needs a declared, named scope.
- **No silent public bucket** — the *absence* of a rule is a refusal, not open access.
- **No altered data served** — integrity is checked on every read.

## Exit & non-hostage

The datum is the owner's own object. The owner walks with it and reads it with **no third party in the loop**. A
share is exactly its declared scope and nothing wider — **revoking is simply not presenting the rule again**; no
grant stands on its own. Nothing holds your data hostage.

## How an app attaches

Your app is the UI and the byte source; the node is the owner-scoping and the integrity check. Your app
**stores** bytes it owns and **retrieves** under the owner's mandate. To share outward, the app asks the owner to
**declare a `SharingRule`** — it cannot widen access on its own. Serving the datum to an *external* system is a
**Port crossing** (`docs/OAUTH_TO_PORT.md`), never a direct push to a public bucket.
