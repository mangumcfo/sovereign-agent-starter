"""
general_sovereign_demo — ultra-light personal sovereignty demo handler.
"""

from typing import Any, Dict


class GeneralSovereignDemoAgent:
    role_id = "general_sovereign_demo"
    framework = "simple-forecast"

    def process(self, request: Any) -> Dict[str, Any]:
        payload = getattr(request, "payload", request) or {}
        return {
            "status": "success",
            "role_id": self.role_id,
            "demo": True,
            "answer": "You are operating in full local sovereignty. This demo role confirms the attestation pipeline is live.",
            "payload_echo": str(payload)[:200]
        }
