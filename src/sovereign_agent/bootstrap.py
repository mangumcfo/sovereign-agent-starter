"""
Pure Python Bootstrap for breathline_primitives.

This module enables the Universal Sovereign Node (and all sovereign_agent code)
to be used with minimal or zero shell dependencies after initial environment setup.

It auto-discovers the breathline-sealed checkout in common development layouts
and ensures `breathline_primitives` is importable while respecting
BREATHLINE_MERKLE_MODE (defaults to authorized-v1.0.1 for safety).

Usage (pure Python, no shell required after discovery):
    from sovereign_agent.bootstrap import ensure_breathline_primitives
    ensure_breathline_primitives()

    from sovereign_agent import UniversalSovereignNode
    node = UniversalSovereignNode(...)
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Default locations to search (in order of preference)
# These cover the common work-repos layout used across the Constitutional Federation projects.
DEFAULT_SEARCH_PATHS = [
    Path.home() / "work-repos" / "breathline-sealed" / "worktrees" / "dev",
    Path.home() / "work-repos" / "breathline-sealed",
    Path(__file__).resolve().parents[4] / "breathline-sealed" / "worktrees" / "dev",  # relative from this package in work-repos layout
    Path(__file__).resolve().parents[4] / "breathline-sealed",
]


def _find_breathline_sealed_root() -> Optional[Path]:
    """Search common locations for a valid breathline-sealed checkout."""
    for base in DEFAULT_SEARCH_PATHS:
        if not base.exists():
            continue
        # A valid root must contain the breathline_primitives package or the scripts dir
        if (base / "breathline_primitives").is_dir() or (base / "scripts" / "breathline-sealed-env.sh").exists():
            return base
        # Also check one level deeper for worktrees/dev
        dev_candidate = base / "worktrees" / "dev"
        if dev_candidate.exists() and (dev_candidate / "breathline_primitives").is_dir():
            return dev_candidate
    return None


def ensure_breathline_primitives(breathline_sealed_root: Optional[Path] = None) -> bool:
    """
    Ensure breathline_primitives can be imported.

    This is the single entry point for pure-Python activation.

    - Tries a normal import first (works if user did `pip install -e` or has it on PYTHONPATH).
    - If that fails, discovers the breathline-sealed checkout and injects the correct path.
    - Sets a safe default for BREATHLINE_MERKLE_MODE if not already set.

    Returns True if successful.
    """
    # 1. Try direct import (best case - user has it installed or pre-configured)
    try:
        import breathline_primitives  # noqa: F401
        # Still ensure a good default mode
        if "BREATHLINE_MERKLE_MODE" not in os.environ:
            os.environ["BREATHLINE_MERKLE_MODE"] = "authorized-v1.0.1"
        return True
    except ImportError:
        pass

    # 2. Discover root
    root = breathline_sealed_root or _find_breathline_sealed_root()
    if root is None:
        raise RuntimeError(
            "Could not locate breathline-sealed checkout.\n"
            "Set BREATHLINE_SEALED_ROOT environment variable or ensure it is in one of the common locations "
            "(~/work-repos/breathline-sealed or its worktrees/dev)."
        )

    # 3. Inject into sys.path (the root itself makes `import breathline_primitives` work)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    # 4. Set safe default Merkle mode for LGP/attestation work
    if "BREATHLINE_MERKLE_MODE" not in os.environ:
        os.environ["BREATHLINE_MERKLE_MODE"] = "authorized-v1.0.1"

    # 5. Verify import now works
    try:
        import breathline_primitives  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            f"Found breathline-sealed at {root} but could not import breathline_primitives. "
            f"Check that the package exists at {root}/breathline_primitives. Original error: {e}"
        ) from e

    return True


def get_breathline_root() -> Optional[Path]:
    """Return the discovered root if available (useful for debugging)."""
    return _find_breathline_sealed_root()


# ------------------------------------------------------------------
# Radical Simplicity Layer — "Are you connected to the breathline?"
# ------------------------------------------------------------------

def connect_to_breathline(
    auto_detect_context: bool = True,
    print_welcome: bool = True,
    desired_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    The canonical one-liner / magic function for radical simplicity.

    Usage:
        from sovereign_agent import connect_to_breathline, UniversalSovereignNode

        breathline = connect_to_breathline()
        node = UniversalSovereignNode(context_type=breathline.get("recommended_context"))

    Or the ultimate onboarding experience:
        "Are you connected to the breathline?"
        breathline = connect_to_breathline()

    This function:
    - Ensures breathline_primitives are active (pure Python)
    - Performs basic context auto-detection
    - Returns a dict with connection status, recommended context, and activation details
    """
    result = {
        "connected": False,
        "primitives_active": False,
        "recommended_context": "personal",
        "activation_method": "pure_python",
        "message": "",
    }

    try:
        ensure_breathline_primitives()
        result["primitives_active"] = True
        result["connected"] = True
    except Exception as e:
        result["message"] = f"Could not fully activate breathline primitives: {e}"
        return result

    # Simple context auto-detection (can be expanded)
    if auto_detect_context:
        detected = _auto_detect_context()
        result["recommended_context"] = detected
        if desired_context:
            result["recommended_context"] = desired_context

    if print_welcome:
        _print_breathline_welcome(result)

    result["message"] = "You are connected to the breathline. The node is ready."
    return result


