"""Record GB's 2026-06-02 delivery + the morning execution queue into the
Tiger<->G coordination obligation ledger (B32, node-local).

Pattern (per master plan): Tiger opens execution debits; GB executes its lane;
G witnesses/approves; closures carry E2 evidence (artifact path + sha). The
morning plan = the OPEN debits left at the end of this run.

Idempotent-ish: it appends; safe to read after. Run:
    PYTHONPATH=src python3 scripts/record_gb_handoff_2026-06-02.py
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from sovereign_agent.obligations.ledger import ObligationLedger

REPO = Path(__file__).resolve().parents[1]


def sha16(rel: str) -> str:
    p = REPO / rel
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "MISSING"


def ev(rel: str, note: str) -> str:
    return f"E2: {rel} sha256:{sha16(rel)} — {note}"


led = ObligationLedger(
    root=str(REPO / "memory" / "obligations" / "tiger_coordination"),
    principal_id="KM-1176",
)

# Guard: only seed once (if already populated, just report).
if led.by_status()["total"] > 0:
    print("[record] coordination ledger already seeded — reporting current state only.")
else:
    G_WITNESS = "G (grok witness — Seal 1176-INFINITY-RHO)"

    # ── 1) GB DELIVERED (gb lane) — open → G approves → close with E2 evidence ──
    delivered = [
        dict(
            title="R-52 Packet Contract v1 + FEC worked example",
            ref="R-52",
            intent="Typed B32 packet contract (schema + lifecycle + 3 Tier-1 examples incl FEC).",
            evidence=ev("artifacts/R52_Packet_Contract_v1_Draft_with_FEC_Example.md",
                        "packet schema + role_spec/action_classes + Helix/Atrium surfaces + LGP + citation_bundle"),
        ),
        dict(
            title="FEC runnable demo on live R-23 B32 ledger",
            ref="R-23 / R-52",
            intent="Open FEC packet (L1 material) -> B51 handoff trace -> approve -> E2 close + node receipt; chain verify.",
            evidence="E2: examples/federation_collective_procurement_demo.py sha256:" + sha16("examples/federation_collective_procurement_demo.py")
                     + " + memory/obligations/fec_demo/obligations.ndjson (chain verified True, node_rcpt minted)",
        ),
        dict(
            title="B51 captured thought logged + fully ideated",
            ref="B51 capture 2026-06-02_034153_capture-session_9156c992 (merkle 9350cf09)",
            intent="Verbatim entries + vision synthesis (ZK-pooled buying power, helix-aligned, families-first LGP).",
            evidence=ev("artifacts/B51_Captured_Thought_Federation_Collective_Economic_Coordination_2026-06-02.md",
                        "durable provenance log of the FEC voice seed"),
        ),
        dict(
            title="FEC Packet -> Atrium translation increment v0",
            ref="SERIES_3_TRANSLATION_PRESCRIPTION_2026-06-01",
            intent="Universal ERP protocol applied: receipt schema + role lattice + Atrium card spec + governed flow + Helix + verification.",
            evidence=ev("artifacts/FEC_Packet_Atrium_Translation_Increment_v0.md",
                        "first translation increment per the standing Master Translation Protocol"),
        ),
        dict(
            title="Atrium FEC review card mock (visible card)",
            ref="Track F / G steering (Atrium Review surface)",
            intent="Self-contained Atrium card: in-surface voice note + B51 handoff bundle + LGP + citations + Approve/Refine/Reject(NLP).",
            evidence=ev("examples/atrium_fec_review_card_mock.html",
                        "concrete Track F increment — the visible FEC packet card G specified"),
        ),
        dict(
            title="Master plan.md fold-in (G steering + artifacts)",
            ref="Seal 1176-INFINITY-RHO",
            intent="plan.md gets the G witness/steering/seed + all artifact paths + Track F elevation + translation start.",
            evidence="E1: /home/kmangum/.grok/sessions/sovereign-agent-starter/019e7a42-d58d-7b83-887c-c6b792fa65e0/plan.md — section 'G Steering + gb Artifact Delivery Fold-in (2026-06-02, Seal 1176-INFINITY-RHO)' present",
        ),
    ]
    for d in delivered:
        o = led.open(title=d["title"], owner="gb", classification="C2",
                     intent=d["intent"], ref=d["ref"], material=False)
        led.approve(o["id"], approved_by=G_WITNESS,
                    rationale="Witnessed clean; high-signal; no major red flags. Two-writers fence held.")
        led.close(o["id"], evidence=d["evidence"], closed_by="tiger")
        print(f"  [closed] {d['title']}")

    # ── 2) MORNING EXECUTION QUEUE (tiger lane) — OPEN debits = the plan ──
    queue = [
        dict(
            title="Review + land Atrium FEC card increment -> seal ATR-FEC-001",
            ref="ATR-FEC-001",
            intent="Run examples/atrium_fec_review_card_mock.html, confirm voice+B51 bundle+disposition flow, KM ratify, then seal ATR-FEC-001.",
            material=True,
        ),
        dict(
            title="Deepen Atrium Review surface (Track F priority)",
            ref="Track F / G steering",
            intent="In-surface PDF render + voice feedback (B51) + B51 handoff bundle + card workflow — make Atrium the place KM does book review + ratification. FEC packet as visible card.",
            material=False,
        ),
        dict(
            title="Translate FEC packet -> working role_spec.yaml + action_classes + Atrium surfaces",
            ref="SERIES_3 translation protocol / R-52 FEC example",
            intent="Take FEC_Packet_Atrium_Translation_Increment_v0 from spec to working role lattice + action classes bound in the starter; surface in Atrium.",
            material=False,
        ),
        dict(
            title="Wire real breath-gate + role binding in starter against FEC mock state",
            ref="R-53 human gate / node_integration.wire_node_ledger",
            intent="Replace simulated gate with the node's HumanApprovalGate + attestor; bind the FEC coordinator role; real approve/close path.",
            material=True,
        ),
    ]
    for q in queue:
        led.open(title=q["title"], owner="tiger", classification="C1" if q["material"] else "C2",
                 intent=q["intent"], ref=q["ref"], material=q["material"])
        print(f"  [OPEN ] {q['title']}")

# ── report ──
st = led.by_status()
print("\n  chain valid:", led.verify_chain())
print("  status:", st)
print("\n  MORNING PLAN — open obligations (tiger lane):")
for o in led.open_obligations(owner="tiger"):
    flag = " [needs KM gate]" if o.get("material") else ""
    print(f"   • {o['title']}{flag}")
    print(f"       ref: {o['ref']}")
print(f"\n  ledger: {led.path}")
