#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proof tests for the USN ERP Operator Surface — P2–P6, P8 and O1–O6.

Run:  ./.venv/bin/python -m pytest apps/usn_erp_surface/tests/ -q

These are not unit tests of the app's internals. Each one asserts a bar row:

  P2  a recorded event changes bytes on disk through a module path, and survives a restart
  P3  a tax event is a record only — no statutory act is reachable, and the fence proves it
  P4  a gated act writes nothing until an explicit human approval; a denial writes nothing at all
  P5  the export is derived from node state and byte-identical on re-run
  P6  the kill-grep actually catches violations — proved by injecting each one and asserting RED
  P8  the stranger sentence, executed clause by clause

  O1  opening an obligation is held at the gate; nothing reaches the ledger until you approve
  O2  approving lands on the node's ledger, survives a restart, and the chain still verifies
  O3  denying writes nothing — not the open, not the approve
  O4  closing goes only through the ledger's own API, and its guards (AH-1, the evidence floor,
      attestation and veto) hold and are surfaced verbatim
  O5  the kill-grep covers the new paths and still bites
  O6  the read panel and the write path are the same bytes — no app cache as truth

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


# ==================================================================================================
# O1–O6 · The obligations write surface
# ==================================================================================================

def obligations_ndjson(node) -> str:
    return os.path.join(node["ledger"], "obligations.ndjson")


def open_obligation(nb, **kw):
    """Open one, approving at the app gate if the posture holds it. Approval is always explicit."""
    kw.setdefault("title", "Send Q3 books to the accountant")
    sub = nb.obligation_open(**kw)
    return approve_all(nb, sub) if sub["gated"] else sub


# ---- O1 · Open → held at the gate; nothing on disk until approve ---------------------------------

def test_o1_open_is_held_at_the_gate(node):
    nb = bind(node, regulated=True)
    sub = nb.obligation_open(title="Send Q3 books to the accountant", intent="comply",
                             ref="q3-books", material=True)

    assert sub["gated"] is True and sub["receipt"] is None
    assert sub["action_class"] == "obligation_open"
    assert nb.gate_state()["pending_count"] == 1
    assert not os.path.exists(obligations_ndjson(node)), "a held obligation reached the ledger"
    assert nb.obligations()["present"] is False


def test_o1_every_obligation_act_is_gated(node):
    """Not just open — approve, close, attest, veto and clear all pass the same gate."""
    nb = bind(node, regulated=True)
    opened = open_obligation(nb, material=True, requires_attestation=["cfo"])
    oid = opened["receipt"]["id"]

    for sub in (nb.obligation_approve(oid),
                nb.obligation_close(oid, evidence="artifact at /tmp/x.pdf"),
                nb.obligation_attest(oid, role="cfo"),
                nb.obligation_veto(oid, role="cfo", reason="hold"),
                nb.obligation_clear_veto(oid, role="cfo")):
        assert sub["gated"] is True, sub["action_class"]
        assert sub["receipt"] is None
    assert nb.gate_state()["pending_count"] == 5


# ---- O2 · Approve → durable, survives restart, chain still verifies ------------------------------

def test_o2_approve_lands_on_the_node_ledger(node):
    nb = bind(node, regulated=True)
    opened = open_obligation(nb, material=True, intent="comply", ref="q3-books")
    entry = opened["receipt"]

    assert entry["type"] == "debit"
    assert entry["material"] is True and entry["draft"] is True
    assert entry["owner"] == "kenn"

    with open(obligations_ndjson(node), encoding="utf-8") as fh:
        rows = [json.loads(x) for x in fh if x.strip()]
    assert len(rows) == 1 and rows[0]["id"] == entry["id"]
    assert rows[0]["prev_hash"] == "genesis"


def test_o2_survives_restart_and_chain_verifies(node):
    nb = bind(node, regulated=True)
    oid = open_obligation(nb, material=True)["receipt"]["id"]
    approve_all(nb, nb.obligation_approve(oid, rationale="books are ready"))
    before = nb.obligations()

    del nb
    nb2 = bind(node, regulated=True)
    after = nb2.obligations()

    assert after["chain_valid"] is True
    assert after["by_status"] == before["by_status"] == {"open": 1, "closed": 0, "total": 1}
    assert [i["id"] for i in after["items"]] == [i["id"] for i in before["items"]]
    assert after["items"][0]["status"] == "approved"


def test_o2_the_recorded_disposition_is_the_operators(node):
    """The gate verdict on the chain is the one the operator gave — never synthesised."""
    nb = bind(node, regulated=True)
    oid = open_obligation(nb, material=True)["receipt"]["id"]
    entry = approve_all(nb, nb.obligation_approve(oid))["receipt"]

    assert entry["type"] == "approval"
    assert entry["disposition"] == "approved"
    assert entry["approved_by"] == "kenn"
    assert entry["gate"]["real"] is True, "a simulated disposition must never reach the chain"
    assert entry["gate"]["approver"] == "kenn"


def test_o2_ledger_gate_fails_closed_without_a_disposition(node):
    """The seam's whole point: with no recorded human verdict, the ledger denies. This is stricter
    than the repo's own `make_gate`, which hardcodes 'approved'."""
    nb = bind(node, regulated=True)
    oid = open_obligation(nb, material=True)["receipt"]["id"]

    led = nb._ledger_for_write(None)          # no disposition — the failure case, made explicit
    with pytest.raises(PermissionError) as exc:
        led.approve(oid, approved_by="kenn")
    assert "DENIED" in str(exc.value)
    assert nb.obligations()["items"][0]["status"] == "draft", "a denied approval must not approve"


# ---- O3 · Deny → nothing written ------------------------------------------------------------------

def test_o3_denying_an_open_writes_nothing(node):
    nb = bind(node, regulated=True)
    sub = nb.obligation_open(title="Renew insurance", material=True)
    disposed = nb.dispose(sub["req_id"], approve=False, reason="not this quarter")

    assert disposed["status"] == "denied" and disposed["receipt"] is None
    assert not os.path.exists(obligations_ndjson(node))
    assert nb.obligations()["present"] is False
    assert nb.gate_state()["pending_count"] == 0


def test_o3_denying_an_approve_leaves_the_draft_untouched(node):
    nb = bind(node, regulated=True)
    oid = open_obligation(nb, material=True)["receipt"]["id"]
    before = len(open(obligations_ndjson(node), encoding="utf-8").read().splitlines())

    sub = nb.obligation_approve(oid, rationale="on reflection, no")
    disposed = nb.dispose(sub["req_id"], approve=False, reason="not yet")

    assert disposed["receipt"] is None
    after = len(open(obligations_ndjson(node), encoding="utf-8").read().splitlines())
    assert after == before, "a denied approval appended to the chain"
    assert nb.obligations()["items"][0]["status"] == "draft"


# ---- O4 · Close, only through the existing API and its guards -------------------------------------

