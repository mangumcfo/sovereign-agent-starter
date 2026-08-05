"""Deal — the governed exit surface: a clean exit (PE carve-out, sale, or generational handoff) as a value-conserving
carve-out and a verifiable diligence package, composing the sealed floors (the migration primitive's provenance and the
sealed audit package). The terminal of the displacement/escape arc (s5_37): the last displacement is not onto the
sovereign core but off the business, and this makes it provable to the buyer or heir who receives it."""
from .clean_exit import (
    carve_out, diligence_package, assert_clean_exit, CleanExitError,
)

__all__ = ["carve_out", "diligence_package", "assert_clean_exit", "CleanExitError"]
