"""
Encryption unit tests.

Verifies:
- Encrypt/decrypt round-trip works correctly
- Tampering with ciphertext is detected (AES-GCM authentication)
- DEK encrypt/decrypt round-trip works
- Wrong DEK fails to decrypt
"""
import base64
import os
import pytest
from unittest.mock import patch


def _make_test_kek() -> str:
    import secrets
    return base64.b64encode(secrets.token_bytes(32)).decode()


@pytest.fixture(autouse=True)
def patch_kek(monkeypatch):
    """Patch the KEK for all encryption tests."""
    test_kek = _make_test_kek()
    monkeypatch.setenv("ENCRYPTION_KEK", test_kek)
    # Reset lru_cache
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_encrypt_decrypt_roundtrip() -> None:
    from app.storage.encryption import decrypt_data, encrypt_data, generate_dek
    dek = generate_dek()
    plaintext = b"Hello, TrustVault! This is a test document."
    ciphertext = encrypt_data(plaintext, dek)
    assert ciphertext != plaintext
    recovered = decrypt_data(ciphertext, dek)
    assert recovered == plaintext


def test_tampered_ciphertext_detected() -> None:
    """AES-GCM authentication tag must detect any tampering."""
    from app.storage.encryption import decrypt_data, encrypt_data, generate_dek
    dek = generate_dek()
    ciphertext = encrypt_data(b"sensitive content", dek)
    # Flip a byte in the ciphertext (after the nonce)
    tampered = bytearray(ciphertext)
    tampered[15] ^= 0xFF
    with pytest.raises(ValueError, match="Decryption failed"):
        decrypt_data(bytes(tampered), dek)


def test_wrong_dek_fails() -> None:
    from app.storage.encryption import decrypt_data, encrypt_data, generate_dek
    dek1 = generate_dek()
    dek2 = generate_dek()
    ciphertext = encrypt_data(b"secret", dek1)
    with pytest.raises(ValueError):
        decrypt_data(ciphertext, dek2)


def test_dek_encrypt_decrypt_roundtrip() -> None:
    from app.storage.encryption import decrypt_dek, encrypt_dek, generate_dek
    dek = generate_dek()
    encrypted = encrypt_dek(dek)
    recovered = decrypt_dek(encrypted)
    assert recovered == dek


def test_encrypted_dek_is_base64_string() -> None:
    from app.storage.encryption import encrypt_dek, generate_dek
    dek = generate_dek()
    encrypted = encrypt_dek(dek)
    assert isinstance(encrypted, str)
    # Must be valid base64
    decoded = base64.b64decode(encrypted)
    assert len(decoded) > 0


def test_each_encryption_produces_different_ciphertext() -> None:
    """Random nonce means same plaintext + same key produces different ciphertext."""
    from app.storage.encryption import encrypt_data, generate_dek
    dek = generate_dek()
    ct1 = encrypt_data(b"same plaintext", dek)
    ct2 = encrypt_data(b"same plaintext", dek)
    assert ct1 != ct2  # different nonces
