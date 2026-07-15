# Governance — The Constitutional Kernel

This kernel enforces four runtime invariants. They are not features you can
toggle — they are conditions of the license (LICENSE §3a) and the reason
this software is safe to hand to an agent.

**K1 · Human Primacy.** Every consequential act starts with you — a living
person, aware, deciding — and the responsibility for it stays with you.
The node proposes; you approve; only then does it execute. Trivial actions
run free, but anything material — moving value, changing records of
consequence, acting on your behalf in the world — stops at the approval
gate and waits for a human hand.

And this is enforced, not promised: in the code, a material obligation on
a ledger with no human gate is *refused outright* — denied, fail-closed,
and written into the record as a denial (`ledger.approve()`, the AH-1
rule). The routes that execute code on your machine accept only the
owner's authenticated approval (`require_owner`) — "execute after
approve" is authorization logic, not a docstring. You can replay the
chain and see every approval, and every refusal, that ever happened.

Why it matters beyond safety: authority that stays with people is what
lets prosperity compound to people. A system whose decisions originate in
human intent — and whose record of those decisions can be handed, intact,
to the next generation — builds wealth that belongs to a family line, not
to whoever operates the machine. The tool serves the living; the living
answer for the tool. That ordering is the whole architecture.

**K2 · Default-Deny.** Nothing is permitted until you permit it. Roles
declare their capabilities in YAML you can read; anything undeclared is
refused. Adding power is always an explicit, visible act.

**K3 · Audit-Immutable.** Everything of consequence is written to a
hash-chained record you hold. Any tampering breaks the chain loudly on
replay. Verify anytime: `python3 scripts/ledger_manifest.py verify`.

**K4 · Constitutional-Validated Extension.** The node grows only through
validation against your declared rules. New roles load through spec
validation; new code enters through your review. It never quietly
extends itself.

**Why license-conditioned:** a fork that keeps this source but strips these
invariants at runtime would look like this software and behave like its
opposite. LICENSE §3a makes such a fork unlicensed. Fork freely — the
right to leave is the point — but what you ship under this lineage keeps
a human in command, denied-by-default, on a record that cannot quietly lie.

*Changes to this document track the license version and are gated by the
repository owner.*
