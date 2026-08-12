#!/usr/bin/env python3
"""Reference example — a gated external send: reach an outside relay ONLY through a sanctioned Port crossing.

Thin client. Builds NO connector, NO queue, NO relay of its own. It composes the sealed Port floor only:
  · objects.registry   ObjectRegistry            (S5 V05 governed object record)
  · objects.scope      SharingRule               (the node's declared boundary rule)
  · port.crossing      open_crossing / sanction_crossing  (Inter-Node Sovereignty S6 V07)

The point an app builder must internalize: when your app needs to reach ANYTHING outside the node — an email
relay, a webhook, a SaaS API, a model endpoint, a bank rail — it does NOT call it directly. It opens a governed
**crossing**, the node's own declared boundary rule must authorize it, and a **named human** must sanction it.
The Port returns a **receipt that the crossing happened** — it never holds or moves the payload/value.

What it demonstrates on a bare public clone (no network, no account, no telemetry):
  1. the app opens a crossing to a named external target, carrying a directive/reference (never value itself);
  2. an undeclared boundary is REFUSED — deny-by-default (the node has not consented to this reach);
  3. the node declares the boundary rule; a crossing with no named human is still REFUSED;
  4. with a declared rule AND a named human's approval, the crossing is sanctioned and RECEIPTED;
  5. the receipt records THAT the crossing happened — it carries no value / funds / balance / held field.

Kill-targets held (an app built on this MUST NOT violate):
  · Port is the ONLY blessed path outward — no direct external call;
  · deny-by-default — an undeclared boundary is refused, not reached;
  · a named human sanctions every external reach — no silent send;
  · money-path OFF — the Port carries a directive, never value, and holds nothing.

Run:  python examples/gated_external_send/run_gated_send.py
Exits non-zero on any failed assertion.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.objects.scope import SharingRule
from sovereign_agent.port.crossing import open_crossing, sanction_crossing, CrossingError

AT = "2026-08-11T19:00:00Z"
NODE = "app-node"
TARGET = "email-relay"          # the external thing being reached
BOUNDARY = "external:relay"     # the boundary mandate the node may reach


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        reg = ObjectRegistry(str(Path(tmp) / "node"))

        # 1 · open a crossing — a directive/reference crosses, never value itself
        crossing = open_crossing(reg, NODE, TARGET,
                                 {"send": "message-ref://m1", "to": "external-recipient"},
                                 mandate=NODE, author=NODE, source_ref=f"crossing://{NODE}/1", at=AT)
        assert crossing["version_hash"] and crossing["object_id"] == f"crossing:{NODE}:{TARGET}"
        print(f"[1] crossing opened to '{TARGET}': {crossing['object_id']} (carries a directive, not value)")

        # 2 · undeclared boundary is REFUSED — deny-by-default
        try:
            sanction_crossing(reg, crossing, rules=[], boundary_mandate=BOUNDARY,
                              approver="ops-lead", approval_ref="send #1")
            raise AssertionError("an undeclared boundary must be refused")
        except CrossingError:
            print("[2] undeclared boundary REFUSED — deny-by-default (the node has not consented to this reach)")

        # 3 · declare the boundary rule, but with NO named human → still REFUSED
        rule = [SharingRule(f"crossing:{NODE}:{TARGET}", BOUNDARY, "write")]
        try:
            sanction_crossing(reg, crossing, rules=rule, boundary_mandate=BOUNDARY,
                              approver="", approval_ref="")
            raise AssertionError("a crossing with no named human must be refused")
        except CrossingError:
            print("[3] declared boundary but NO named human → REFUSED (no silent send)")

        # 4 · declared rule AND a named human's approval → sanctioned + receipted
        res = sanction_crossing(reg, crossing, rules=rule, boundary_mandate=BOUNDARY,
                                approver="ops-lead", approval_ref="send authorization #1")
        assert res["crossed"] is True and res["boundary"] == BOUNDARY
        assert res["crossing_root"] == crossing["version_hash"] and res["approver"] == "ops-lead"
        print(f"[4] sanctioned by a named human (ops-lead) → receipt: boundary={res['boundary']} "
              f"root={res['crossing_root'][:16]}…")

        # 5 · the receipt records THAT it happened — it holds no value
        for k in ("value", "amount", "funds", "balance", "held"):
            assert k not in res, f"the Port must not custody value (found {k!r})"
        print("[5] receipt carries NO value/funds/balance/held field — money-path OFF, the Port holds nothing")

    print("\nGATED EXTERNAL SEND EXAMPLE — all checks passed. "
          "Port-only reach: deny-by-default, named-human sanction, receipt-not-value.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
