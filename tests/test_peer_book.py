"""Tests for the LOCAL peer book (scripts/peer_book.py) — P0-4.

The peer book is a local-only file: public_hex + label, no defaults, no network, no route.
These assert the honest invariants: empty by default, add/list, bad-hex refused, dupe refused,
poisoned-HOME fail-loud, and — structurally — that no node_api route reads or writes it.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_PB = _ROOT / "scripts" / "peer_book.py"

_spec = importlib.util.spec_from_file_location("peer_book", _PB)
peer_book = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(peer_book)

HEX = "ab" * 64  # a well-formed 128-hex public_hex


@pytest.fixture()
def book(tmp_path, monkeypatch):
    p = tmp_path / "book.jsonl"
    monkeypatch.setenv("SOVEREIGN_PEER_BOOK", str(p))
    return p


def test_empty_by_default(book, capsys):
    # A fresh book ships with NO peers — the anti-directory invariant.
    assert peer_book.main(["list"]) == 0
    assert not book.exists()
    assert "empty" in capsys.readouterr().out.lower()


def test_add_then_list(book, capsys):
    rc = peer_book.main(["add", "--label", "Beard", "--public-hex", HEX,
                         "--where-met", "TCP 2026", "--at", "2026-08-13T00:00:00+00:00"])
    assert rc == 0
    rows = [json.loads(l) for l in book.read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    assert rows[0]["public_hex"] == HEX and rows[0]["label"] == "Beard"
    # file is owner-only
    assert (book.stat().st_mode & 0o777) == 0o600
    out = capsys.readouterr().out.lower()
    assert "not recognition" in out and "not" in out  # label != recognition/standing


def test_bad_hex_refused(book):
    assert peer_book.main(["add", "--label", "x", "--public-hex", "deadbeef"]) == 2
    assert not book.exists()  # nothing written on refusal


def test_duplicate_refused(book):
    assert peer_book.main(["add", "--label", "a", "--public-hex", HEX, "--at", "2026-08-13T00:00:00+00:00"]) == 0
    assert peer_book.main(["add", "--label", "b", "--public-hex", HEX, "--at", "2026-08-13T00:01:00+00:00"]) == 1
    rows = [l for l in book.read_text().splitlines() if l.strip()]
    assert len(rows) == 1  # the dupe did not append


def test_empty_label_refused(book):
    assert peer_book.main(["add", "--label", "   ", "--public-hex", HEX]) == 2


def test_poisoned_home_fails_loud(monkeypatch):
    monkeypatch.delenv("SOVEREIGN_PEER_BOOK", raising=False)
    monkeypatch.setenv("HOME", "/path/to/home")
    with pytest.raises(SystemExit):
        peer_book.book_path()


def test_no_http_route_touches_a_peer_book():
    # Structural: the capture we refuse is a served/synced directory. No node_api source may
    # read/write a peer book. (peer_book.py lives under scripts/, never imported by a route.)
    import re
    routes_dir = _ROOT / "src" / "sovereign_agent" / "node_api"
    hits = []
    for py in routes_dir.rglob("*.py"):
        if re.search(r"peer_book|peerbook|address_book|\bcontact\b", py.read_text()):
            hits.append(py.name)
    assert hits == [], f"a node_api file references a peer book (directory-capture risk): {hits}"
