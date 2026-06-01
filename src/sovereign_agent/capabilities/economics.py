"""
Economic / Yield Capability Module — Enhanced for Generational Use

Focus: Sovereign wealth preservation, yield generation, antifragile assets,
and explicit LGP (Lasting Generational Prosperity) scoring.
"""

from typing import Dict, Any, List


class EconomicEngine:
    def __init__(self):
        self.name = "EconomicEngine"

    def analyze_yield_strategy(
        self, capital: float, horizon_years: int = 50, risk_tolerance: str = "medium"
    ) -> Dict[str, Any]:
        """Core multi-generational yield reasoning."""
        strategies = {
            "low": {
                "allocation": {
                    "Bitcoin (self-custodied)": 0.30,
                    "Productive land + skills": 0.40,
                    "Stable sovereign bonds": 0.30,
                },
                "expected_real_yield": "3-5% long-term",
                "antifragility": "High (hard assets + human capital)",
            },
            "medium": {
                "allocation": {
                    "Bitcoin (self-custodied)": 0.25,
                    "Diversified productive businesses": 0.35,
                    "Real assets (land, energy, timber)": 0.25,
                    "Knowledge & reputation capital": 0.15,
                },
                "expected_real_yield": "5-8% long-term (with volatility)",
                "antifragility": "Very High (convex to disorder)",
            },
            "high": {
                "allocation": {
                    "Bitcoin + high-conviction asymmetric bets": 0.40,
                    "Founder/owner equity in antifragile companies": 0.35,
                    "Physical + intellectual real assets": 0.25,
                },
                "expected_real_yield": "7-12%+ long-term (high variance)",
                "antifragility": "Extreme (benefits from black swans)",
            },
        }

        chosen = strategies.get(risk_tolerance, strategies["medium"])

        return {
            "horizon_years": horizon_years,
            "recommended_allocation": chosen["allocation"],
            "expected_real_yield": chosen["expected_real_yield"],
            "antifragility_score": chosen["antifragility"],
            "lgp_notes": "Prioritizes assets that retain or increase value across societal regime changes. Avoids heavy reliance on any single monetary or political system.",
            "attestation_note": "This analysis should be signed and Merkle-attested by the agent for generational auditability.",
        }

    def lgp_capital_allocation(
        self, capital: float, generations: int = 3, threat_model: str = "tyranny_or_inflation"
    ) -> Dict[str, Any]:
        """
        Explicit multi-generational capital allocation with LGP focus.
        """
        if threat_model == "tyranny_or_inflation":
            allocation = {
                "Hard assets (land, energy, precious metals)": 0.35,
                "Bitcoin (self-custodied, multisig)": 0.30,
                "Productive skills & reputation": 0.20,
                "Decentralized businesses / equity": 0.15,
            }
            rationale = "Maximizes optionality and resilience against monetary debasement and authoritarian overreach."
        else:
            allocation = {
                "Bitcoin (self-custodied)": 0.40,
                "Real productive assets": 0.30,
                "Human + intellectual capital": 0.20,
                "Diversified global equities (with caution)": 0.10,
            }
            rationale = "Balanced growth with strong antifragile tilt."

        lgp_score = self._calculate_lgp_score(allocation, generations)

        return {
            "total_capital": capital,
            "generations": generations,
            "threat_model": threat_model,
            "recommended_allocation": allocation,
            "lgp_score": round(lgp_score, 3),
            "rationale": rationale,
            "attestation_note": "Agent should produce Merkle-attested version of this allocation.",
        }

    def _calculate_lgp_score(self, allocation: Dict[str, float], generations: int) -> float:
        """Simple heuristic for multi-generational robustness."""
        base = 0.0
        for asset, weight in allocation.items():
            asset_lower = asset.lower()
            if "bitcoin" in asset_lower or "land" in asset_lower or "energy" in asset_lower:
                base += weight * 0.95
            elif "skills" in asset_lower or "reputation" in asset_lower:
                base += weight * 0.85
            else:
                base += weight * 0.5
        # Slight decay over generations if not antifragile enough
        return min(1.0, base * (1 - (generations - 1) * 0.05))

    def capital_preservation_score(self, allocation: Dict[str, float]) -> float:
        """Legacy method for compatibility."""
        return self._calculate_lgp_score(allocation, generations=2)
