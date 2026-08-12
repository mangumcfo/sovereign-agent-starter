# Example — gated external send (Port only)

Your app needs to reach something **outside** the node — an email relay, a webhook, a SaaS API, a model
endpoint. This shows the only blessed way: a governed **Port crossing**, deny-by-default, sanctioned by a named
human, returning a receipt that the crossing happened — never the payload or value. Composes the sealed Port
floor only; builds no connector, queue, or relay.

## Run it

```bash
# from the repo root, after `pip install -e .` (see RUN_THE_NODE.md)
python examples/gated_external_send/run_gated_send.py
```

No arguments, no network, no account. Throwaway temp dir, cleaned up. **Exits non-zero on any failed
assertion** — it doubles as a regression test.

## What it proves (each line asserts)

| step | act | sealed floor | assertion |
|---|---|---|---|
| 1 | open a crossing | `port.crossing.open_crossing` (Inter-Node Sovereignty (S6) V07) | a directive/reference crosses — never value |
| 2 | undeclared boundary | `sanction_crossing` with no rule | **refused — deny-by-default** |
| 3 | declared, no human | `sanction_crossing` with a rule but no approver | **refused — no silent send** |
| 4 | declared + named human | `sanction_crossing` with rule + approver | sanctioned → **receipt** (boundary, root, approver) |
| 5 | receipt not value | inspect the receipt | **no `value`/`funds`/`balance`/`held`** field — money-path OFF |

## Kill-targets held (do not violate when you build on this)

- **Port is the only blessed path outward** — no direct external call.
- **Deny-by-default** — an undeclared boundary is refused, not reached.
- **A named human sanctions every external reach** — no silent send.
- **Money-path OFF** — the Port carries a directive, never value, and holds nothing.

## How an app attaches

Your app supplies the directive (what to send, to which external target) and surfaces the sanction decision to a
named human. It never calls the external service directly and never moves value through the node. The `send` in
the instruction is a **reference** your app's own transport resolves *after* the crossing is sanctioned — the
node governs and attests the reach; it does not open the socket.
