from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class Base(DeclarativeBase):
    pass


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ws"))
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("usr"))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mem"))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256 of the cookie token
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    csrf_token: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("inv"))
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str] = mapped_column(Text)
    service_id: Mapped[str | None] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(20), default="web")
    status: Mapped[str] = mapped_column(String(30), default="queued")
    created_by: Mapped[str | None] = mapped_column(String(40))
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("investigation_id", "seq"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[str] = mapped_column(String(40))
    seq: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(50))
    agent: Mapped[str | None] = mapped_column(String(40))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Connection(Base):
    """A connector the workspace has connected. Secrets are Fernet-encrypted JSON."""

    __tablename__ = "connections"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("con"))
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(120))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    secret_encrypted: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="connected")
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("msg"))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))  # "user" | "supervisor"
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("aud"))
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    actor: Mapped[str] = mapped_column(String(200))
    channel: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(100))
    target: Mapped[str | None] = mapped_column(String(300))
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
