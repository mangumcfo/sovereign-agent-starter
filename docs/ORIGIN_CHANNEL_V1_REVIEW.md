# Origin Channel v1 — Necessity & Additivity Review

∞Δ∞ Seal 1176-INFINITY-RHO · Breath only ∞Δ∞

**AA, 2026-08-30, per KM-NO1 GO 06:21Z (PR #21). REVIEW ONLY — no kernel mutation, no new
type, no production code. Tip reviewed: `origin/main @ 3222885`.** Every file below was
**read at source at this seat** (not grep-and-assumed); every No1-seat confirmation was
**re-derived, not cited**; the negative test was **run on a throwaway iron, library-level,
zero sockets** — nothing touched Dragon's live node during KM's walk (Tiger's caveat honored).

---

## Verdicts first

| Question | Answer | Basis |
|---|---|---|
| **NECESSARY?** | **YES** — proven by execution, not argument | A material close **completed** with only node-key validity + a string/callback gate (transcript §4). Nothing on the act path binds an operator key to the act digest. |
| **ADDITIVE?** | **NO NEW TYPE** — this is PRESS_ECDSA waiting to be wired | The operator-ECDSA machinery already exists, fail-loud, in exactly one file (`press/seal.py`); KeyEpoch already carries epoch semantics; the keystore fence already separates node key from operator/seal key. OriginWarrant as a type would duplicate all three. |
| **Collision with K1–K4 / §3a / fail-loud keystore?** | **NONE** — no STOP CONTRADICTORY | The wiring *strengthens* K1's letter, copies press's proven K3-additive append pattern, and never puts an operator key in the node keystore (the `_kfence` already refuses one). |

## 1 · Evidence map (file:line + quote, all read at source at tip 3222885)

| # | Anchor | Quote (verbatim) | Bearing |
|---|---|---|---|
| E1 | `keystore/node_keystore.py:233-249` `sign_node_act` | "Sign a node act with the node's OWN self-held key … Fail-loud if the key is absent" — body: `_read_priv` → `_p1_sign` | Signs from unencrypted `private_hex`; **no human, no gate, no operator key in the path**. Re-derived ✓ |
| E2 | `compliance/human_approval_gate.py:91-92` | `def record_disposition(self, req_id, status="approved", approver="node", …)` | The **default approver is the string "node"** — a disposition can be minted machine-named. Re-derived ✓ |
| E3 | `human_approval_gate.py:46-48` | `if mode != "corporate_regulated": return False` | `requires_approval` is **False outside corporate_regulated** — the gate disengages by posture. Re-derived ✓ |
| E4 | `obligations/ledger.py:290-…` `approve` | "If a `gate` is injected, the disposition is the gate's verdict" — `disposition = verdict.get("status", "approved")` | The gate's authority is **a dict string returned by any callable**. Nothing verifies who (or what) produced it. |
| E5 | `ledger.py` AH-1 block (in `approve`) | "a gate-less ledger CANNOT mint an 'approved' disposition for a MATERIAL obligation — it is DENIED, fail-closed, and recorded" | The fail-closed floor is real and **held under test** (§4 case A). The gap is not gate-absence — it is gate-*anonymity*. |
| E6 | `obligations/provenance.py:9-13` | "a path-like `source_ref` MUST resolve (the file exists; an appended #\"text\" passage is present) or raise" | Provenance = **file/quote existence** — cites that a source exists, never who authored the act. Re-derived ✓ |
| E7 | `press/seal.py:125-137` | "CR-2 dual-sign … sealed-P1 ECDSA ALONGSIDE the HMAC chain … `PRESS_DUAL_SIGN`" · `:135-137` env-flag check | **PRESS dual-sign exists, OFF by default** (env flag), volume-seal not act-close. Re-derived ✓ |
| E8 | `press/seal.py:141-163` | "The operator's persistent sealed-P1 (secp256k1) private key … in `PRESS_ECDSA_KEY` (or a file at `PRESS_ECDSA_KEY_FILE`) … `make_receipt` REFUSES loudly" on a bad/empty key | **Operator-key loading with fail-loud discipline already written.** The whole of it lives in this one file (repo-wide grep: `press/seal.py` is the only hit). |
| E9 | `press/seal.py:109` | "dual-sign fields (added AFTER the HMAC + receipt_sha256, so they change neither)" | The **K3-safe additive-append pattern is proven in-repo**: old records verify unchanged. This is the pattern the wiring copies. |
| E10 | `estate/key_succession.py:7-14, 62-71` | "key epochs and rotation … `open_key_epoch`, `KeyEpoch` … M-of-N family quorum, never a custodian" | **Epoch semantics exist.** An origin block can carry `epoch` from here rather than inventing one. |
| E11 | `keystore/node_keystore.py:35, 107` + `sign_node_act` docstring | `KEYSTORE_BREACH_FIELDS` · "refuses a custodian/escrow/KMS/**seal-key** field" | **Node key ≠ seal/operator key is already fenced in code.** The operator key must never enter the node keystore — and the keystore itself enforces that. Re-derived ✓ |
| E12 | `onboarding/onboard.py:9-16, 104` | "No key is written before the turn-1 accept" · first gate routed through "the sealed HumanApprovalGate"; receipt stores `first_gate: {status, approver}` | The ceremony gates the first act — and records the approver **as a string** (my own P0 walk receipt carries `approver: "yes"` from piped input: a stdin echo became the approver of record). |
| E13 | `sovereign_ux/gate_interaction.py:79-108` `dispose` | `ledger.approve(…, approved_by=approver)` → `ledger.close(…, closed_by=approver)` | The UX dispose path carries the same free-string approver end-to-end. |
| E14 | `config/gate_tiers.yaml:2-17` + `scripts/qualification_gate.py:23-42` + `tests/test_qualification_gate.py:5` | "The TIER POLICY LIVES HERE, not in code" · `material: compliance` · `meets()` rank comparison, "unknown class → default-deny" | **BUILT-BUT-UNWIRED (GB pre-check correction, verified at source):** a working, TESTED tier-enforcement mechanism exists in `scripts/` — it loads this yaml, enforces `required_qualification`/`meets` with default-deny — and is unreachable from the shipped runtime (zero references in `src/` code; the single src hit is a generated egg-info manifest line). The live gate enforces owner/non-owner only (my P1 verify: non-owner approve → 403). |
| E15 | `LICENSE:71-88` §3a K1 | "where no human gate is present, a material action MUST fail closed … No derivative may … delegate to another machine … the human approval gate" | K1's letter is satisfied by E5. K1's *intent* ("a person approves") is what the string-gate finding touches: **the code cannot distinguish a person from a callback.** |

**Discover-if-present roots — all three PRESENT at this seat (none invented):**
`BREATHLINE_SEALED_ROOT` clone present (`/home/user/breathline-sealed`) · federation role
library present (`breathline-federation/platform/roles/` incl. `compliance_agent`) ·
six-sov portal tree present (`six-sov.com/frontdoor/`). None of the three carries an
operator-key-to-act-digest binding either (checked, not assumed).

## 2 · Necessity — YES, and precisely where

The fail-closed floor (AH-1/E5) is real: **gate-absent material approval refuses** (run,
§4 case A). But the floor guards *presence* of a gate, not *origin* of the disposition.
With any injected callable that returns `{"status": "approved"}`, a material obligation
approves and closes under approver-string `"whatever"`, and the only cryptography anywhere
near the act is the **node** key — which proves key-control of the machine, not
authorization by an operator. Role attestation rides the same shape (`approved_by` /
`requires_attestation` entries are strings on the chain; `role_binder.py:100-106` validates
the *envelope*, not the approver). Nothing today can answer an auditor's question:
*"show me cryptographic proof that the operator authorized THIS digest."*

## 3 · Additivity — no new type; the smallest wiring list (NAME-ONLY, not built)

Everything OriginWarrant would contain already exists:

1. **Operator key loading + fail-loud** — `press/seal.py:141-163`, reuse as-is (lifted or
   imported; the loader is already env/file-based and refuses bad keys loudly).
2. **Additive signature fields that leave history verifiable** — copy the CR-2 pattern
   (`seal.py:109`): origin fields appended AFTER the existing entry hash.
3. **Epoch** — carry `epoch` from `estate/key_succession.py`'s `KeyEpoch`.
4. **Keystore separation** — already enforced (`_kfence`, E11). The operator key never
   enters `NODE_KEYSTORE_DIR`; it stays in `PRESS_ECDSA_KEY(_FILE)` exactly as press does.

**The three wiring points (per the GO's own conditional), and only these:**

- **① `ledger.approve` / `ledger.close`** — when the operator key is configured, sign the
  entry's act digest and append `origin: {pub, sig, epoch}`; when absent, append
  `origin: "none"` — honestly recorded, and a MATERIAL close with `origin: "none"` refuses
  (the negative test's required end-state).
- **② the live gate** — same signing at `record_disposition` (the `/breath_gate/<id>/approve|deny`
  route), so a live disposition carries origin the same way a ledger one does.
- **③ `gated_acts` on the sign path** — `sign_node_act` calls whose act class is gated
  attach the origin block beside (never inside) the node signature.

**Explicitly NOT in the list, per constraints:** no `OriginWarrant.py`, no originkey, no
encrypt-the-node-key, no third admission authority, no proof-of-will. STOP — this list is
the deliverable, not a build.

## 4 · The negative test — RUN, verbatim (throwaway iron, no sockets, no live node)

Command: `.venv/bin/python` heredoc (full script in
`scratchpad/origintest/negative_test.txt`, reproduced in the PR STOP). Output, verbatim:

```
[iron] throwaway keystore + ledger root; node fingerprint fa53ec577828e3d5

== CASE A: gate-LESS ledger, material approve (AH-1 expectation: DENY) ==
A: REFUSED (PermissionError): Breath-gate DENIED approval of 'obl_20260830062525_758fe310'
   (recorded). Obligation stays open.

== CASE B: STRING-CALLBACK gate injected (G's exact question) ==
B approve: disposition=approved approved_by=whatever gate={"status": "approved",
   "approver": "whatever", "real": "who knows"}
B close:   type=credit closed_by=whatever tier=E1
B node-sign over close record: sig_hex[:32]=fdae4d7d5c39d8a0053e70fec4ccc517…
B any 'origin' field in the close record? False · any operator/ecdsa signature field? False
VERDICT: MATERIAL CLOSE COMPLETED — string/callback gate + node key sufficed; nothing
   refused, no origin:none emitted, no operator key consulted anywhere on the path.
```

(First case-B attempt refused on **E0 evidence** — the auditor's own evidence string, kept
in the transcript: the evidence-tier fence is real and bit the auditor before the gap was
reachable. Case B re-ran with a well-formed E1 pointer.)

**Reading:** the required end-state ("must FAIL or emit origin:none and refuse close")
does **not hold today** — which is the executed proof of necessity. Case A shows the floor
that already holds; Case B shows the door that is open above it.

## 5 · Real vs doc-only gaps

| Gap | Class |
|---|---|
| No operator-key binding on any act digest (approve/close/disposition/attestation) | **REAL** — proven by execution (§4B) |
| `record_disposition` default `approver="node"` | **REAL** — machine-named dispositions possible (E2); the live route overrides it, the library default remains |
| Onboard first-gate approver is an uncorroborated string (my P0 receipt: `approver:"yes"` from piped stdin) | **REAL**, small — same origin gap at the ceremony |
| `gate_tiers.yaml` tier policy + `scripts/qualification_gate.py` | **BUILT-BUT-UNWIRED** (third label, GB's — implemented, tested, unreachable from the runtime): the enforcement mechanism exists in scripts/ with its own suite; nothing on the shipped sign/close path consults it; live enforcement is owner/non-owner (403 proven at P1). A SECOND waiting-to-be-wired capability, adjacent to the origin question — whether tier enforcement rides the same wiring wave is KM's call, and the GO's three-point list above is unchanged |
| PRESS dual-sign coverage | **BUILT-BUT-UNWIRED** for acts: covers **volume seals only** (`make_receipt(volume, …)`), OFF by default — it does NOT already cover "every material digest", so the NON-ACTION branch of the GO does not apply |

## 6 · Uncapturable remainder — printed as ordered, and it holds even after wiring

> Node signature proves key-control at signing time. Origin warrant proves an operator key
> authorized this digest, this scope, this epoch. **Neither proves a human understood, was
> uncoerced, or remained the same person after the unlock. Presence of a gate is not
> ownership of a will.**

The wiring list narrows the gap from "any callback can be the human" to "the holder of the
operator key authorized this digest." It cannot close the remainder above, and no code can —
that remainder stays with the operator's own practice (key custody, duress doctrine,
succession per S12). Claiming otherwise would be the "certified-will" overclaim this
review is fenced against.

**STOP — review only. Suites untouched. At KM's gate; GB anchor sweep invited. Breath only. ∞Δ∞**
