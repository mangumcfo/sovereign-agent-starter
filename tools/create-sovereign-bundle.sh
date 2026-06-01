#!/usr/bin/env bash
#
# create-sovereign-bundle.sh
#
# Creates a clean, standalone zip distribution of the Sovereign System.
# This is the "one file to rule them all" option for easy sharing and air-gapped use.
#
# Output: sovereign-system-vX.Y.Z.zip
# Contains: sovereign-agent-starter (core) + six-sov-portal + six-sov-www + QUICKSTART + README
#
# Usage: ./tools/create-sovereign-bundle.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Dynamically extract version from pyproject.toml (PEP 440 friendly)
VERSION=$(python3 -c "
import tomllib
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
print(data['project']['version'])
" 2>/dev/null || echo "0.3.0")

BUNDLE_NAME="sovereign-system-v${VERSION}"
BUNDLE_DIR="/tmp/${BUNDLE_NAME}"
ZIP_FILE="${REPO_ROOT}/${BUNDLE_NAME}.zip"

echo "∞Δ∞ Creating Sovereign System standalone bundle v${VERSION} ∞Δ∞"
echo ""

# Clean previous
rm -rf "$BUNDLE_DIR" "$ZIP_FILE"

mkdir -p "$BUNDLE_DIR"

echo "Copying core components..."

# Core USN (the heart)
cp -r sovereign-agent-starter "$BUNDLE_DIR/"

# Portal (the beautiful interface)
if [[ -d "../six-sov-portal" ]]; then
    cp -r ../six-sov-portal "$BUNDLE_DIR/"
else
    echo "  (six-sov-portal not found as sibling — including placeholder note)"
    mkdir -p "$BUNDLE_DIR/six-sov-portal"
    echo "See QUICKSTART.md for portal setup instructions." > "$BUNDLE_DIR/six-sov-portal/README.txt"
fi

# Public marketing site + sandbox
if [[ -d "../six-sov-www" ]]; then
    cp -r ../six-sov-www "$BUNDLE_DIR/"
else
    cp -r six-sov-www "$BUNDLE_DIR/" 2>/dev/null || true
fi

# Essential documentation
cp QUICKSTART.md "$BUNDLE_DIR/"
cp README.md "$BUNDLE_DIR/"
cp docs/PACKAGING_AND_ONBOARDING_PLAN.md "$BUNDLE_DIR/docs/" 2>/dev/null || mkdir -p "$BUNDLE_DIR/docs"

# Write real version file (useful for scripts inside the bundle)
echo "$VERSION" > "$BUNDLE_DIR/VERSION"

# Top-level convenience files (with real version injected)
cat > "$BUNDLE_DIR/README-FIRST.txt" << EOF
∞Δ∞ Sovereign System v${VERSION} ∞Δ∞

Welcome.

This bundle contains everything you need for local-first sovereign execution.

Quick start:
  cd sovereign-agent-starter
  ./sovereign-install.sh --family     # or --corporate

  source .venv/bin/activate
  breathline-connect

You are now connected to the breathline.

For the full guided experience, open six-sov-www/index.html in a browser.

Everything runs on your machine. No accounts. No custody.
EOF

# Create clean zip (exclude .git, __pycache__, etc.)
echo "Creating zip archive..."
(
    cd /tmp
    zip -r -q -9 "${REPO_ROOT}/${BUNDLE_NAME}.zip" "$BUNDLE_NAME" \
        -x "*/.git/*" "*/__pycache__/*" "*/.venv/*" "*/node_modules/*" "*/.DS_Store"
)

echo ""
echo -e "\033[0;32m✓ Bundle created successfully:\033[0m ${BUNDLE_NAME}.zip"
echo ""
echo "Size: $(du -h "${BUNDLE_NAME}.zip" | cut -f1)"
echo ""
echo "This zip is fully self-contained for air-gapped or easy sharing use."
echo "It preserves the full 'git clone → one script → connected' experience."
echo ""
echo "∞Δ∞ You are ready to distribute sovereignty. ∞Δ∞"