"""
STEGOSAURUS WRECKS - Cryptography Module
AES encryption for steganographic payloads
"""

import os
import hashlib
import secrets
from typing import Tuple, Optional
from dataclasses import dataclass

# Try to import cryptography library, fall back to basic XOR if not available
HAS_CRYPTO = False
try:
    # Pre-check: verify cryptography's native bindings work.
    # Some systems have a broken cryptography install where the Rust
    # bindings crash with a pyo3 panic that Python can't catch.
    import subprocess as _sp
    _probe = _sp.run(
        ['python3', '-c', 'from cryptography.exceptions import InvalidSignature'],
        capture_output=True, timeout=5
    )
    if _probe.returncode == 0:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.backends import default_backend
        HAS_CRYPTO = True
except Exception:
    HAS_CRYPTO = False


@dataclass
class EncryptedPayload:
    """Container for encrypted data with metadata"""
    ciphertext: bytes
    iv: bytes
    salt: bytes
    method: str  # 'aes-256-cbc', 'aes-256-gcm', 'xor'


def derive_key(password: str, salt: bytes, key_length: int = 32) -> bytes:
    """
    Derive encryption key from password using PBKDF2

    Args:
        password: User password
        salt: Random salt (should be stored with ciphertext)
        key_length: Desired key length in bytes (32 for AES-256)

    Returns:
        Derived key bytes
    """
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        iterations=600000,
        dklen=key_length
    )


def generate_salt(length: int = 16) -> bytes:
    """Generate cryptographically secure random salt"""
    return secrets.token_bytes(length)


def generate_iv(length: int = 16) -> bytes:
    """Generate cryptographically secure random IV"""
    return secrets.token_bytes(length)


# ============== AES Encryption (requires cryptography library) ==============

def encrypt_aes_cbc(data: bytes, password: str) -> EncryptedPayload:
    """
    Encrypt data using AES-256-CBC

    Args:
        data: Plaintext bytes
        password: Encryption password

    Returns:
        EncryptedPayload with ciphertext, IV, and salt
    """
    if not HAS_CRYPTO:
        raise RuntimeError("cryptography library not installed. Install with: pip install cryptography")

    salt = generate_salt()
    iv = generate_iv()
    key = derive_key(password, salt)

    # Pad data to block size
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()

    # Encrypt
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    return EncryptedPayload(
        ciphertext=ciphertext,
        iv=iv,
        salt=salt,
        method='aes-256-cbc'
    )


