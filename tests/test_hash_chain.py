"""Tests: tamper-evident hash chain"""
import hashlib, json
from backend.routers.consent import _compute_log_hash


def test_genesis_hash_deterministic():
    payload = {"action": "test", "farmer_id": 1, "ts": "2026-01-01T00:00:00"}
    h1 = _compute_log_hash("GENESIS", payload)
    h2 = _compute_log_hash("GENESIS", payload)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_different_payloads_produce_different_hashes():
    p1 = {"action": "grant", "farmer_id": 1}
    p2 = {"action": "revoke", "farmer_id": 1}
    h1 = _compute_log_hash("GENESIS", p1)
    h2 = _compute_log_hash("GENESIS", p2)
    assert h1 != h2


def test_hash_chain_links_correctly():
    """Verify that chain: genesis -> entry1 -> entry2 is consistent."""
    payload1 = {"action": "consent_granted", "farmer_id": 42, "lender_id": 7}
    h1 = _compute_log_hash("GENESIS", payload1)

    payload2 = {"action": "data_accessed", "farmer_id": 42}
    h2 = _compute_log_hash(h1, payload2)

    # Recompute independently — must match
    assert h2 == _compute_log_hash(h1, payload2)
    # Chain must differ from genesis
    assert h2 != h1


def test_tamper_detection():
    """If a log entry's previous_hash is wrong, hash chain breaks."""
    payload = {"action": "grant", "farmer_id": 5}
    real_prev = "GENESIS"
    fake_prev = "TAMPERED"

    real_hash = _compute_log_hash(real_prev, payload)
    fake_hash = _compute_log_hash(fake_prev, payload)
    assert real_hash != fake_hash
