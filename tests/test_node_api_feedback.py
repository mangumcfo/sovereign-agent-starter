"""Node API /feedback + /awaiting_km + disposition gates (every_gate_earns_a_test, audit 2026-06-11).

The Atrium loop-closure intake (feedback.py) carries three constitutional gates the audit asked be
EARNED by a test, not asserted by a docstring:
  1. principal-binding — owner is the AUTHENTICATED principal, never the request body (no spoofing).
  2. error voice — not-found → 404, already-closed → 409, bad action → 400 (loud + contextual, §4).
  3. the Awaiting-KM projection only lists obligations gated on the human and not yet disposed.
Storage is a node-local ledger in a tmp dir (never the live seal chain).
"""
import pytest


@pytest.fixture
def owner_client(tmp_path, monkeypatch):
    """Loopback-trust owner (KM-1176) — a real authenticated principal, not dev/anonymous."""
    monkeypatch.delenv("BREATHLINE_NODE_API_DEV", raising=False)
    monkeypatch.setenv("BREATHLINE_NODE_LOOPBACK_OWNER", "KM-1176")
    monkeypatch.setenv("OBLIGATION_LEDGER_ROOT", str(tmp_path / "obligations"))
    from sovereign_agent.node_api import deps
    deps.reset_node()
    from sovereign_agent.node_api.server import create_app
    yield create_app().test_client()
    deps.reset_node()


def _mint(client, text="Tighten the ch3 cross-foot", **extra):
    # default category=judgment so the packet is KM-gated (lands in Awaiting-Me) for the gate tests below.
    body = {"text": text, "type": "viewer", "book": "B12", "chapter": 3, "category": "judgment", **extra}
    r = client.post("/api/v1/feedback", json=body)
    return r


def test_feedback_binds_owner_to_authenticated_principal(owner_client):
    # Even if the body tries to set owner, the ledger records the AUTHENTICATED principal (no spoofing).
    r = _mint(owner_client, owner="attacker", produced_by="attacker")
    assert r.status_code == 201
    ob = r.get_json()["obligation"]
    assert ob["owner"] == "KM-1176"           # bound to current_principal, NOT the request body
    assert ob["ref"] == "viewer:B12 ch3"      # resolving source ref built from the typed fields
    assert ob["next_gate"] == "Human disposition"   # judgment → KM-gated discrete lane
    assert ob["category"] == "judgment" and ob["lane"] == "discrete"


def test_a2_mechanical_goes_to_batch_not_km(owner_client):
    # A mechanical capture (wording/typo/structure) is born-approved into the batch lane — it does NOT
    # land on KM's Awaiting-Me. This is the burden-removal: mechanical edits never touch his attention.
    for cat in ("typo", "wording", "structure"):
        r = owner_client.post("/api/v1/feedback", json={"text": "fix this", "category": cat})
        assert r.status_code == 201
        body = r.get_json()
        assert body["lane"] == "batch" and body["category"] == cat
        ob = body["obligation"]
        assert ob["material"] is False and ob["next_gate"] == "batch:mechanical"
    aw = owner_client.get("/api/v1/awaiting_km").get_json()
    assert aw["meta"]["count"] == 0           # nothing mechanical reached KM


def test_a2_technical_routes_to_tiger_implement(owner_client):
    ob = owner_client.post("/api/v1/feedback", json={"text": "TOC links broken", "category": "technical"}).get_json()["obligation"]
    assert ob["lane"] == "discrete" and ob["next_gate"] == "KM confirm → Tiger implement" and ob["material"] is False


def test_a2_judgment_is_km_gated_discrete(owner_client):
    ob = owner_client.post("/api/v1/feedback", json={"text": "is this framing right?", "category": "judgment"}).get_json()["obligation"]
    assert ob["lane"] == "discrete" and ob["next_gate"] == "Human disposition" and ob["material"] is True
    assert owner_client.get("/api/v1/awaiting_km").get_json()["meta"]["count"] == 1


def test_a2_smart_default_kills_other(owner_client):
    # No category given → smart default 'wording' (mechanical), flagged as defaulted. Never 'other'.
    body = owner_client.post("/api/v1/feedback", json={"text": "no category here"}).get_json()
    assert body["category"] == "wording" and body["category_defaulted"] is True and body["lane"] == "batch"


