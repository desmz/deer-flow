"""JWT token creation and verification."""

from datetime import UTC, datetime, timedelta

import jwt
from pydantic import BaseModel

from app.gateway.auth.config import get_auth_config
from app.gateway.auth.errors import TokenError


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # user_id
    exp: datetime
    iat: datetime | None = None
    # [DL-INSIGHT] `ver` is the stateless invalidation key: deps.py and langgraph_auth.py
    # reject tokens where payload.ver != user.token_version fetched from the DB.
    ver: int = 0  # token_version — must match User.token_version


def create_access_token(user_id: str, expires_delta: timedelta | None = None, token_version: int = 0) -> str:
    """Create a JWT access token.

    Args:
        user_id: The user's UUID as string
        expires_delta: Optional custom expiry, defaults to 7 days
        token_version: User's current token_version for invalidation

    Returns:
        Encoded JWT string
    """
    config = get_auth_config()
    expiry = expires_delta or timedelta(days=config.token_expiry_days)

    now = datetime.now(UTC)
    payload = {"sub": user_id, "exp": now + expiry, "iat": now, "ver": token_version}
    # [DL-NOTE] HS256 is symmetric — same secret signs and verifies. Correct for a
    # single-server deployment; RS256 (asymmetric) would be needed for distributed verifiers.
    return jwt.encode(payload, config.jwt_secret, algorithm="HS256")


# [DL-INSIGHT] Returns a union instead of raising — the caller must branch on
# isinstance(result, TokenError) before using it. Railway-oriented error handling.
def decode_token(token: str) -> TokenPayload | TokenError:
    """Decode and validate a JWT token.

    Returns:
        TokenPayload if valid, or a specific TokenError variant.
    """
    config = get_auth_config()
    try:
        # [DL-NOTE] jwt.decode validates the `exp` claim automatically and raises
        # ExpiredSignatureError if the token has expired — no manual datetime check needed.
        payload = jwt.decode(token, config.jwt_secret, algorithms=["HS256"])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        return TokenError.EXPIRED
    except jwt.InvalidSignatureError:
        return TokenError.INVALID_SIGNATURE
    # [DL-NOTE] PyJWTError is the base of all JWT exceptions — must be the last catch
    # or it would swallow ExpiredSignatureError and InvalidSignatureError above it.
    except jwt.PyJWTError:
        return TokenError.MALFORMED
