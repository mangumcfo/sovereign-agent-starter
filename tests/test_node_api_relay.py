"""Agent Channel relay (A1) — the card → KM gate → THREAD append → reply fold-back (every_gate_earns_a_test).

Asserts GB meta-review #1 end to end: an agent posts a prompt, KM (owner) clicks Relay, the prompt lands
on the receipted THREAD, and the other agent's reply surfaces back on the card. KM gates every relay
(owner-only) but performs none. Uses a tmp THREAD + tmp relay store — never the live coordination record.
"""
import pytest

from sovereign_agent.node_api import thread_channel


@pytest.fixture
def owner_client(tmp_path, monkeypatch):
    monkeypatch.delenv("BREATHLINE_NODE_API_DEV", raising=False)
    monkeypatch.setenv("BREATHLINE_NODE_LOOPBACK_OWNER", "KM-1176")
    monkeypatch.setenv("OBLIGATION_LEDGER_ROOT", str(tmp_path / "obligations"))
    monkeypatch.setenv("RELAY_STORE", str(tmp_path / "relays.json"))
    monkeypatch.setenv("BREATHLINE_THREAD_FILE", str(tmp_path / "THREAD_Tiger_GB.ndjson"))
    from sovereign_agent.node_api import deps
    deps.reset_node()
    from sovereign_agent.node_api.server import create_app
    yield create_app().test_client()
    deps.reset_node()


@pytest.fixture
def dev_client(tmp_path, monkeypatch):
    monkeypatch.setenv("BREATHLINE_NODE_API_DEV", "1")
    monkeypatch.delenv("BREATHLINE_NODE_LOOPBACK_OWNER", raising=False)
    monkeypatch.delenv("BREATHLINE_NODE_OWNER", raising=False)
    monkeypatch.setenv("RELAY_STORE", str(tmp_path / "relays.json"))
    monkeypatch.setenv("BREATHLINE_THREAD_FILE", str(tmp_path / "THREAD_Tiger_GB.ndjson"))
    from sovereign_agent.node_api import deps
    deps.reset_node()
    from sovereign_agent.node_api.server import create_app
    yield create_app().test_client()
    deps.reset_node()


def test_post_relay_creates_pending_card(owner_client):
    r = owner_client.post("/api/v1/relay", json={"from": "gb", "to": "tiger", "prompt": "Wire A2 next."})
    assert r.status_code == 201
    it = r.get_json()
    assert it["status"] == "pending" and it["from"] == "gb" and it["to"] == "tiger"
    assert it["created_by"] == "KM-1176"          # bound to the authenticated principal, not the body
    lst = owner_client.get("/api/v1/relays").get_json()
    assert lst["meta"]["counts"]["pending"] == 1


def test_missing_prompt_and_same_agent_are_400(owner_client):
    r = owner_client.post("/api/v1/relay", json={"to": "tiger"})
    assert r.status_code == 400
    # canonical error shape (audit 2026-06-13d #9): code == friendly slug, plus what/why/next_step.
    b = r.get_json()
    assert b["error"] == "missing_prompt" and b["code"] == "missing_prompt"
    assert b["why"] and b["next_step"] and "cylinder_ref" in b
    assert owner_client.post("/api/v1/relay", json={"from": "gb", "to": "gb", "prompt": "x"}).status_code == 400


def test_relay_is_owner_gated(dev_client):
    # create as dev (allowed: any principal can post a prompt)
    rid = dev_client.post("/api/v1/relay", json={"to": "tiger", "prompt": "hi"}).get_json()["id"]
    # but dev/anonymous cannot perform KM's Relay gate
    r = dev_client.post(f"/api/v1/relay/{rid}/relay")
    assert r.status_code == 403 and r.get_json()["error"] == "forbidden"


def test_relay_appends_to_thread_and_reply_folds_back(owner_client, tmp_path):
    rid = owner_client.post("/api/v1/relay",
                            json={"from": "gb", "to": "tiger", "prompt": "Confirm pins for A2.",
                                  "ref": "a2-pins"}).get_json()["id"]
    # KM clicks Relay → it lands on the THREAD
    r = owner_client.post(f"/api/v1/relay/{rid}/relay")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "relayed" and body["to"] == "tiger" and body["receipt"]
    thread = thread_channel.load()
    assert thread and thread[-1]["from"] == "gb" and thread[-1]["to"] == "tiger" and "A2" in thread[-1]["msg"]

    # before a reply: status stays relayed
    lst = owner_client.get("/api/v1/relays").get_json()
    assert lst["meta"]["counts"]["relayed"] == 1 and lst["meta"]["counts"]["answered"] == 0

    # the other agent replies on the THREAD → it surfaces back on the card
    thread_channel.append("tiger", "gb", "a2-pins-ack", "Pins confirmed; building A2.")
    lst2 = owner_client.get("/api/v1/relays").get_json()
    card = lst2["relays"][0]
    assert card["status"] == "answered"
    assert card["reply"]["from"] == "tiger" and "building A2" in card["reply"]["msg"]


def test_double_relay_is_409(owner_client):
    rid = owner_client.post("/api/v1/relay", json={"to": "tiger", "prompt": "x"}).get_json()["id"]
    assert owner_client.post(f"/api/v1/relay/{rid}/relay").status_code == 200
    assert owner_client.post(f"/api/v1/relay/{rid}/relay").status_code == 409


def test_relay_send_unknown_is_404(owner_client):
    assert owner_client.post("/api/v1/relay/relay_nope/relay").status_code == 404


def test_dismiss_archives(owner_client):
    rid = owner_client.post("/api/v1/relay", json={"to": "tiger", "prompt": "x"}).get_json()["id"]
    assert owner_client.post(f"/api/v1/relay/{rid}/dismiss").status_code == 200
    assert all(c["id"] != rid for c in owner_client.get("/api/v1/relays").get_json()["relays"])


def test_thread_format_matches_scripts_thread(owner_client, tmp_path):
    """The node-written THREAD entry must carry the same receipt the scripts/thread.py chain computes."""
    rid = owner_client.post("/api/v1/relay", json={"from": "gb", "to": "tiger", "prompt": "hash check"}).get_json()["id"]
    owner_client.post(f"/api/v1/relay/{rid}/relay")
    e = thread_channel.load()[-1]
    import hashlib
    expect = hashlib.sha256("|".join(["GENESIS", "gb", "tiger", e["ref"], "hash check"]).encode()).hexdigest()
    assert e["hash"] == expect and e["prev"] == "GENESIS" and e["n"] == 1
