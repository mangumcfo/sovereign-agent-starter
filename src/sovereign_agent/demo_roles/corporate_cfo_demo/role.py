"""
corporate_cfo_demo role handler (pure, self-contained).

Designed for the corporate/regulated first experience. Output includes
fields that the compliance engine and receipt explorer already understand.
"""

from typing import Any, Dict


class CorporateCfoDemoAgent:
    """Demo implementation that feels regulated (risk, classification, notes)."""

    role_id = "corporate_cfo_demo"
    framework = "simple-forecast"

    def process(self, request: Any) -> Dict[str, Any]:
        if hasattr(request, "payload"):
            payload = request.payload or {}
            action_class = getattr(request, "action_class", None) or "produce_forecast_artifact"
        else:
            payload = request if isinstance(request, dict) else {}
            action_class = payload.get("action_class", "produce_forecast_artifact")

        horizon = int(payload.get("forecast_horizon", 3))

        result = {
            "status": "success",
            "role_id": self.role_id,
            "action_class": action_class,
            "demo": True,
            "risk_classification": "internal",
            "forecast": {
                "horizon_years": horizon,
                "revenue_cagr": "8.4%",
                "margin_expansion": "120bps",
                "board_recommendation": "Proceed with disciplined growth + antifragile reserves."
            },
            "compliance_note": "Demo role. Real regulated execution would include policy checks, human approval gate (if configured), and full SIX-structured receipt.",
            "message": "Corporate demo role active. Set BREATHLINE_FEDERATION_ROOT + corporate context for live compliance-aware roles and full audit chains."
        }
        return result
