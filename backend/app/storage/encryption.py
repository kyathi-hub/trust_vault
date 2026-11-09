"""
Envelope encryption for document storage.

Design:
- Each document version gets a unique 256-bit Data Encryption Key (DEK)
- The DEK is encrypted with the master Key Encryption Key (KEK) from config
- Files are encrypted with AES-256-GCM: authenticated, confidential, tamper-evident
- Nonce: 96-bit random per encryption operation (stored with ciphertext)
- Wire format: base64(nonce[12] + ciphertext + tag[16])
- KEK is base64-encoded 32 bytes from environment — never stored in DB or object store
- KEK version is stored with each DEK record to support rotation

Key rotation:
- Increment encryption_kek_version in config and provide new KEK
- Re-encrypt DEKs using rotate_dek() (migration script, not auto-applied)
- Old documents remain accessible while their DEKs are re-encrypted in background

Security notes:
- We never invent our own crypto — we use the Python cryptography library
- AES-GCM provides authenticated encryption — tampering is detected on decrypt
- Nonce uniqueness is critical: we use random 96-bit nonces, not counters
  (counter nonces require careful state management; random nonces are safe at this scale)
"""

import base64
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings

NONCE_SIZE = 12   # 96 bits — recommended for AES-GCM
KEY_SIZE = 32     # 256 bits
TAG_SIZE = 16     # 128-bit authentication tag (appended by AESGCM automatically)


def _get_kek() -> bytes:
    """Decode the master KEK from settings. Called at operation time, not module load."""
    settings = get_settings()
    return base64.b64decode(settings.encryption_kek)


def generate_dek() -> bytes:
    """Generate a new random 256-bit Data Encryption Key."""
    return secrets.token_bytes(KEY_SIZE)


def encrypt_dek(dek: bytes) -> str:
    """
    Encrypt a DEK with the master KEK.
    Returns base64(nonce + ciphertext+tag) — stored in document_versions.encrypted_dek.
    """
    kek = _get_kek()
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(kek)
    ciphertext_with_tag = aesgcm.encrypt(nonce, dek, None)
    return base64.b64encode(nonce + ciphertext_with_tag).decode("utf-8")


def decrypt_dek(encrypted_dek: str) -> bytes:
    """
    Decrypt an encrypted DEK using the master KEK.
    Raises ValueError if decryption fails (tampering or wrong KEK).
    """
    kek = _get_kek()
    raw = base64.b64decode(encrypted_dek)
    nonce = raw[:NONCE_SIZE]
    ciphertext_with_tag = raw[NONCE_SIZE:]
    aesgcm = AESGCM(kek)
    try:
        return aesgcm.decrypt(nonce, ciphertext_with_tag, None)
    except Exception as exc:
        raise ValueError("DEK decryption failed — wrong KEK or tampered data") from exc


def encrypt_data(plaintext: bytes, dek: bytes) -> bytes:
    """
    Encrypt data with the DEK using AES-256-GCM.
    Returns nonce + ciphertext+tag as bytes.
    """
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(dek)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext_with_tag


def decrypt_data(ciphertext: bytes, dek: bytes) -> bytes:
    """
    Decrypt data with the DEK using AES-256-GCM.
    Raises ValueError if authentication fails (data tampering detected).
    """
    nonce = ciphertext[:NONCE_SIZE]
    ct_with_tag = ciphertext[NONCE_SIZE:]
    aesgcm = AESGCM(dek)
    try:
        return aesgcm.decrypt(nonce, ct_with_tag, None)
    except Exception as exc:
        raise ValueError("Decryption failed — data may be tampered or DEK is wrong") from exc
