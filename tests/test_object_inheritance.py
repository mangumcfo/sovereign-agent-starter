"""S5-05-E8-1 · E8-4: the successor packet verifies offline; unsourced is disclosed."""
from sovereign_agent.objects.inheritance import build_packet, verify_packet
from sovereign_agent.objects.manifest import cut_manifest
from sovereign_agent.objects.registry import ObjectRegistry


def _packet(tmp_path):
    reg = ObjectRegistry(str(tmp_path))
    for i in range(5):
        payload = {"desc": f"item {i}"}
        if i >= 3:
            payload["unsourced"] = True  # migration left 2 without paper
        reg.append(f"part:P-{i}", payload, author="d.reyes",
                   source_ref=f"MIG-{i}:cutover", at="2029-09-01", mandate="operating")
    return build_packet(reg, cut_manifest(reg, at="2029-09-30", period_end=True))


def test_packet_verifies_offline_from_root_and_object_list(tmp_path):
    import json
    packet = _packet(tmp_path)
    # simulate the successor's machine: only the packet's own bytes, no store
    carried = json.loads(json.dumps(packet))
    ok, fails = verify_packet(carried)
    assert ok, fails
    carried["objects"][2]["payload"]["desc"] = "altered"
    ok, fails = verify_packet(carried)
    assert not ok and any("root" in f or "packet_hash" in f for f in fails)


def test_unsourced_objects_are_disclosed_in_packet(tmp_path):
    packet = _packet(tmp_path)
    assert packet["unsourced_disclosure"] == ["part:P-3", "part:P-4"]
    stripped = dict(packet, unsourced_disclosure=[])  # try to hide the marks
    ok, fails = verify_packet(stripped)
    assert not ok  # stripping the disclosure is detectable, always
