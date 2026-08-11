#!/usr/bin/env python3
"""Phase 2 BATTERY runner (KM GO 2026-08-11) — exercises the sealed inter-node / economic / ops surfaces on
iron and emits a real-artifact pack per AA's Phase 2 BAR.

Each case runs the REAL kernel calls, captures the observed object shapes (schema snapshot), and asserts the
exact shapes + refusals AA published. A refusal that does not fire is a HOLD (load-bearing: P2-03, P2-04
deny-by-default, P2-07's two refusals). Output pack (self-verifying merkle bundle):
  receipts.json · schema_snapshot.yaml · verdict.txt · packet.json · obligation.json (on any HOLD)
Harness: uat:true inside a node-signed attestation · principal != KM-1176 · never the seal ledger.

  PYTHONPATH=src python3 scripts/phase2_battery.py <keystore_dir> <kernel_sha> <out_pack_dir>
"""
from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.objects.scope import SharingRule
from sovereign_agent.evidence.export_packet import _merkle_root, _canon, _sha
from sovereign_agent.keystore.node_keystore import (
    generate_node_key, has_node_key, load_node_key, sign_node_act, verify_node_act, SIG_SCHEME)

AT = "2026-08-11T21:00:00Z"
PRINCIPAL = "dragon-phase2-uat"          # reserved test principal, never KM-1176


def _safe(o):
    """JSON-safe: Decimals -> str, dataclasses/objects -> their __dict__, tuples -> lists."""
    if isinstance(o, Decimal):
        return str(o)
    if isinstance(o, dict):
        return {str(k): _safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_safe(v) for v in o]
    if hasattr(o, "__dict__"):
        return {k: _safe(v) for k, v in vars(o).items()}
    if hasattr(o, "_asdict"):
        return _safe(o._asdict())
    return o


class Case:
    def __init__(self, cid, title):
        self.cid, self.title, self.asserts, self.snapshot, self.verdict, self.defect = cid, title, [], {}, "GREEN", ""

    def check(self, name, ok, detail=""):
        self.asserts.append({"assert": name, "ok": bool(ok), "detail": detail})
        if not ok:
            self.verdict = "HOLD"
            if not self.defect:
                self.defect = f"{name} failed: {detail}"
        return ok

    def refused(self, name, fn):
        """A required refusal: GREEN iff fn() raises. A refusal that does not fire is a HOLD."""
        try:
            fn()
            self.check(name + " (refusal must fire)", False, "no exception raised — the fence did NOT hold")
        except Exception as e:
            self.check(name, True, "refused: " + str(e)[:120])

    def receipt(self):
        return {"case": self.cid, "title": self.title, "verdict": self.verdict, "asserts": self.asserts,
                "snapshot": _safe(self.snapshot), "uat": True, "principal": PRINCIPAL, "defect": self.defect}


