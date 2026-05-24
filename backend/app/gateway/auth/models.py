"""User Pydantic models for authentication."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# [DL-NOTE] datetime.now(UTC) returns a timezone-aware datetime; datetime.utcnow()
# returns a naive one and is deprecated in Python 3.12+.
def _utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(UTC)


class User(BaseModel):
    """Internal user representation."""

    # [DL-INSIGHT] from_attributes=True lets Pydantic construct User from a SQLAlchemy ORM row directly.
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4, description="Primary key")
    email: EmailStr = Field(..., description="Unique email address")
    password_hash: str | None = Field(None, description="bcrypt hash, nullable for OAuth users")
    system_role: Literal["admin", "user"] = Field(default="user")
    created_at: datetime = Field(default_factory=_utc_now)

    # OAuth linkage (optional)
    oauth_provider: str | None = Field(None, description="e.g. 'github', 'google'")
    oauth_id: str | None = Field(None, description="User ID from OAuth provider")

    # Auth lifecycle
    # [DL-NOTE] needs_setup=True is set by reset_admin.py; cleared when the user completes first-login setup.
    needs_setup: bool = Field(default=False, description="True when a reset account must complete setup")
    # [DL-INSIGHT] Stateless JWT invalidation: bump this counter to invalidate all tokens without a blacklist DB.
    token_version: int = Field(default=0, description="Incremented on password change to invalidate old JWTs")


class UserResponse(BaseModel):
    """Response model for user info endpoint."""

    # [DL-NOTE] Deliberately omits password_hash, oauth fields, token_version — safe to expose externally.
    # [DL-NOTE] id is str here (not UUID) — the HTTP response serializes the UUID as a plain string.
    id: str
    email: str
    system_role: Literal["admin", "user"]
    needs_setup: bool = False
