"""
family_cfo_demo role handler (pure, self-contained, no external dependencies).

Used automatically in demo mode or when the full breathline-federation is not configured.
Produces a real, structured result that flows through the entire BoundRole + USN attestation pipeline.
"""

from typing import Any, Dict


class FamilyCfoDemoAgent:
    """Minimal but complete demo implementation for the Family/Legacy audience."""

    role_id = "family_cfo_demo"
    framework = "simple-forecast"

    def process(self, request: Any) -> Dict[str, Any]:
        # Support both the PlugInRequest style and plain dicts (demo flexibility)
        if hasattr(request, "payload"):
            payload = request.payload or {}
            action_class = getattr(request, "action_class", None) or "produce_forecast_artifact"
        else:
            payload = request if isinstance(request, dict) else {}
            action_class = payload.get("action_class", "produce_forecast_artifact")

        horizon = int(payload.get("forecast_horizon", 3))

        # Beautiful, realistic demo output (real structure, real numbers)
        result = {
            "status": "success",
            "role_id": self.role_id,
            "action_class": action_class,
            "demo": True,
            "forecast": {
                "horizon_years": horizon,
                "projected_wealth_multiple": round(2.4 + (horizon * 0.15), 2),
                "annual_compounding_rate": "7.2%",
                "key_drivers": [
                    "Disciplined savings rate + equity tilt",
                    "Tax-efficient legacy vehicles",
                    "Family governance cadence (quarterly reviews)"
                ],
                "next_generation_note": "Strong probability of multi-generational wealth transfer with preserved purchasing power."
            },
            "recommendations": [
                "Establish or refresh the Family Constitution (LGP lens)",
                "Schedule the next 90-day prosperity review",
                "Consider a small allocation to antifragile yield strategies"
            ],
            "message": "This is a fully self-contained demo role. Real family_cfo_agent from your breathline-federation adds deeper models, constitutional scoring, and cross-role review."
        }
        return result
