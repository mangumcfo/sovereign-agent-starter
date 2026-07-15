"""AH-5 closure — the dev-mode/non-loopback refusal must live in create_app(), not only in cli_serve().

A direct-WSGI host (gunicorn/uwsgi) importing create_app() with BREATHLINE_NODE_API_DEV=1 bound off-loopback
previously bypassed the cli_serve guard, letting an unauthenticated caller self-assign the audit actor. The
factory now refuses at build time when the intended-bind host env is non-loopback.

The refusal path raises BEFORE any Flask/route import, so it runs without the sealed crypto substrate. The
loopback pass-through builds the full app (routes/crypto), which needs the sealed host — skipped-with-reason
here, while still asserting the AH-5 guard does NOT over-fire on loopback.
"""
import pytest

from sovereign_agent.node_api import server

_ENVS = ("BREATHLINE_NODE_API_DEV", "BREATHLINE_NODE_API_HOST")


def _clear(monkeypatch):
    for k in _ENVS:
        monkeypatch.delenv(k, raising=False)


def test_create_app_refuses_dev_mode_off_loopback(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("BREATHLINE_NODE_API_DEV", "1")
    monkeypatch.setenv("BREATHLINE_NODE_API_HOST", "0.0.0.0")
    with pytest.raises(RuntimeError, match="REFUSING TO BUILD APP"):
        server.create_app()


def test_create_app_dev_loopback_is_not_refused(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("BREATHLINE_NODE_API_DEV", "1")
    monkeypatch.setenv("BREATHLINE_NODE_API_HOST", "127.0.0.1")
    try:
        app = server.create_app()
    except Exception as e:  # noqa: BLE001
        assert not (isinstance(e, RuntimeError) and "REFUSING TO BUILD APP" in str(e)), \
            "AH-5 guard over-fired on a loopback bind"
        pytest.skip(f"full app build needs the sealed crypto substrate (absent): {type(e).__name__}")
    else:
        assert app is not None


def test_create_app_no_dev_off_loopback_is_allowed(monkeypatch):
    """Without dev mode, an off-loopback host is fine (real bearer auth applies) — the guard must not fire."""
    _clear(monkeypatch)
    monkeypatch.setenv("BREATHLINE_NODE_API_HOST", "0.0.0.0")
    try:
        app = server.create_app()
    except Exception as e:  # noqa: BLE001
        assert not (isinstance(e, RuntimeError) and "REFUSING TO BUILD APP" in str(e)), \
            "AH-5 guard fired without dev mode"
        pytest.skip(f"full app build needs the sealed crypto substrate (absent): {type(e).__name__}")
    else:
        assert app is not None
