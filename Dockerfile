# Dockerfile — Sovereign Agent Starter (Universal Sovereign Node)
#
# Self-contained: the build context is THIS repo (sovereign-agent-starter). Builds anywhere with no
# sibling-repo assumptions (runs_anywhere, audit 2026-06-11). Demo mode by default — zero external
# clones required; set BREATHLINE_FEDERATION_ROOT / BREATHLINE_BOOKS_VAULT to wire real sources.
#
# IMPORTANT SOVEREIGNTY NOTICE:
# Containers reduce some sovereignty guarantees (ephemeral filesystems, shared kernel). For maximum
# local-first sovereignty, prefer the native installer on bare metal or a dedicated VM. This image is
# provided for convenience, testing, or air-gapped server environments.
#
# Build: docker build -t sovereign-node .
# Run:   docker run -p 8421:8421 -e BREATHLINE_NODE_API_HOST=0.0.0.0 --rm -it sovereign-node
#        (the API binds 127.0.0.1 by default — sovereign loopback; set HOST=0.0.0.0 to reach it via -p.
#         Mount a volume at /data to persist the hash-chained obligation ledger across runs.)

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SOVEREIGN_DEMO_MODE=1 \
    OBLIGATION_LEDGER_ROOT=/data/obligations

WORKDIR /app

# System dependencies (minimal) — git only, for any source-of-truth clones the operator mounts later.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Install the package (context = this repo). Copy metadata first for a cached dependency layer.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -e ".[portal]"

# Node-local, persistent ledger root (mount a volume here to keep the hash-chained ledger across runs).
RUN mkdir -p /data/obligations
VOLUME ["/data"]

EXPOSE 8421

# Run the Node API (the console script declared in pyproject). Loopback-trust owner is set at run time
# via BREATHLINE_NODE_LOOPBACK_OWNER; absent that, auth requires a bearer token (the honest default).
CMD ["breathline-node-api"]
