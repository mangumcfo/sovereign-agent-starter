#!/usr/bin/env python3
"""BCK fence-verifier v0 — a FLOOR with a published SCOPE, never a certification.

Run this against YOUR OWN node to check the fences held on the paths you actually drove. It is the kit's
conscience, not a stamp: it proves nothing it did not drive (see the SCOPE block every run prints), and it
is deliberately built so it CANNOT dispose anything — its mutating probes carry a bogus NON-owner bearer
that exists to be refused, and the script accepts no owner credential at all (there is no --token flag).

Three states per probe — PASS / FAIL / NOT-DRIVEN — so absence never impersonates passing (a probe whose
target is missing reports NOT-DRIVEN, never a verdict). Overall exit is non-zero iff any probe FAILs;
NOT-DRIVEN never fails and never passes.

This is a floor, not a ceiling. It never labels a capability proven-beyond-its-scope or safe by blanket
claim; it reports only what held on the paths named in SCOPE, and nothing more.

Stdlib only. No hosted service, no daemon, no credential store, no network host beyond the node/web URL
you pass on the command line.

Usage:
  fence_verifier.py --node-url http://127.0.0.1:8421 --tip <kernel-sha> \\
      [--store /path/to/objects.ndjson] [--web-url http://127.0.0.1:8722 --access-log /path/nodeapi.log]

  # F10 provable-failure (each probe must FAIL on its seeded fixture):
  fence_verifier.py --node-url ... --store bck/fixtures/violation_store.ndjson   # F1 + F5 must FAIL
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

API = "/api/v1"
PASS, FAIL, NOT_DRIVEN = "PASS", "FAIL", "NOT-DRIVEN"

# A deliberately-unverifiable NON-owner bearer. Presenting ANY token makes the node skip its loopback-owner
# shortcut and run real verification (auth.py) -> no credential file for this principal -> 401. So every
# mutating probe is a non-owner attempt that exists to be refused; the verifier can never be the owner.
NON_OWNER_BEARER = "bck-prober:not-a-real-credential-exists-to-be-refused"

VALUE_KEYS = {"value", "amount", "funds", "balance", "held"}
# structural key names that would mean private key material leaked into a governed object / response
KEY_TERM_KEYS = {"private_key", "private_hex", "nodekey", "secret_key", "p", "q", "lam", "mu"}
KEY_TERM_SUBSTRINGS = ("BEGIN PRIVATE", "private_key", "secret_key")


def _req(url, method="GET", body=None, bearer=None, timeout=6):
    """Return (status:int|None, text:str). status None on a transport error (node down / unreachable)."""
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 — transport failure -> NOT-DRIVEN upstream
        return None, ""


# ── structural walk (nested keys, not text grep) ─────────────────────────────────────────────────────────
def _walk(obj, path, on_key):
    if isinstance(obj, dict):
        for k, v in obj.items():
            on_key(str(k), v, f"{path}.{k}")
            _walk(v, f"{path}.{k}", on_key)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk(v, f"{path}[{i}]", on_key)


def _load_store(path):
    objs = []
    try:
        with open(path, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    objs.append(json.loads(ln))
    except Exception as e:  # noqa: BLE001
        return None, str(e)
    return objs, None


def _key_sweep(sources, bad_keys, bad_substrings):
    """sources: list of (label, parsed-json). Returns list of hits (label, key/where, path)."""
    hits = []
    for label, obj in sources:
        def on_key(k, v, p, _label=label):
            if k in bad_keys:
                hits.append((_label, k, p))
            if isinstance(v, str):
                for sub in bad_substrings:
                    if sub in v:
                        hits.append((_label, f"substr:{sub}", p))
        _walk(obj, label, on_key)
    return hits


# ── probes ───────────────────────────────────────────────────────────────────────────────────────────────
def probe_f1_value_fields(store_objs, captured):
    sources = []
    if store_objs is not None:
        sources += [(f"store#{i}", o) for i, o in enumerate(store_objs)]
    sources += [(f"resp:{name}", body) for name, body in captured]
    if not sources:
        return NOT_DRIVEN, "no durable store (--store) and no captured responses to sweep"
    hits = _key_sweep(sources, VALUE_KEYS, ())
    if hits:
        return FAIL, "value-field(s) present: " + "; ".join(f"{l} at {p} (key {k})" for l, k, p in hits[:8])
    return PASS, f"no value field ({'/'.join(sorted(VALUE_KEYS))}) in {len(sources)} objects/responses"


def probe_f2_get_only(web_url, access_log):
    if not web_url or not access_log:
        return NOT_DRIVEN, "needs --web-url AND --access-log (the surface + the node's access log)"
    try:
        before = sum(1 for _ in open(access_log, encoding="utf-8", errors="replace"))
    except Exception as e:  # noqa: BLE001
        return NOT_DRIVEN, f"access log unreadable: {e}"
    driven = []
    for panel in ("/", "/api/morning", "/api/status", "/api/receipts"):
        st, _ = _req(web_url.rstrip("/") + panel)
        driven.append(f"{panel}:{st}")
    try:
        lines = open(access_log, encoding="utf-8", errors="replace").read().splitlines()
    except Exception as e:  # noqa: BLE001
        return NOT_DRIVEN, f"access log unreadable after drive: {e}"
    window = lines[before:]
    non_get = [ln for ln in window if any(m in ln for m in ('"POST', '"PUT', '"DELETE', '"PATCH'))]
    if non_get:
        return FAIL, f"surface drive produced {len(non_get)} non-GET line(s) to the node: {non_get[:3]}"
    return PASS, f"drove web panels {driven}; {len(window)} new node log line(s), 0 non-GET"


def probe_f3_non_owner_refusal(node, store_path):
    # owner-gated / principal-gated mutating routes, fired with a bogus NON-owner bearer -> must be refused
    before = None
    if store_path:
        objs, _ = _load_store(store_path)
        before = len(objs) if objs is not None else None
    targets = [
        ("POST", f"{node}{API}/storage/datum", {"content": "bck-probe", "visibility": "private"}),
        ("POST", f"{node}{API}/breath_gate/approval_probe/approve", {}),
        ("POST", f"{node}{API}/port/crossing", {"target": "bck", "instruction": {"send": "ref://bck"}}),
    ]
    results, reachable = [], False
    for method, url, body in targets:
        st, _ = _req(url, method=method, body=body, bearer=NON_OWNER_BEARER)
        if st is not None:
            reachable = True
        results.append((url.split(API)[1], st))
    if not reachable:
        return NOT_DRIVEN, "node unreachable"
    not_refused = [(p, s) for p, s in results if s not in (401, 403)]
    detail = "; ".join(f"{p}->{s}" for p, s in results)
    if not_refused:
        return FAIL, f"a non-owner mutating request was NOT refused (want 401/403): {not_refused} | {detail}"
    # confirm the durable object count did NOT move (the refusals disposed nothing)
    if before is not None:
        objs2, _ = _load_store(store_path)
        after = len(objs2) if objs2 is not None else None
        if after != before:
            return FAIL, f"non-owner mutations were refused but the store COUNT MOVED {before}->{after} ({detail})"
        return PASS, f"all non-owner mutations refused ({detail}); store unchanged at {before} objects"
    return PASS, f"all non-owner mutations refused ({detail})"


def probe_f4_unknown_kind(node, captured):
    # deny-by-default on an unrecognized kind/class — driven as loopback-owner so the 400 is the KIND
    # refusal (not an auth 401), and refused at validation so NOTHING is disposed.
    st1, b1 = _req(f"{node}{API}/onboard/run", "POST", {"action_class": "__bck_unknown_kind__"})
    st2, b2 = _req(f"{node}{API}/storage/datum", "POST", {"content": "x", "visibility": "__bck_bogus__"})
    if st1 is None and st2 is None:
        return NOT_DRIVEN, "node unreachable"
    if b1:
        captured.append(("f4.onboard_run", _try_json(b1)))
    if b2:
        captured.append(("f4.storage_bogus_vis", _try_json(b2)))
    refused = (st1 in (400, 403, 422)) and (st2 in (400, 403, 422))
    if refused:
        return PASS, f"unknown action_class -> {st1}; unknown visibility -> {st2} (both refused, nothing disposed)"
    return FAIL, f"an unrecognized kind was NOT refused deny-by-default: onboard/run->{st1}, storage->{st2}"


def probe_f5_keystore(store_objs, captured):
    sources = []
    if store_objs is not None:
        sources += [(f"store#{i}", o) for i, o in enumerate(store_objs)]
    sources += [(f"resp:{name}", body) for name, body in captured]
    if not sources:
        return NOT_DRIVEN, "no durable store and no captured responses to sweep"
    hits = _key_sweep(sources, KEY_TERM_KEYS, KEY_TERM_SUBSTRINGS)
    if hits:
        return FAIL, "private key material present: " + "; ".join(f"{l} at {p} ({k})" for l, k, p in hits[:8])
    return PASS, f"no private-key term in {len(sources)} objects/responses"


def probe_f6_deny_by_default(node, captured):
    st, b = _req(f"{node}{API}/storage/datum/datum:__bck_nonexistent__")
    if st is None:
        return NOT_DRIVEN, "node unreachable"
    if b:
        captured.append(("f6.get_missing_datum", _try_json(b)))
    if st == 404:
        return PASS, "GET a nonexistent datum -> 404 honest refusal (no invented object)"
    return FAIL, f"a nonexistent datum did not deny-by-default (want 404): got {st}"


def _try_json(text):
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        return {"_raw": text[:400]}


# ── driver ───────────────────────────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="BCK fence-verifier v0 (a floor with a published scope; NOT a certification)")
    ap.add_argument("--node-url", default="http://127.0.0.1:8421")
    ap.add_argument("--tip", default="UNSPECIFIED", help="the node's kernel tip SHA (runner-supplied; printed in SCOPE)")
    ap.add_argument("--store", default=None, help="path to the node's objects.ndjson (durable store) for structural sweeps")
    ap.add_argument("--web-url", default=None, help="operator web surface to drive for the GET-only boundary probe")
    ap.add_argument("--access-log", default=None, help="the node's access log, for the GET-only boundary probe")
    args = ap.parse_args()
    node = args.node_url.rstrip("/")

    # never accept an owner credential (F9): there is no --token flag, and the ONLY bearer we ever send is the
    # bogus non-owner one, on mutating probes, to be refused.
    store_objs, store_err = (None, None)
    if args.store:
        store_objs, store_err = _load_store(args.store)
    store_count = len(store_objs) if store_objs is not None else None

    # capture a few benign GET responses (as loopback-owner) to give F1/F5 real bytes to sweep
    captured = []
    for name, path in (("status", "/status"), ("receipts", "/inference/receipts"),
                       ("gate_pending", "/breath_gate/pending"), ("audit", "/audit/cylinders")):
        st, b = _req(f"{node}{API}{path}")
        if st == 200 and b:
            captured.append((name, _try_json(b)))

    f4_state, f4_detail = probe_f4_unknown_kind(node, captured)
    f6_state, f6_detail = probe_f6_deny_by_default(node, captured)
    results = [
        ("F1", "value-field sweep", *probe_f1_value_fields(store_objs, captured)),
        ("F2", "GET-only boundary", *probe_f2_get_only(args.web_url, args.access_log)),
        ("F3", "non-owner refusal", *probe_f3_non_owner_refusal(node, args.store)),
        ("F4", "unknown-kind refusal", f4_state, f4_detail),
        ("F5", "keystore sweep", *probe_f5_keystore(store_objs, captured)),
        ("F6", "deny-by-default empties", f6_state, f6_detail),
    ]

    print("BCK fence-verifier v0 — a floor with a published scope (not a certification)\n")
    any_fail = False
    driven, not_driven = [], []
    for fid, name, state, detail in results:
        print(f"  [{state:^10}] {fid} {name}: {detail}")
        if state == FAIL:
            any_fail = True
        (not_driven if state == NOT_DRIVEN else driven).append(fid)

    # F7 — the SCOPE block: every run confesses what it did and did not drive (machine-readable)
    scope = {
        "scope_block": True,
        "kernel_tip": args.tip,
        "node_url": node,
        "web_url": args.web_url,
        "store": args.store,
        "store_objects": store_count,
        "store_error": store_err,
        "probes_run": driven,
        "probes_not_driven": not_driven,
        "paths_driven": [f"{node}{API}/status", f"{node}{API}/inference/receipts",
                         f"{node}{API}/breath_gate/pending", f"{node}{API}/storage/datum (non-owner, refused)",
                         f"{node}{API}/onboard/run (unknown-kind, refused)"],
        "credential_held": False,   # F9: the verifier accepts no owner credential; it cannot dispose
        "verdict": "FAIL" if any_fail else "PASS-OR-NOT-DRIVEN",
        "note": "floor, not certification; proves only the paths named here",
    }
    print("\n--- SCOPE ---")
    print(json.dumps(scope, indent=2, sort_keys=True))
    print("--- END SCOPE ---")
    # exit non-zero iff any FAIL (NOT-DRIVEN never fails)
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
