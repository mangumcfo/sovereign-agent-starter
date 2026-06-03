"""
Data-Room Classifier — extruded from AI Agents for M&A (Book 11), Ch 2:

  "Unstructured data rooms with 30,000 documents overwhelm human review capacity.
   The deal team lead defines clean-room separation and data classification for each deal."

Book→code: the human (deal team lead) DEFINES the classification scheme (material, gated); the
agent APPLIES it (GREEN); cross-compartment leaks are flagged as proposals only (RED, never auto).
Agents propose; the human disposes. No external deps — pure capability + governance.
"""
from __future__ import annotations

GATES = {
    "classify_document":          ("read",     "GREEN"),   # apply the lead's scheme
    "define_classification_scheme": ("write",  "YELLOW"),  # material — human defines/approves
    "flag_cross_compartment_leak": ("escalate", "RED"),    # proposal-only, never auto-acts
}


class DataRoomClassifier:
    """Operator-adaptable. The deal team lead's scheme is the source of truth."""

    def __init__(self, scheme: dict | None = None):
        # scheme: {compartment: [keywords]} — defined by the human (define_classification_scheme).
        self.scheme = scheme or {}

    def _scope(self, action: str) -> str:
        return GATES.get(action, ("?", "RED"))[1]

    def classify_document(self, doc: dict) -> dict:
        """GREEN — apply the lead's scheme to one document. Returns a classification result."""
        text = (doc.get("name", "") + " " + doc.get("text", "")).lower()
        hits = [c for c, kws in self.scheme.items() if any(k.lower() in text for k in kws)]
        compartment = hits[0] if hits else "unclassified"
        return {"action": "classify_document", "scope": "GREEN", "executed": True,
                "doc_id": doc.get("id"), "compartment": compartment,
                "needs_human": compartment == "unclassified"}

    def define_classification_scheme(self, scheme: dict) -> dict:
        """YELLOW — material. The agent PROPOSES; the human (deal team lead) approves before it applies."""
        return {"action": "define_classification_scheme", "scope": "YELLOW", "executed": False,
                "proposal": {"scheme": scheme}, "needs_human": True}

    def flag_cross_compartment_leak(self, doc_id: str, frm: str, to: str) -> dict:
        """RED — proposal only; never auto-acts on a suspected clean-room breach."""
        return {"action": "flag_cross_compartment_leak", "scope": "RED", "executed": False,
                "proposal": {"doc_id": doc_id, "from": frm, "to": to,
                             "why": "possible clean-room separation breach"}, "needs_human": True}