def test_o4_close_mints_a_receipt_on_the_chain(node):
    nb = bind(node, regulated=True)
    oid = open_obligation(nb, material=True)["receipt"]["id"]
    approve_all(nb, nb.obligation_approve(oid))
    entry = approve_all(nb, nb.obligation_close(
        oid, evidence="emailed 2026-08-19 · receipt_id rcpt_9f3a2b1c"))["receipt"]

    assert entry["type"] == "credit"
    assert entry["evidence_tier"] == "E1"
    assert entry["closed_by"] == "kenn"
    assert entry["receipt"]["receipt_id"].startswith("rcpt_")
    assert entry["receipt"]["payload_hash"]

    panel = nb.obligations()
    assert panel["by_status"] == {"open": 0, "closed": 1, "total": 1}
    assert panel["items"][0]["status"] == "closed"
    assert panel["items"][0]["closure"]["receipt_id"] == entry["receipt"]["receipt_id"]
    assert panel["chain_valid"] is True


def test_o4_material_cannot_close_before_the_breath_gate(node):
    """The ledger's own rule, surfaced verbatim — not re-implemented here."""
    nb = bind(node, regulated=True)
    oid = open_obligation(nb, material=True)["receipt"]["id"]
    sub = nb.obligation_close(oid, evidence="artifact at /tmp/x.pdf")

    with pytest.raises(SurfaceError) as exc:
        nb.dispose(sub["req_id"], approve=True)
    assert "has not cleared the breath-gate" in str(exc.value)
    assert nb.obligations()["items"][0]["status"] == "draft"


def test_o4_claim_only_evidence_will_not_close(node):
    nb = bind(node, regulated=False)
    oid = open_obligation(nb)["receipt"]["id"]
    with pytest.raises(SurfaceError) as exc:
        nb.obligation_close(oid, evidence="I did it")
    assert "claim-only" in str(exc.value)
    assert nb.obligations()["items"][0]["status"] != "closed"


def test_o4_a_refusal_needs_no_gate(node):
    """Saying no is itself the human disposition — the module exempts a rejection, and so do we."""
    nb = bind(node, regulated=False)
    oid = open_obligation(nb, material=True)["receipt"]["id"]
    entry = nb.obligation_close(oid, evidence="declined — client withdrew, see /tmp/note.txt",
                                rejected=True)["receipt"]
    assert entry["type"] == "credit"
    assert nb.obligations()["by_status"]["closed"] == 1


def test_o4_cannot_close_twice(node):
    nb = bind(node, regulated=False)
    oid = open_obligation(nb)["receipt"]["id"]
    nb.obligation_close(oid, evidence="done at /tmp/x.pdf")
    with pytest.raises(SurfaceError) as exc:
        nb.obligation_close(oid, evidence="done again at /tmp/x.pdf")
    assert "already closed" in str(exc.value)


def test_o4_attestation_and_veto_guards_hold(node):
    nb = bind(node, regulated=False)
    oid = open_obligation(nb, material=True, requires_attestation=["cfo", "counsel"])["receipt"]["id"]
    nb.obligation_approve(oid)

    with pytest.raises(SurfaceError) as exc:                       # partial attestation
        nb.obligation_close(oid, evidence="done at /tmp/x.pdf")
    assert "attestation" in str(exc.value).lower()

    nb.obligation_attest(oid, role="cfo")
    nb.obligation_attest(oid, role="counsel")
    nb.obligation_veto(oid, role="counsel", reason="needs review")
    with pytest.raises(SurfaceError) as exc:                       # standing veto, default-deny
        nb.obligation_close(oid, evidence="done at /tmp/x.pdf")
    assert "VETOED" in str(exc.value)

    nb.obligation_clear_veto(oid, role="counsel")
    entry = nb.obligation_close(oid, evidence="done at /tmp/x.pdf hash a1b2c3d4e5f60718")["receipt"]
    assert entry["type"] == "credit" and entry["evidence_tier"] == "E2"
    assert nb.obligations()["chain_valid"] is True


def test_o4_veto_requires_a_reason(node):
    nb = bind(node, regulated=False)
    oid = open_obligation(nb, requires_attestation=["cfo"])["receipt"]["id"]
    with pytest.raises(SurfaceError):
        nb.obligation_veto(oid, role="cfo", reason="")


def test_o4_unresolvable_path_reference_is_refused(node):
    """R22-3: a path-like reference must resolve. A citation is never written false."""
    nb = bind(node, regulated=False)
    with pytest.raises(SurfaceError) as exc:
        nb.obligation_open(title="bad ref", ref="invoices/inv-12.pdf")
    assert "does not resolve" in str(exc.value)
    assert not os.path.exists(obligations_ndjson(node))


def test_o4_unknown_obligation_is_actionable(node):
    nb = bind(node, regulated=False)
    open_obligation(nb)
    with pytest.raises(SurfaceError) as exc:
        nb.obligation_approve("obl_nope")
    assert "No obligation" in str(exc.value)


# ---- O5 · Kill-grep still GREEN, covering the new paths -------------------------------------------

