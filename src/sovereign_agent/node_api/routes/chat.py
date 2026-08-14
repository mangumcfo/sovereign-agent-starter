"""chat.py — the node's talk surface: POST /api/v1/chat → loopback mind (read facts + local completion) that
ADVISES and PROPOSES, never executes. Composes sovereign_agent.agent.local_mind (package→package). Loopback-only;
no admission logic; consequential acts come back as PROPOSE text for KM's keyboard / the Gate Inbox."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..auth import require_principal
from ...agent import local_mind

bp = Blueprint("chat", __name__, url_prefix="/api/v1")


@bp.route("/chat", methods=["POST"])
@require_principal
def chat():
    body = request.get_json(silent=True) or {}
    prompt = str(body.get("prompt", "")).strip()
    if not prompt:
        return jsonify({"error": "prompt required"}), 400
    f = local_mind.facts()
    proposals = local_mind.proposals_text(f)
    model = body.get("model") or local_mind.pick_model()
    if not model:
        # no model up: still return substance from the read tools (facts + exact proposals)
        return jsonify({"model": None, "answer": "", "facts": f, "proposals": proposals,
                        "note": "no local model on loopback — start Ollama/vLLM or pass a model; FACTS + PROPOSALS "
                                "above come from read tools. Nothing executed."}), 200
    try:
        ans = local_mind.complete(prompt, model=model)
    except ValueError as e:            # loopback refusal (no cloud brain)
        return jsonify({"error": str(e)}), 400
    except Exception as e:             # noqa: BLE001 — model down: substance still returned
        return jsonify({"model": model, "answer": "", "facts": f, "proposals": proposals,
                        "note": f"model not answering ({type(e).__name__}); FACTS + PROPOSALS from read tools. Nothing executed."}), 200
    return jsonify({"model": model, "answer": ans, "facts": f, "proposals": proposals,
                    "note": "advise-only; the node executed nothing. Consequential change stays behind KM's keyboard / Gate Inbox."})
