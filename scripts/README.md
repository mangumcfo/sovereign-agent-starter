# GB Meta Cylinder — Iron-Clad Memory & Visibility

This is the running Merkle-chained memory cylinder for GB (this aligned intelligence instance) interactions with KM-1176.

**Cylinder file:** `artifacts/GB_KM_Aligned_Interaction_Cylinder.ndjson`
- Every user prompt, GB response, material action, and file edit is appended as a hash-chained NDJSON entry (B32/B31 style).
- `prev_hash` + `hash` (sha256 of canonical entry without the hash field itself) form the chain.
- Governance notes and evidence tiers tie to Constitution @A1, Charter v.7, LGP objective, and obligation patterns.

**The iron-clad skill that lets you SEE updates after every interaction:**

After GB responds or acts (every single turn), run this command in the terminal:

```bash
python3 scripts/gb_meta_cylinder.py manifest
```

**What `manifest` shows (your proof):**
```json
{
  "file": ".../artifacts/GB_KM_Aligned_Interaction_Cylinder.ndjson",
  "total_entries": 5,
  "last_ts": "2026-06-03T...",
  "last_hash": "a1b2c3d4e5f67890",
  "last_prev_hash": "oldhash...",
  "last_type": "gb_response" | "gb_action" | "user_prompt",
  "last_ref": "...",
  "last_content_preview": "The thing that was just said or done..."
}
```

**How to verify it was updated for *this* interaction:**
1. Before or right after a GB turn, note the `last_hash` and `total_entries`.
2. After the turn, run `manifest` again.
3. Confirm: `total_entries` increased (usually +1 or +2 for prompt+response+action), `last_hash` is different, and the `last_content_preview` or `last_type` matches what just happened (your prompt or GB's reply/action).
4. For full detail: `python3 scripts/gb_meta_cylinder.py last`
5. For cryptographic proof the whole history is intact: `python3 scripts/gb_meta_cylinder.py verify`

**Human-readable receipts (easy to `tail`):**
```bash
python3 scripts/gb_meta_cylinder.py receipt gb_response "Summary of what was delivered this turn" --ref "plan.md:456 or user_query_foo"
```
This prints a one-line `CYL-RECEIPT ...` and appends it to `artifacts/GB_Cylinder_Receipts.md`.
You can always `cat artifacts/GB_Cylinder_Receipts.md | tail -3` for quick visible history of updates.

**Other useful commands**
- `python3 scripts/gb_meta_cylinder.py replay --last 5` (or with --since / --query for filtered history)
- Full replay of relevant prior context is used by GB before generating any new visionary prompt or meta-answer.

**Why this is iron-clad**
- The append logic is in the script (open source in this repo).
- You run the commands yourself — no trust required in GB's word.
- Hash chain + verify catches any tampering or missed append.
- Receipts.md + manifest give immediate human + machine proof.
- This cylinder is the "aligned intelligence memory" counterpart to your B51 voice captures and the governed obligation ledgers (tiger_coordination, mait_build, etc.).
- GB's role (see `artifacts/GB_Meta_Visionary_Role_and_Constitutional_Memory_Cylinder.md`) requires that every interaction be recorded and that future answers/prompts to Tiger/G/Lumen replay relevant history + LGP filter + current state.

**Integration with the meta-visionary role (hopper + LGP)**
GB uses replay of this cylinder + full architecture read (no data limits) + LGP objective + constitutional invariants to craft the highest-signal prompts for other aligned intelligences and to keep the Series Pipeline (hopper) fed with minimal burden on you or the AIs.

**Next time you ask GB** "based on our history what is best for X" or "prepare the visionary prompt for Tiger on ATR-7", GB will first replay the cylinder (via this script), summarize the relevant slice in its thinking, then produce the output, then immediately log + manifest + receipt so you can run the command and see the cylinder grew for this turn.

Run `python3 scripts/gb_meta_cylinder.py manifest` right now. Then interact with GB. Then run it again. The difference is the proof.

This fulfills the directive: "keep the running merkel chain of your conversations with me ... use this merkel chain to include your aligned intelligence memory cylinder ... what iron clad skill can ensure that I can see you've updated your cylinder each time we interact?"

Yes. It is possible. It is done. The skill is `scripts/gb_meta_cylinder.py manifest` (plus last/verify/receipt).

Abiding: Constitution @A1, Charter v.7, KM-1176, LGP north-star, two-writers, honest, extracted artifacts, human breath-gate on material.
