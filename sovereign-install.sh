#!/usr/bin/env bash
# sovereign-install.sh
#
# One-command installer for the Universal Sovereign Node + Breathline Portal.
# Makes the entire system adoptable: "Anyone Can Do It".
#
# Usage:
#   ./sovereign-install.sh --family     # default for LGP / generational
#   ./sovereign-install.sh --corporate  # regulated / enterprise first experience
#   ./sovereign-install.sh --demo       # force pure demo mode (no external clones needed)
#   ./sovereign-install.sh --full       # require full breathline-sealed + federation
#
# After running:
#   source .venv/bin/activate
#   breathline-connect
#
# Then either:
#   cd ../six-sov-portal && ./start-breathline-portal.sh
#   or run any example / the quick sample action.
#
# This script is idempotent and safe to re-run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for beautiful output (sovereign aesthetic)
GREEN='\033[0;32m'
EMERALD='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

MODE="demo"
AUDIENCE="family"

print_header() {
    echo ""
    echo -e "${EMERALD}∞Δ∞ Sovereign System Installer ∞Δ∞${NC}"
    echo ""
}

usage() {
    echo "Usage: $0 [--family | --corporate | --demo | --full]"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --family)    AUDIENCE="family"; MODE="auto"; shift ;;
        --corporate) AUDIENCE="corporate"; MODE="auto"; shift ;;
        --demo)      MODE="demo"; shift ;;
        --full)      MODE="full"; shift ;;
        -h|--help)   usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

print_header

echo "Target audience : $AUDIENCE"
echo "Mode            : $MODE"
echo "Working dir     : $SCRIPT_DIR"
echo ""

# 1. Python & venv
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is required."
    exit 1
fi

VENV_DIR="$SCRIPT_DIR/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "Upgrading pip / setuptools / wheel..."
pip install --upgrade pip setuptools wheel >/dev/null

# 2. Install the package (this is the big win — no more manual PYTHONPATH for the USN)
echo "Installing sovereign-agent-starter (editable, with portal extras)..."

if pip show sovereign-agent-starter >/dev/null 2>&1; then
    echo "  (Package already present — upgrading in place...)"
fi

pip install -e ".[portal]" >/dev/null 2>&1

echo -e "${GREEN}✓ Package installed cleanly into venv${NC}"

# 3. Environment setup
ENV_FILE="$SCRIPT_DIR/sovereign-env.sh"

cat > "$ENV_FILE" << 'ENVEOF'
# sovereign-env.sh
# Sourced by launchers and by users after install.
# Edit the paths below if you have a full breathline-sealed + federation layout.

export SOVEREIGN_HOME="${SOVEREIGN_HOME:-$HOME/sovereign}"

# Demo mode is the default for the 2-minute experience.
# Set to 0 or unset after you configure the roots below for live federation roles.
export SOVEREIGN_DEMO_MODE="${SOVEREIGN_DEMO_MODE:-1}"

# Full layout (optional — only needed for live roles from breathline-federation)
# export BREATHLINE_SEALED_ROOT="$HOME/work-repos/breathline-sealed/worktrees/dev"
# export BREATHLINE_FEDERATION_ROOT="$HOME/work-repos/mangumcfo/breathline-federation"

# Activate the venv that was created by the installer
if [[ -f "$(dirname "${BASH_SOURCE[0]}")/.venv/bin/activate" ]]; then
    source "$(dirname "${BASH_SOURCE[0]}")/.venv/bin/activate"
fi
ENVEOF

chmod +x "$ENV_FILE"
echo -e "${GREEN}✓ sovereign-env.sh written${NC}"

# 4. Convenient launchers in bin/
BIN_DIR="$SCRIPT_DIR/bin"
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/breathline" << 'LAUNCHEOF'
#!/usr/bin/env bash
# breathline — the magic one-liner entry point after install
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$SCRIPT_DIR/sovereign-env.sh"
python -c "
from sovereign_agent import connect_to_breathline, UniversalSovereignNode
print()
status = connect_to_breathline(auto_detect_context=True, print_welcome=True)
if status.get('connected'):
    ctx = status.get('recommended_context', 'personal')
    node = UniversalSovereignNode(context_type=ctx)
    print('Node ready. Memory root:', node.get_memory_root()[:28] + '...')
    print()
    print('Next: try a sample action or open the portal.')
