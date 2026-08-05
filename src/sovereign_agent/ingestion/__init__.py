"""Ingestion — Multi-Standard Ingestion (s5_25): map external standards into sovereign-typed intake. It maps an
external-standard record (an EDI document, an ISO message, a regulatory board's schema — already extracted; the
connectors that reach the external systems are the sovereign port's, not this module's) into a sealed sovereign
OBJECT VERSION, drift-safe, and receipts a batch to a provenance root — composing the sealed Sovereign Object Model
(identity, authored + provenance-stamped versions, merkle proofs). It builds no second master-data system: the identity,
versioning, provenance, and integrity are the object model's, not reimplemented here."""
from .standards import map_record, ingest_record, ingest_standard, IngestionError

__all__ = ["map_record", "ingest_record", "ingest_standard", "IngestionError"]
