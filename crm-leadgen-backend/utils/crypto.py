# Inspired By: common security patterns
# Feature: Password hashing and secure token generation
# Reason: Secure credential handling
# ============================================================

import secrets, hashlib, base64
from typing import Tuple

def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    if salt is None:
        salt = secrets.token_bytes(32)
    iterations = 100000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return salt, dk

def verify_password(password: str, salt: bytes, derived_key: bytes) -> bool:
    _, new_dk = hash_password(password, salt)
    return secrets.compare_digest(new_dk, derived_key)

def generate_secure_token(length: int = 32) -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(length)).decode("ascii")
