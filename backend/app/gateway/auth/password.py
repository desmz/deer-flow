"""Password hashing utilities with versioned hash format.

Hash format: ``$dfv<N>$<bcrypt_hash>`` where ``<N>`` is the version.

- **v1** (legacy): ``bcrypt(password)`` — plain bcrypt, susceptible to
  72-byte silent truncation.
- **v2** (current): ``bcrypt(b64(sha256(password)))`` — SHA-256 pre-hash
  avoids the 72-byte truncation limit so the full password contributes
  to the hash.

Verification auto-detects the version and falls back to v1 for hashes
without a prefix, so existing deployments upgrade transparently on next
login.
"""

import asyncio
import base64
import hashlib

import bcrypt

_CURRENT_VERSION = 2
_PREFIX_V2 = "$dfv2$"
_PREFIX_V1 = "$dfv1$"


# [DL-INSIGHT] bcrypt silently truncates input at 72 bytes — passwords differing only
# after byte 72 would produce the same hash. SHA-256 collapses any-length input to 32
# bytes; base64-encoding produces 44 printable ASCII bytes (safe for bcrypt, within limit).
def _pre_hash_v2(password: str) -> bytes:
    """SHA-256 pre-hash to bypass bcrypt's 72-byte limit."""
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    """Hash a password (current version: v2 — SHA-256 + bcrypt)."""
    raw = bcrypt.hashpw(_pre_hash_v2(password), bcrypt.gensalt()).decode("utf-8")
    return f"{_PREFIX_V2}{raw}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password, auto-detecting the hash version.

    Accepts v2 (``$dfv2$…``), v1 (``$dfv1$…``), and bare bcrypt hashes
    (treated as v1 for backward compatibility with pre-versioning data).
    """
    try:
        if hashed_password.startswith(_PREFIX_V2):
            bcrypt_hash = hashed_password[len(_PREFIX_V2) :]
            return bcrypt.checkpw(_pre_hash_v2(plain_password), bcrypt_hash.encode("utf-8"))

        if hashed_password.startswith(_PREFIX_V1):
            bcrypt_hash = hashed_password[len(_PREFIX_V1) :]
        else:
            # [DL-NOTE] Bare bcrypt hash (no prefix) = legacy pre-versioning data, treated as v1.
            bcrypt_hash = hashed_password

        return bcrypt.checkpw(plain_password.encode("utf-8"), bcrypt_hash.encode("utf-8"))
    except ValueError:
        # [DL-WARN] Fail closed: malformed/corrupt hash returns False instead of raising,
        # preventing a 500 that would leak hash corruption to the caller.
        return False


# [DL-INSIGHT] Transparent migration: local_provider calls needs_rehash() after a
# successful login and silently upgrades v1/bare hashes to v2 in place.
def needs_rehash(hashed_password: str) -> bool:
    """Return True if the hash uses an older version and should be rehashed."""
    return not hashed_password.startswith(_PREFIX_V2)


# [DL-NOTE] bcrypt is CPU-bound (intentionally slow). asyncio.to_thread() offloads it
# to avoid stalling the FastAPI event loop during login/register requests.
async def hash_password_async(password: str) -> str:
    """Hash a password using bcrypt (non-blocking).

    Wraps the blocking bcrypt operation in a thread pool to avoid
    blocking the event loop during password hashing.
    """
    return await asyncio.to_thread(hash_password, password)


async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash (non-blocking).

    Wraps the blocking bcrypt operation in a thread pool to avoid
    blocking the event loop during password verification.
    """
    return await asyncio.to_thread(verify_password, plain_password, hashed_password)