def decrypt_aes_cbc(payload: EncryptedPayload, password: str) -> bytes:
    """
    Decrypt AES-256-CBC encrypted data

    Args:
        payload: EncryptedPayload from encrypt_aes_cbc
        password: Decryption password

    Returns:
        Decrypted plaintext bytes
    """
    if not HAS_CRYPTO:
        raise RuntimeError("cryptography library not installed. Install with: pip install cryptography")

    key = derive_key(password, payload.salt)

    # Decrypt
    cipher = Cipher(algorithms.AES(key), modes.CBC(payload.iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(payload.ciphertext) + decryptor.finalize()

    # Unpad
    unpadder = padding.PKCS7(128).unpadder()
    data = unpadder.update(padded_data) + unpadder.finalize()

    return data


def encrypt_aes_gcm(data: bytes, password: str) -> EncryptedPayload:
    """
    Encrypt data using AES-256-GCM (authenticated encryption)

    Args:
        data: Plaintext bytes
        password: Encryption password

    Returns:
        EncryptedPayload with ciphertext (includes auth tag), IV, and salt
    """
    if not HAS_CRYPTO:
        raise RuntimeError("cryptography library not installed. Install with: pip install cryptography")

    salt = generate_salt()
    iv = generate_iv(12)  # GCM uses 12-byte IV
    key = derive_key(password, salt)

    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(data) + encryptor.finalize()

    # Append auth tag to ciphertext
    ciphertext_with_tag = ciphertext + encryptor.tag

    return EncryptedPayload(
        ciphertext=ciphertext_with_tag,
        iv=iv,
        salt=salt,
        method='aes-256-gcm'
    )


def decrypt_aes_gcm(payload: EncryptedPayload, password: str) -> bytes:
    """
    Decrypt AES-256-GCM encrypted data

    Args:
        payload: EncryptedPayload from encrypt_aes_gcm
        password: Decryption password

    Returns:
        Decrypted plaintext bytes
    """
    if not HAS_CRYPTO:
        raise RuntimeError("cryptography library not installed. Install with: pip install cryptography")

    key = derive_key(password, payload.salt)

    # Extract auth tag (last 16 bytes)
    ciphertext = payload.ciphertext[:-16]
    tag = payload.ciphertext[-16:]

    cipher = Cipher(algorithms.AES(key), modes.GCM(payload.iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    data = decryptor.update(ciphertext) + decryptor.finalize()

    return data


# ============== XOR Encryption (fallback, no dependencies) ==============

def encrypt_xor(data: bytes, password: str) -> EncryptedPayload:
    """
    Simple XOR encryption (fallback when cryptography not available)
    NOT CRYPTOGRAPHICALLY SECURE - use only as fallback

    Args:
        data: Plaintext bytes
        password: Encryption password

    Returns:
        EncryptedPayload with XOR'd ciphertext
    """
    salt = generate_salt()
    key = derive_key(password, salt, key_length=len(data))

    # Extend key to match data length using key derivation
    extended_key = b''
    counter = 0
    while len(extended_key) < len(data):
        extended_key += hashlib.sha256(key + counter.to_bytes(4, 'big')).digest()
        counter += 1
    extended_key = extended_key[:len(data)]

    ciphertext = bytes(a ^ b for a, b in zip(data, extended_key))

    return EncryptedPayload(
        ciphertext=ciphertext,
        iv=b'',  # XOR doesn't use IV
        salt=salt,
        method='xor'
    )


def decrypt_xor(payload: EncryptedPayload, password: str) -> bytes:
    """
    Decrypt XOR encrypted data

    Args:
        payload: EncryptedPayload from encrypt_xor
        password: Decryption password

    Returns:
        Decrypted plaintext bytes
    """
    key = derive_key(password, payload.salt, key_length=len(payload.ciphertext))

    # Extend key to match data length
    extended_key = b''
    counter = 0
    while len(extended_key) < len(payload.ciphertext):
        extended_key += hashlib.sha256(key + counter.to_bytes(4, 'big')).digest()
        counter += 1
    extended_key = extended_key[:len(payload.ciphertext)]

    plaintext = bytes(a ^ b for a, b in zip(payload.ciphertext, extended_key))
    return plaintext


# ============== Unified Interface ==============

def encrypt(data: bytes, password: str, method: str = 'auto') -> bytes:
    """
    Encrypt data with specified method

    Args:
        data: Plaintext bytes
        password: Encryption password
        method: 'aes-cbc', 'aes-gcm', 'xor', or 'auto'

    Returns:
        Packed encrypted payload (can be embedded directly)
    """
    if method == 'auto':
        method = 'aes-gcm' if HAS_CRYPTO else 'xor'

    if method == 'aes-cbc':
        payload = encrypt_aes_cbc(data, password)
    elif method == 'aes-gcm':
        payload = encrypt_aes_gcm(data, password)
    elif method == 'xor':
        payload = encrypt_xor(data, password)
    else:
        raise ValueError(f"Unknown encryption method: {method}")

    return pack_payload(payload)


def decrypt(packed_data: bytes, password: str) -> bytes:
    """
    Decrypt packed encrypted payload

    Args:
        packed_data: Packed payload from encrypt()
        password: Decryption password

    Returns:
        Decrypted plaintext bytes
    """
    payload = unpack_payload(packed_data)

    if payload.method == 'aes-256-cbc':
        return decrypt_aes_cbc(payload, password)
    elif payload.method == 'aes-256-gcm':
        return decrypt_aes_gcm(payload, password)
    elif payload.method == 'xor':
        return decrypt_xor(payload, password)
    else:
        raise ValueError(f"Unknown encryption method: {payload.method}")


def pack_payload(payload: EncryptedPayload) -> bytes:
    """
    Pack EncryptedPayload into bytes for embedding

    Format:
    [1 byte: method ID][1 byte: salt len][salt][1 byte: iv len][iv][ciphertext]
    """
    method_ids = {'aes-256-cbc': 1, 'aes-256-gcm': 2, 'xor': 3}
    method_id = method_ids.get(payload.method, 0)

    packed = bytes([method_id])
    packed += bytes([len(payload.salt)]) + payload.salt
    packed += bytes([len(payload.iv)]) + payload.iv
    packed += payload.ciphertext

    return packed


def unpack_payload(data: bytes) -> EncryptedPayload:
    """
    Unpack bytes into EncryptedPayload

    Args:
        data: Packed payload bytes

    Returns:
        EncryptedPayload object
    """
    method_names = {1: 'aes-256-cbc', 2: 'aes-256-gcm', 3: 'xor'}

    idx = 0
    method_id = data[idx]
    method = method_names.get(method_id, 'unknown')
    idx += 1

    salt_len = data[idx]
    idx += 1
    salt = data[idx:idx + salt_len]
    idx += salt_len

    iv_len = data[idx]
    idx += 1
    iv = data[idx:idx + iv_len]
    idx += iv_len

    ciphertext = data[idx:]

    return EncryptedPayload(
        ciphertext=ciphertext,
        iv=iv,
        salt=salt,
        method=method
    )


def get_available_methods() -> list:
    """Get list of available encryption methods"""
    methods = ['xor']  # Always available
    if HAS_CRYPTO:
        methods = ['aes-gcm', 'aes-cbc'] + methods
    return methods


def crypto_status() -> dict:
    """Get cryptography library status"""
    return {
        "cryptography_available": HAS_CRYPTO,
        "available_methods": get_available_methods(),
        "recommended": 'aes-gcm' if HAS_CRYPTO else 'xor'
    }
