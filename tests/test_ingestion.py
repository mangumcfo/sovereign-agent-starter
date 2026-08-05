"""Multi-Standard Ingestion (s5_25 / reading Vol 27) — proof that external-standard records map into sealed
sovereign object versions drift-safe, and a batch receipts to a provenance root, composing the Sovereign Object
Model and building no second master-data system.

Pure composition (the object model is hashlib-based, no crypto substrate) — runs green on a bare public clone."""
import pytest

from sovereign_agent import ingestion as ing
from sovereign_agent.ingestion import IngestionError
from sovereign_agent.objects.identity import VersionRefused

# An external standard (e.g. an EDI-850 purchase order) and its DECLARED mapping into the sovereign type.
EDI_850 = {"BEG03": "PO-1001", "N1_ST": "Meridian Chemical", "PO1_02": "250"}
MAP_850 = {"BEG03": "po_number", "N1_ST": "buyer", "PO1_02": "quantity"}
# a SYMBOLIC source_ref (no path separator) — the provenance law accepts it as a standard citation, not a file claim
SRC = "EDI-850:2024-po-standard"


def _ingest_one(external=None, mapping=None, **kw):
    return ing.ingest_record(external or EDI_850, mapping or MAP_850,
                             cls_="purchase_order", natural_key_field="po_number",
                             author="ingest-bot", source_ref=SRC, at="2026-08-05", **kw)


# --- mapping: drift-safe, value-conserving -----------------------------------------------------------------------

def test_map_record_maps_declared_fields_value_conserving():
    p = ing.map_record(EDI_850, MAP_850)
    assert p == {"po_number": "PO-1001", "buyer": "Meridian Chemical", "quantity": "250"}


def test_map_record_refuses_an_unmapped_source_field_drift():
    drifted = dict(EDI_850, PO1_09="NEW_FIELD")  # the standard added a field the mapping does not declare
    with pytest.raises(IngestionError, match="unmapped source field"):
        ing.map_record(drifted, MAP_850)


def test_map_record_drops_an_explicitly_dropped_field():
    withextra = dict(EDI_850, CTT01="1")
    p = ing.map_record(withextra, MAP_850, drop=["CTT01"])
    assert "CTT01" not in p and p["po_number"] == "PO-1001"


def test_map_record_refuses_a_collision_on_one_sovereign_field():
    ext = {"a": "X", "b": "Y"}
    m = {"a": "buyer", "b": "buyer"}  # two source fields -> one sovereign field, different values
    with pytest.raises(IngestionError, match="collision"):
        ing.map_record(ext, m)


# --- sovereign-typed version: composes the sealed object model ----------------------------------------------------

def test_ingest_record_makes_a_sealed_sovereign_object_version():
    v = _ingest_one()
    assert v["object_id"] == "purchase_order:PO-1001"
    assert v["payload"] == {"po_number": "PO-1001", "buyer": "Meridian Chemical", "quantity": "250"}
    assert v["author"] == "ingest-bot" and v["source_ref"] == SRC and v["kind"] == "ingest"
    assert v["version_hash"]  # the object model stamps an integrity hash over every field


def test_ingest_record_refuses_a_record_with_no_natural_key():
    ext = {"N1_ST": "Meridian Chemical", "PO1_02": "250"}  # no BEG03 -> no po_number
    with pytest.raises(IngestionError, match="no natural key"):
        _ingest_one(external=ext)


def test_ingest_record_false_authorship_is_refused_by_the_sealed_object_model_not_by_us():
    # composition proof: an empty author is barred by objects.make_version (the sealed floor), through ingestion
    # exactly as if make_version were called directly — this module adds no authorship of its own.
    with pytest.raises(VersionRefused):
        ing.ingest_record(EDI_850, MAP_850, cls_="purchase_order", natural_key_field="po_number",
                          author="", source_ref=SRC, at="2026-08-05")


# --- batch ingestion: receipted provenance root, fail-closed ------------------------------------------------------

def test_ingest_standard_batch_receipts_to_a_provenance_root():
    recs = [EDI_850, {"BEG03": "PO-1002", "N1_ST": "Harbor Co", "PO1_02": "10"}]
    out = ing.ingest_standard(recs, MAP_850, cls_="purchase_order", natural_key_field="po_number",
                              author="ingest-bot", source_ref=SRC, at="2026-08-05")
    assert out["count"] == 2
    assert len(out["versions"]) == 2
    assert isinstance(out["ingestion_root"], str) and len(out["ingestion_root"]) >= 32


def test_ingest_standard_is_fail_closed_one_drifted_record_refuses_the_whole_batch():
    recs = [EDI_850, {"BEG03": "PO-1002", "N1_ST": "Harbor Co", "PO1_99": "drift"}]  # 2nd has an unmapped field
    with pytest.raises(IngestionError, match="unmapped source field"):
        ing.ingest_standard(recs, MAP_850, cls_="purchase_order", natural_key_field="po_number",
                            author="ingest-bot", source_ref=SRC, at="2026-08-05")


def test_ingestion_root_is_deterministic_and_drift_detectable():
    # the same records + mapping give the same root; a changed value gives a different root (Ch6 maintenance:
    # drift between two ingests is visible as a changed fingerprint).
    recs = [EDI_850]
    r1 = ing.ingest_standard(recs, MAP_850, cls_="purchase_order", natural_key_field="po_number",
                             author="ingest-bot", source_ref=SRC, at="2026-08-05")["ingestion_root"]
    r2 = ing.ingest_standard(recs, MAP_850, cls_="purchase_order", natural_key_field="po_number",
                             author="ingest-bot", source_ref=SRC, at="2026-08-05")["ingestion_root"]
    changed = ing.ingest_standard([dict(EDI_850, PO1_02="999")], MAP_850, cls_="purchase_order",
                                  natural_key_field="po_number", author="ingest-bot", source_ref=SRC, at="2026-08-05")["ingestion_root"]
    assert r1 == r2 and r1 != changed
