"""Password hashing, token digests and password rules."""

import hashlib
import hmac
import secrets

SCRYPT_N, SCRYPT_R, SCRYPT_P, KEY_LEN = 16384, 8, 1, 64
MIN_PASSWORD = 8
MAX_PASSWORD = 200


def _scrypt(password: str, salt: bytes, length: int) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=length, maxmem=64 * 1024 * 1024)


def hash_password(password: str) -> str:
    """Hash a password as scrypt$salt$hash."""
    salt = secrets.token_bytes(16)
    return f"scrypt${salt.hex()}${_scrypt(password, salt, KEY_LEN).hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    """Check a password against a stored scrypt hash in constant time."""
    parts = str(stored).split("$")
    if len(parts) != 3 or parts[0] != "scrypt" or not parts[1] or not parts[2]:
        return False
    expected = bytes.fromhex(parts[2])
    return hmac.compare_digest(_scrypt(password, bytes.fromhex(parts[1]), len(expected)), expected)


DUMMY_HASH = hash_password(secrets.token_hex(16))
UNUSABLE = "!"


def token_hash(token: str) -> str:
    """Return the sha256 hex digest stored instead of a token."""
    return hashlib.sha256(token.encode()).hexdigest()


def password_problem(password: object) -> str | None:
    """Return a message when a password is not allowed."""
    text = str(password or "")
    if len(text) < MIN_PASSWORD:
        return f"Use a password of at least {MIN_PASSWORD} characters."
    if len(text) > MAX_PASSWORD:
        return f"Use a password of at most {MAX_PASSWORD} characters."
    if text.isdigit() or text.isalpha():
        return "Use a mix of letters and numbers or symbols."
    return None
