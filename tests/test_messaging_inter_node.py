"""Acceptance tests for Receipted Inter-Node Messaging (s6_01, S6 Vol 1) — a message is a governed, provenance-carrying
object each peer validates independently, composing the sealed object registry + Federation Node Governance. No central
broker, no hub, no relay. Pure / structural (F-1 clean)."""
import pytest

from sovereign_agent.objects.registry import ObjectRegistry
from sovereign_agent.messaging.inter_node import (
    send_message, carry_to_peer, receive_from_peer, MessagingError,
)


def _reg(tmp_path):
    return ObjectRegistry(str(tmp_path))


def test_send_message_registers_a_governed_provenance_carrying_object(tmp_path):
    reg = _reg(tmp_path)
    m = send_message(reg, "m1", {"body": "hello peer"}, mandate="nodeA",
                     author="nodeA", source_ref="msg://nodeA/1", at="2026-08-05")
    assert m["version_hash"]                 # integrity identity (a receipt)
    assert m["author"] == "nodeA"            # provenance author
    assert m["source_ref"] == "msg://nodeA/1"  # provenance source
    assert m["object_id"] == "message:m1"


def test_send_message_refuses_empty_id_or_body(tmp_path):
    reg = _reg(tmp_path)
    with pytest.raises(MessagingError):
        send_message(reg, "", {"body": "x"}, mandate="nodeA", author="nodeA", source_ref="msg://a/1", at="t")
    with pytest.raises(MessagingError):
        send_message(reg, "m1", {}, mandate="nodeA", author="nodeA", source_ref="msg://a/1", at="t")


def test_carry_to_peer_packages_a_self_verifying_packet(tmp_path):
    reg = _reg(tmp_path)
    send_message(reg, "m1", {"body": "hi"}, mandate="nodeA", author="nodeA", source_ref="msg://a/1", at="t")
    pkt = carry_to_peer(reg, at="2026-08-05")
    assert isinstance(pkt, dict) and pkt.get("manifest")   # a self-verifying packet, no hub


def test_receive_from_peer_validates_independently_round_trip(tmp_path):
    reg = _reg(tmp_path)
    send_message(reg, "m1", {"body": "hi"}, mandate="nodeA", author="nodeA", source_ref="msg://a/1", at="t")
    pkt = carry_to_peer(reg, at="2026-08-05")
    res = receive_from_peer(pkt)
    assert res["received"] is True
    assert res["validated_by"] == "self"
    assert res["message_root"] == pkt["manifest"]["root"]


def test_receive_from_peer_refuses_a_tampered_packet(tmp_path):
    reg = _reg(tmp_path)
    send_message(reg, "m1", {"body": "hi"}, mandate="nodeA", author="nodeA", source_ref="msg://a/1", at="t")
    pkt = carry_to_peer(reg, at="2026-08-05")
    pkt["manifest"] = dict(pkt["manifest"]); pkt["manifest"]["root"] = "0" * 64  # tamper the root
    with pytest.raises(MessagingError):
        receive_from_peer(pkt)


def test_receive_from_peer_refuses_empty_packet_or_root_mismatch(tmp_path):
    reg = _reg(tmp_path)
    send_message(reg, "m1", {"body": "hi"}, mandate="nodeA", author="nodeA", source_ref="msg://a/1", at="t")
    pkt = carry_to_peer(reg, at="2026-08-05")
    with pytest.raises(MessagingError):
        receive_from_peer({})
    with pytest.raises(MessagingError):
        receive_from_peer(pkt, expected_root="deadbeef")  # peer expected a different root
