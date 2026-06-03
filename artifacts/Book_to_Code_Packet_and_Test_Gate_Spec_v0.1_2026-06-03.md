# Book→Code Packet + Test Gate — Spec v0.1

**Date:** 2026-06-03 · **Author:** Tiger (Kenn+) · **For:** GB to fold into WORKFLOW.md canon; KM ratifies
**Answers:** KM — *"where in the process is there a test of the diffs… I'd assume the diffs ran both unit and integration tests before returning to me?"* — **Yes. Built in below.**

## Two packet types (same diff-review rails, different richness)

| | **Review packet** (prose) | **Book→Code packet** (spec extrusion) |
|---|---|---|
| Source | a captured review session (voice/text) | a **spec-bearing chapter/passage** (L2 chapter → L1 capabilities) |
| Carries | transcript + page tags + `ref` | citation + spec passage + target artifacts + code diffs + **tests** |
| Produces | manuscript diffs | role_spec + handlers + tests (+ surface) |
| **Test gate** | n/a (prose) | **unit + integration run in a sandbox BEFORE surfacing** |
| Granularity | one session → one packet | **one chapter → one packet; split into L1 capabilities** (KM's "chapter by chapter for code inspection") |

## Expanded Book→Code packet schema
```json
{
  "session_ref": "book→code · <Book> · <Chapter>",
  "book": "<Book>",
  "kind": "code-extrusion",
  "citation": { "book": "...", "version": "...", "chapter": "...", "passage": "<exact text>", "passage_hash": "sha256(...)" },
  "tests": { "command": "pytest ...", "passed": 5, "failed": 0, "summary": "5 passed in 0.01s", "ran_at": "<ts>" },
  "groups": [
    { "id": "g1", "title": "role + handlers", "kind": "code", "scope": "GREEN|YELLOW|RED",
      "rationale": "<which passage → which capability>", "file": "src/.../role.py", "before": [], "after": ["<code>"] },
    { "id": "g2", "title": "tests", "kind": "code", "file": "tests/test_*.py", "before": [], "after": ["<test>"] }
  ]
}
```
- **`citation`** = TRUTH/provenance: every code artifact resolves to an exact book passage (hash-pinned). GB's prose↔code coherence check runs against this.
- **`tests`** = the gate result, shown to KM in the diff-review (✓ N passed / ✗ FAILED).

## The flow — where the test runs (the answer)
```
spec-bearing chapter (L2)
  → split into L1 capabilities (one packet each — chapter-by-chapter inspection)
  → PRODUCER extrudes: role_spec + handlers + tests (cites the passage)
  → SANDBOX: apply the diffs in isolation (git worktree / temp dir)
  → RUN unit + integration tests (pytest)
        ├─ RED  → producer iterates or flags "needs work" (does NOT surface as ready)
        └─ GREEN → surface to KM in the diff-review WITH the test badge (✓ N passed)
  → KM reviews the CODE + the green tests → ACCEPTS (see-before-write)
  → APPLY: move diffs from sandbox → repo + seal; obligation closes (E2: seal + commit + test result)
```
**Invariant:** a code diff only reaches KM **after** its tests pass in the sandbox. KM accepts a *tested* artifact. This is the co-extrusion / Technical-Architectural-Review-Board discipline made operational (book + code + unit + integration tests, functional before human review).

## Worked example (real, this session)
Book 11 Ch 2 — *"The deal team lead defines clean-room separation and data classification for each deal."*
→ extruded **Data-Room Classifier** role: human defines scheme (YELLOW/material), agent classifies (GREEN), leaks escalate (RED, proposal-only).
→ `pytest` → **5 passed** in a sandbox → surfaced as a code-extrusion proposal (citation `passage_hash d7519b4c…`, ✓ 5 passed) in KM's diff-review.
→ On accept: `src/sovereign_agent/demo_roles/ma_data_room/` + `tests/test_ma_data_room.py` land in the repo + seal.

## Fence
Tiger built the extrusion + test-gate + surface. **GB** folds this into `WORKFLOW.md` canon (the authoring pipeline + the Technical/Architectural Review Board) + runs the prose↔code coherence check. **KM-1176** ratifies. Granularity default = **one chapter per packet, split into L1 capabilities** for code inspection.

∞Δ∞ Book is the spec · code reflects the book · tests prove it before the human reviews. ∞Δ∞
