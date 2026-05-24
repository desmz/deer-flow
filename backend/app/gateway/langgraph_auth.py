"""LangGraph compatibility auth handler — shares JWT logic with Gateway.

The default DeerFlow runtime is embedded in the FastAPI Gateway; scripts and
Docker deployments do not load this module.  It is retained for LangGraph
tooling, Studio, or direct LangGraph Server compatibility through
``langgraph.json``'s ``auth.path``.

When that compatibility path is used, this module reuses the same JWT and CSRF
rules as Gateway so both modes validate sessions consistently.

Two layers:
  1. @auth.authenticate — validates JWT cookie, extracts user_id,
     and enforces CSRF on state-changing methods (POST/PUT/DELETE/PATCH)
  2. @auth.on — returns metadata filter so each user only sees own threads
"""

import secrets

from langgraph_sdk import Auth

from app.gateway.auth.errors import TokenError
from app.gateway.auth.jwt import decode_token
from app.gateway.deps import get_local_provider

# [DL-NOTE] auth is wired via langgraph.json "auth.path" — it only activates in LangGraph Server
# mode (Studio, `langgraph dev`). The default Gateway-embedded deployment never loads this.
auth = Auth()

# Methods that require CSRF validation (state-changing per RFC 7231).
_CSRF_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})


# [DL-WARN] Duplicates the Double Submit Cookie logic from CSRFMiddleware. If the CSRF header
# name, cookie name, or comparison algorithm changes, this function must be updated too.
def _check_csrf(request) -> None:
    """Enforce Double Submit Cookie CSRF check for state-changing requests.

    Mirrors Gateway's CSRFMiddleware logic so that LangGraph routes
    proxied directly by nginx have the same CSRF protection.
    """
    method = getattr(request, "method", "") or ""
    if method.upper() not in _CSRF_METHODS:
        return

    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("x-csrf-token")

    if not cookie_token or not header_token:
        raise Auth.exceptions.HTTPException(
            status_code=403,
            detail="CSRF token missing. Include X-CSRF-Token header.",
        )

    if not secrets.compare_digest(cookie_token, header_token):
        raise Auth.exceptions.HTTPException(
            status_code=403,
            detail="CSRF token mismatch.",
        )


# [DL-INSIGHT] Mirrors deps.get_current_user_from_request exactly (cookie → JWT → DB →
# token_version). Gateway middleware handles this in embedded mode; here it runs inside LangGraph.
@auth.authenticate
async def authenticate(request):
    """Validate the session cookie, decode JWT, and check token_version.

    Same validation chain as Gateway's get_current_user_from_request:
      cookie → decode JWT → DB lookup → token_version match
    Also enforces CSRF on state-changing methods.
    """
    # CSRF check before authentication so forged cross-site requests
    # are rejected early, even if the cookie carries a valid JWT.
    _check_csrf(request)

    token = request.cookies.get("access_token")
    if not token:
        raise Auth.exceptions.HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    payload = decode_token(token)
    if isinstance(payload, TokenError):
        raise Auth.exceptions.HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    user = await get_local_provider().get_user(payload.sub)
    if user is None:
        raise Auth.exceptions.HTTPException(
            status_code=401,
            detail="User not found",
        )
    if user.token_version != payload.ver:
        raise Auth.exceptions.HTTPException(
            status_code=401,
            detail="Token revoked (password changed)",
        )

    # [DL-NOTE] payload.sub (user UUID string) becomes ctx.user.identity in @auth.on callbacks.
    return payload.sub


# [DL-INSIGHT] LangGraph Server equivalent of @require_permission(owner_check=True):
# stamps user_id on writes and injects it as a DB-level filter on reads/deletes.
@auth.on
async def add_owner_filter(ctx: Auth.types.AuthContext, value: dict):
    """Inject user_id metadata on writes; filter by user_id on reads.

    Gateway stores thread ownership as ``metadata.user_id``.
    This handler ensures LangGraph Server enforces the same isolation.
    """
    # On create/update: stamp user_id into metadata
    metadata = value.setdefault("metadata", {})
    metadata["user_id"] = ctx.user.identity

    # Return filter dict — LangGraph applies it to search/read/delete
    return {"user_id": ctx.user.identity}
