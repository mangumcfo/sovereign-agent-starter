#!/usr/bin/env python3
"""BCK · capability-graph GENERATOR (harvest-only — never hand-authored rows).

Harvests, from the kernel tree at the PINNED tip, one row per HTTP capability:
  route -> verb(s) -> owner-gate -> fences -> test IDs -> series cite -> PRESENT?

Rules (KM · BCK phase 1):
  * No hand-authored rows: every field is derived from the tree (routes, decorators, module fences,
    the test corpus) or from an authoritative in-repo map (the ratified sealed-home table).
  * PRESENT is TRUE only when at least one test in tests/ references the route path (present-with-test-IDs).
  * Counts re-derive: run `python3 bck/compose_graph_generator.py` on any checkout of the pinned tip.
  * The machine graph carries NO platform≈series maps — sealed homes only; platform framing = ADR appendix.
Usage: python3 bck/compose_graph_generator.py            -> writes bck/compose_graph.yaml (+ prints pinned tip)
       python3 bck/compose_graph_generator.py --check    -> CI: regenerate + diff; nonzero exit on drift

v0 HARVEST LIMITATIONS (honest, not silent):
  * verbs are detected by literal symbol match in the handler body; a route that reaches a kernel verb through a
    local helper may under-report its verb list (e.g. some /peers/* rows). Fences/gate/tests are unaffected.
  * fences are harvested from the handler body UNION the verb's module; a fence enforced two composition-layers
    down is attributed to the composed floor by name, not re-walked.
  * series_home is the ratified sealed-home table (seal-ledger-grounded), the ONLY non-tree-derived field, and
    carries sealed volumes ONLY — never a platform-clone map (those stay in the ADR appendix, ADR-0001).
"""
from __future__ import annotations
import os, re, subprocess, glob, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # sovereign-agent-starter root
SRC  = os.path.join(ROOT, "src", "sovereign_agent")
ROUTES_DIR = os.path.join(SRC, "node_api", "routes")
TESTS_DIR  = os.path.join(ROOT, "tests")

PINNED_TIP = "c2706ce"   # KM re-pin (BCK phase-1 close) — the shipped kit tip; graph harvested from the tree at this lineage

def observed_tip():
    try: return subprocess.check_output(["git","-C",ROOT,"rev-parse","--short","HEAD"],text=True).strip()
    except Exception: return "UNKNOWN"

def tip(): return PINNED_TIP

# ── authoritative sealed-home map (ratified, seal-ledger-grounded; not per-row invention) ──
# capability-key -> series-qualified sealed home (mirrors GB_CARD_HOMES ratification 2026-08-11).
HOMES = {
 "onboard":   "Inter-Node Sovereignty (Series 6) V6 + Full Production ERP (Series 5) V16",
 "gate":      "Inter-Node Sovereignty (Series 6) V6 + Full Production ERP (Series 5) V16",
 "storage":   "Zero-Trust Sovereignty (Series 7) V3",
 "port":      "Inter-Node Sovereignty (Series 6) V7",
 "peers_recognize": "Sovereign Peerhood (Series 14) V2",
 "peers_refuse":    "Sovereign Peerhood (Series 14) V2",
 "peers_clean_exit":"Sovereign Peerhood (Series 14) V5",
 "peers_message":   "Inter-Node Sovereignty (Series 6) V1",
 "peers_verify":    "Full Production ERP (Series 5) V26",
 "relay":     "Inter-Node Sovereignty (Series 6) V7 (adapter surface)",
 "proposals": "Full Production ERP (Series 5) V26",
}
# verb-symbol -> owning module (for the fence lookup); harvested set of kernel verbs to detect in handlers
VERB_MODULES = {
 "request_approval":"compliance.human_approval_gate","record_disposition":"compliance.human_approval_gate",
 "open_crossing":"port.crossing","sanction_crossing":"port.crossing",
 "store_datum":"storage.sovereign_store","retrieve_datum":"storage.sovereign_store",
 "mutual_recognition":"peerhood.recognition","refuse_recognition":"peerhood.recognition","verify_recognition":"peerhood.recognition",
 "clean_exit":"peerhood.clean_exit","exit_green_light":"peerhood.clean_exit",
 "send_message":"messaging.inter_node","receive_from_peer":"messaging.inter_node","validate_received":"federation.node_gov",
 "run_onboard":"onboarding.onboard",
}
def scan_fences(body):
    """Harvest fence signals from any source text (a verb module OR a route handler body)."""
    f=set(re.findall(r'([A-Z_]+_BREACH_FIELDS)\b', body))
    if re.search(r'money[_-]?path', body, re.I): f.add("money_path-OFF")
    if re.search(r'\("value",\s*"amount",\s*"funds",\s*"balance",\s*"held"\)', body): f.add("receipt-value-stripped")
    if re.search(r'deny.by.default', body, re.I): f.add("deny-by-default")
    if re.search(r'require_owner', body): f.add("owner-disposes")
    if re.search(r'record_disposition\(', body) and not re.search(r'simulate_', body): f.add("real-disposition-no-simulate")
    return f

def module_fences(modrel):
    p=os.path.join(SRC, modrel.replace(".","/")+".py")
    if not os.path.exists(p): return set()
    return scan_fences(open(p,encoding="utf-8",errors="replace").read())

