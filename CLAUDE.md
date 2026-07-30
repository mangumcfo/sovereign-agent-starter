# sas-public-genesis / sovereign-agent-starter — operating notes

## Push policy for the Press kernel (KM/G, 2026-07-30 — P-Push)

**This checkout is the single shared authority for the Press kernel** (`src/sovereign_agent/press/`).
`kernel_staging` is retired; `press.py` resolves the kernel from this starter checkout. Because more than
one party reads this code — the drafting lane, the AA audit lane, and the seal path — **gate-relevant fixes
are pushed to `origin/main` immediately: at minimum before any audit is run against the kernel and before
any volume is sealed.** Never hold a gate fix on push-on-request.

The reason this rule exists: on 2026-07-30 an audit read `origin/main` and reported the receipt-truth check
and the SEAM-4 fix "missing from the code" — they were done in the working tree but sat in five unpushed
commits, so the audit and the running kernel disagreed. A shared authority that lags its own origin cannot
be audited. Keep `git rev-list --count origin/main..HEAD` at 0 for gate-touching work.

(Volume content repos and vaults keep their own push cadence; this rule is specifically for the Press
kernel, which every lane resolves and runs.)