def test_feedback_missing_text_is_loud_400(owner_client):
    r = owner_client.post("/api/v1/feedback", json={"type": "general"})
    assert r.status_code == 400
    body = r.get_json()
    assert body["error"] == "missing_text"
    assert "next_step" in body and "what" in body   # error voice: what + next step (§4)
    # canonical shape (audit 2026-06-13d #9): machine code mirrors the slug + why + cylinder_ref present
    assert body["code"] == "missing_text" and body["why"] and "cylinder_ref" in body


def test_awaiting_km_lists_then_drops_on_accept(owner_client):
    oid = _mint(owner_client).get_json()["obligation"]["id"]
    # projection lists it while it awaits the human
    aw = owner_client.get("/api/v1/awaiting_km").get_json()
    assert aw["meta"]["gate"] == "Human disposition" and aw["meta"]["chain_ok"] is True
    assert any(i["id"] == oid and i["owner"] == "KM-1176" for i in aw["awaiting"])
    # accept = approve → it clears the gate and leaves the Awaiting-KM view
    r = owner_client.post(f"/api/v1/feedback/{oid}/disposition", json={"action": "accept"})
    assert r.status_code == 200 and r.get_json()["action"] == "accept"
    aw2 = owner_client.get("/api/v1/awaiting_km").get_json()
    assert all(i["id"] != oid for i in aw2["awaiting"])


def test_reject_closes_and_double_reject_is_409(owner_client):
    oid = _mint(owner_client).get_json()["obligation"]["id"]
    r = owner_client.post(f"/api/v1/feedback/{oid}/disposition",
                          json={"action": "reject", "note": "out of scope"})
    assert r.status_code == 200 and r.get_json()["action"] == "reject"
    # already disposed → loud 409, not a silent re-close
    r2 = owner_client.post(f"/api/v1/feedback/{oid}/disposition", json={"action": "reject"})
    assert r2.status_code == 409 and r2.get_json()["error"] == "already_closed"


def test_reject_with_note_routes_feedback_to_owning_agent(owner_client):
    """GB [454]/[456] Item 1 — a reject carrying a NOTE must mint TRACKED follow-on work owned by the
    card's owner-agent (not bounce back to KM, not die in the close-evidence string)."""
    oid = _mint(owner_client).get_json()["obligation"]["id"]
    j = owner_client.post(f"/api/v1/feedback/{oid}/disposition",
                          json={"action": "reject", "note": "make the carousel pop — aha per slide"}).get_json()
    assert j["action"] == "reject"
    # the note minted a follow-on obligation, routed to the agent (tiger by default)
    assert j["feedback_obligation"], "reject-with-note must mint a tracked follow-on obligation"
    assert j["routed_to"] == "tiger"
    # it is gated on the AGENT, so it does NOT reappear in KM's awaiting-me queue
    aw = owner_client.get("/api/v1/awaiting_km").get_json()
    assert all(i["id"] != j["feedback_obligation"] for i in aw["awaiting"])
    # a reject WITHOUT a note mints nothing (just a close)
    oid2 = _mint(owner_client).get_json()["obligation"]["id"]
    j2 = owner_client.post(f"/api/v1/feedback/{oid2}/disposition", json={"action": "reject"}).get_json()
    assert j2.get("feedback_obligation") is None


def test_disposition_not_found_is_404(owner_client):
    r = owner_client.post("/api/v1/feedback/obl_does_not_exist/disposition", json={"action": "accept"})
    assert r.status_code == 404 and r.get_json()["error"] == "obligation_not_found"


def test_disposition_bad_action_is_400(owner_client):
    oid = _mint(owner_client).get_json()["obligation"]["id"]
    r = owner_client.post(f"/api/v1/feedback/{oid}/disposition", json={"action": "maybe"})
    assert r.status_code == 400 and r.get_json()["error"] == "bad_action"


