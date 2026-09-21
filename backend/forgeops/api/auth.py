from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import delete, select

from forgeops.api.deps import SESSION_COOKIE, CurrentUser, current_user, require_csrf
from forgeops.db.models import AuditLog, AuthSession, Membership, User, Workspace, utcnow
from forgeops.security.passwords import verify_password
from forgeops.security.tokens import hash_token, new_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str


class WorkspaceOut(BaseModel):
    id: str
    name: str


class MeOut(BaseModel):
    user: UserOut
    workspace: WorkspaceOut
    csrf_token: str


@router.post("/login", response_model=MeOut)
async def login(body: LoginIn, request: Request, response: Response) -> MeOut:
    settings = request.app.state.settings
    limiter = request.app.state.login_limiter
    email = body.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    key = f"{email}|{client_ip}"
    if limiter.is_blocked(key):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Too many failed attempts. Try again in 5 minutes"
        )

    async with request.app.state.session_factory() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if user is None or not verify_password(user.password_hash, body.password):
            limiter.record_failure(key)
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect")
        limiter.reset(key)

        membership = await session.scalar(select(Membership).where(Membership.user_id == user.id))
        workspace = await session.get(Workspace, membership.workspace_id)
        token = new_token()
        csrf = new_token()
        session.add(
            AuthSession(
                id=hash_token(token),
                user_id=user.id,
                workspace_id=workspace.id,
                csrf_token=csrf,
                expires_at=utcnow() + timedelta(hours=settings.session_ttl_hours),
            )
        )
        session.add(
            AuditLog(workspace_id=workspace.id, actor=user.email, channel="web", action="auth.login")
        )
        await session.commit()

    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )
    return MeOut(
        user=UserOut(id=user.id, email=user.email),
        workspace=WorkspaceOut(id=workspace.id, name=workspace.name),
        csrf_token=csrf,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request, response: Response, user: CurrentUser = Depends(require_csrf)
) -> Response:
    async with request.app.state.session_factory() as session:
        await session.execute(delete(AuthSession).where(AuthSession.id == user.session_id))
        await session.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser = Depends(current_user)) -> MeOut:
    return MeOut(
        user=UserOut(id=user.user_id, email=user.email),
        workspace=WorkspaceOut(id=user.workspace_id, name=user.workspace_name),
        csrf_token=user.csrf_token,
    )
