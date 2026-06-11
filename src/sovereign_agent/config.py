"""
Sovereign System Configuration & Root Resolution

Centralizes all path and mode logic so the system is portable and supports
both "demo mode" (zero external clones, always works after pip install) and
full breathline-federation power users.

Environment variables (all optional):
  BREATHLINE_SEALED_ROOT       - Path to breathline-sealed checkout
  BREATHLINE_FEDERATION_ROOT   - Path to breathline-federation (or mangumcfo/breathline-federation)
  SOVEREIGN_DEMO_MODE          - "1" or "true" forces bundled demo roles
  SOVEREIGN_HOME               - Base directory for sovereign artifacts (default: ~/sovereign or cwd)
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
import importlib.resources

# ------------------------------------------------------------------
# Constants & Defaults
# ------------------------------------------------------------------
DEMO_MODE_ENV = "SOVEREIGN_DEMO_MODE"
SEALED_ROOT_ENV = "BREATHLINE_SEALED_ROOT"
FEDERATION_ROOT_ENV = "BREATHLINE_FEDERATION_ROOT"
SOVEREIGN_HOME_ENV = "SOVEREIGN_HOME"
BOOKS_VAULT_ENV = "BREATHLINE_BOOKS_VAULT"   # path to the breathline-books-vault/kdp root

FRIENDLY_DEMO_ROLES = [
    "family_cfo_agent",      # maps to family_cfo_demo internally
    "cfo_agent",             # maps to corporate_cfo_demo
    "general_sovereign_agent",
    "compliance_agent_demo",
]

# The friendly names users and the portal already expect
DEMO_ROLE_ALIASES = {
    "family_cfo_agent": "family_cfo_demo",
    "cfo_agent": "corporate_cfo_demo",
    "general_sovereign_agent": "general_sovereign_demo",
    "compliance_agent": "corporate_cfo_demo",  # reuse for demo
}

# Re-export for modules that do "from . import config as sovereign_config"
__all__ = [
    "is_demo_mode",
    "get_sealed_root",
    "get_federation_root",
    "get_demo_roles_dir",
    "resolve_primary_source",
    "get_friendly_demo_role_names",
    "map_to_demo_role",
    "get_books_kdp_root",
    "get_playbooks_dir",
    "DEMO_ROLE_ALIASES",
    "FRIENDLY_DEMO_ROLES",
]


def _is_truthy(val: Optional[str]) -> bool:
    if not val:
        return False
    return val.lower() in ("1", "true", "yes", "on")


def is_demo_mode() -> bool:
    """Returns True if we should use only bundled demo roles (fast path, no external deps)."""
    if _is_truthy(os.environ.get(DEMO_MODE_ENV)):
        return True
    # Auto-demo if no federation root can be resolved
    return get_federation_root() is None


def get_sovereign_home() -> Path:
    env = os.environ.get(SOVEREIGN_HOME_ENV)
    if env:
        return Path(env).expanduser().resolve()
    # Sensible default next to common work areas
    return (Path.home() / "sovereign").resolve()


def get_sealed_root() -> Optional[Path]:
    """
    Resolve the breathline-sealed checkout (for real primitives + Merkle).
    Returns None if not found and we are in demo mode.
    """
    env = os.environ.get(SEALED_ROOT_ENV)
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "breathline_primitives").is_dir() or (p / "scripts" / "breathline-sealed-env.sh").exists():
            return p
        return p  # user explicitly set it; let bootstrap handle validation

    # Reuse the excellent discovery logic from bootstrap if available
    try:
        from .bootstrap import _find_breathline_sealed_root
        root = _find_breathline_sealed_root()
        if root:
            return root
    except Exception:
        pass

    # Common fallbacks (kept in sync with bootstrap)
    candidates = [
        Path.home() / "work-repos" / "breathline-sealed" / "worktrees" / "dev",
        Path.home() / "work-repos" / "breathline-sealed",
        get_sovereign_home() / "breathline-sealed",
    ]
    for c in candidates:
        if c.exists() and ((c / "breathline_primitives").is_dir() or (c / "scripts").exists()):
            return c
    return None


def get_federation_root() -> Optional[Path]:
    """
    Resolve the breathline-federation root that contains platform/roles/ and specs/.
    Returns None when we should fall back to demo roles.
    """
    env = os.environ.get(FEDERATION_ROOT_ENV)
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "platform" / "roles").exists() or (p / "specs").exists():
            return p
        return p  # explicit user path

    # Common locations (the original hardcoded one + new sovereign home + relative)
    candidates = [
        Path("/home/kmangum/work-repos/mangumcfo/breathline-federation"),  # legacy exact (will be removed)
        Path.home() / "work-repos" / "mangumcfo" / "breathline-federation",
        Path.home() / "work-repos" / "breathline-federation",
        get_sovereign_home() / "breathline-federation",
        Path(__file__).resolve().parents[4] / "mangumcfo" / "breathline-federation",  # dev layout
    ]
    for c in candidates:
        if c.exists() and ((c / "platform" / "roles").exists() or (c / "specs").exists()):
            return c
    return None


def get_books_kdp_root() -> Optional[Path]:
    """Resolve the breathline-books-vault/kdp root (interiors, covers, metadata, ASIN/CHANNEL trackers).

    Portability (runs_anywhere, audit 2026-06-11): the modules that serve books used to hardcode
    '/home/kmangum/work-repos/mangumcfo/breathline-books-vault/kdp'. Now the path flows from
    BREATHLINE_BOOKS_VAULT (explicit) or a candidate sweep that still INCLUDES the legacy location, so
    KM's machine resolves identically while any other host sets one env var. Returns None when no vault
    is present (a node with no published-books surface — the honest empty state, not a crash)."""
    env = os.environ.get(BOOKS_VAULT_ENV)
    if env:
        return Path(env).expanduser().resolve()   # explicit operator config wins, validated by callers
    candidates = [
        Path("/home/kmangum/work-repos/mangumcfo/breathline-books-vault/kdp"),  # legacy exact (KM's host)
        Path.home() / "work-repos" / "mangumcfo" / "breathline-books-vault" / "kdp",
        Path.home() / "work-repos" / "breathline-books-vault" / "kdp",
        get_sovereign_home() / "breathline-books-vault" / "kdp",
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()
    return None


def get_playbooks_dir() -> Optional[Path]:
    """The agentic_playbooks directory under the kdp vault (where manuscripts + trackers live)."""
    root = get_books_kdp_root()
    return (root / "agentic_playbooks") if root else None


def get_demo_roles_dir() -> Path:
    """Return the directory containing the shipped demo roles (works in dev and after pip install)."""
    try:
        # Preferred for installed packages (importlib.resources)
        ref = importlib.resources.files("sovereign_agent") / "demo_roles"
        # In Python 3.9+ this is Traversable; convert to Path when possible
        if hasattr(ref, "joinpath"):
            # Best effort
            return Path(str(ref))
    except Exception:
        pass

    # Fallback for development / editable installs
    here = Path(__file__).resolve().parent
    demo = here / "demo_roles"
    if demo.exists():
        return demo

    # Last resort
    return here / "demo_roles"


def resolve_primary_source(explicit: Optional[Path] = None) -> Path:
    """
    Used by PlaybookLoader and PolicyLoader.
    Returns either the real federation root or the demo_roles directory.
    """
    if explicit:
        return explicit
    fed = get_federation_root()
    if fed and not is_demo_mode():
        return fed
    return get_demo_roles_dir()


def get_friendly_demo_role_names() -> list[str]:
    """Role names shown to users in demo mode (match what the portal and examples already request)."""
    return FRIENDLY_DEMO_ROLES.copy()


def map_to_demo_role(role_key: str) -> str:
    """Map a friendly name the user/portal requests to the internal demo role directory name."""
    return DEMO_ROLE_ALIASES.get(role_key, role_key)