def run(KSD):
    from sovereign_agent.peerhood.bridging import form_peer_pool, attribute_pool_value, settle_pool_on_port
    from sovereign_agent.economy.pool import POOL_BREACH_FIELDS, PoolSettlement
    from sovereign_agent.port.crossing import open_crossing, sanction_crossing
    from sovereign_agent.peerhood.genesis import establish_self_held_identity
    from sovereign_agent.peerhood.recognition import mutual_recognition, verify_recognition, refuse_recognition
    from sovereign_agent.peerhood.delegation import join_mutual_protection, PeerhoodError
    from sovereign_agent.peerhood.clean_exit import clean_exit, exit_green_light, CleanExit
    from sovereign_agent.manufacturing.production_order import (open_order, transition, issue_materials,
                                                                is_fully_issued, ProductionError)
    from sovereign_agent.manufacturing.federated_bom import open_bom, bom_root
    from sovereign_agent.economy.income import attribute_income, verify_income, IncomeRefused, MONEY_PATH_BREACH_FIELDS
    from sovereign_agent.estate.generational_transfer import open_key_epoch, family_quorum_recovery

    cases = []
    reg = lambda name: ObjectRegistry(str(Path(KSD) / ("reg_" + name)))

    # ---- P2-01 · Pool form + contribute ----
    c = Case("P2-01", "Pool form + contribute"); cases.append(c)
    r = reg("p01")
    establish_self_held_identity(KSD, "a", at=AT, registry=r)      # pool members hold their own keys
    establish_self_held_identity(KSD, "b", at=AT, registry=r)
    pool, mem = form_peer_pool(KSD, "pool-1", ["a", "b"], "a")
    contrib = attribute_pool_value(pool, "a", "welding", "w:1", at=AT, registry=r, amount=100)
    c.snapshot = {"Pool": {"pool_id": pool.pool_id, "members": list(pool.members)}, "contribution": contrib}
    c.check("pool has >=2 members", len(pool.members) >= 2, str(pool.members))
    c.check("contribution_class attested", contrib.get("payload", {}).get("contribution_class") == "attested"
            or "attested" in json.dumps(_safe(contrib)), "attested")
    c.refused("pool of one refused", lambda: form_peer_pool(KSD, "pool-solo", ["a"], "a"))

    # ---- P2-02 · pool_settlement -> Port directives ONLY ----
    c = Case("P2-02", "pool_settlement -> Port directives only"); cases.append(c)
    ps = settle_pool_on_port(pool, [("a", {"share": "0.5", "port_ref": "port:1"}),
                                    ("b", {"share": "0.5", "port_ref": "port:2"})])
    c.snapshot = {"PoolSettlement": {"pool_id": ps.pool_id, "directives": [dict(d) for d in ps.directives]}}
    d0 = dict(ps.directives[0])
    c.check("directive keys exactly {member,share,port_ref}", set(d0) == {"member", "share", "port_ref"}, str(sorted(d0)))
    surface = [a for a in dir(ps) if any(b in a.lower() for b in ("balance", "net", "settle_amount")) and not a.startswith("__")]
    c.check("no in-node value surface (balance/net/settle_amount)", surface == [], "found: " + str(surface))
    c.check("settlement is a list of directives", isinstance(ps.directives, tuple) and len(ps.directives) == 2, "2 directives")

    # ---- P2-03 · in-node value field REFUSED (a pass here is a HOLD) ----
    c = Case("P2-03", "in-node pool-value field REFUSED"); cases.append(c)
    c.snapshot = {"POOL_BREACH_FIELDS": sorted(POOL_BREACH_FIELDS)}
    c.check("POOL_BREACH_FIELDS n>=10", len(POOL_BREACH_FIELDS) >= 10, str(len(POOL_BREACH_FIELDS)))
    for bf in ("pool_balance", "netting", "internal_settlement", "clearing_balance"):
        c.refused(f"share carrying {bf} refused",
                  (lambda f=bf: settle_pool_on_port(pool, [("a", {"share": "1.0", "port_ref": "p:1", f: "100"})])))

    # ---- P2-04 · Port crossing, deny-by-default ----
    c = Case("P2-04", "Port crossing deny-by-default"); cases.append(c)
    rc = reg("p04")
    crossing = open_crossing(rc, "nodeA", "bank-rail", {"pay": "invoice://123", "to": "acct-external"},
                             mandate="nodeA", author="nodeA", source_ref="crossing://nodeA/1", at=AT)
    c.snapshot["crossing"] = crossing
    c.refused("unsanctioned crossing denied by default (no rule)",
              lambda: sanction_crossing(rc, crossing, rules=[], boundary_mandate="external:bank",
                                        approver="treasurer", approval_ref="run#7"))
    rules = [SharingRule("crossing:nodeA:bank-rail", "external:bank", "write")]
    c.refused("crossing with no named approver refused",
              lambda: sanction_crossing(rc, crossing, rules=rules, boundary_mandate="external:bank",
                                        approver="", approval_ref=""))
    res = sanction_crossing(rc, crossing, rules=rules, boundary_mandate="external:bank",
                            approver="treasurer", approval_ref="payment run #7")
    c.snapshot["sanctioned_receipt"] = res
    c.check("sanctioned crossing crossed=True with named approver", res.get("crossed") is True and res.get("approver") == "treasurer", str(res.get("approver")))
    c.check("receipt holds no value", not any(k in res for k in ("value", "amount", "funds", "balance", "held")), "no value keys")

    # ---- P2-05 · recognize -> verify LIVE -> refuse -> DEAD (multi-peer) ----
    c = Case("P2-05", "multi-peer recognize->live->refuse->DEAD"); cases.append(c)
    rr = reg("p05")
    A = establish_self_held_identity(KSD, "peer-A", at=AT, registry=rr)
    B = establish_self_held_identity(KSD, "peer-B", at=AT, registry=rr)
    rec = mutual_recognition(KSD, "peer-A", "peer-B", at=AT, registry=rr)
    live = verify_recognition(rec, A, B)
    refusal = refuse_recognition(KSD, "peer-A", "peer-B", at=AT, registry=rr, reason="phase2")
    dead = verify_recognition(rec, A, B, revocations=[refusal])
    # OBL-P2-H1: carry the FULL public_hex so a reader can verify both peer identities from the pack alone
    # (recompute node_fingerprint(public_hex) == fingerprint). No truncation.
    c.snapshot = {"peer_A": {"peer_id": A.peer_id, "fingerprint": A.fingerprint, "public_hex": A.public_hex},
                  "peer_B": {"peer_id": B.peer_id, "fingerprint": B.fingerprint, "public_hex": B.public_hex},
                  "recognition": _safe(rec), "refusal": _safe(refusal), "verify_live": live, "verify_dead": dead}
    c.check("verify LIVE first == True", live is True, str(live))
    c.check("after refuse verify DEAD == False", dead is False, str(dead))
    c.check("distinct per-peer fingerprints", A.fingerprint != B.fingerprint, f"{A.fingerprint} vs {B.fingerprint}")

    # ---- P2-06 · U-20 clean exit on iron with real D1 keys ----
    c = Case("P2-06", "U-20 clean_exit sever-kills-live + exit-light"); cases.append(c)
    re6 = reg("p06")
    from sovereign_agent.peerhood.delegation import delegate_governed
    P = establish_self_held_identity(KSD, "peer-P", at=AT, registry=re6)
    Q = establish_self_held_identity(KSD, "peer-Q", at=AT, registry=re6)
    rec2 = mutual_recognition(KSD, "peer-P", "peer-Q", at=AT, registry=re6)
    dele = delegate_governed(KSD, "peer-P", "agent-Q", "cap", expires_at="2026-12-31T00:00:00Z", at=AT,
                             registry=re6, approver="km-op", approval_ref="d:1")
    pool2, mem2 = form_peer_pool(KSD, "pool-P", ["peer-P", "peer-Q"], "peer-P")
    ex = clean_exit(KSD, "peer-P", recognitions=[rec2], delegations=[dele], memberships=[mem2], at=AT, registry=re6)
    gl = exit_green_light(KSD, "peer-P", ex)
    # one grant left un-revoked -> light OFF
    incomplete = CleanExit(peer_id="peer-P", severances=(), grants_severed=2, grants_total=3, no_residual=True)
    gl_off = exit_green_light(KSD, "peer-P", incomplete)
    c.snapshot = {"CleanExit": {"peer_id": ex.peer_id, "grants_severed": ex.grants_severed,
                                "grants_total": ex.grants_total, "no_residual": ex.no_residual,
                                "severances": _safe(list(ex.severances))},
                  "ExitLight": {"on": gl.on, "reason": gl.reason},
                  "ExitLight_one_grant_left": {"on": gl_off.on, "reason": gl_off.reason}}
    c.check("all grants severed", ex.grants_severed == ex.grants_total == 3, f"{ex.grants_severed}/{ex.grants_total}")
    c.check("exit green-light ON on clean exit", gl.on is True, gl.reason)
    c.check("one grant left un-revoked -> light OFF", gl_off.on is False, gl_off.reason)
    c.check("peer still holds its key", has_node_key(KSD, "peer-P"), "key present")

    # ---- P2-07 · manufacturing order lifecycle + two refusals ----
    c = Case("P2-07", "manufacturing order lifecycle + refusals (Vol 19)"); cases.append(c)
    po = open_order("PO-1", "widget", {"steel": 2, "bolt": 8}, 10)
    c.snapshot["planned"] = po
    c.check("required = BOM x qty", str(po["required"].get("steel")) in ("20", "20.0") and str(po["required"].get("bolt")) in ("80", "80.0"), str(_safe(po["required"])))
    c.check("status planned", po["status"] == "planned", po["status"])
    c.refused("issue to a released (not in_process) order refused",
              lambda: issue_materials(transition(po, "released")[0], {"steel": 20, "bolt": 80}))
    po, ev1 = transition(po, "released")
    po, ev2 = transition(po, "in_process")
    c.snapshot["in_process"] = po; c.snapshot["events"] = [ev1, ev2]
    c.refused("over-issue beyond BOM refused",
              lambda: issue_materials(po, {"steel": 25}))
    po = issue_materials(po, {"steel": 20, "bolt": 80})
    c.snapshot["issued"] = po
    c.check("is_fully_issued after full issue", is_fully_issued(po) is True, "fully issued")

    # ---- P2-08 · federated BOM roll-up ----
    c = Case("P2-08", "federated BOM roll-up"); cases.append(c)
    rb = reg("p08")
    b = open_bom(rb, "bom-1", {"steel": 2, "bolt": 8}, mandate="nodeA", author="nodeA", source_ref="bom://1", at=AT)
    root = bom_root(rb, at=AT)
    c.snapshot = {"bom": _safe(b), "bom_root": root}
    c.check("bom root present", bool(root), str(root)[:16])

    # ---- P2-09 · income attribute/verify + money-path refusal ----
    c = Case("P2-09", "income attribute/verify + money-path refusal"); cases.append(c)
    ri = reg("p09")
    inc = attribute_income("earner-1", "welding-qms", mandate="earner-1", author="earner-1",
                           source_ref="income:welding-qms", at=AT, registry=ri, amount=1200.0)
    vi = verify_income(inc, "earner-1", "welding-qms", amount=1200.0)
    c.snapshot = {"income": _safe(inc), "verify": _safe(vi), "MONEY_PATH_BREACH_FIELDS": sorted(MONEY_PATH_BREACH_FIELDS)}
    c.check("income verifies for the earner (IncomeStatus.provisioned)", getattr(vi, "provisioned", None) is True, str(_safe(vi))[:80])
    bf = sorted(MONEY_PATH_BREACH_FIELDS)[0]
    c.refused(f"income carrying money-path field {bf} refused",
              lambda: attribute_income("earner-1", "x", mandate="earner-1", author="earner-1", source_ref="i:x",
                                       at=AT, registry=reg("p09b"), extra={bf: "1"}))

    # ---- P2-10 · join_mutual_protection, no central insurer ----
    c = Case("P2-10", "join_mutual_protection — no central insurer"); cases.append(c)
    rm = reg("p10")
    establish_self_held_identity(KSD, "peer-M", at=AT, registry=rm)
    j = join_mutual_protection(KSD, "peer-M", "pool-x", at=AT, registry=rm)
    c.snapshot = {"join": _safe(j)}
    c.check("central_insurer is None", j.get("central_insurer") is None, str(j.get("central_insurer")))
    c.check("portable True", j.get("portable") is True, "portable")
    c.refused("insurer field refused",
              lambda: join_mutual_protection(KSD, "peer-M", "pool-x", at=AT, registry=rm, extra={"insurer": "acme-ins"}))

    # ---- P2-11 · open_key_epoch -> family_quorum_recovery ----
    c = Case("P2-11", "key epoch + family quorum recovery"); cases.append(c)
    rk = reg("p11")
    ka = establish_self_held_identity(KSD, "kin-A", at=AT, registry=rk)
    kb = establish_self_held_identity(KSD, "kin-B", at=AT, registry=rk)
    kc = establish_self_held_identity(KSD, "kin-C", at=AT, registry=rk)
    epoch = open_key_epoch("fam-1", 1, [ka.fingerprint, kb.fingerprint, kc.fingerprint])
    two_of_n = family_quorum_recovery(epoch, [ka.fingerprint, kb.fingerprint], quorum=2)
    one_only = family_quorum_recovery(epoch, [ka.fingerprint], quorum=2)
    c.snapshot = {"KeyEpoch": {"family_id": epoch.family_id, "epoch": epoch.epoch,
                               "keyholders": list(epoch.keyholders)}, "recover_2of3": two_of_n, "recover_1only": one_only}
    c.check("KeyEpoch records the family keyholders", len(epoch.keyholders) == 3, str(len(epoch.keyholders)))
    c.check("2-of-N recovery True", two_of_n is True, str(two_of_n))
    c.check("below-quorum recovery False", one_only is False, str(one_only))

    return cases