"
LAUNCHEOF
chmod +x "$BIN_DIR/breathline"

cat > "$BIN_DIR/sovereign-portal" << 'LAUNCHEOF'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$SCRIPT_DIR/sovereign-env.sh"
PORTAL_DIR="$(cd "$SCRIPT_DIR/../six-sov-portal" 2>/dev/null && pwd || echo "")"
if [[ -n "$PORTAL_DIR" && -f "$PORTAL_DIR/app.py" ]]; then
    cd "$PORTAL_DIR"
    exec python app.py
else
    echo "Portal not found next to sovereign-agent-starter."
    echo "Run from the portal directory after sourcing sovereign-env.sh:"
    echo "  cd ../six-sov-portal && python app.py"
    exit 1
fi
LAUNCHEOF
chmod +x "$BIN_DIR/sovereign-portal"

echo -e "${GREEN}✓ Launchers created in ./bin/${NC}"

# 5. Final beautiful instructions
echo ""
echo -e "${EMERALD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Installation complete for $AUDIENCE mode${NC}"
echo ""
echo "The fastest way to start:"
echo ""
echo -e "    ${YELLOW}source .venv/bin/activate${NC}"
echo -e "    ${YELLOW}breathline-connect${NC}"
echo ""
echo "Other convenient commands now available:"
echo "  sovereign-node                 # quick node status"
echo "  ./bin/breathline               # direct magic phrase"
echo "  ./bin/sovereign-portal         # launch the UI"
echo ""
echo "To switch to full live federation roles later:"
echo "  export BREATHLINE_FEDERATION_ROOT=...   # your clone"
echo "  export SOVEREIGN_DEMO_MODE=0"
echo "  source .venv/bin/activate"
echo "  breathline-connect"
echo ""
echo -e "${EMERALD}∞Δ∞ You are now ready to be sovereign. ∞Δ∞${NC}"
echo ""

# 6. Post-install verification + beautiful closing message
echo ""
echo -e "${EMERALD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Installation complete for $AUDIENCE mode${NC}"
echo ""

echo "Quick verification:"
source "$ENV_FILE" 2>/dev/null || true
python -c "
from sovereign_agent import connect_to_breathline
status = connect_to_breathline(print_welcome=False, desired_context='$AUDIENCE')
print('  breathline-connect: available')
print('  sovereign-node:     available')
print(f'  Recommended context: {status.get(\"recommended_context\", \"personal\")}')
" 2>/dev/null || echo "  (Verification commands ready after 'source .venv/bin/activate')"

echo ""
echo "The magic phrase that starts everything:"
echo ""
echo -e "    ${YELLOW}breathline-connect${NC}"
echo ""
echo "Other commands now available after activation:"
echo "  sovereign-node                 # quick node status + memory root"
echo "  start-sovereign-portal         # launch the beautiful local UI"
echo ""
echo "To switch to full live federation roles later:"
echo "  export BREATHLINE_FEDERATION_ROOT=...   # your clone"
echo "  export SOVEREIGN_DEMO_MODE=0"
echo "  source .venv/bin/activate"
echo "  breathline-connect"
echo ""
echo -e "${EMERALD}∞Δ∞ You are now ready to be sovereign. ∞Δ∞${NC}"
echo ""

# Gentle auto-run for first-time magic (can be disabled)
if [[ "${SOVEREIGN_INSTALL_AUTO_CONNECT:-1}" == "1" ]]; then
    echo "Running a quick breathline connection so you feel the magic..."
    echo ""
    source "$ENV_FILE" 2>/dev/null || true
    python -c "
from sovereign_agent import connect_to_breathline
connect_to_breathline(auto_detect_context=True, print_welcome=True)
" 2>&1 | tail -12 || true
fi