def test_doc_serves_whitelisted_and_refuses_traversal(owner_client, tmp_path):
    # serves a real artifact under the repo's artifacts/ root
    import pathlib
    repo = pathlib.Path(__file__).resolve().parents[1]
    sample = repo / "artifacts" / "DISTRIBUTION_P1_G1_2026-06-11.md"
    if sample.exists():
        r = owner_client.get("/api/v1/doc?path=artifacts/DISTRIBUTION_P1_G1_2026-06-11.md")
        assert r.status_code == 200 and "markdown" in r.get_json()
    # missing path → 400; traversal + absolute system path → refused (not served)
    assert owner_client.get("/api/v1/doc").status_code == 400
    assert owner_client.get("/api/v1/doc?path=../../../../etc/passwd").status_code == 404
    assert owner_client.get("/api/v1/doc?path=/etc/passwd").status_code == 404
    # non-doc extension under a root is refused (only .md/.txt/.yaml served)
    assert owner_client.get("/api/v1/doc?path=artifacts/../src/sovereign_agent/node_api/server.py").status_code == 404


def test_handshakes_filters_done_and_tolerates_malformed(owner_client, tmp_path, monkeypatch):
    """audit 2026-06-13d #29: /handshakes returns only non-'done' residue, correct meta.count, and
    degrades to an empty list (no 500) on a malformed store."""
    import json
    store = tmp_path / "handshakes.json"
    store.write_text(json.dumps([
        {"id": "hs1", "status": "pending", "created_at": "2026-06-13T01:00:00Z"},
        {"id": "hs2", "status": "done", "created_at": "2026-06-13T02:00:00Z"},
    ]), encoding="utf-8")
    monkeypatch.setenv("HANDSHAKES_STORE", str(store))
    body = owner_client.get("/api/v1/handshakes").get_json()
    assert [h["id"] for h in body["handshakes"]] == ["hs1"] and body["meta"]["count"] == 1
    store.write_text("{ broken json", encoding="utf-8")
    r2 = owner_client.get("/api/v1/handshakes")
    assert r2.status_code == 200 and r2.get_json()["handshakes"] == []


def test_reply_on_open_gate_attaches_and_never_batches(owner_client):
    """finding:feedback_misroute_2026-06-13 (52acd023): a reply typed ON an open human-gated card is
    INPUT — it must ATTACH to that card (carry its obligation_id) and NEVER be auto-batched into
    invisibility. Root cause of 'KM's feedback gets missed': his ISBNs were born-approved as [wording]
    into batch:mechanical and never linked to the card."""
    # 1) an open human-gated 'provide value' card (e.g. "provide Vol 1 ISBNs")
    parent = _mint(owner_client, text="Provide the Vol 1 ISBNs", category="judgment").get_json()["obligation"]
    assert parent["next_gate"] == "Human disposition"
    # 2) KM replies on that card with the value, classified (or defaulting) as mechanical wording
    r = owner_client.post("/api/v1/feedback", json={
        "text": "978-1-..., 978-1-...", "category": "wording", "reply_to": parent["id"]})
    assert r.status_code == 201
    body = r.get_json()
    # the reply is NOT batched (would have been invisible) — it routes to a visible discrete lane...
    assert body["lane"] != "batch"
    assert body["replies_to"] == parent["id"]          # ...and ATTACHES to the parent card
    assert body["obligation"]["ref"] == f"card:{parent['id']}"   # carries the parent obligation_id
    assert body["obligation"]["material"] is False     # input, not a new KM-decision, but visible+linked


def test_plain_mechanical_still_batches_when_no_reply_to(owner_client):
    """Guard: the fix only fires for replies to an OPEN gate — a free-standing wording edit still batches
    (the burden-removal for genuine mechanical edits is preserved)."""
    body = owner_client.post("/api/v1/feedback", json={"text": "fix a typo", "category": "wording"}).get_json()
    assert body["lane"] == "batch" and body["replies_to"] is None


def test_reply_to_closed_or_missing_id_does_not_attach(owner_client):
    """A reply_to that does not resolve to an OPEN obligation is ignored (no false attach); the packet
    classifies normally — a pointer is never written false."""
    body = owner_client.post("/api/v1/feedback", json={
        "text": "stray", "category": "wording", "reply_to": "obl_does_not_exist"}).get_json()
    assert body["replies_to"] is None and body["lane"] == "batch"
