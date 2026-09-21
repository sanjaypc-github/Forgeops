import hmac
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select

from forgeops.db.models import AuthSession, User, Workspace, utcnow
from forgeops.security.tokens import hash_token

SESSION_COOKIE = "forgeops_session"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    email: str
    workspace_id: str
    workspace_name: str
    csrf_token: str
    session_id: str


async def current_user(request: Request) -> CurrentUser:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required")
    # Short-lived DB session so long-running responses (SSE) do not hold a connection.
    async with request.app.state.session_factory() as session:
        row = await session.execute(
            select(AuthSession, User, Workspace)
            .join(User, User.id == AuthSession.user_id)
            .join(Workspace, Workspace.id == AuthSession.workspace_id)
            .where(AuthSession.id == hash_token(token))
        )
        found = row.first()
    if found is None or found.AuthSession.expires_at <= utcnow():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required")
    auth, user, workspace = found
    return CurrentUser(
        user_id=user.id,
        email=user.email,
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        csrf_token=auth.csrf_token,
        session_id=auth.id,
    )


async def require_csrf(
    request: Request, user: CurrentUser = Depends(current_user)
) -> CurrentUser:
    if request.method in UNSAFE_METHODS:
        sent = request.headers.get("x-csrf-token", "")
        if not hmac.compare_digest(sent, user.csrf_token):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing or invalid CSRF token")
    return user
