"""Constitution — Private Series Templates (s5_28): family and enterprise constitutions as governed objects. A
constitution is opened as a governed object under a mandate, with a declared core-protection envelope; amendments
are governed versions (never in-place edits), and a change to the core beyond the envelope is refused unless
human-gated. Composes the sealed Sovereign Object Model (registry, versioned lifecycle, change envelope); it builds
no constitution store and no amendment engine of its own — the core truth is preserved by the object model's own law."""
from .templates import open_constitution, core_envelope, amend, ConstitutionError

__all__ = ["open_constitution", "core_envelope", "amend", "ConstitutionError"]
