import pytest
from cryptography.fernet import Fernet

from forgeops.security.crypto import DecryptionError, SecretBox
from forgeops.security.passwords import hash_password, verify_password
from forgeops.security.rate_limit import LoginLimiter
from forgeops.security.tokens import hash_token, new_token


def test_password_round_trip():
    h = hash_password("s3cret-pass")
    assert h.startswith("$argon2id$")
    assert verify_password(h, "s3cret-pass")
    assert not verify_password(h, "wrong")


def test_verify_password_with_garbage_hash_is_false():
    assert not verify_password("not-a-hash", "anything")


def test_secret_box_round_trip():
    box = SecretBox(Fernet.generate_key().decode())
    token = box.encrypt_json({"token": "ghp_abc", "url": "https://x"})
    assert "ghp_abc" not in token
    assert box.decrypt_json(token) == {"token": "ghp_abc", "url": "https://x"}


def test_secret_box_wrong_key_raises():
    token = SecretBox(Fernet.generate_key().decode()).encrypt_json({"a": 1})
    with pytest.raises(DecryptionError):
        SecretBox(Fernet.generate_key().decode()).decrypt_json(token)


def test_tokens():
    a, b = new_token(), new_token()
    assert a != b and len(a) >= 40
    assert len(hash_token(a)) == 64
    assert hash_token(a) == hash_token(a)


def test_login_limiter_blocks_after_max_and_expires():
    now = [1000.0]
    limiter = LoginLimiter(max_failures=3, window_seconds=60, clock=lambda: now[0])
    for _ in range(3):
        assert not limiter.is_blocked("k")
        limiter.record_failure("k")
    assert limiter.is_blocked("k")
    now[0] += 61
    assert not limiter.is_blocked("k")


def test_login_limiter_reset():
    limiter = LoginLimiter(max_failures=1, window_seconds=60)
    limiter.record_failure("k")
    assert limiter.is_blocked("k")
    limiter.reset("k")
    assert not limiter.is_blocked("k")
