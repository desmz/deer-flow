"""ORM model for the users table.

Lives in the harness persistence package so it is picked up by
``Base.metadata.create_all()`` alongside ``threads_meta``, ``runs``,
``run_events``, and ``feedback``. Using the shared engine means:

- One SQLite/Postgres database, one connection pool
- One schema initialisation codepath
- Consistent async sessions across auth and persistence reads
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from deerflow.persistence.base import Base


class UserRow(Base):
    __tablename__ = "users"

    # [DL-INSIGHT] Boundary inversion: the ORM table lives in the harness (so the shared engine's
    # create_all picks it up), but ALL auth domain logic lives in app/gateway/auth. The app's sqlite
    # repo maps row↔Pydantic User via _row_to_user/_user_to_row — harness owns the storage, app owns
    # the behaviour. Keeps the harness→app import firewall intact (harness never imports app).
    # UUIDs are stored as 36-char strings for cross-backend portability.
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # [DL-NOTE] email is the natural login key (unique+indexed). nullable=False — every account has one.
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    # [DL-NOTE] Nullable because OAuth-only accounts have no password; the local provider sets it,
    # OAuth linkage (below) leaves it NULL.
    password_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # "admin" | "user" — kept as plain string to avoid ALTER TABLE pain
    # when new roles are introduced.
    system_role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # OAuth linkage (optional). A partial unique index enforces one
    # account per (provider, oauth_id) pair, leaving NULL/NULL rows
    # unconstrained so plain password accounts can coexist.
    oauth_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    oauth_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Auth lifecycle flags
    # [DL-NOTE] needs_setup forces a setup/password step on first login (admin- or reset-created accounts).
    needs_setup: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # [DL-INSIGHT] Stateless JWT revocation: token_version is embedded as the "ver" claim (auth/jwt.py),
    # and bumped on password change. Old JWTs carry a stale ver and are rejected — invalidating every
    # outstanding token WITHOUT a server-side session/blocklist. The one mutable-state cost of stateless auth.
    token_version: Mapped[int] = mapped_column(nullable=False, default=0)

    # [DL-INSIGHT] Partial unique index: "one account per (provider, oauth_id)" but the WHERE predicate
    # EXCLUDES NULL/NULL rows, so password-only accounts (both NULL) never collide. This is the *correct*
    # fix for the multiple-NULLs problem — contrast feedback's plain UniqueConstraint, which leans on SQL's
    # NULL-distinctness by accident. Here NULL-exclusion is explicit and intentional.
    # [DL-WARN] sqlite_where is SQLite-only. On PostgreSQL this clause is ignored (use postgresql_where),
    # so the partial predicate silently won't apply — half-NULL oauth rows could behave differently per dialect.
    __table_args__ = (
        Index(
            "idx_users_oauth_identity",
            "oauth_provider",
            "oauth_id",
            unique=True,
            sqlite_where=text("oauth_provider IS NOT NULL AND oauth_id IS NOT NULL"),
        ),
    )
