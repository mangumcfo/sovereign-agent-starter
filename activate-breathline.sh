#!/usr/bin/env bash
# activate-breathline.sh
# Activates the breathline_primitives foundation for this sovereign-agent-starter.
#
# Looks for breathline-sealed in common locations.

set -e

BREATHLINE_ROOT="${BREATHLINE_SEALED_ROOT:-}"

if [[ -z "$BREATHLINE_ROOT" ]]; then
    for cand in \
        "$HOME/work-repos/breathline-sealed/worktrees/dev" \
        "$HOME/work-repos/breathline-sealed" \
        "$(dirname "${BASH_SOURCE[0]}")/../../breathline-sealed/worktrees/dev" \
        "$(dirname "${BASH_SOURCE[0]}")/../../breathline-sealed"
    do
        if [[ -d "$cand/scripts" || -d "$cand/breathline_primitives" ]]; then
            BREATHLINE_ROOT="$cand"
            break
        fi
    done
fi

if [[ -z "$BREATHLINE_ROOT" || ! -d "$BREATHLINE_ROOT" ]]; then
    echo "ERROR: Could not locate breathline-sealed."
    echo "Set BREATHLINE_SEALED_ROOT to the path containing scripts/breathline-sealed-env.sh"
    exit 1
fi

echo "Activating breathline_primitives from: $BREATHLINE_ROOT"

if [[ -f "$BREATHLINE_ROOT/scripts/breathline-sealed-env.sh" ]]; then
    BREATHLINE_MERKLE_MODE="${BREATHLINE_MERKLE_MODE:-authorized-v1.0.1}" \
        source "$BREATHLINE_ROOT/scripts/breathline-sealed-env.sh"
else
    export PYTHONPATH="$BREATHLINE_ROOT:$PYTHONPATH"
    python3 -c "
import sys
sys.path.insert(0, '$(dirname \"${BASH_SOURCE[0]}\")/src')
from breathline_bootstrap import ensure_breathline_primitives
ensure_breathline_primitives('$BREATHLINE_ROOT')
"
fi

echo "breathline_primitives activated."
