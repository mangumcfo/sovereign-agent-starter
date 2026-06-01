"""
Thin-waist JSON shim — translate Python-native receipt types into JSON
without mutating the core's receipt envelope.

The Python core emits receipts containing:

    - `sign.ECDSASignature` objects (from breathline_primitives)
    - `AuditRecord` dataclasses (from compliance_engine)
    - `bytes` objects (Merkle leaves)
    - `datetime` objects (timestamps)
    - `enum.Enum` values (RiskLevel, ApprovalStatus)

These are all richer than JSON's primitives. The HTTP boundary must serialise
them faithfully (preserving information; not stringifying away structure) so
downstream consumers can reconstruct or verify them.

The discipline (Principle 7 — Thin-Waist):

    The HTTP layer does NOT remove information; it only translates the
    Python-native representation into JSON-equivalent form. Hex-encoded
    signatures, ISO-8601 timestamps, dict-of-fields for dataclasses.

If a new core type appears that we cannot translate losslessly, we raise so
the developer notices — silent stringification of structured data would
violate TRUTH (Constitution §0).
"""

from __future__ import annotations

import dataclasses
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from flask.json.provider import DefaultJSONProvider


def _to_jsonable(obj: Any) -> Any:
    """Recursively convert Python-native receipt types to JSON-safe forms."""
    # JSON primitives passthrough
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # bytes → hex (preserves all information)
    if isinstance(obj, (bytes, bytearray)):
        return obj.hex()

    # datetime → ISO-8601 (preserves precision)
    if isinstance(obj, datetime):
        if obj.tzinfo is None:
            obj = obj.replace(tzinfo=timezone.utc)
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()

    # Enum → its value
    if isinstance(obj, Enum):
        return obj.value

    # dataclass → dict of fields
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}

    # dict → recurse on values
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}

    # list/tuple → recurse
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]

    # set → sorted list (JSON has no native set)
    if isinstance(obj, (set, frozenset)):
        return sorted([_to_jsonable(v) for v in obj], key=lambda x: str(x))

    # Breathline-primitives signature objects expose `r` and `s` byte fields
    # (ECDSASignature). Translate to a structured dict so receipt verifiers
    # can reconstruct the signature object losslessly.
    if hasattr(obj, "r") and hasattr(obj, "s") and not callable(obj):
        try:
            r_val = getattr(obj, "r")
            s_val = getattr(obj, "s")
            return {
                "type": type(obj).__name__,
                "r": _to_jsonable(r_val),
                "s": _to_jsonable(s_val),
            }
        except Exception:  # noqa: BLE001 — fall through to the named-fallback below
            pass

    # Last-resort: try the object's __dict__ for plain attribute carriers.
    # If even this fails, raise so we don't silently lose structure.
    if hasattr(obj, "__dict__"):
        try:
            attrs = {k: v for k, v in vars(obj).items() if not k.startswith("_")}
            if attrs:
                return {
                    "type": f"{type(obj).__module__}.{type(obj).__name__}",
                    **{k: _to_jsonable(v) for k, v in attrs.items()},
                }
        except Exception:  # noqa: BLE001
            pass

    # Final fallback: explicit failure. TRUTH > silent stringification.
    raise TypeError(
        f"node_api.json_provider cannot losslessly serialise "
        f"{type(obj).__module__}.{type(obj).__name__}. Extend _to_jsonable() "
        f"with a faithful translation rather than letting structure leak away."
    )


class BreathlineJSONProvider(DefaultJSONProvider):
    """Flask JSON provider that handles breathline-primitives receipt types."""

    def default(self, o: Any) -> Any:
        try:
            return _to_jsonable(o)
        except TypeError:
            # Re-raise to keep the loud-failure discipline.
            raise


def install(app) -> None:
    """Install the BreathlineJSONProvider on a Flask app."""
    app.json = BreathlineJSONProvider(app)
