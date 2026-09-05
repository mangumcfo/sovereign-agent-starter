"""identity_fp_matches_expected — the MATCH flag (AA's condition, KM GO 2026-09-05).

`expected_fp_configured` reports that *a* value is configured. It cannot report whether it is the
*right* one — which is how a 12-char prefix sat in the running process refusing the operator's own
correct key while every gate row read green.

AA's condition on the fix: the flag must be computed by the SAME function /api/open enforces with,
never a reimplementation. A second copy drifts from the bind exactly as the prefix did. These tests
pin that, and include the pair nobody ran before the failed click: flag true <-> a subsequent open
actually succeeds.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "usn_erp_surface"))
import server as surface  # noqa: E402
from sovereign_agent.keystore.node_keystore import generate_node_key  # noqa: E402


@pytest.fixture
def env(tmp_path, monkeypatch):
    ks = tmp_path / "keystore"
    ks.mkdir()
    node = generate_node_key(str(ks), "UniversalSovereignNode", at="2026-09-05T00:00:00Z")
    monkeypatch.setenv("NODE_KEYSTORE_DIR", str(ks))
    monkeypatch.setenv("SUBSTRATE_STORAGE_ROOT", str(tmp_path / "substrate"))
    monkeypatch.delenv("USN_EXPECTED_FINGERPRINT", raising=False)
    surface._BINDING = None
    yield surface.app.test_client(), node.fingerprint
    surface._BINDING = None


def _flag(client):
    return client.get("/api/vocab").get_json()["identity_fp_matches_expected"]


# ── AA's regression set ────────────────────────────────────────────────────────────────────────
def test_truncated_expected_refuses_and_flag_is_false(env, monkeypatch):
    """12-char prefix of the real fingerprint — pinned forever. This is the live failure of
    2026-09-02: the correct key, refused, while the presence flag read true."""
    client, fp = env
    assert len(fp) == 16, "fingerprints are 16 chars; the prefix bug lived in that gap"
    monkeypatch.setenv("USN_EXPECTED_FINGERPRINT", fp[:12])
    assert client.get("/api/vocab").get_json()["expected_fp_configured"] is True  # presence: yes
    assert _flag(client) is False                                                # match: NO
    assert client.post("/api/open", json={}).status_code == 403
    assert surface._BINDING is None


def test_full_expected_opens_and_flag_is_true(env, monkeypatch):
    client, fp = env
    monkeypatch.setenv("USN_EXPECTED_FINGERPRINT", fp)
    assert _flag(client) is True
    assert client.post("/api/open", json={}).status_code == 200
    assert surface._BINDING is not None


def test_flag_true_iff_open_succeeds(env, monkeypatch):
    """THE PAIR — the pass-direction nobody ran before the click failed. The flag and the bind must
    agree in BOTH directions, because a flag that is true while the open refuses is exactly the
    hazard this exists to remove."""
    client, fp = env
    for expected, want in ((fp, True), (fp[:12], False), ("0" * 16, False)):
        monkeypatch.setenv("USN_EXPECTED_FINGERPRINT", expected)
        surface._BINDING = None
        flag = _flag(client)
        opened = client.post("/api/open", json={}).status_code == 200
        assert flag is want, f"flag {flag} != {want} for expected={expected!r}"
        assert flag == opened, f"flag {flag} disagrees with open success {opened}"


def test_flag_is_null_when_nothing_is_expected(env):
    """No expectation configured -> null, never True. An uncomputable check must not read as a pass."""
    client, _ = env
    assert _flag(client) is None
    assert client.get("/api/vocab").get_json()["expected_fp_configured"] is False


def test_flag_never_leaks_the_fingerprint(env, monkeypatch):
    client, fp = env
    monkeypatch.setenv("USN_EXPECTED_FINGERPRINT", fp)
    body = json.dumps(client.get("/api/vocab").get_json())
    assert fp not in body, "the flag is a boolean; the value must never reach the wire"


def test_open_and_vocab_share_one_implementation(env):
    """AA's structural condition: /api/open must not carry its own copy of the comparison."""
    src = Path(surface.__file__).read_text()
    open_body = src[src.index("def open_node"):src.index("def close_node")]
    assert "_expected_fingerprint_check" in open_body, "open must call the shared check"
    # Naming the variable in prose is fine; RE-READING it in open is the second implementation.
    assert 'os.environ.get("USN_EXPECTED_FINGERPRINT")' not in open_body, (
        "open re-reads the env itself — that is a second copy of the comparison, and it will drift"
    )
    assert "identity_fingerprint()" not in open_body, (
        "open derives the fingerprint itself — same drift hazard; let the shared check do it"
    )
