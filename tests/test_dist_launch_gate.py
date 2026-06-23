"""Constitutional gate on live distribution (audit [468]): a --live post is REFUSED unless the
distribution_launch:<book> obligation is APPROVED by the human (Propose→Approve→Execute), and the
approving principal is stamped on dispatch. Fail-closed: no ledger / no obligation / unapproved → no post."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_scheduler():
    spec = importlib.util.spec_from_file_location("sch", ROOT / "scripts" / "dist_scheduler" / "scheduler.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def sch(tmp_path, monkeypatch):
    m = _load_scheduler()
    # isolate the dist dir + assets so dispatch has something to iterate
    dist = tmp_path / "dist" / "bookX"
    dist.mkdir(parents=True)
    (dist / "x_thread.json").write_text(json.dumps({"content": ["post"], "meta": {}}), encoding="utf-8")
    monkeypatch.setattr(m, "DIST", tmp_path / "dist")
    monkeypatch.setattr(m, "_load_standard", lambda: {})
    monkeypatch.setattr(m, "_v1_headless_channels", lambda std: ["x"])
    monkeypatch.setattr(m, "_drip_schedule", lambda std: [])

    class _FakeClient:
        def post(self, asset, dry_run=True):
            return {"channel": "x", "ok": True, "live": not dry_run, "detail": "ok", "ts": "now"}

        def available(self):
            return True

    monkeypatch.setattr(m, "CLIENTS", {"x": _FakeClient()})
    monkeypatch.setattr(m, "CHANNEL_ASSET", {"x": "x_thread"})
    return m


def test_live_refused_when_launch_not_approved(sch, monkeypatch):
    monkeypatch.setattr(sch, "launch_approval", lambda b: (False, None, "not approved"))
    res = sch.dispatch("bookX", dry_run=False)
    assert res["refused"] is True
    assert not any(r.get("live") for r in res["results"])   # NOTHING posted


def test_live_permitted_and_principal_stamped_when_approved(sch, monkeypatch):
    monkeypatch.setattr(sch, "launch_approval", lambda b: (True, "KM-1176", "approved"))
    res = sch.dispatch("bookX", dry_run=False)
    assert not res.get("refused")
    assert res["approved_by"] == "KM-1176"
    assert any(r.get("live") and r.get("approved_by") == "KM-1176" for r in res["results"])


def test_dry_run_never_gated_never_posts(sch):
    res = sch.dispatch("bookX", dry_run=True)
    assert not res.get("refused")
    assert not any(r.get("live") for r in res["results"])   # dry-run never goes live


def test_launch_approval_fails_closed_without_ledger(sch, monkeypatch):
    # point at a bogus ledger root → ledger error → fail CLOSED (not approved)
    monkeypatch.setenv("OBLIGATION_LEDGER_ROOT", "/nonexistent/path/xyz")
    ok, principal, reason = sch.launch_approval("no_such_book")
    assert ok is False and principal is None
