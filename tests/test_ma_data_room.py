"""Unit + integration tests for the extruded Data-Room Classifier (Book 11 Ch 2)."""
from sovereign_agent.demo_roles.ma_data_room.role import DataRoomClassifier, GATES


def test_classify_document_is_green_and_applies_scheme():
    agent = DataRoomClassifier({"financial": ["EBITDA", "QoE"], "legal": ["indemnity"]})
    r = agent.classify_document({"id": "d1", "name": "QoE_report.xlsx", "text": "EBITDA bridge"})
    assert r["scope"] == "GREEN" and r["executed"] is True
    assert r["compartment"] == "financial"


def test_unclassified_doc_flags_for_human():
    agent = DataRoomClassifier({"financial": ["EBITDA"]})
    r = agent.classify_document({"id": "d2", "name": "misc.txt", "text": "hello"})
    assert r["compartment"] == "unclassified" and r["needs_human"] is True


def test_define_scheme_is_material_and_proposal_only():
    agent = DataRoomClassifier()
    r = agent.define_classification_scheme({"hr": ["salary"]})
    assert r["scope"] == "YELLOW" and r["executed"] is False and r["needs_human"] is True


def test_leak_flag_is_red_and_never_auto_acts():
    agent = DataRoomClassifier()
    r = agent.flag_cross_compartment_leak("d3", "legal", "financial")
    assert r["scope"] == "RED" and r["executed"] is False


def test_governance_gates_match_spec():
    # Integration: the gate map reflects the book — human defines (YELLOW), agent applies (GREEN),
    # leaks escalate (RED). No action class executes a material change autonomously.
    assert GATES["classify_document"][1] == "GREEN"
    assert GATES["define_classification_scheme"][1] == "YELLOW"
    assert GATES["flag_cross_compartment_leak"][1] == "RED"
