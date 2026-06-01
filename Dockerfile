# Dockerfile
#
# Minimal containerized option for the Sovereign System (advanced users only).
#
# IMPORTANT SOVEREIGNTY NOTICE:
# Containers reduce some sovereignty guarantees (ephemeral filesystems, shared kernel, etc.).
# For maximum local-first sovereignty, prefer the native installer on bare metal or a dedicated VM.
# This image is provided for convenience, testing, or air-gapped server environments.
#
# Build: docker build -t sovereign-system .
# Run:   docker run -p 5000:5000 --rm -it sovereign-system

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    SOVEREIGN_DEMO_MODE=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# System dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the sovereign-agent-starter (core)
COPY sovereign-agent-starter /app/sovereign-agent-starter

# Install the USN + portal extras
RUN pip install --no-cache-dir -e "/app/sovereign-agent-starter[portal]"

# Copy portal (if present in build context)
COPY six-sov-portal /app/six-sov-portal 2>/dev/null || true

# Copy www + docs for convenience
COPY six-sov-www /app/six-sov-www 2>/dev/null || true
COPY QUICKSTART.md README.md /app/

# Default to running the portal (most common "connected" experience)
WORKDIR /app/six-sov-portal

EXPOSE 5000

# Entry point runs the portal with demo mode by default
CMD ["python", "app.py"]