@pytest.mark.parametrize("label,inject", [
    ("chain repair", "def _fix(led):\n    return led.repair_chain()\n"),
    ("out-of-scope reopen", "def _undo(led, oid):\n    return led.reopen(oid, 'because')\n"),
    ("ledger private append", "def _sneak(led, e):\n    return led._append(e)\n"),
    ("ledger private replay", "def _peek(led):\n    return led._entries()\n"),
])
def test_o5_killgrep_catches_obligation_violations(tmp_path, label, inject):
    copy = tmp_path / "app"
    shutil.copytree(APP_DIR, copy, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    target = copy / "node_binding.py"
    target.write_text(target.read_text() + "\n\n" + textwrap.dedent(inject), encoding="utf-8")

    proc = _run_killgrep(str(copy))
    assert proc.returncode == 1, f"kill-grep stayed GREEN with '{label}' injected:\n{proc.stdout}"


def test_o5_app_owns_no_obligation_store(node):
    """Every byte under the ledger root belongs to the node's own ObligationLedger."""
    nb = bind(node, regulated=False)
    oid = open_obligation(nb, material=True)["receipt"]["id"]
    nb.obligation_approve(oid)
    nb.obligation_close(oid, evidence="done at /tmp/x.pdf")
    nb.obligations()

    files = sorted(os.listdir(node["ledger"]))
    assert files in (["obligations.ndjson"], ["obligations.lock", "obligations.ndjson"]), files


# ---- O6 · The panel and the write path read the same bytes ----------------------------------------

def test_o6_panel_matches_the_ledger_file(node):
    nb = bind(node, regulated=False)
    a = open_obligation(nb, title="One", material=True)["receipt"]["id"]
    b = open_obligation(nb, title="Two")["receipt"]["id"]
    nb.obligation_approve(a)
    nb.obligation_close(a, evidence="done at /tmp/x.pdf")

    panel = nb.obligations()
    with open(obligations_ndjson(node), encoding="utf-8") as fh:
        rows = [json.loads(x) for x in fh if x.strip()]

    assert panel["chain_entries"] == len(rows)
    assert {i["id"] for i in panel["items"]} == {r["id"] for r in rows if r["type"] == "debit"}
    assert next(i for i in panel["items"] if i["id"] == a)["status"] == "closed"
    assert next(i for i in panel["items"] if i["id"] == b)["status"] == "draft"
    assert panel["ledger_file"] == obligations_ndjson(node)


def test_o6_panel_reports_a_tampered_chain(node):
    """`chain_valid` is a real check. Alter one entry and the panel must say so."""
    nb = bind(node, regulated=False)
    oid = open_obligation(nb, material=True)["receipt"]["id"]
    nb.obligation_approve(oid)
    assert nb.obligations()["chain_valid"] is True

    with open(obligations_ndjson(node), encoding="utf-8") as fh:
        rows = [json.loads(x) for x in fh if x.strip()]
    rows[0]["title"] = "Something else entirely"
    with open(obligations_ndjson(node), "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")

    assert bind(node, regulated=False).obligations()["chain_valid"] is False


def test_o6_reads_create_nothing(node):
    """Opening the ledger to read must not bring a file into being."""
    nb = bind(node, regulated=False)
    assert nb.obligations()["present"] is False
    assert not os.path.exists(node["ledger"]) or os.listdir(node["ledger"]) == []


def test_o6_filter_agrees_with_the_full_panel(node):
    nb = bind(node, regulated=False)
    a = open_obligation(nb, title="Closed one")["receipt"]["id"]
    open_obligation(nb, title="Still open")
    nb.obligation_close(a, evidence="done at /tmp/x.pdf")

    assert nb.obligations(only="open")["total"] == 1
    assert nb.obligations(only="closed")["total"] == 1
    assert nb.obligations()["total"] == 2


# ==================================================================================================
# I1–I6 · Invoice / receivable-lite — a governed billing-event record (KM ruling, Option A)
#
#   I1  create invoice-shaped record → gate → disk via module; survives restart
#   I2  deny → nothing written
#   I3  list / aging reflects node state only (no app cache as truth)
#   I4  no pay / remit / file / crossing callable reachable from the binding
#   I5  kill-grep GREEN with injected-violation proofs for the invoice money-path verbs
#   I6  the read panel and the write path are one source of truth; prior P/O rows stay green
# ==================================================================================================

def _lines(*triples):
    return [{"description": d, "quantity": q, "unit_price": p} for d, q, p in triples]


# ---- I1 -----------------------------------------------------------------------------------------

def test_i1_invoice_gated_then_lands_on_disk_and_survives_restart(node):
    nb = bind(node)  # regulated → gated
    sub = nb.record_invoice(invoice_id="INV-001", customer="Acme Co",
                            lines=_lines(("consulting", 10, 150), ("setup", 1, 500)),
                            tax=120, currency="USD", issued_day=10, due_day=40)
    assert sub["gated"] is True and sub["receipt"] is None
    assert not os.path.exists(objects_ndjson(node)), "nothing may be written before approval"

    disposed = approve_all(nb, sub)
    assert disposed["status"] == "approved" and disposed["real"] is True
    rec = disposed["receipt"]
    assert rec["kind"] == "income" and rec["payload"]["doc_kind"] == "invoice"
    assert rec["payload"]["amount"] == 2120.0          # 1500 + 500 + 120, computed by the billing surface
    assert os.path.exists(objects_ndjson(node))

    # a fresh binding replays from disk — the record survives a restart, and verifies against its receipt
    nb2 = bind(node)
    inv = nb2.invoices()
    assert inv["total"] == 1
    row = inv["items"][0]
    assert row["invoice_id"] == "INV-001" and row["customer"] == "Acme Co"
    assert row["total"] == 2120.0 and row["check"]["verified"] is True


def test_i1_total_is_computed_by_the_billing_surface_not_typed(node):
    nb = bind(node, regulated=False)
    r = nb.record_invoice(invoice_id="INV-2", customer="Beta",
                          lines=_lines(("widgets", 3, 33.34)), currency="USD")["receipt"]
    assert r["payload"]["amount"] == 100.02            # 3 × 33.34, quantized by the sealed surface


# ---- I2 -----------------------------------------------------------------------------------------

def test_i2_denied_invoice_writes_nothing(node):
    nb = bind(node)
    sub = nb.record_invoice(invoice_id="INV-9", customer="X", lines=_lines(("a", 1, 10)))
    disposed = nb.dispose(sub["req_id"], approve=False, reason="wrong customer")
    assert disposed["status"] == "denied" and disposed["receipt"] is None
    assert not os.path.exists(objects_ndjson(node)), "a denial writes nothing at all"
    assert nb.invoices()["total"] == 0


# ---- I3 -----------------------------------------------------------------------------------------

def test_i3_aging_is_a_projection_over_the_records_only(node):
    nb = bind(node, regulated=False)
    nb.record_invoice(invoice_id="A", customer="C1", lines=_lines(("x", 1, 1000)), issued_day=10)
    nb.record_invoice(invoice_id="B", customer="C2", lines=_lines(("y", 1, 2000)), issued_day=70)

    # a fresh binding — the panel replays the node, it is not an app cache
    aged = bind(node, regulated=False).ar_aging(as_of_day=75)
    assert aged["total_receivable"] == "3000.00"
    assert aged["buckets"]["61_90"] == "1000.00"       # A: age 65
    assert aged["buckets"]["current"] == "2000.00"     # B: age 5
    assert aged["balances"] is True and aged["open_invoice_count"] == 2


def test_i3_invoices_read_matches_the_written_bytes(node):
    nb = bind(node, regulated=False)
    r = nb.record_invoice(invoice_id="INV-7", customer="Gamma",
                          lines=_lines(("svc", 2, 250)), currency="USD", issued_day=5)["receipt"]
    # the read panel projects the same object the write produced — one set of bytes, no cache
    row = bind(node, regulated=False).invoices()["items"][0]
    assert row["object_id"] == r["object_id"]
    assert row["version_hash"] == r["version_hash"]
    assert row["total"] == 500.0 and row["check"]["verified"] is True


# ---- I4 -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("field", ["balance", "transfer_funds", "held_funds", "settlement"])
def test_i4_money_path_field_on_an_invoice_is_refused_by_the_module(node, field):
    """An invoice rides the same fence-owning writer as income, so the module's money-path fence
    refuses a money-movement field on it exactly as it does on an earning."""
    nb = bind(node, regulated=False)
    with pytest.raises(SurfaceError) as exc:
        nb.record_invoice(invoice_id="INV-M", customer="X",
                          lines=_lines(("a", 1, 10)), extra={field: 1})
    assert "money-path" in str(exc.value)
    assert nb.invoices()["total"] == 0


@pytest.mark.parametrize("field", ["file_return", "remit", "pay_tax", "form_entity"])
def test_i4_statutory_field_on_an_invoice_is_refused_by_the_app(node, field):
    nb = bind(node, regulated=False)
    with pytest.raises(SurfaceError):
        nb.record_invoice(invoice_id="INV-S", customer="X",
                          lines=_lines(("a", 1, 10)), extra={field: True})
    assert nb.invoices()["total"] == 0


def test_i4_binding_exposes_no_collection_verb(node):
    """The vertical bills; it never collects. No public method name on the binding may imply a
    money-path — collection is out of scope by construction."""
    nb = bind(node, regulated=False)
    forbidden = ("collect", "disburse", "remit", "settle_pay", "capture_payment", "mark_paid",
                 "receive_payment", "apply_payment", "pay_invoice", "charge")
    for name in dir(nb):
        if name.startswith("__"):
            continue
        low = name.lower()
        assert not any(f in low for f in forbidden), f"binding exposes a money-path-shaped method: {name}"


# ---- I5 -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("label,inject", [
    ("collect payment", "def collect_payment(inv):\n    return inv\n"),
    ("apply payment", "def apply_payment(inv, amt):\n    return amt\n"),
    ("settle invoice", "def settle_invoice(inv):\n    return inv\n"),
    ("mark paid binding", "def _f(inv):\n    mark_paid = True\n    return mark_paid\n"),
])
def test_i5_killgrep_catches_invoice_money_path_verbs(tmp_path, label, inject):
    """Inject an invoice-collection verb into a copy of the app and assert the gate goes RED."""
    copy = tmp_path / "app"
    shutil.copytree(APP_DIR, copy, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    target = copy / "node_binding.py"
    target.write_text(target.read_text() + "\n\n" + textwrap.dedent(inject), encoding="utf-8")
    proc = _run_killgrep(str(copy))
    assert proc.returncode == 1, f"kill-grep stayed GREEN with '{label}' injected:\n{proc.stdout}"
    assert "P6: RED" in proc.stdout


# ---- I6 -----------------------------------------------------------------------------------------

def test_i6_invoice_read_and_write_are_one_source_of_truth(node):
    nb = bind(node, regulated=False)
    nb.record_invoice(invoice_id="INV-1", customer="One", lines=_lines(("a", 1, 100)), issued_day=1)
    # status(), invoices() and ar_aging() all replay the same node — they cannot disagree
    st = bind(node, regulated=False).status()["registry"]
    inv = bind(node, regulated=False).invoices()
    aged = bind(node, regulated=False).ar_aging(as_of_day=1)
    assert st["invoices"] == 1 == inv["total"]
    assert aged["total_receivable"] == "100.00" and aged["open_invoice_count"] == 1


# ==================================================================================================
# PV1–PV6 · Period view + close — GAAP-shaped books derived at read time (KM CFO ruling)
#
#   PV1  trial balance / statement reads reflect node state only; survive restart
#   PV2  close holds at gate → deny writes nothing → approve persists via the ledger
#   PV3  open invoices are earned revenue (Dr AR / Cr Revenue), classified distinctly from cash
#        income; deferred invoices post to Unearned; tax notes never touch the P&L
#   PV4  no pay / remit / file / crossing reachable
#   PV5  kill-grep GREEN + injected-violation proofs
#   PV6  BAR.md updated; prior rows GREEN
# ==================================================================================================

def _seed_books(nb):
    """A mixed book: a cash earning, an open invoice, a deferred invoice, and a tax note."""
    nb.record_income(work_ref="consulting", amount=2400, unit="USD")
    nb.record_invoice(invoice_id="INV-1", customer="Acme", lines=_lines(("svc", 1, 1000)),
                      currency="USD", issued_day=5)
    nb.record_invoice(invoice_id="INV-2", customer="Beta", lines=_lines(("retainer", 1, 600)),
                      currency="USD", issued_day=1, extra={"deferred": True})
    nb.record_tax_note(work_ref="tax:consulting", category="labor", amount=300)


# ---- PV1 ----------------------------------------------------------------------------------------

def test_pv1_statements_reflect_node_state_and_survive_restart(node):
    _seed_books(bind(node, regulated=False))
    # a fresh binding replays from disk — the statements are a projection of the node, not a cache
    pv = bind(node, regulated=False).period_view()
    assert pv["nets_to_zero"] is True
    assert pv["income_statement"]["revenue"] == "3400.0"      # 2400 cash + 1000 earned invoice
    assert pv["income_statement"]["net_income"] == "3400.0"
    assert pv["balance_sheet"]["assets"] == "4000.0"          # cash 2400 + AR 1600
    assert pv["balance_sheet"]["liabilities"] == "600.0"      # deferred invoice -> unearned
    assert pv["trial_balance"]["cash"] == "2400.0"
    assert pv["trial_balance"]["accounts_receivable"] == "1600.0"


def test_pv1_empty_node_projects_zero_and_balances(node):
    pv = bind(node, regulated=False).period_view()
    assert pv["posting_count"] == 0 and pv["nets_to_zero"] is True
    assert pv["income_statement"]["revenue"] == "0"


# ---- PV2 ----------------------------------------------------------------------------------------

def test_pv2_close_gated_then_deny_writes_nothing(node):
    _seed_books(bind(node, regulated=False))
    nb = bind(node)  # regulated → gated
    sub = nb.close_period(period_id="2026-Q3")
    assert sub["gated"] is True and sub["receipt"] is None
    ledger = os.path.join(node["ledger"], "obligations.ndjson")
    nb.dispose(sub["req_id"], approve=False, reason="not yet")
    assert not os.path.exists(ledger), "a denied close writes nothing to the ledger"


def test_pv2_close_approve_persists_via_the_ledger(node):
    _seed_books(bind(node, regulated=False))
    nb = bind(node)
    sub = nb.close_period(period_id="2026-Q3")
    res = nb.dispose(sub["req_id"], approve=True)
    assert res["status"] == "approved" and res["real"] is True
    rec = res["receipt"]
    assert rec["close_record"]["locked"] is True and rec["close_record"]["period"] == "2026-Q3"
    # the close is durable on the node's own obligation ledger, and the chain verifies
    obs = bind(node).obligations()
    assert obs["present"] is True and obs["chain_valid"] is True and obs["by_status"]["closed"] == 1


# ---- PV3 ----------------------------------------------------------------------------------------

def test_pv3_open_invoice_is_earned_revenue_not_cash(node):
    nb = bind(node, regulated=False)
    nb.record_invoice(invoice_id="INV-1", customer="Acme", lines=_lines(("svc", 1, 1000)), issued_day=5)
    pv = nb.period_view()
    assert pv["income_statement"]["revenue"] == "1000.0"           # earned billing -> revenue (KM ruling)
    assert pv["trial_balance"]["accounts_receivable"] == "1000.0"  # Dr AR, not cash
    assert "cash" not in pv["trial_balance"]
    assert pv["classification"]["invoice_receivable"] == 1000.0


def test_pv3_deferred_invoice_is_unearned_not_revenue(node):
    nb = bind(node, regulated=False)
    nb.record_invoice(invoice_id="INV-D", customer="Beta", lines=_lines(("retainer", 1, 600)),
                      issued_day=1, extra={"deferred": True})
    pv = nb.period_view()
    assert pv["income_statement"]["revenue"] == "0"                # deferred -> not revenue
    assert pv["balance_sheet"]["liabilities"] == "600.0"          # unearned liability
    assert pv["classification"]["deferred_unearned"] == 600.0


def test_pv3_tax_note_never_appears_in_the_pl(node):
    nb = bind(node, regulated=False)
    nb.record_income(work_ref="job", amount=1000)
    nb.record_tax_note(work_ref="tax:job", category="labor", amount=250)
    pv = nb.period_view()
    assert pv["income_statement"]["revenue"] == "1000.0"          # tax note excluded from the P&L
    assert pv["income_statement"]["expense"] == "0"
    assert pv["classification"]["tax_notes"] == 1


def test_pv3_cash_income_and_invoice_are_classified_distinctly(node):
    nb = bind(node, regulated=False)
    nb.record_income(work_ref="cash-sale", amount=500)
    nb.record_invoice(invoice_id="INV-9", customer="X", lines=_lines(("a", 1, 700)), issued_day=1)
    cl = nb.period_view()["classification"]
    assert cl["cash_income"] == 500.0 and cl["invoice_receivable"] == 700.0


# ---- PV4 ----------------------------------------------------------------------------------------

def test_pv4_no_money_path_or_pay_verb_leaks_from_the_binding(node):
    nb = bind(node, regulated=False)
    forbidden = ("pay_", "remit", "disburse", "settle_pay", "collect", "wire_", "bank_transfer")
    for name in dir(nb):
        if name.startswith("__"):
            continue
        low = name.lower()
        assert not any(f in low for f in forbidden), f"binding exposes a money-path method: {name}"


def test_pv4_period_surface_reaches_no_statutory_or_crossing_callable(node):
    """Period view is a pure read; the close persists only through the obligation ledger. Neither
    reaches a filing, a payment, or a Port crossing — proven by the kill-grep on the shipped app."""
    proc = _run_killgrep(APP_DIR)
    assert proc.returncode == 0 and "P6: GREEN" in proc.stdout


# ---- PV5 ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("label,inject", [
    ("second GL store", "import sqlite3\n_gl = sqlite3.connect('gl.db')\n"),
    ("bank egress", "import requests\ndef _bank():\n    return requests.post('http://bank/pay')\n"),
    ("money movement", "def _settle(period):\n    settle_payment = True\n    return settle_payment\n"),
    ("reopen closed period", "def _f(led, oid):\n    return led.reopen(oid)\n"),
])
def test_pv5_killgrep_catches_period_close_violations(tmp_path, label, inject):
    copy = tmp_path / "app"
    shutil.copytree(APP_DIR, copy, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    target = copy / "node_binding.py"
    target.write_text(target.read_text() + "\n\n" + textwrap.dedent(inject), encoding="utf-8")
    proc = _run_killgrep(str(copy))
    assert proc.returncode == 1, f"kill-grep stayed GREEN with '{label}' injected:\n{proc.stdout}"
    assert "P6: RED" in proc.stdout


# ---- PV6 ----------------------------------------------------------------------------------------

def test_pv6_period_view_agrees_with_the_receivables_detail(node):
    _seed_books(bind(node, regulated=False))
    # period_view and invoices() both replay the same node — the statement AR ties to the detail,
    # and both derive from the same objects: no app cache, no second GL store
    pv = bind(node, regulated=False).period_view()
    inv = bind(node, regulated=False).invoices()
    assert pv["trial_balance"]["accounts_receivable"] == "1600.0"
    assert inv["total"] == 2


# ==================================================================================================
# A1–A6 · Audit package — accountant/audit evidence from node state only
#
#   A1  completeness: every section present, counts tie to node state
#   A2  determinism: same state → same hash (incl. across restart); state change → new hash
#   A3  classification honest: open invoices ≠ earned cash; tax memos not filings; no completed
#       statutory act anywhere in the package
#   A4  no money-path verbs reachable; package self-verifies via the sealed verifier
#   A5  kill-grep bites on injected violations into the new path
#   A6  BAR updated; prior rows GREEN (the whole suite)
# ==================================================================================================

def _seed_audit_books(nb):
    _seed_books(nb)                                   # cash 2400 + open inv 1000 + deferred 600 + tax note
    sub = nb.close_period(period_id="2026-Q3")
    if sub["gated"]:
        nb.dispose(sub["req_id"], approve=True)


# ---- A1 -----------------------------------------------------------------------------------------

def test_a1_package_is_complete_and_ties_to_node_state(node):
    nb = bind(node, regulated=False)
    _seed_audit_books(nb)
    pkg, digest = bind(node, regulated=False).audit_package()

    s = pkg["sections"]
    for section in ("revenue_events", "invoices", "ar_aging", "tax_memos", "obligations",
                    "period_closes", "statements", "classification"):
        assert section in s, f"package is missing section '{section}'"
    assert pkg["counts"]["revenue_events"] == 1
    assert pkg["counts"]["invoices"] == 2
    assert pkg["counts"]["tax_memos"] == 1
    assert pkg["counts"]["period_closes"] == 1
    assert s["period_closes"][0]["period"] == "2026-Q3" and s["period_closes"][0]["locked"] is True
    assert s["statements"]["nets_to_zero"] is True
    assert s["obligations"]["chain_valid"] is True
    assert len(digest) == 64
    # the compliance core is audit-ready and every receipted check passed
    assert pkg["compliance_core"]["ready"] is True
    assert all(r["passed"] for r in pkg["checks"])


# ---- A2 -----------------------------------------------------------------------------------------

def test_a2_package_is_deterministic_and_tracks_state(node):
    nb = bind(node, regulated=False)
    _seed_audit_books(nb)
    _, h1 = nb.audit_package()
    _, h2 = nb.audit_package()                          # same binding, same state
    _, h3 = bind(node, regulated=False).audit_package() # fresh binding (restart)
    assert h1 == h2 == h3, "unchanged node state must re-export the identical package hash"
    nb.record_income(work_ref="new-job", amount=10)
    _, h4 = nb.audit_package()
    assert h4 != h1, "a state change must change the package hash"


def test_a2_bytes_are_the_artifact(node):
    nb = bind(node, regulated=False)
    _seed_audit_books(nb)
    b1, d1 = nb.audit_package_bytes()
    b2, d2 = bind(node, regulated=False).audit_package_bytes()
    assert b1 == b2 and d1 == d2, "the on-disk bytes must be byte-identical on re-export"


# ---- A3 -----------------------------------------------------------------------------------------

def test_a3_classification_honest_in_the_package(node):
    nb = bind(node, regulated=False)
    _seed_audit_books(nb)
    pkg, _ = nb.audit_package()
    cl = pkg["sections"]["classification"]
    # open invoices are earned billings (AR), never cash; deferred stays out of revenue
    assert cl["cash_income"] == 2400.0
    assert cl["invoice_receivable"] == 1000.0
    assert cl["deferred_unearned"] == 600.0
    stmts = pkg["sections"]["statements"]
    assert stmts["income_statement"]["revenue"] == "3400.0"   # cash + earned, NOT deferred
    # the receipted classification check passed, and its claim is in the package itself
    check = next(r for r in pkg["checks"] if r["check"] == "classification_honest")
    assert check["passed"] is True


def test_a3_tax_memos_are_records_not_filings(node):
    nb = bind(node, regulated=False)
    _seed_audit_books(nb)
    pkg, _ = nb.audit_package()
    assert "not filings" in pkg["declarations"]["tax_memos"]
    check = next(r for r in pkg["checks"] if r["check"] == "no_statutory_act_recorded")
    assert check["passed"] is True, "the package must prove the node filed nothing"
    # and no completed statutory act appears anywhere in the canonical package text
    import json as _json
    text = _json.dumps(pkg, default=str).lower()
    for verb in ("return_filed", "tax_paid", "remitted_to", "submitted_return"):
        assert verb not in text, f"package text carries a completed statutory act: {verb}"


# ---- A4 -----------------------------------------------------------------------------------------

def test_a4_package_self_verifies_via_the_sealed_verifier(node):
    from sovereign_agent.compliance.audit_package import verify_audit_package
    nb = bind(node, regulated=False)
    _seed_audit_books(nb)
    pkg, _ = nb.audit_package()
    core = pkg["compliance_core"]
    assert verify_audit_package(core) is True
    tampered = dict(core, reports=[dict(core["reports"][0], ready=False)])
    assert verify_audit_package(tampered) is False, "a tampered core must fail verification"


def test_a4_no_money_path_verb_on_the_binding_still(node):
    nb = bind(node, regulated=False)
    forbidden = ("pay_", "remit", "disburse", "settle_pay", "collect", "wire_", "bank_transfer")
    for name in dir(nb):
        if not name.startswith("__"):
            assert not any(f in name.lower() for f in forbidden), name


# ---- A5 -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("label,inject", [
    ("filing emission", "def file_return(pkg):\n    return pkg\n"),
    ("remit in package path", "def _send(pkg):\n    remit = True\n    return remit\n"),
    ("package egress", "import requests\ndef _upload(pkg):\n    return requests.post('http://x/pkg')\n"),
])
def test_a5_killgrep_catches_audit_package_violations(tmp_path, label, inject):
    copy = tmp_path / "app"
    shutil.copytree(APP_DIR, copy, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    target = copy / "node_binding.py"
    target.write_text(target.read_text() + "\n\n" + textwrap.dedent(inject), encoding="utf-8")
    proc = _run_killgrep(str(copy))
    assert proc.returncode == 1, f"kill-grep stayed GREEN with '{label}' injected:\n{proc.stdout}"


# ---- A6 (plus the AA fold: closed periods surface in the period view) -----------------------------

def test_a6_closed_periods_surface_in_the_period_view(node):
    nb = bind(node, regulated=False)
    _seed_audit_books(nb)
    pv = bind(node, regulated=False).period_view()
    assert pv["closed_periods"] == [dict(pv["closed_periods"][0])]  # shape sanity
    assert pv["closed_periods"][0]["period"] == "2026-Q3"
    assert pv["closed_periods"][0]["locked"] is True


# ==================================================================================================
# E1–E6 · Exception queue — pending deviations from node state, sealed-router classified
#
#   E1  queue lists exceptions/holds/denies/locks from node state only; survives restart
#   E2  no silent clear — the queue exposes no dismiss; a row leaves only via an existing gated verb
#   E3  classification is the sealed router's — material+ungated = policy_gap, never auto-resolved
#   E4  no pay/remit/file/crossing reachable; queue itself writes nothing
#   E5  kill-grep bites on injected silent-clear verbs
#   E6  BAR updated; prior P/O/I/PV/A rows stay GREEN
# ==================================================================================================

def _seed_exceptions(nb):
    """A material draft (hold), a standing veto, and a locked period."""
    nb.record_income(work_ref="j", amount=100)
    nb.obligation_open(title="Material thing", material=True)
    vetoed = nb.obligation_open(title="Vetoed thing")["receipt"]["id"]
    nb.obligation_veto(vetoed, role="cfo", reason="numbers off")
    nb.close_period(period_id="2026-Q3")
    return vetoed


# ---- E1 -----------------------------------------------------------------------------------------

def test_e1_queue_reads_node_state_and_survives_restart(node):
    _seed_exceptions(bind(node, regulated=False))
    # a FRESH binding derives the same queue — node state, not app memory
    q = bind(node, regulated=True).exceptions_queue()
    kinds = sorted(i["kind"] for i in q["items"])
    assert kinds == ["hold", "lock", "veto"]
    assert q["by_status"]["pending_gate"] == 2      # hold + veto, both gated under regulated
    assert q["by_status"]["recorded"] == 1          # the lock, informational
    assert all(i["durable"] for i in q["items"])    # nothing session-scoped seeded


def test_e1_clean_node_has_an_empty_queue(node):
    nb = bind(node, regulated=False)
    nb.record_income(work_ref="clean", amount=10)
    q = nb.exceptions_queue()
    assert q["total"] == 0 and q["items"] == []


def test_e1_session_pending_is_listed_and_labeled(node):
    nb = bind(node)  # regulated
    nb.record_income(work_ref="held", amount=10)   # stages at the gate
    q = nb.exceptions_queue()
    pend = [i for i in q["items"] if i["kind"] == "pending-approval"]
    assert len(pend) == 1 and pend[0]["durable"] is False


# ---- E2 -----------------------------------------------------------------------------------------

def test_e2_no_dismiss_exists_and_governed_act_is_the_only_exit(node):
    vetoed = _seed_exceptions(bind(node, regulated=False))
    nb = bind(node)  # regulated
    # (a) the binding exposes no dismiss/clear verb for the queue
    for name in dir(nb):
        low = name.lower()
        assert not any(v in low for v in ("dismiss", "suppress", "ignore_exception",
                                          "clear_exception", "silent")), name
    # (b) the veto row leaves ONLY via the existing gated clear_veto
    assert sum(1 for i in nb.exceptions_queue()["items"] if i["kind"] == "veto") == 1
    sub = nb.obligation_clear_veto(vetoed, role="cfo")
    assert sub["gated"] is True
    nb.dispose(sub["req_id"], approve=False, reason="not yet")     # denial changes nothing
    assert sum(1 for i in nb.exceptions_queue()["items"] if i["kind"] == "veto") == 1
    sub2 = nb.obligation_clear_veto(vetoed, role="cfo")
    nb.dispose(sub2["req_id"], approve=True)                        # the governed act
    assert sum(1 for i in nb.exceptions_queue()["items"] if i["kind"] == "veto") == 0


def test_e2_queue_read_writes_nothing(node):
    nb = bind(node, regulated=False)
    nb.record_income(work_ref="j", amount=10)
    reg_log = objects_ndjson(node)
    before = open(reg_log, "rb").read()
    nb.exceptions_queue()
    assert open(reg_log, "rb").read() == before
    assert not os.path.exists(os.path.join(node["ledger"], "obligations.ndjson"))


# ---- E3 -----------------------------------------------------------------------------------------

def test_e3_sovereign_posture_surfaces_policy_gap_not_auto_resolve(node):
    """Under the ungated (sovereign) posture no gate covers a material deviation — the sealed
    router refuses it (default-deny) and the queue shows a POLICY GAP, never a silent pass."""
    _seed_exceptions(bind(node, regulated=False))
    q = bind(node, regulated=False).exceptions_queue()
    assert q["by_status"]["policy_gap"] == 2        # hold + veto: material, no gate stands
    assert q["by_status"]["pending_gate"] == 0
    gap = [i for i in q["items"] if i["status"] == "policy_gap"]
    assert all(i["materiality"] == "high" for i in gap)


def test_e3_integrity_breach_is_a_material_row(node):
    nb = bind(node, regulated=False)
    nb.record_income(work_ref="j", amount=100)
    # tamper the registry log — the roots stop matching and every verify goes red
    log = objects_ndjson(node)
    raw = open(log, "r", encoding="utf-8").read()
    open(log, "w", encoding="utf-8").write(raw.replace('"amount": 100', '"amount": 999'))
    q = bind(node, regulated=False).exceptions_queue()
    kinds = {i["kind"] for i in q["items"]}
    assert "integrity" in kinds or "verify-failure" in kinds
    assert all(i["materiality"] == "high" for i in q["items"] if i["kind"] in ("integrity", "verify-failure"))


# ---- E4 -----------------------------------------------------------------------------------------

def test_e4_no_money_path_reachable_from_the_queue_surface(node):
    nb = bind(node, regulated=False)
    forbidden = ("pay_", "remit", "disburse", "collect", "wire_", "bank_transfer", "settle_pay")
    for name in dir(nb):
        if not name.startswith("__"):
            assert not any(f in name.lower() for f in forbidden), name
    proc = _run_killgrep(APP_DIR)
    assert proc.returncode == 0 and "P6: GREEN" in proc.stdout


# ---- E5 -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("label,inject", [
    ("dismiss verb", "def dismiss_exception(row):\n    return row\n"),
    ("silent clear", "def _tidy(q):\n    silent_clear = True\n    return silent_clear\n"),
    ("bulk dismiss", "def bulk_dismiss(rows):\n    return []\n"),
])
def test_e5_killgrep_catches_silent_clear_verbs(tmp_path, label, inject):
    copy = tmp_path / "app"
    shutil.copytree(APP_DIR, copy, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    target = copy / "node_binding.py"
    target.write_text(target.read_text() + "\n\n" + textwrap.dedent(inject), encoding="utf-8")
    proc = _run_killgrep(str(copy))
    assert proc.returncode == 1, f"kill-grep stayed GREEN with '{label}' injected:\n{proc.stdout}"


# ---- E6 -----------------------------------------------------------------------------------------

def test_e6_queue_agrees_with_the_panels_it_points_at(node):
    _seed_exceptions(bind(node, regulated=False))
    nb = bind(node, regulated=True)
    q = nb.exceptions_queue()
    obs = nb.obligations()
    # the hold row's obligation is genuinely open+material+unapproved on the obligations panel
    hold = next(i for i in q["items"] if i["kind"] == "hold")
    ob = next(o for o in obs["items"] if o["id"] == hold["ref"])
    assert ob["material"] is True and ob["status"] == "draft" and not ob["closed"]
    # the lock row ties to the period view's closed periods
    lock = next(i for i in q["items"] if i["kind"] == "lock")
    assert any(c["period"] == "2026-Q3" for c in nb.period_view()["closed_periods"])
    assert lock["status"] == "recorded"


# ==================================================================================================
# H1–H6 · Operator status home — ONE read-only screen composing ONLY existing reads
# ==================================================================================================

def test_h1_home_composes_existing_reads_and_survives_restart(node):
    nb = bind(node, regulated=False)
    _seed_exceptions(nb)                                  # material hold + veto + closed period
    h = bind(node, regulated=True).status_home()          # fresh binding = restart
    q = bind(node, regulated=True).exceptions_queue()
    pv = bind(node, regulated=True).period_view()
    # every home figure equals the panel it names — same reads, no new derivation
    assert h["open_exceptions"]["open"] == q["by_status"]["pending_gate"] + q["by_status"]["policy_gap"]
    assert h["open_exceptions"]["recorded"] == q["by_status"]["recorded"]
    assert h["approvals"]["material_awaiting_gate"] == sum(1 for i in q["items"] if i["kind"] == "hold")
    assert h["period"]["in_balance"] == pv["nets_to_zero"]
    assert [c["period"] for c in h["period"]["closed_periods"]] == \
           [c["period"] for c in pv["closed_periods"]]


def test_h2_home_read_writes_nothing(node):
    nb = bind(node, regulated=False)
    _seed_exceptions(nb)
    reg_log, led_log = objects_ndjson(node), os.path.join(node["ledger"], "obligations.ndjson")
    before = (open(reg_log, "rb").read(), open(led_log, "rb").read())
    bind(node, regulated=True).status_home()
    assert (open(reg_log, "rb").read(), open(led_log, "rb").read()) == before


def test_h3_audit_ready_is_the_existing_package_verdict(node):
    nb = bind(node, regulated=False)
    _seed_audit_books(nb)
    h = nb.status_home()
    pkg, digest = nb.audit_package()
    assert h["audit_readiness"]["ready"] == pkg["compliance_core"]["ready"]
    assert h["audit_readiness"]["package_sha256"] == digest      # same path, same verdict
    assert h["audit_readiness"]["checks_total"] == len(pkg["checks"])


def test_h4_home_uses_enterprise_labels_and_no_write_verbs(node):
    nb = bind(node, regulated=False)
    nb.record_income(work_ref="j", amount=10)
    h = nb.status_home()
    assert h["open_exceptions"]["label"] == "Open exceptions"
    assert h["approvals"]["label"] == "Approvals"
    assert h["period"]["label"] == "Period status"
    assert h["audit_readiness"]["label"] == "Audit readiness"
    # no kernel jargon leaks into the home payload's labels
    text = json.dumps(h)
    for jargon in ("doc_kind", "work_ref", "obl_open"):
        assert jargon not in text, f"kernel jargon '{jargon}' leaked into the home screen"


def test_h5_killgrep_still_bites_silent_clear_on_the_home_build(tmp_path):
    copy = tmp_path / "app"
    shutil.copytree(APP_DIR, copy, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    target = copy / "node_binding.py"
    target.write_text(target.read_text() + "\n\ndef dismiss_exception(row):\n    return row\n",
                      encoding="utf-8")
    proc = _run_killgrep(str(copy))
    assert proc.returncode == 1 and "P6: RED" in proc.stdout



# ==================================================================================================
# M1–M6 · Master data — chart of accounts + party roll-ups, READ-ONLY, derived from records
# ==================================================================================================

def _seed_master(nb):
    nb.record_income(work_ref="consult", amount=2400, unit="USD")
    nb.record_contribution_event(source="skill_service", work_ref="tutoring", amount=300)
    nb.record_invoice(invoice_id="INV-1", customer="Acme", lines=_lines(("svc", 1, 1000)), issued_day=5)
    nb.record_invoice(invoice_id="INV-2", customer="Acme", lines=_lines(("svc2", 1, 500)), issued_day=8)
    nb.record_invoice(invoice_id="INV-3", customer="Beta", lines=_lines(("x", 1, 600)),
                      issued_day=1, extra={"deferred": True})


def test_m1_chart_reflects_node_state_and_survives_restart(node):
    _seed_master(bind(node, regulated=False))
    coa = bind(node, regulated=False).chart_of_accounts_view()      # fresh binding = restart
    by = {a["account"]: a for a in coa["accounts"]}
    assert by["cash"]["net"] == "2700.0" and by["cash"]["type"] == "asset"
    assert by["accounts_receivable"]["net"] == "2100.0"
    assert by["unearned_revenue"]["net"] == "-600.0"               # credit-natural
    assert by["revenue"]["net"] == "-4200.0"
    assert by["expense"]["active"] is False and by["expense"]["net"] == "0"
    assert coa["account_count"] == 6


def test_m1_empty_node_shows_the_typed_chart_with_zero_balances(node):
    coa = bind(node, regulated=False).chart_of_accounts_view()
    assert coa["account_count"] == 6 and coa["active_count"] == 0
    assert all(a["net"] == "0" for a in coa["accounts"])


def test_m2_party_rollups_tie_to_the_records(node):
    _seed_master(bind(node, regulated=False))
    p = bind(node, regulated=False).parties()
    acme = next(c for c in p["customers"] if c["customer"] == "Acme")
    assert acme["invoices"] == 2 and acme["total_billed"] == 1500.0
    assert acme["last_invoice_id"] == "INV-2"                      # newest by timestamp
    beta = next(c for c in p["customers"] if c["customer"] == "Beta")
    assert beta["total_billed"] == 600.0
    srcs = {s["source"]: s for s in p["revenue_sources"]}
    assert srcs["direct"]["total"] == 2400.0                        # plain income
    assert srcs["skill_service"]["total"] == 300.0                  # contribution source
    assert p["vendor_count"] == 0 and "empty by construction" in p["vendor_note"]


def test_m2_customer_appears_exactly_when_a_record_names_it(node):
    nb = bind(node, regulated=False)
    assert nb.parties()["customer_count"] == 0
    nb.record_invoice(invoice_id="I1", customer="NewCo", lines=_lines(("a", 1, 10)))
    assert [c["customer"] for c in nb.parties()["customers"]] == ["NewCo"]


def test_m3_master_data_reads_write_nothing(node):
    nb = bind(node, regulated=False)
    _seed_master(nb)
    reg_log = objects_ndjson(node)
    before = open(reg_log, "rb").read()
    f = bind(node, regulated=False)
    f.chart_of_accounts_view(); f.parties()
    assert open(reg_log, "rb").read() == before
    assert not os.path.exists(os.path.join(node["ledger"], "obligations.ndjson"))


def test_m4_no_master_data_write_verb_exists(node):
    nb = bind(node, regulated=False)
    forbidden = ("add_account", "edit_account", "delete_account", "add_customer", "edit_customer",
                 "add_vendor", "merge_part", "update_master")
    for name in dir(nb):
        if not name.startswith("__"):
            assert not any(f in name.lower() for f in forbidden), name


@pytest.mark.parametrize("label,inject", [
    ("second master store", "import sqlite3\n_md = sqlite3.connect('master.db')\n"),
    ("silent clear on party", "def dismiss_exception(row):\n    return row\n"),
])
def test_m5_killgrep_bites_on_master_data_violations(tmp_path, label, inject):
    copy = tmp_path / "app"
    shutil.copytree(APP_DIR, copy, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    target = copy / "node_binding.py"
    target.write_text(target.read_text() + "\n\n" + textwrap.dedent(inject), encoding="utf-8")
    proc = _run_killgrep(str(copy))
    assert proc.returncode == 1, f"kill-grep stayed GREEN with '{label}' injected:\n{proc.stdout}"


def test_m6_chart_ties_to_the_period_view(node):
    _seed_master(bind(node, regulated=False))
    nb = bind(node, regulated=False)
    coa = {a["account"]: a["net"] for a in nb.chart_of_accounts_view()["accounts"] if a["active"]}
    assert coa == nb.period_view()["trial_balance"]                 # same sealed projection



# ==================================================================================================
# D1–D6 · Transaction / journal drill-down — READ-ONLY, every drill carries its equality proof
# ==================================================================================================

def test_d1_every_active_account_drill_ties_to_the_trial_balance(node):
    _seed_master(bind(node, regulated=False))
    f = bind(node, regulated=False)                                   # fresh binding = restart
    tb = f.period_view()["trial_balance"]
    for acct, stated in tb.items():
        d = f.drill(kind="account", key=acct)
        assert d["ties"] is True, f"{acct}: {d['sum_of_lines']} != {d['stated_total']}"
        assert d["sum_of_lines"] == d["stated_total"] == str(round(float(stated), 2)) or \
               float(d["sum_of_lines"]) == float(stated)              # EQUALITY, not presence
        assert d["line_count"] >= 1


def test_d1_tb_alias_is_the_same_drill(node):
    _seed_master(bind(node, regulated=False))
    f = bind(node, regulated=False)
    assert f.drill(kind="tb", key="cash") == f.drill(kind="account", key="cash")


def test_d2_customer_and_source_drills_tie_to_the_rollups(node):
    _seed_master(bind(node, regulated=False))
    f = bind(node, regulated=False)
    p = f.parties()
    for c in p["customers"]:
        d = f.drill(kind="customer", key=c["customer"])
        assert d["ties"] is True and float(d["sum_of_lines"]) == c["total_billed"]
        assert d["line_count"] == c["invoices"]
    for s in p["revenue_sources"]:
        d = f.drill(kind="source", key=s["source"])
        assert d["ties"] is True and float(d["sum_of_lines"]) == s["total"]


def test_d2_period_drill_nets_to_zero_with_every_posting_balanced(node):
    _seed_master(bind(node, regulated=False))
    d = bind(node, regulated=False).drill(kind="period")
    assert d["ties"] is True and float(d["sum_of_lines"]) == 0.0
    assert d["line_count"] == 5
    assert all(l["balanced"] for l in d["lines"])


def test_d3_every_drilled_line_names_a_resolvable_governed_record(node):
    _seed_master(bind(node, regulated=False))
    f = bind(node, regulated=False)
    known = {e.get("object_id") for e in f._income_entries()}
    for kind, key in (("account", "revenue"), ("account", "cash"), ("customer", "Acme"),
                      ("source", "direct"), ("period", None)):
        d = f.drill(kind=kind, key=key)
        for l in d["lines"]:
            src = l["source"]
            assert src["object_id"] in known, f"{kind}:{key} line names unknown record {src}"
            assert src["record_type"] in ("income", "contribution", "invoice")


def test_d4_drill_reads_write_nothing_and_unknowns_refuse(node):
    nb = bind(node, regulated=False)
    _seed_master(nb)
    reg_log = objects_ndjson(node)
    before = open(reg_log, "rb").read()
    f = bind(node, regulated=False)
    f.drill(kind="account", key="cash"); f.drill(kind="period")
    assert open(reg_log, "rb").read() == before
    with pytest.raises(SurfaceError):
        f.drill(kind="account", key="slush_fund")
    with pytest.raises(SurfaceError):
        f.drill(kind="customer", key="Nobody Inc")
    with pytest.raises(SurfaceError):
        f.drill(kind="ledger_rewrite", key="x")


@pytest.mark.parametrize("label,inject", [
    ("plug the difference", "def plug_difference(total, lines):\n    return total\n"),
    ("force balance", "def _fix(tb):\n    force_balance = True\n    return force_balance\n"),
    ("adjust total", "def adjust_total(d):\n    return d\n"),
])
def test_d5_killgrep_bites_tie_out_tampering(tmp_path, label, inject):
    copy = tmp_path / "app"
    shutil.copytree(APP_DIR, copy, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    target = copy / "node_binding.py"
    target.write_text(target.read_text() + "\n\n" + textwrap.dedent(inject), encoding="utf-8")
    proc = _run_killgrep(str(copy))
    assert proc.returncode == 1, f"kill-grep stayed GREEN with '{label}' injected:\n{proc.stdout}"


def test_d6_drill_provenance_never_forks_the_derivation(node):
    """_derive_postings and _derived_journal must be the same accounting — the postings list is
    exactly the journal's postings, so provenance can never drift from the books."""
    _seed_master(bind(node, regulated=False))
    f = bind(node, regulated=False)
    assert f._derive_postings() == [j["posting"] for j in f._derived_journal()]


def test_h6_home_reflects_governed_change_only(node):
    vetoed = _seed_exceptions(bind(node, regulated=False))
    nb = bind(node, regulated=True)
    before = nb.status_home()["open_exceptions"]["open"]
    sub = nb.obligation_clear_veto(vetoed, role="cfo")
    nb.dispose(sub["req_id"], approve=False, reason="hold")       # denial changes nothing
    assert nb.status_home()["open_exceptions"]["open"] == before
    sub2 = nb.obligation_clear_veto(vetoed, role="cfo")
    nb.dispose(sub2["req_id"], approve=True)                       # the governed act moves the tile
    assert nb.status_home()["open_exceptions"]["open"] == before - 1
