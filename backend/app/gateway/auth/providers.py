"""Auth provider abstraction."""

from abc import ABC, abstractmethod


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""

    # [DL-NOTE] credentials: dict is intentionally untyped — local provider expects
    # {"email", "password"}, an OAuth provider would expect {"code", "state"}, etc.
    @abstractmethod
    async def authenticate(self, credentials: dict) -> "User | None":
        """Authenticate user with given credentials.

        Returns User if authentication succeeds, None otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_user(self, user_id: str) -> "User | None":
        """Retrieve user by ID."""
        raise NotImplementedError


# [DL-INSIGHT] Bottom-of-file import prevents a circular init: __init__.py imports
# local_provider → local_provider imports providers → if providers imported from
# `app.gateway.auth` (the package) at the top, it would re-enter a partially-executed
# __init__.py. Importing from `app.gateway.auth.models` directly bypasses __init__.py.
from app.gateway.auth.models import User  # noqa: E402
