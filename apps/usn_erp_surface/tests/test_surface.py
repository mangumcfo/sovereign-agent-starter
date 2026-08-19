#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proof tests for the USN ERP Operator Surface — P2, P3, P4, P5, P6.

Run:  ./.venv/bin/python -m pytest apps/usn_erp_surface/tests/ -q

These are not unit tests of the app's internals. Each one asserts a bar row:

  P2  a recorded event changes bytes on disk through a module path, and survives a restart
  P3  a tax event is a record only — no statutory act is reachable, and the fence proves it
  P4  a gated act writes nothing until an explicit human approval; a denial writes nothing at all
  P5  the export is derived from node state and byte-identical on re-run
  P6  the kill-grep actually catches violations — proved by injecting each one and asserting RED

The negative tests matter as much as the positive ones. A gate that only ever says yes is not a
gate, and a kill-grep that has never gone RED is a rubber stamp.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import textwrap

import pytest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS_ROOT = os.path.dirname(APP_DIR)
if APPS_ROOT not in sys.path:
    sys.path.insert(0, APPS_ROOT)

from usn_erp_surface.node_binding import (  # noqa: E402
    STATUTORY_FENCE_FIELDS,
    NodeBinding,
    SurfaceError,
)

AT = "2026-08-19T00:00:00+00:00"


# ==================================================================================================
# Fixtures
# ==================================================================================================

@pytest.fixture()
def node(tmp_path):
    """A throwaway node: a real key, and empty registry/ledger roots."""
    from sovereign_agent.keystore.node_keystore import generate_node_key

    ks = tmp_path / "keystore"
    ks.mkdir()
    generate_node_key(str(ks), "node", at=AT)
    return {"keystore": str(ks), "registry": str(tmp_path / "registry"),
            "ledger": str(tmp_path / "ledger"), "root": tmp_path}


def bind(node, *, regulated=True, operator="kenn"):
    return NodeBinding(node["keystore"], node["registry"], node["ledger"],
                       regulated=regulated, operator=operator, mandate="household")


def objects_ndjson(node) -> str:
    return os.path.join(node["registry"], "objects.ndjson")


def approve_all(nb, submitted):
    """Approve a staged act. Only ever called explicitly — mirroring the UI, where the only path to
    approval is an operator click."""
    assert submitted["gated"], "expected this act to be held at the gate"
    return nb.dispose(submitted["req_id"], approve=True)


# ==================================================================================================
# P2 · A recorded event changes disk, through a module path, and survives a restart
# ==================================================================================================

def test_p2_record_changes_disk_via_module_path(node):
    nb = bind(node, regulated=False)
    assert not os.path.exists(objects_ndjson(node)), "registry should not exist before any record"

    receipt = nb.record_income(work_ref="consulting-august", amount=2400, unit="USD")["receipt"]

    assert os.path.isfile(objects_ndjson(node)), "the node's own store was not created"
    with open(objects_ndjson(node), encoding="utf-8") as fh:
        lines = [json.loads(x) for x in fh if x.strip()]
    assert len(lines) == 1
    row = lines[0]

    # the bytes on disk are the module's own governed-object shape, not an app-invented one
    assert row["object_id"] == "IncomeEvent:kenn:consulting-august"
    assert row["kind"] == "income"
    assert row["mandate"] == "household"
    assert row["payload"] == {"id": "kenn:consulting-august", "earner": "kenn",
                              "work_ref": "consulting-august", "amount": 2400.0, "unit": "USD"}
    assert row["version_hash"] == receipt["version_hash"]
    assert row["prev_hash"] is None


def test_p2_survives_restart(node):
    """A fresh binding over the same paths — the app equivalent of relaunching — still sees it."""
    nb = bind(node, regulated=False)
    nb.record_income(work_ref="job-1", amount=100, unit="USD")
    nb.record_income(work_ref="job-2", amount=250, unit="USD")
    before = nb.events()

    del nb
    nb2 = bind(node, regulated=False)
    after = nb2.events()

    assert after["total"] == before["total"] == 2
    assert [e["object_id"] for e in after["items"]] == [e["object_id"] for e in before["items"]]
    assert all(e["check"]["verified"] for e in after["items"])
    assert nb2.status()["registry"]["roots_match"] is True


def test_p2_app_writes_nothing_of_its_own(node):
    """The only files that appear anywhere are the node's own keystore and registry."""
    nb = bind(node, regulated=False)
    nb.record_income(work_ref="job-1", amount=10)
    nb.record_tax_note(work_ref="tax:job-1", category="labor")
    nb.export_package()
    nb.events()
    nb.status()

    files = sorted(str(p.relative_to(node["root"])) for p in node["root"].rglob("*") if p.is_file())
    assert files == ["keystore/node.nodekey.json", "registry/objects.ndjson"], files


