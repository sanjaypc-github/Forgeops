from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forgeops.config import Settings
from forgeops.db.models import Membership, User, Workspace
from forgeops.security.passwords import hash_password


async def ensure_admin(session: AsyncSession, settings: Settings) -> tuple[User, Workspace]:
    """Create the first workspace and admin user if the admin email does not exist yet.

    Never resets an existing user's password.
    """
    email = settings.forgeops_admin_email.strip().lower()
    user = await session.scalar(select(User).where(User.email == email))
    if user is not None:
        membership = await session.scalar(select(Membership).where(Membership.user_id == user.id))
        workspace = await session.get(Workspace, membership.workspace_id)
        return user, workspace

    workspace = Workspace(name=settings.forgeops_workspace_name)
    user = User(
        email=email,
        password_hash=hash_password(settings.forgeops_admin_password.get_secret_value()),
    )
    session.add_all([workspace, user])
    await session.flush()
    session.add(Membership(workspace_id=workspace.id, user_id=user.id, role="admin"))
    await session.commit()
    return user, workspace
