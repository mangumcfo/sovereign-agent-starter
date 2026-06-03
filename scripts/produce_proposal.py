#!/usr/bin/env python3
"""
Producer (Step C-full): POST a grouped-diff proposal to the node so it appears in the Atrium
diff-review surface for the operator to accept/reject (see-before-write).

The *agent* authors the proposal — it reads a captured session's transcript (the obligation's
`intent`) plus the manuscript/code, and produces grouped diffs. This script is the transport:
it POSTs the authored proposal JSON to the local node (loopback-trust → no token needed).

Usage:
    scripts/produce_proposal.py proposal.json
    cat proposal.json | scripts/produce_proposal.py -

Proposal JSON shape:
    {
      "session_ref": "review:AI Agents for M&A (Book 11) · ~p34",
      "obligation_id": "obl_...",                 # optional: link to the session obligation
      "book": "AI Agents for M&A (Book 11)",
      "groups": [
        {"id":"g1","title":"...","kind":"prose|code","scope":"GREEN|YELLOW|RED",
         "rationale":"...","file":"...","before":["..."],"after":["..."]}
      ]
    }
"""
import sys
import urllib.request

NODE = "http://127.0.0.1:8421/api/v1/proposals"


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else "-"
    data = sys.stdin.read() if arg == "-" else open(arg, encoding="utf-8").read()
    req = urllib.request.Request(
        NODE, data=data.encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        print(resp.read().decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