def cap_key(path):
    p=path.strip("/")
    if p.startswith("onboard"): return "onboard"
    if p.startswith("storage"): return "storage"
    if p.startswith("port"): return "port"
    if p.startswith("peers/refuse"): return "peers_refuse"
    if p.startswith("peers/clean_exit"): return "peers_clean_exit"
    if p.startswith("peers/recognize"): return "peers_recognize"
    if p.startswith("peers/message"): return "peers_message"
    if p.startswith("peers/verify"): return "peers_verify"
    if p.startswith("relay"): return "relay"
    if p.startswith("proposal"): return "proposals"
    return p.split("/")[0]

# ── harvest test IDs: any test file whose text references the route path ──
def test_ids_for(path):
    hits=[]
    frag=path.split("<")[0].rstrip("/")           # stable prefix, drop path params
    for tf in glob.glob(os.path.join(TESTS_DIR,"test_*.py")):
        body=open(tf,encoding="utf-8",errors="replace").read()
        if frag and frag in body:
            hits.append(os.path.relpath(tf,ROOT))
    return sorted(set(hits))

def harvest():
    rows=[]
    for rf in sorted(glob.glob(os.path.join(ROUTES_DIR,"*.py"))):
        lines=open(rf,encoding="utf-8",errors="replace").read().split("\n")
        for i,l in enumerate(lines):
            m=re.search(r'@bp\.(get|post|put|delete)\("([^"]+)"\)', l)
            if not m: continue
            method, path = m.group(1).upper(), m.group(2)
            # collect decorators + def below
            gate="require_principal"; handler=None; body=[]
            for j in range(i+1, min(i+12,len(lines))):
                if "@require_owner" in lines[j]: gate="require_owner"
                dm=re.match(r'\s*def (\w+)\(', lines[j])
                if dm: handler=dm.group(1); 
                if dm:
                    for k in range(j+1, len(lines)):
                        if re.search(r'@bp\.(get|post|put|delete)\(', lines[k]): break
                        body.append(lines[k])
                    break
            btxt="\n".join(body)
            verbs=sorted({v for v in VERB_MODULES if re.search(rf'\b{v}\b', btxt)})
            fences=set(scan_fences(btxt))
            for v in verbs: fences |= module_fences(VERB_MODULES[v])
            fences=sorted(fences)
            tids=test_ids_for(path)
            ck=cap_key(path)
            rows.append({
                "capability": f"{method} /api/v1{path}" if not path.startswith("/api") else f"{method} {path}",
                "route_file": os.path.relpath(rf,ROOT), "handler": handler,
                "verbs": verbs, "owner_gate": gate,
                "fences": fences, "test_files": tids,
                "series_home": HOMES.get(ck, "UNMAPPED — ADR review"),
                "present": bool(tids),        # PRESENT only with test coverage
            })
    return rows

def main():
    T=tip()
    rows=harvest()
    present=[r for r in rows if r["present"]]
    out={"meta":{"kit":"BCK","pinned_tip":PINNED_TIP,"observed_tip":observed_tip(),"home":"sovereign-agent-starter","generated_by":"bck/compose_graph_generator.py (harvest-only)",
                 "rule":"PRESENT iff a test references the route; no hand-authored rows; sealed homes only (platform maps = ADR appendix)",
                 "counts":{"routes":len(rows),"present_with_tests":len(present),"owner_gated":sum(1 for r in rows if r['owner_gate']=='require_owner')}},
         "capabilities":rows}
    import yaml
    yaml.safe_dump(out, open(os.path.join(os.path.dirname(__file__),"compose_graph.yaml"),"w"), sort_keys=False, width=200, allow_unicode=True)
    print(f"PINNED TIP: {T}")
    print(f"harvested {len(rows)} routes · {len(present)} PRESENT-with-tests · {out['meta']['counts']['owner_gated']} owner-gated")

def ci_check():
    """CI: regenerate in-memory and diff against the committed compose_graph.yaml. Nonzero exit on drift."""
    import yaml, io
    committed=open(os.path.join(os.path.dirname(__file__),"compose_graph.yaml")).read()
    rows=harvest(); T=tip()
    fresh={"meta":{"kit":"BCK","pinned_tip":PINNED_TIP,"observed_tip":observed_tip(),"home":"sovereign-agent-starter","generated_by":"bck/compose_graph_generator.py (harvest-only)",
                 "rule":"PRESENT iff a test references the route; no hand-authored rows; sealed homes only (platform maps = ADR appendix)",
                 "counts":{"routes":len(rows),"present_with_tests":sum(1 for r in rows if r['present']),"owner_gated":sum(1 for r in rows if r['owner_gate']=='require_owner')}},
           "capabilities":rows}
    buf=io.StringIO(); yaml.safe_dump(fresh,buf,sort_keys=False,width=200,allow_unicode=True)
    if buf.getvalue()!=committed:
        print("BCK-GRAPH-DRIFT: committed compose_graph.yaml != regenerated at tip",T); raise SystemExit(1)
    print("BCK graph re-derives clean at tip",T); raise SystemExit(0)

if __name__=="__main__":
    import sys
    ci_check() if "--check" in sys.argv else main()
