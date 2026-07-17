"""
utils/crypto.py
AES-128 (Fernet) encryption helpers for securing profile zip files.
Key is derived per-user and per-profile from SHA-256.
"""
import hashlib
import base64
from cryptography.fernet import Fernet


def get_profile_key(user_id: str, profile_name: str) -> bytes:
    """Derive a deterministic Fernet-compatible 32-byte key."""
    raw = hashlib.sha256(
        f"{user_id}_{profile_name}_anv_secure_salt_2026".encode()
    ).digest()
    return base64.urlsafe_b64encode(raw)


def encrypt_file(file_path: str, key: bytes) -> None:
    """Encrypt *file_path* in-place using Fernet (AES-128-CBC + HMAC)."""
    with open(file_path, "rb") as f:
        data = f.read()
    encrypted = Fernet(key).encrypt(data)
    with open(file_path, "wb") as f:
        f.write(encrypted)


def decrypt_file(file_path: str, key: bytes) -> None:
    """Decrypt *file_path* in-place using Fernet."""
    with open(file_path, "rb") as f:
        data = f.read()
    decrypted = Fernet(key).decrypt(data)
    with open(file_path, "wb") as f:
        f.write(decrypted)
