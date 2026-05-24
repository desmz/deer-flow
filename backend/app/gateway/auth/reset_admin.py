"""CLI tool to reset an admin password.

Usage:
    python -m app.gateway.auth.reset_admin
    python -m app.gateway.auth.reset_admin --email admin@example.com

Writes the new password to ``.deer-flow/admin_initial_credentials.txt``
(mode 0600) instead of printing it, so CI / log aggregators never see
the cleartext secret.
"""

from __future__ import annotations

import argparse
import asyncio
import secrets
import sys

from sqlalchemy import select

from app.gateway.auth.credential_file import write_initial_credentials
from app.gateway.auth.password import hash_password
from app.gateway.auth.repositories.sqlite import SQLiteUserRepository
from deerflow.persistence.user.model import UserRow


async def _run(email: str | None) -> int:
    from deerflow.config import get_app_config
    from deerflow.persistence.engine import (
        close_engine,
        get_session_factory,
        init_engine_from_config,
    )

    # [DL-NOTE] Bootstraps the full persistence engine from config.yaml — this CLI
    # runs outside the Gateway process, so it must init the engine itself.
    config = get_app_config()
    await init_engine_from_config(config.database)
    try:
        sf = get_session_factory()
        if sf is None:
            print("Error: persistence engine not available (check config.database).", file=sys.stderr)
            return 1

        repo = SQLiteUserRepository(sf)

        if email:
            user = await repo.get_user_by_email(email)
        else:
            # Find first admin via direct SELECT — repository does not
            # expose a "first admin" helper and we do not want to add
            # one just for this CLI.
            async with sf() as session:
                stmt = select(UserRow).where(UserRow.system_role == "admin").limit(1)
                row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                user = None
            else:
                user = await repo.get_user_by_id(row.id)

        if user is None:
            if email:
                print(f"Error: user '{email}' not found.", file=sys.stderr)
            else:
                print("Error: no admin user found.", file=sys.stderr)
            return 1

        new_password = secrets.token_urlsafe(16)
        user.password_hash = hash_password(new_password)
        # [DL-INSIGHT] token_version += 1 invalidates all existing JWT sessions for this
        # user immediately — any token carrying the old version will be rejected by deps.py.
        user.token_version += 1
        # [DL-NOTE] needs_setup=True forces the setup flow on next login so the operator
        # is prompted to choose a new email + password via the change_password endpoint.
        user.needs_setup = True
        await repo.update_user(user)

        cred_path = write_initial_credentials(user.email, new_password, label="reset")
        print(f"Password reset for: {user.email}")
        print(f"Credentials written to: {cred_path} (mode 0600)")
        print("Next login will require setup (new email + password).")
        return 0
    finally:
        # [DL-NOTE] finally block ensures the DB connection pool is released even if
        # an exception occurs mid-script — avoids leaked connections in the CLI context.
        await close_engine()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset admin password")
    parser.add_argument("--email", help="Admin email (default: first admin found)")
    args = parser.parse_args()

    exit_code = asyncio.run(_run(args.email))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