def test_p2_registry_root_replays_after_every_write(node):
    nb = bind(node, regulated=False)
    for i in range(4):
        nb.record_income(work_ref=f"job-{i}", amount=i * 10)
        st = nb.status()["registry"]
        assert st["roots_match"] is True, f"root stopped replaying after write {i}"


# ==================================================================================================
# P3 · Tax event is a RECORD. No statutory act is reachable.
# ==================================================================================================

def test_p3_tax_event_is_record_only(node):
    nb = bind(node, regulated=False)
    nb.record_income(work_ref="consulting-august", amount=2400, unit="USD")
    receipt = nb.record_tax_note(
        work_ref="tax:consulting-august", category="self_employment",
        references_income="IncomeEvent:kenn:consulting-august", amount=2400, unit="USD")["receipt"]

    payload = receipt["payload"]
    assert payload["tax_event"] is True
    assert payload["tax_category"] == "self_employment"
    assert payload["reportable"] is True
    assert payload["references_income"] == "IncomeEvent:kenn:consulting-august"

    # Nothing in the stored record asserts a statutory act — which is the point: a green verify is
    # also proof the node filed nothing.
    for key in payload:
        assert key.lower() not in STATUTORY_FENCE_FIELDS, f"statutory field '{key}' reached disk"
    for banned in ("filing", "filed", "paid", "remitted", "submitted", "authority"):
        assert banned not in json.dumps(payload).lower()


@pytest.mark.parametrize("field", ["file_return", "e_file", "submit_return", "remit", "pay_tax",
                                   "settle_tax", "form_entity", "power_of_attorney", "represent"])
def test_p3_statutory_field_refused_on_every_act(node, field):
    """The module's tax fence guards tax events. This app narrows further and refuses the same
    vocabulary on a plain earning and a contribution too."""
    nb = bind(node, regulated=False)
    for call in (lambda: nb.record_income(work_ref=f"a-{field}", extra={field: True}),
                 lambda: nb.record_contribution_event(source="skill_service",
                                                      work_ref=f"b-{field}", extra={field: True}),
                 lambda: nb.record_tax_note(work_ref=f"c-{field}", category="labor",
                                            extra={field: True})):
        with pytest.raises(SurfaceError):
            call()
    assert not os.path.exists(objects_ndjson(node)), "a refused act still touched the store"


@pytest.mark.parametrize("field", ["balance", "custody", "escrow", "wallet", "settlement",
                                   "held_funds", "transfer_funds", "yield", "mint"])
def test_p3_money_path_field_refused_by_the_module(node, field):
    """This one is the module's own fence, not ours — we simply do not route around it."""
    nb = bind(node, regulated=False)
    with pytest.raises(SurfaceError) as exc:
        nb.record_income(work_ref=f"m-{field}", extra={field: 1})
    assert "money-path" in str(exc.value)


def test_p3_unknown_tax_category_refused(node):
    nb = bind(node, regulated=False)
    with pytest.raises(SurfaceError) as exc:
        nb.record_tax_note(work_ref="x", category="capital_gains_probably")
    assert "Unknown income category" in str(exc.value)


def test_p3_no_statutory_or_crossing_callable_is_imported(node):
    """Nothing in the app's namespace can file, remit, or cross."""
    import usn_erp_surface.node_binding as nbmod
    import usn_erp_surface.server as srvmod

    for mod in (nbmod, srvmod):
        names = {n.lower() for n in dir(mod)}
        for banned in ("open_crossing", "sanction_crossing", "record_tax_filing", "remit",
                       "file_return", "simulate_approval", "simulate_denial", "store_datum"):
            assert banned not in names, f"{mod.__name__} exposes '{banned}'"


# ==================================================================================================
# P4 · The gate. No auto-approve.
# ==================================================================================================

def test_p4_gated_act_writes_nothing_until_approved(node):
    nb = bind(node, regulated=True)
    sub = nb.record_income(work_ref="consulting-august", amount=2400, unit="USD")

    assert sub["gated"] is True and sub["receipt"] is None
    assert nb.gate_state()["pending_count"] == 1
    assert not os.path.exists(objects_ndjson(node)), "a held act wrote to the store"
    assert nb.events()["total"] == 0

    disposed = approve_all(nb, sub)
    assert disposed["status"] == "approved"
    assert disposed["real"] is True, "a simulated disposition must never be used"
    assert disposed["receipt"]["approver"] == "kenn"
    assert disposed["receipt"]["approval_ref"] == sub["req_id"]
    assert nb.events()["total"] == 1


def test_p4_denial_writes_nothing_at_all(node):
    nb = bind(node, regulated=True)
    sub = nb.record_income(work_ref="mistake", amount=999)
    disposed = nb.dispose(sub["req_id"], approve=False, reason="wrong client")

    assert disposed["status"] == "denied"
    assert disposed["receipt"] is None
    assert nb.events()["total"] == 0
    assert not os.path.exists(objects_ndjson(node))
    assert nb.gate_state()["pending_count"] == 0