def main():
    KSD, KERNEL, OUT = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "unknown", Path(sys.argv[3])
    Path(KSD).mkdir(parents=True, exist_ok=True)
    if not has_node_key(KSD, "node"):
        generate_node_key(KSD, "node", at=AT)                    # the node that signs the pack attestation

    cases = run(KSD)
    receipts = [c.receipt() for c in cases]
    leaves = [_sha(_canon(r)) for r in receipts]
    merkle = {"root": _merkle_root(leaves), "leaves": leaves}

    # node-signed attestation with uat:true INSIDE the signed payload (harness law)
    att_body = {"phase": "2-battery", "host": "iron", "kernel": KERNEL, "uat": True, "principal": PRINCIPAL,
                "merkle_root": merkle["root"], "case_count": len(cases),
                "greens": sum(1 for c in cases if c.verdict == "GREEN"),
                "holds": [c.cid for c in cases if c.verdict == "HOLD"]}
    att_payload = json.dumps(att_body, sort_keys=True).encode("utf-8")
    signature = sign_node_act(KSD, "node", att_payload)
    nk = load_node_key(KSD, "node")
    attestation = {**att_body, "signed_payload": att_payload.hex(), "signature": signature,
                   "signer_fingerprint": nk.fingerprint, "signer_public_hex": nk.public_hex,
                   "verify": "verify_node_act(attestation.signer_public_hex, bytes.fromhex(signed_payload), "
                             "signature) is True — the pack carries the pubkey; no keystore needed. (Also: "
                             "node_fingerprint(signer_public_hex) == signer_fingerprint.)"}

    core = {"manifest": {"version": "phase2-battery/v1", "kernel": KERNEL, "case_count": len(cases),
                         "note": "self-verifies: recompute merkle root over sha256(canon(receipt)) leaves; "
                                 "recompute sha over canon(core); attestation signature is node-D1-signed with uat inside"},
            "receipts": receipts, "merkle_proof": merkle, "attestation": attestation}
    bundle = {**core, "sha": _sha(_canon(core))}
    assert _sha(_canon(core)) == bundle["sha"]
    assert _merkle_root([_sha(_canon(r)) for r in receipts]) == merkle["root"]
    assert verify_node_act(nk.public_hex, att_payload, signature) is True

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "packet.json").write_text(json.dumps(bundle, indent=1, sort_keys=True))
    (OUT / "receipts.json").write_text(json.dumps(receipts, indent=1, sort_keys=True))
    (OUT / "schema_snapshot.yaml").write_text(
        "# Phase 2 battery — observed object shapes per case (real kernel calls)\n" +
        json.dumps({c.cid: c.snapshot for c in cases}, indent=1, sort_keys=True, default=str) + "\n")

    holds = [c for c in cases if c.verdict == "HOLD"]
    if holds:
        (OUT / "obligation.json").write_text(json.dumps(
            [{"case": c.cid, "defect": c.defect, "fix_owed": True} for c in holds], indent=1, sort_keys=True))

    lines = ["Phase 2 BATTERY - iron verdict", "kernel: " + KERNEL,
             "signer fingerprint: " + nk.fingerprint + "  (uat:true inside the signed attestation)",
             "merkle root: %s...  bundle sha: %s...  (self-verifies)" % (merkle["root"][:16], bundle["sha"][:16]), ""]
    for c in cases:
        na = sum(1 for a in c.asserts if a["ok"]); n = len(c.asserts)
        lines.append("  %-6s %-46s %s  (%d/%d asserts)%s" % (
            c.cid, c.title[:46], c.verdict, na, n, ("  DEFECT: " + c.defect if c.verdict == "HOLD" else "")))
    lines += ["", "VERDICT: " + ("GREEN - all %d cases green; merkle self-verifies; attestation node-signed (uat inside)" % len(cases)
                                 if not holds else "HOLD - %d case(s): %s" % (len(holds), ", ".join(c.cid for c in holds)))]
    (OUT / "verdict.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 1 if holds else 0


if __name__ == "__main__":
    sys.exit(main())
