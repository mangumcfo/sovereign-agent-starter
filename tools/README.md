# Sovereign System — Distribution Tools

This directory contains tools for packaging and distributing the Sovereign System while preserving radical simplicity and local-first sovereignty.

## Scripts

### `create-sovereign-bundle.sh`

Creates a clean, self-contained zip archive of the entire Sovereign System.

**Usage:**
```bash
./tools/create-sovereign-bundle.sh
```

**Output:**
- `sovereign-system-vX.Y.Z.zip` in the repository root

**What it includes:**
- `sovereign-agent-starter/` (core USN + demo roles + installer)
- `six-sov-portal/` (if present as sibling)
- `six-sov-www/` (marketing site + `taste.html` sandbox)
- `QUICKSTART.md` and `README.md`
- `README-FIRST.txt` (top-level instructions)
- `VERSION` file (for scripting inside the bundle)

This is the recommended way to create distributable bundles for air-gapped environments, family offices, or easy sharing.

---

## Philosophy

All distribution tooling is designed to support the canonical story:

> **git clone → one script → "Are you connected to the breathline?"**

We deliberately avoid complex build systems, monorepo tooling, or heavy CI in favor of simple, auditable bash + Python scripts.

## Future Ideas (not yet implemented)

- Automated GitHub Release attachment of the bundle
- GPG signing of bundles
- Minimal "sovereign-bootstrap" single-file downloader

Contributions that maintain radical simplicity are welcome.

---

**Remember:** The goal is not maximum packaging sophistication — it is maximum sovereignty and minimum friction for the user.