def test_p4_every_action_class_is_gated(node):
    nb = bind(node, regulated=True)
    subs = [
        nb.record_income(work_ref="i1", amount=1),
        nb.record_contribution_event(source="idle_compute", work_ref="c1", amount=1),
        nb.record_tax_note(work_ref="t1", category="labor"),
    ]
    assert [s["gated"] for s in subs] == [True, True, True]
    assert {s["action_class"] for s in subs} == {"attribute_income", "record_contribution",
                                                 "record_tax_event"}
    assert nb.gate_state()["pending_count"] == 3
    assert nb.events()["total"] == 0


def test_p4_module_itself_refuses_a_gated_act_without_approval(node):
    """Belt and braces: even if the app tried to skip the gate, the module refuses. This calls the
    module's own path with a gate that requires approval and no approver."""
    from sovereign_agent.economy.income import IncomeRefused, attribute_income

    nb = bind(node, regulated=True)
    with pytest.raises(IncomeRefused) as exc:
        attribute_income("kenn", "sneaky", mandate="household", author="kenn",
                         source_ref="test", at=AT, registry=nb._registry(),
                         gate=nb.gate, mode="corporate_regulated",
                         action_class="attribute_income")
    assert "human approval" in str(exc.value)


def test_p4_unknown_request_is_refused(node):
    nb = bind(node, regulated=True)
    with pytest.raises(SurfaceError):
        nb.dispose("approval_999", approve=True)


def test_p4_sovereign_posture_is_genuinely_ungated(node):
    """Not a weakened gate — the module's `requires_approval` returns False outside regulated mode."""
    nb = bind(node, regulated=False)
    assert nb.gate.requires_approval("attribute_income", {}, nb.mode) is False
    sub = nb.record_income(work_ref="direct", amount=5)
    assert sub["gated"] is False and sub["receipt"]["approver"] is None


# ==================================================================================================
# P5 · The package
# ==================================================================================================

def _seed(nb):
    nb.record_income(work_ref="consulting-august", amount=2400, unit="USD")
    nb.record_contribution_event(source="skill_service", work_ref="tutoring-august",
                                 amount=300, unit="USD")
    nb.record_tax_note(work_ref="tax:consulting-august", category="self_employment",
                       references_income="IncomeEvent:kenn:consulting-august",
                       amount=2400, unit="USD")


def test_p5_export_is_byte_identical_on_rerun(node):
    nb = bind(node, regulated=False)
    _seed(nb)
    a, sha_a = nb.export_bytes()
    b, sha_b = nb.export_bytes()
    assert a == b and sha_a == sha_b
    assert sha_a == hashlib.sha256(json.dumps(json.loads(a), sort_keys=True,
                                              separators=(",", ":"),
                                              ensure_ascii=False).encode()).hexdigest()


def test_p5_export_is_identical_across_a_restart(node):
    nb = bind(node, regulated=False)
    _seed(nb)
    first, sha_first = nb.export_bytes()
    del nb
    second, sha_second = bind(node, regulated=False).export_bytes()
    assert first == second and sha_first == sha_second


def test_p5_export_changes_when_node_state_changes(node):
    """Determinism must not be staleness."""
    nb = bind(node, regulated=False)
    _seed(nb)
    _, before = nb.export_bytes()
    nb.record_income(work_ref="another-job", amount=50)
    _, after = nb.export_bytes()
    assert before != after


def test_p5_export_is_derived_from_node_state(node):
    nb = bind(node, regulated=False)
    _seed(nb)
    pkg, _ = nb.export_package()
    reg_root = nb._registry().population_root()

    assert pkg["population_root"] == reg_root
    assert pkg["manifest"]["root"] == reg_root
    assert pkg["as_of"] == nb._registry().entries()[-1]["at"], "as_of must come from state, not now()"
    assert pkg["tax_event_count"] == 1
    assert pkg["reporting_package"]["complete"] is True
    assert pkg["reporting_package"]["by_category"]["self_employment"] == 1
    assert pkg["verification"]["all_events_verify"] is True
    assert pkg["declarations"]["statutory_acts"].startswith("NONE")


def test_p5_export_carries_no_export_timestamp(node):
    """An export-time stamp would break byte comparability, so there must not be one."""
    nb = bind(node, regulated=False)
    _seed(nb)
    pkg, _ = nb.export_package()
    blob = json.dumps(pkg).lower()
    for banned in ("exported_at", "generated_at", "created_at", "timestamp"):
        assert banned not in blob


