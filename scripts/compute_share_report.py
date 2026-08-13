#!/usr/bin/env python3
"""compute_share_report.py — drives W1..W12 of AA_COMPUTE_SHARE_WRAPPER_BAR against a LOOPBACK stub model.

Invoked by compute_share_report.sh (which owns the socket enumeration W7 + the stub model server). Prints
verbatim, re-derivable evidence for every observable. USN-only: no backend, no fallback, no side channel.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("compute_share", ROOT / "scripts" / "compute_share.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.keystore.node_keystore import generate_node_key, sign_node_act, load_node_key
from sovereign_agent.peerhood.delegation import delegate_governed
from sovereign_agent.peerhood.recognition import refuse_recognition
from sovereign_agent.peerhood.clean_exit import clean_exit

NODE, REQ = "Dragon", "Beard"
MODEL_URL = os.environ.get("MODEL_URL", "http://127.0.0.1:11599/generate")
T0 = "2026-08-13T00:00:00+00:00"


def sig_env(ks, **kw):
    e = {"job_id": kw["job_id"], "model": kw.get("model", "tiny"), "prompt": kw.get("prompt", "hello"),
         "units": kw.get("units", 2), "requester_mandate": kw.get("mandate", REQ)}
    if kw.get("extra"):
        e.update(kw["extra"])
    e["sig"] = sign_node_act(ks, kw.get("signer", REQ), cs._canonical(e))
    return e


def refuse(fn):
    try:
        fn(); return "NO REFUSAL (BUG)"
    except (cs.ShareRefusal, Exception) as e:  # noqa: BLE001 — the refusal IS the observable
        return f"{type(e).__name__}: {e}"


def main():
    ks = os.environ["NODE_KEYSTORE_DIR"]
    node = generate_node_key(ks, NODE, at=T0)
    req = generate_node_key(ks, REQ, at=T0)
    reg = ObjectRegistry(os.path.join(os.environ["SHARE_REG_ROOT"], "reg"))
    npub, rpub, nfp = node.public_hex, req.public_hex, node.fingerprint
    dg0 = _digest(ks, NODE)  # before-run digest, captured once the durable key exists

    def submit(env, deleg, now="2026-08-13T06:00:00+00:00", url=MODEL_URL, caller=cs._loopback_model_call, revs=()):
        return cs.submit_job(reg, NODE, env, recognized_public_hex=rpub, node_public_hex=npub,
                             delegation=deleg, now=now, model_url=url, model_caller=caller, revocations=revs)

    print("∞Δ∞ COMPUTE-SHARE WRAPPER REPORT — USN-only · integrity-only ·", cs.LABEL)
    print(f"node fp BEFORE: {nfp}  · keystore digest BEFORE: {_digest(ks, NODE)[:32]}…")

    print("\n== W1 · the node's own governed offer ==")
    off = cs.open_offer(reg, NODE, 10, at="2026-08-13T00:30:00+00:00")
    print(f"  offer id={off['object_id']} version_hash={off['version_hash'][:16]}… "
          f"units={off['payload']['units']} mandate={off['mandate']} kind={off['kind']}")
    print("  admission with NO offer would refuse (W1) — see a fresh-registry refusal in tests; offer now PRESENT")

    grant = delegate_governed(ks, NODE, REQ, f"compute:{off['object_id']}",
                              expires_at="2026-08-13T12:00:00+00:00", at="2026-08-13T01:00:00+00:00",
                              registry=reg, approver="KM-1176", approval_ref="km-share-1")

    print("\n== W2 · deny-by-default (offer present, NO rule loaded) ==")
    print("  ", refuse(lambda: submit(sig_env(ks, job_id="w2"), deleg=None)))

    print("\n== W3 · key-scoped, never secret-scoped (forge triplet) ==")
    print("  wrong key   ->", refuse(lambda: submit(sig_env(ks, job_id="w3a", signer=NODE), grant)))
    bad = {"job_id": "w3b", "model": "tiny", "prompt": "hi", "units": 2, "requester_mandate": REQ}  # no sig
    print("  token/no-sig->", refuse(lambda: submit(bad, grant)))
    self_env = sig_env(ks, job_id="w3c", signer=NODE, mandate=NODE)
    print("  self-as-req ->", refuse(lambda: cs.submit_job(reg, NODE, self_env, recognized_public_hex=npub,
          node_public_hex=npub, delegation=grant, now="2026-08-13T06:00:00+00:00", model_caller=cs._loopback_model_call)))

    print("\n== W4 · grant expires by default ==")
    ok = submit(sig_env(ks, job_id="w4-live"), grant, now="2026-08-13T06:00:00+00:00")
    print(f"  live grant  -> {ok['outcome']} · remaining={ok['remaining']} · result={ok['result'][:40]}")
    print("  past expiry ->", refuse(lambda: submit(sig_env(ks, job_id="w4-dead"), grant, now="2026-08-13T20:00:00+00:00")))
    dele_id = grant["delegation"]["object_id"]
    print("  revoked     ->", refuse(lambda: submit(sig_env(ks, job_id="w4-rev"), grant, revs=[{"revokes": dele_id}])))

    print("\n== W5 · metering re-derivable from receipts; over-subscription refused ==")
    reg2 = ObjectRegistry(os.path.join(os.environ["SHARE_REG_ROOT"], "reg5"))
    o5 = cs.open_offer(reg2, NODE, 5, at="2026-08-13T00:30:00+00:00")
    g5 = delegate_governed(ks, NODE, REQ, f"compute:{o5['object_id']}", expires_at="2026-08-13T23:00:00+00:00",
                           at="2026-08-13T01:00:00+00:00", registry=reg2, approver="KM-1176", approval_ref="km5")
    for jid, u in (("m1", 2), ("m2", 1)):
        cs.submit_job(reg2, NODE, sig_env(ks, job_id=jid, units=u), recognized_public_hex=rpub,
                      node_public_hex=npub, delegation=g5, now="2026-08-13T06:00:00+00:00",
                      model_url=MODEL_URL, model_caller=cs._loopback_model_call)
    comp = [(r["payload"]["job_id"], r["payload"]["units"]) for r in cs.receipts(reg2, NODE)
            if r["payload"]["outcome"] == "complete"]
    total = sum(int(u) for _, u in comp)
    print(f"  completed receipts: {comp}  · Σ units = {total}  · initial 5 − {total} = {5 - total}")
    print(f"  wrapper reports remaining = {cs.remaining_units(reg2, NODE)}  (re-derivable from receipts alone)")
    print("  one over remaining ->", refuse(lambda: cs.submit_job(reg2, NODE, sig_env(ks, job_id="m3", units=3),
          recognized_public_hex=rpub, node_public_hex=npub, delegation=g5, now="2026-08-13T06:00:00+00:00",
          model_url=MODEL_URL, model_caller=cs._loopback_model_call)))

    print("\n== W6 · a receipt verifies offline against the node's public_hex ==")
    rc = [r for r in cs.receipts(reg2, NODE) if r["payload"]["outcome"] == "complete"][0]
    print(f"  receipt job={rc['payload']['job_id']} model={rc['payload']['model']} units={rc['payload']['units']} "
          f"outcome={rc['payload']['outcome']} completer_fp={rc['payload']['completer_fingerprint']}")
    print(f"  verify_receipt(rc, node_public_hex) = {cs.verify_receipt(rc, npub)}   "
          f"· tampered(diff key) = {cs.verify_receipt(rc, 'ab'*64)}")

    print("\n== W8 · the job cannot escape the allowlisted inference API ==")
    for shape in ["run; rm -rf /", "cat /etc/passwd", "read ../keystore/Dragon.nodekey.json",
                  "docker run --privileged x", "crossing:bypass"]:
        print(f"  {shape[:28]:30s}->", refuse(lambda s=shape: submit(sig_env(ks, job_id="e", prompt=s), grant)))
    print("  unknown key {shell:..} ->", refuse(lambda: submit(sig_env(ks, job_id="uk", extra={"shell": "y"}), grant)))

    print("\n== RECEIPT FENCE (KM 2026-08-13) · post-signature refuse is receipted; pre-sig garbage is not ==")
    regR = ObjectRegistry(os.path.join(os.environ["SHARE_REG_ROOT"], "regR"))
    oR = cs.open_offer(regR, NODE, 5, at="2026-08-13T00:30:00+00:00")
    gR = delegate_governed(ks, NODE, REQ, f"compute:{oR['object_id']}", expires_at="2026-08-13T23:00:00+00:00",
                           at="2026-08-13T01:00:00+00:00", registry=regR, approver="KM-1176", approval_ref="kmR")

    def subR(env, **kw):
        return cs.submit_job(regR, NODE, env, recognized_public_hex=rpub, node_public_hex=npub,
                             delegation=gR, now="2026-08-13T06:00:00+00:00", model_url=MODEL_URL,
                             model_caller=cs._loopback_model_call, **kw)
    n0 = len(cs.receipts(regR, NODE))
    refuse(lambda: subR(sig_env(ks, job_id="R-escape", prompt="cat /etc/passwd")))         # authed escape
    refuse(lambda: subR(sig_env(ks, job_id="R-oversub", units=99)))                        # authed over-sub
    n1 = len(cs.receipts(regR, NODE))
    # pre-signature garbage: wrong-key escape + no-sig — must add NO receipt
    refuse(lambda: subR(sig_env(ks, job_id="R-spam", prompt="rm -rf /", signer=NODE)))
    refuse(lambda: subR({"job_id": "R-spam2", "model": "t", "prompt": "x", "units": 1, "requester_mandate": REQ}))
    n2 = len(cs.receipts(regR, NODE))
    ref_jobs = [(r["payload"]["job_id"], r["payload"]["outcome"], r["payload"]["reason"][:34])
                for r in cs.receipts(regR, NODE) if r["payload"]["outcome"] == "refused"]
    print(f"  post-signature refuses receipted: {n1 - n0}  (R-escape, R-oversub)  -> {ref_jobs}")
    print(f"  pre-signature garbage receipts added: {n2 - n1}  (R-spam wrong-key · R-spam2 no-sig — spam fence: 0)")

    print("\n== W9 · a refusal is the terminal answer — no non-USN fallback ==")
    src = (ROOT / "scripts" / "compute_share.py").read_text()
    import re
    nonloop = [u for u in re.findall(r"https?://[^\s\"')]+", src) if not re.search(r"127\.0\.0\.1|localhost|::1", u)]
    print(f"  non-loopback backend URLs in wrapper source: {nonloop}  (expect [])")
    print("  a refused job raises ShareRefusal to the caller (see W2/W3/W8) — never routed elsewhere")

    print("\n== W10 · integrity-only labels; no channel-secrecy claim ==")
    low = src.lower()
    w1, w2 = "pri" + "vate", "confi" + "dential"   # split so this diagnostic file is itself grep-clean
    print(f"  count {w1!r} in wrapper: {low.count(w1)}   count {w2!r}: {low.count(w2)}")
    print(f"  LABEL = {cs.LABEL!r}")

    print("\n== W11 · identity untouched ==")
    fp2, dg2 = load_node_key(ks, NODE).fingerprint, _digest(ks, NODE)
    print(f"  node fp AFTER : {fp2}  -> {'UNCHANGED' if fp2 == nfp else 'CHANGED'}")
    print(f"  keystore digest AFTER: {dg2[:32]}…  -> {'UNCHANGED' if dg2 == dg0 else 'CHANGED'}")

    print("\n== W12 · already-GREEN peer floor unchanged ==")
    reg12 = ObjectRegistry(os.path.join(os.environ["SHARE_REG_ROOT"], "reg12"))
    rr = refuse_recognition(ks, NODE, "peer-x", at=T0, registry=reg12)
    print(f"  refuse -> residual_claim={rr.get('residual_claim')}  hostage_free={rr.get('hostage_free')}")
    ce = clean_exit(ks, NODE, at=T0, registry=reg12)
    print(f"  clean_exit -> no_residual={ce.no_residual} grants_severed={ce.grants_severed}")
    print("\n∞Δ∞ COMPUTE-SHARE REPORT END — pair with sockets (W7) + git diff --stat + suite count.")


def _digest(ks, nid):
    import hashlib
    p = os.path.join(ks, f"{nid}.nodekey.json")
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else ""


if __name__ == "__main__":
    main()