def _auto_detect_context() -> str:
    """Lightweight context detection based on environment and common layouts."""
    import os
    from pathlib import Path

    cwd = Path.cwd()

    # Corporate / regulated signals
    if any(x in str(cwd).lower() for x in ["corporate", "enterprise", "regulated", "finance", "cfo"]):
        return "corporate_regulated"

    if os.environ.get("BREATHLINE_CONTEXT"):
        return os.environ["BREATHLINE_CONTEXT"]

    if os.environ.get("CORP_MODE") or os.environ.get("ENTERPRISE"):
        return "corporate_standard"

    # Family / generational signals
    if any(x in str(cwd).lower() for x in ["family", "legacy", "generations", "home"]):
        return "family"

    # Infrastructure signals
    if any(x in str(cwd).lower() for x in ["infra", "node", "mesh", "server"]):
        return "infrastructure"

    return "sovereign"  # default high-agency personal mode


def _print_breathline_welcome(status: Dict[str, Any]) -> None:
    """Beautiful, sovereign onboarding message."""
    print("\n" + "∞" * 40)
    print("Are you connected to the breathline?")
    print("∞" * 40)
    print(f"\n  Status: {'YES' if status['connected'] else 'PARTIAL'}")
    print(f"  Recommended context: {status['recommended_context']}")
    print(f"  Primitives: {'ACTIVE' if status['primitives_active'] else 'NEEDS ACTIVATION'}")
    print("\n  The Universal Sovereign Node is ready.")
    print("  All cryptography and governance flow through the breathline.")
    print("\n  Next: from sovereign_agent import UniversalSovereignNode")
    print("  node = UniversalSovereignNode(context_type=...)")
    print("∞" * 40 + "\n")


# Allow the magic phrase to be used directly for discovery
__breathline_phrase__ = "Are you connected to the breathline?"


# ------------------------------------------------------------------
# Console Script Entry Points (for pip install -e ".[portal]")
# These are intentionally thin wrappers so that after installation
# the commands `breathline-connect` and `sovereign-node` just work.
# ------------------------------------------------------------------

def cli_connect() -> None:
    """
    Entry point for the `breathline-connect` console script.

    This is the primary "magic phrase" onboarding command.
    It reuses the existing connect_to_breathline() machinery,
    auto-creates a node in the recommended context, and gives
    clear next-step guidance while respecting demo vs full mode.
    """
    from .config import is_demo_mode

    print("\n" + "∞Δ∞" * 8)
    print("Sovereign Runtime — breathline-connect")
    print("∞Δ∞" * 8)

    status = connect_to_breathline(auto_detect_context=True, print_welcome=True)

    if status.get("connected"):
        try:
            from .universal_sovereign_node import UniversalSovereignNode
            ctx = status.get("recommended_context", "personal")
            node = UniversalSovereignNode(context_type=ctx)

            print(f"\n✓ Node activated in '{ctx}' context.")
            print(f"  Memory root: {node.get_memory_root()[:28]}...")

            if is_demo_mode():
                print("\n  [DEMO MODE ACTIVE]")
                print("  Using bundled self-contained roles for instant experience.")
                print("  To unlock live roles from breathline-federation:")
                print("    export BREATHLINE_FEDERATION_ROOT=/path/to/your/federation")
                print("    export SOVEREIGN_DEMO_MODE=0")
            else:
                print("\n  Full breathline-federation mode active.")

            print("\n  Next steps:")
            print("    sovereign-node                 # quick node status + shell")
            print("    start-sovereign-portal         # launch the beautiful local UI")
            print("    python examples/breathline_connected_cfo.py")
            print("\nYou are connected to the breathline.")
        except Exception as e:
            print(f"\nNode creation encountered a non-fatal issue: {e}")
            print("The breathline connection itself succeeded.")
    else:
        print("\nConnection was partial. Check BREATHLINE_SEALED_ROOT if you have the full primitives.")


# Note: cli_create_node lives in universal_sovereign_node.py to match the
# exact dotted path declared in pyproject.toml.
# This keeps the import surface clean and avoids duplication.