def test_p5_empty_node_exports_honestly(node):
    nb = bind(node, regulated=False)
    pkg, _ = nb.export_package()
    assert pkg["tax_event_count"] == 0
    assert pkg["reporting_package"]["complete"] is False
    assert "nothing filed" in pkg["reporting_package"]["reason"]


def test_p5_tampered_registry_line_flips_the_verify(node):
    """The package's `all_events_verify` is a real check, not a decoration."""
    nb = bind(node, regulated=False)
    _seed(nb)
    assert nb.export_package()[0]["verification"]["all_events_verify"] is True

    with open(objects_ndjson(node), encoding="utf-8") as fh:
        rows = [json.loads(x) for x in fh if x.strip()]
    rows[0]["payload"]["amount"] = 999999.0
    with open(objects_ndjson(node), "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")

    nb2 = bind(node, regulated=False)
    assert nb2.export_package()[0]["verification"]["all_events_verify"] is False
    assert any(not e["check"]["verified"] for e in nb2.events()["items"])


# ==================================================================================================
# P6 · The kill-grep, and proof that it bites
# ==================================================================================================

def _run_killgrep(app_dir: str):
    return subprocess.run([sys.executable, os.path.join(app_dir, "killgrep.py")],
                          capture_output=True, text=True)


def test_p6_killgrep_is_green_on_the_shipped_app():
    proc = _run_killgrep(APP_DIR)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "P6: GREEN" in proc.stdout


@pytest.mark.parametrize("label,inject", [
    ("second ledger store", "import sqlite3\n_db = sqlite3.connect('app.db')\n"),
    ("http client egress", "import requests\ndef _spine():\n    return requests.get('http://127.0.0.1:8421/api/v1/node')\n"),
    ("port crossing", "from sovereign_agent.port.crossing import open_crossing\n"),
    ("faked human", "def _auto(gate, rid):\n    return gate.simulate_approval(rid)\n"),
    ("statutory act", "def file_return(x):\n    return x\n"),
    ("balance custody", "def _authority(rows):\n    balance = sum(rows)\n    return balance\n"),
    ("app-side write", "def _persist(p, d):\n    with open(p, 'w') as fh:\n        fh.write(d)\n"),
])
def test_p6_killgrep_catches_each_violation(tmp_path, label, inject):
    """Inject one violation into a copy of the app and assert the gate goes RED. A kill-grep that
    has never gone RED proves nothing."""
    copy = tmp_path / "app"
    shutil.copytree(APP_DIR, copy, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    target = copy / "node_binding.py"
    target.write_text(target.read_text() + "\n\n" + textwrap.dedent(inject), encoding="utf-8")

    proc = _run_killgrep(str(copy))
    assert proc.returncode == 1, f"kill-grep stayed GREEN with '{label}' injected:\n{proc.stdout}"
    assert "P6: RED" in proc.stdout


def test_p6_killgrep_does_not_fire_on_refusal_prose(tmp_path):
    """The app's own guard text says 'remit' and 'file_return'. That is the law working, and the
    gate must not mistake it for a violation."""
    copy = tmp_path / "app"
    shutil.copytree(APP_DIR, copy, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    target = copy / "node_binding.py"
    target.write_text(
        target.read_text()
        + '\n\ndef _explain():\n'
        + '    """This app never files a return, never remits, and never holds a balance."""\n'
        + '    return "refused: file_return / remit / escrow / custody are your acts, not ours"\n',
        encoding="utf-8")

    proc = _run_killgrep(str(copy))
    assert proc.returncode == 0, proc.stdout


# ==================================================================================================
# P8 · The stranger sentence, executed
# ==================================================================================================

def test_p8_the_stranger_sentence_is_true(node):
    """“I opened my node, recorded an earning, recorded a tax note, and exported a package for my
    accountant.” Run exactly that, in that order, and assert each clause."""
    nb = bind(node, regulated=True)                                   # I opened my node
    assert nb.status()["identity"]["present"] is True

    earn = approve_all(nb, nb.record_income(                          # recorded an earning
        work_ref="consulting-august", amount=2400, unit="USD"))
    assert earn["receipt"]["kind"] == "income"

    tax = approve_all(nb, nb.record_tax_note(                         # recorded a tax note
        work_ref="tax:consulting-august", category="self_employment",
        references_income=earn["receipt"]["object_id"], amount=2400, unit="USD"))
    assert tax["receipt"]["payload"]["tax_event"] is True

    blob, digest = nb.export_bytes()                                  # exported a package
    pkg = json.loads(blob)
    assert pkg["reporting_package"]["complete"] is True
    assert pkg["reporting_package"]["event_count"] == 1
    assert pkg["verification"]["all_events_verify"] is True
    assert len(digest) == 64
    # …for my accountant: it files nothing and claims no authority.
    assert pkg["declarations"]["statutory_acts"].startswith("NONE")
    assert "no statutory authority" in pkg["declarations"]["authority"]
