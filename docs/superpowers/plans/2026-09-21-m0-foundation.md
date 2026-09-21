# M0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A running ForgeOps skeleton: Postgres in Docker, FastAPI backend with admin login, workspace-scoped investigations, a persisted event stream over SSE, and a React app where an admin signs in, creates an investigation and sees its real events live.

**Architecture:** Python 3.12 backend (`backend/forgeops`) built as an app factory (`create_app`) with state initialized in `startup()`. SQLAlchemy async models with `workspace_id` on every tenant row; Alembic for schema. An in-process `EventBus` persists every event with a per-investigation sequence number and fans out to SSE subscribers, replaying history by `Last-Event-ID`. React + TypeScript frontend (Vite) talks to `/api` through a dev proxy with a session cookie and CSRF header.

**Tech Stack:** Python 3.12 (uv), FastAPI 0.141, Starlette 1.6, Pydantic 2.13, pydantic-settings 2.15, SQLAlchemy 2.0 (asyncio) + asyncpg, Alembic 1.20, argon2-cffi, cryptography (Fernet), sse-starlette 3.4, structlog; pytest 9 + pytest-asyncio 1.4 + httpx 0.28. React 19, React Router 7, TanStack Query 5, Vite 8, Vitest, Testing Library. PostgreSQL 16.

**Spec:** [docs/TRD.md](../../TRD.md) (sections 1, 2, 4, 6, 7, 8, 9.1, 12, 15, 16, 17-M0) and [docs/PRD.md](../../PRD.md) (US-1, US-7 partial, US-17 partial).

## Global Constraints

- Python `>=3.12,<3.13`, managed with uv; commands run from `backend/` as `uv run …`.
- No mock or fallback data in runtime code. Fakes exist only under `backend/tests/` and `frontend/src/**/*.test.*`.
- Every tenant table has `workspace_id`; every query in API code filters by the current user's workspace.
- Secrets never appear in API responses, logs or events. `.env` is git-ignored.
- IDs are strings `<prefix>_<uuid4 hex>` (`ws_`, `usr_`, `mem_`, `inv_`, `aud_`).
- Event types are exactly the TRD §6.3 list.
- Postgres is exposed on host port `5433` (avoids clashing with a local Postgres on 5432).
- Every commit message ends with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Deviation from TRD M0 list: the Chroma container is added in M1/M5 when it is first used (YAGNI).

## File Structure

```text
.gitignore                                  ignore env, venv, node_modules, caches, build output
.env.example                                documented configuration template
docker-compose.yml                          postgres (+ api in Task 7)
docker/postgres/init/01-test-db.sql         creates forgeops_test database
backend/
  pyproject.toml, .python-version, uv.lock
  Dockerfile, .dockerignore
  alembic.ini, alembic/env.py, alembic/versions/<rev>_initial.py
  forgeops/
    __init__.py
    config.py                 Settings (pydantic-settings), get_settings()
    logging.py                structlog configuration
    main.py                   create_app(), startup(), shutdown()
    devtools/envfile.py       fill .env from .env.example, generating secrets
    security/passwords.py     argon2 hash/verify
    security/crypto.py        SecretBox (Fernet JSON encrypt/decrypt)
    security/tokens.py        session token generation + hashing
    security/rate_limit.py    LoginLimiter
    db/models.py              Base + Workspace, User, Membership, AuthSession, Investigation, Event, AuditLog
    db/session.py             create_engine_and_factory()
    services/bootstrap.py     ensure_admin()
    events/models.py          EventType, TERMINAL_EVENTS, EventIn, EventOut
    events/bus.py             EventBus (emit, history, is_terminal, subscribe, stream)
    api/deps.py               CurrentUser, current_user, require_csrf
    api/health.py             GET /api/health
    api/auth.py               POST /api/auth/login, POST /api/auth/logout, GET /api/auth/me
    api/investigations.py     POST/GET /api/investigations, GET /{id}, GET /{id}/events (SSE)
  tests/
    conftest.py, test_envfile.py, test_security.py, test_health.py,
    test_auth.py, test_event_bus.py, test_investigations_api.py
frontend/
  package.json, vite.config.ts, index.html, tsconfig*.json (from scaffold)
  src/
    main.tsx, app/App.tsx
    styles/tokens.css, styles/global.css
    api/types.ts, api/client.ts, api/auth.ts, api/investigations.ts
    auth/AuthProvider.tsx
    components/Layout.tsx
    pages/LoginPage.tsx, pages/InvestigationsPage.tsx, pages/InvestigationPage.tsx
    investigations/eventStream.ts
    test/setup.ts
    pages/LoginPage.test.tsx, investigations/eventStream.test.ts
```

---

### Task 1: Repository tooling, env file generator, Postgres

**Files:**
- Create: `.gitignore`, `.env.example`, `docker-compose.yml`, `docker/postgres/init/01-test-db.sql`
- Create: `backend/pyproject.toml`, `backend/.python-version`, `backend/forgeops/__init__.py`, `backend/forgeops/devtools/__init__.py`, `backend/forgeops/devtools/envfile.py`
- Test: `backend/tests/test_envfile.py`

**Interfaces:**
- Produces: `forgeops.devtools.envfile.fill_env(template: str, existing: str = "") -> str`, `parse_env(text: str) -> dict[str, str]`, CLI `uv run python -m forgeops.devtools.envfile` (writes repo-root `.env`).
- Produces: `.env` keys `FORGEOPS_ENV, FORGEOPS_SECRET_KEY, FORGEOPS_ADMIN_EMAIL, FORGEOPS_ADMIN_PASSWORD, FORGEOPS_WORKSPACE_NAME, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT, DATABASE_URL`.

- [ ] **Step 1: Create repo-level files**

`.gitignore`:
```gitignore
# env and secrets
.env
.env.*
!.env.example

# python
__pycache__/
*.pyc
.venv/
.pytest_cache/
.ruff_cache/

# node
node_modules/
dist/
coverage/

# editors / OS
.vscode/
.idea/
.DS_Store
Thumbs.db
```

`.env.example`:
```dotenv
# ForgeOps configuration.
# Create your .env with:  cd backend && uv run python -m forgeops.devtools.envfile
# Empty secrets below are generated automatically. Never commit .env.

FORGEOPS_ENV=development
FORGEOPS_SECRET_KEY=
FORGEOPS_ADMIN_EMAIL=admin@forgeops.local
FORGEOPS_ADMIN_PASSWORD=
FORGEOPS_WORKSPACE_NAME=My workspace

POSTGRES_USER=forgeops
POSTGRES_PASSWORD=
POSTGRES_DB=forgeops
POSTGRES_PORT=5433
DATABASE_URL=
```

`docker/postgres/init/01-test-db.sql`:
```sql
CREATE DATABASE forgeops_test;
```

`docker-compose.yml`:
```yaml
name: forgeops

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "127.0.0.1:${POSTGRES_PORT:-5433}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./docker/postgres/init:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 3s
      retries: 20

volumes:
  pgdata:
```

- [ ] **Step 2: Create the backend project**

`backend/.python-version`:
```text
3.12
```

`backend/pyproject.toml`:
```toml
[project]
name = "forgeops"
version = "0.1.0"
description = "ForgeOps incident investigation platform"
requires-python = ">=3.12,<3.13"
dependencies = [
    "fastapi>=0.141",
    "uvicorn[standard]>=0.53",
    "pydantic>=2.13",
    "pydantic-settings>=2.15",
    "sqlalchemy[asyncio]>=2.0.54",
    "asyncpg>=0.31",
    "alembic>=1.20",
    "argon2-cffi>=25.1",
    "cryptography>=50",
    "sse-starlette>=3.4",
    "structlog>=26.1",
]

[dependency-groups]
dev = [
    "pytest>=9.1",
    "pytest-asyncio>=1.4",
    "httpx>=0.28",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["forgeops"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

`backend/forgeops/__init__.py` and `backend/forgeops/devtools/__init__.py`: empty files.

Run: `cd backend && uv sync`
Expected: creates `.venv` with Python 3.12 and writes `uv.lock`.

- [ ] **Step 3: Write the failing test**

`backend/tests/test_envfile.py`:
```python
from cryptography.fernet import Fernet

from forgeops.devtools.envfile import fill_env, parse_env

TEMPLATE = """# comment line
FORGEOPS_ENV=development
FORGEOPS_SECRET_KEY=
FORGEOPS_ADMIN_EMAIL=admin@forgeops.local
FORGEOPS_ADMIN_PASSWORD=
POSTGRES_USER=forgeops
POSTGRES_PASSWORD=
POSTGRES_DB=forgeops
POSTGRES_PORT=5433
DATABASE_URL=
"""


def test_generates_missing_secrets():
    values = parse_env(fill_env(TEMPLATE))
    Fernet(values["FORGEOPS_SECRET_KEY"].encode())  # raises if not a valid Fernet key
    assert len(values["FORGEOPS_ADMIN_PASSWORD"]) >= 12
    assert len(values["POSTGRES_PASSWORD"]) == 32


def test_derives_database_url_from_postgres_values():
    values = parse_env(fill_env(TEMPLATE))
    assert values["DATABASE_URL"] == (
        f"postgresql+asyncpg://forgeops:{values['POSTGRES_PASSWORD']}@localhost:5433/forgeops"
    )


def test_existing_values_win_and_extras_are_kept():
    existing = "POSTGRES_PASSWORD=keepme\nFORGEOPS_ADMIN_EMAIL=me@x.io\nOPENROUTER_API_KEY=abc\n"
    out = fill_env(TEMPLATE, existing)
    values = parse_env(out)
    assert values["POSTGRES_PASSWORD"] == "keepme"
    assert values["FORGEOPS_ADMIN_EMAIL"] == "me@x.io"
    assert values["OPENROUTER_API_KEY"] == "abc"
    assert "keepme@localhost:5433" in values["DATABASE_URL"]


def test_comments_are_preserved():
    assert fill_env(TEMPLATE).startswith("# comment line\n")


def test_parse_env_ignores_blank_and_comment_lines():
    assert parse_env("# x\n\nA=1\nB = two \n") == {"A": "1", "B": "two"}
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_envfile.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'forgeops.devtools.envfile'`

- [ ] **Step 5: Implement**

`backend/forgeops/devtools/envfile.py`:
```python
"""Create or update the repo-root .env from .env.example, generating secrets."""

import base64
import os
import secrets
import sys
from collections.abc import Callable
from pathlib import Path

GENERATORS: dict[str, Callable[[], str]] = {
    "FORGEOPS_SECRET_KEY": lambda: base64.urlsafe_b64encode(os.urandom(32)).decode(),
    "FORGEOPS_ADMIN_PASSWORD": lambda: secrets.token_urlsafe(12),
    "POSTGRES_PASSWORD": lambda: secrets.token_hex(16),
}


def parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def fill_env(template: str, existing: str = "") -> str:
    current = parse_env(existing)
    entries: list[tuple[str | None, str]] = []
    values: dict[str, str] = {}

    for line in template.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            entries.append((None, line))
            continue
        key, default = stripped.split("=", 1)
        key = key.strip()
        value = current.get(key) or default.strip()
        if not value and key in GENERATORS:
            value = GENERATORS[key]()
        values[key] = value
        entries.append((key, ""))

    if "DATABASE_URL" in values and not values["DATABASE_URL"]:
        values["DATABASE_URL"] = (
            f"postgresql+asyncpg://{values.get('POSTGRES_USER', 'forgeops')}"
            f":{values.get('POSTGRES_PASSWORD', '')}"
            f"@localhost:{values.get('POSTGRES_PORT', '5433')}"
            f"/{values.get('POSTGRES_DB', 'forgeops')}"
        )

    lines = [raw if key is None else f"{key}={values[key]}" for key, raw in entries]
    extras = [key for key in current if key not in values]
    if extras:
        lines += ["", "# Kept from existing .env"] + [f"{key}={current[key]}" for key in extras]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[0]) if args else Path(__file__).resolve().parents[3]
    template = (root / ".env.example").read_text(encoding="utf-8")
    env_path = root / ".env"
    existing = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    env_path.write_text(fill_env(template, existing), encoding="utf-8")
    print(f"Wrote {env_path}. The admin password is FORGEOPS_ADMIN_PASSWORD in that file.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_envfile.py -v`
Expected: 5 passed

- [ ] **Step 7: Generate .env and start Postgres**

Run: `cd backend && uv run python -m forgeops.devtools.envfile`
Expected: `Wrote …\Forgeops\.env …`

Run (repo root, Docker Desktop running): `docker compose up -d postgres` then `docker compose ps`
Expected: `postgres` shows `healthy`.

Run: `docker compose exec postgres psql -U forgeops -d forgeops -c "\l"`
Expected: list includes `forgeops` and `forgeops_test`.

- [ ] **Step 8: Commit**

```bash
git add .gitignore .env.example docker-compose.yml docker/ backend/pyproject.toml backend/uv.lock backend/.python-version backend/forgeops backend/tests/test_envfile.py
git commit -m "Add backend project, env generator and Postgres compose service" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Security primitives

**Files:**
- Create: `backend/forgeops/security/__init__.py` (empty), `passwords.py`, `crypto.py`, `tokens.py`, `rate_limit.py`
- Test: `backend/tests/test_security.py`

**Interfaces:**
- Produces: `hash_password(password: str) -> str`, `verify_password(password_hash: str, password: str) -> bool`
- Produces: `SecretBox(key: str)` with `encrypt_json(value: dict) -> str`, `decrypt_json(token: str) -> dict`; `DecryptionError`
- Produces: `new_token() -> str`, `hash_token(token: str) -> str` (64-char hex)
- Produces: `LoginLimiter(max_failures=5, window_seconds=300, clock=time.monotonic)` with `is_blocked(key) -> bool`, `record_failure(key)`, `reset(key)`

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_security.py`:
```python
import pytest
from cryptography.fernet import Fernet

from forgeops.security.crypto import DecryptionError, SecretBox
from forgeops.security.passwords import hash_password, verify_password
from forgeops.security.rate_limit import LoginLimiter
from forgeops.security.tokens import hash_token, new_token


def test_password_round_trip():
    h = hash_password("s3cret-pass")
    assert h.startswith("$argon2id$")
    assert verify_password(h, "s3cret-pass")
    assert not verify_password(h, "wrong")


def test_verify_password_with_garbage_hash_is_false():
    assert not verify_password("not-a-hash", "anything")


def test_secret_box_round_trip():
    box = SecretBox(Fernet.generate_key().decode())
    token = box.encrypt_json({"token": "ghp_abc", "url": "https://x"})
    assert "ghp_abc" not in token
    assert box.decrypt_json(token) == {"token": "ghp_abc", "url": "https://x"}


def test_secret_box_wrong_key_raises():
    token = SecretBox(Fernet.generate_key().decode()).encrypt_json({"a": 1})
    with pytest.raises(DecryptionError):
        SecretBox(Fernet.generate_key().decode()).decrypt_json(token)


def test_tokens():
    a, b = new_token(), new_token()
    assert a != b and len(a) >= 40
    assert len(hash_token(a)) == 64
    assert hash_token(a) == hash_token(a)


def test_login_limiter_blocks_after_max_and_expires():
    now = [1000.0]
    limiter = LoginLimiter(max_failures=3, window_seconds=60, clock=lambda: now[0])
    for _ in range(3):
        assert not limiter.is_blocked("k")
        limiter.record_failure("k")
    assert limiter.is_blocked("k")
    now[0] += 61
    assert not limiter.is_blocked("k")


def test_login_limiter_reset():
    limiter = LoginLimiter(max_failures=1, window_seconds=60)
    limiter.record_failure("k")
    assert limiter.is_blocked("k")
    limiter.reset("k")
    assert not limiter.is_blocked("k")
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_security.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'forgeops.security'`

- [ ] **Step 3: Implement**

`backend/forgeops/security/passwords.py`:
```python
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False
```

`backend/forgeops/security/crypto.py`:
```python
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class DecryptionError(Exception):
    """Raised when a stored secret cannot be decrypted with the configured key."""


class SecretBox:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode())

    def encrypt_json(self, value: dict[str, Any]) -> str:
        return self._fernet.encrypt(json.dumps(value).encode()).decode()

    def decrypt_json(self, token: str) -> dict[str, Any]:
        try:
            return json.loads(self._fernet.decrypt(token.encode()))
        except InvalidToken as exc:
            raise DecryptionError(
                "Stored secret cannot be decrypted with the current FORGEOPS_SECRET_KEY"
            ) from exc
```

`backend/forgeops/security/tokens.py`:
```python
import hashlib
import secrets


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
```

`backend/forgeops/security/rate_limit.py`:
```python
import time
from collections import defaultdict, deque
from collections.abc import Callable


class LoginLimiter:
    """In-process failed-login limiter keyed by e.g. "email|ip"."""

    def __init__(
        self,
        max_failures: int = 5,
        window_seconds: float = 300,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max = max_failures
        self._window = window_seconds
        self._clock = clock
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str) -> deque[float]:
        entries = self._failures[key]
        cutoff = self._clock() - self._window
        while entries and entries[0] <= cutoff:
            entries.popleft()
        return entries

    def is_blocked(self, key: str) -> bool:
        return len(self._prune(key)) >= self._max

    def record_failure(self, key: str) -> None:
        self._prune(key).append(self._clock())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && uv run pytest tests/test_security.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add backend/forgeops/security backend/tests/test_security.py
git commit -m "Add password hashing, secret encryption, tokens and login limiter" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Config, database models, app factory, health endpoint, migrations

**Files:**
- Create: `backend/forgeops/config.py`, `logging.py`, `main.py`
- Create: `backend/forgeops/db/__init__.py` (empty), `db/models.py`, `db/session.py`
- Create: `backend/forgeops/api/__init__.py` (empty), `api/health.py`
- Create: `backend/forgeops/events/__init__.py` (empty), `events/models.py`, `events/bus.py` — `main.py` imports `EventBus`, so create both files now with the exact content shown in Task 5 Step 2. Task 5 then adds the event bus tests.
- Create: `backend/forgeops/services/__init__.py` (empty), `services/bootstrap.py`
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/<rev>_initial.py` (generated)
- Test: `backend/tests/conftest.py`, `backend/tests/test_health.py`

**Interfaces:**
- Produces: `Settings` fields `forgeops_env, database_url, forgeops_secret_key: SecretStr, forgeops_admin_email, forgeops_admin_password: SecretStr, forgeops_workspace_name, cors_origins, session_ttl_hours`, property `is_production`; `get_settings() -> Settings`.
- Produces: ORM classes `Base, Workspace, User, Membership, AuthSession, Investigation, Event, AuditLog`; helpers `new_id(prefix) -> str`, `utcnow() -> datetime`.
- Produces: `create_engine_and_factory(url: str) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]`.
- Produces: `create_app(settings: Settings | None = None) -> FastAPI`, `async startup(app, settings)`, `async shutdown(app)`. `app.state` has `settings, engine, session_factory, event_bus, login_limiter, secret_box`.
- Produces: `ensure_admin(session, settings) -> tuple[User, Workspace]` (idempotent).
- Produces test fixtures: `settings`, `app`, `client`, `session_factory`; constants `ADMIN_EMAIL`, `ADMIN_PASSWORD` in `tests/conftest.py`.

- [ ] **Step 1: Implement config, logging, models, session**

`backend/forgeops/config.py`:
```python
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Repo-root .env when running from backend/; container env vars override both.
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    forgeops_env: str = "development"
    database_url: str
    forgeops_secret_key: SecretStr
    forgeops_admin_email: str
    forgeops_admin_password: SecretStr
    forgeops_workspace_name: str = "My workspace"
    cors_origins: list[str] = ["http://localhost:5173"]
    session_ttl_hours: int = 72

    @property
    def is_production(self) -> bool:
        return self.forgeops_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`backend/forgeops/logging.py`:
```python
import logging

import structlog


def configure_logging(production: bool) -> None:
    renderer = (
        structlog.processors.JSONRenderer() if production else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )
```

`backend/forgeops/db/models.py`:
```python
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
```

`backend/forgeops/db/session.py`:
```python
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

SessionFactory = async_sessionmaker[AsyncSession]


def create_engine_and_factory(url: str) -> tuple[AsyncEngine, SessionFactory]:
    engine = create_async_engine(url, pool_pre_ping=True)
    return engine, async_sessionmaker(engine, expire_on_commit=False)
```

- [ ] **Step 2: Implement bootstrap, health, app factory**

`backend/forgeops/services/bootstrap.py`:
```python
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
```

`backend/forgeops/api/health.py`:
```python
from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, str]:
    database = "ok"
    try:
        async with request.app.state.session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        database = "unavailable"
    return {"status": "ok" if database == "ok" else "degraded", "database": database}
```

`backend/forgeops/main.py`:
```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forgeops.api import health
from forgeops.config import Settings, get_settings
from forgeops.db.session import create_engine_and_factory
from forgeops.events.bus import EventBus
from forgeops.logging import configure_logging
from forgeops.security.crypto import SecretBox
from forgeops.security.rate_limit import LoginLimiter
from forgeops.services.bootstrap import ensure_admin

log = structlog.get_logger()


async def startup(app: FastAPI, settings: Settings) -> None:
    configure_logging(settings.is_production)
    engine, session_factory = create_engine_and_factory(settings.database_url)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.event_bus = EventBus(session_factory)
    app.state.login_limiter = LoginLimiter()
    app.state.secret_box = SecretBox(settings.forgeops_secret_key.get_secret_value())
    async with session_factory() as session:
        _, workspace = await ensure_admin(session, settings)
    log.info("forgeops.started", workspace_id=workspace.id, env=settings.forgeops_env)


async def shutdown(app: FastAPI) -> None:
    await app.state.engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await startup(app, settings)
        yield
        await shutdown(app)

    app = FastAPI(title="ForgeOps API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    return app
```

(Tasks 4 and 6 add `app.include_router(auth.router, prefix="/api")` and `app.include_router(investigations.router, prefix="/api")` after the health router.)

- [ ] **Step 3: Write test fixtures and the failing health test**

`backend/tests/conftest.py`:
```python
import os

import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from forgeops.config import Settings
from forgeops.db.models import Base
from forgeops.main import create_app, shutdown, startup

ADMIN_EMAIL = "admin@test.local"
ADMIN_PASSWORD = "correct horse battery"


def _test_database_url() -> str:
    if url := os.environ.get("TEST_DATABASE_URL"):
        return url
    base = Settings().database_url  # repo-root .env
    return make_url(base).set(database="forgeops_test").render_as_string(hide_password=False)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url=_test_database_url(),
        forgeops_secret_key=Fernet.generate_key().decode(),
        forgeops_admin_email=ADMIN_EMAIL,
        forgeops_admin_password=ADMIN_PASSWORD,
        forgeops_workspace_name="Test workspace",
    )


@pytest.fixture
async def app(settings):
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    application = create_app(settings)
    await startup(application, settings)
    yield application
    await shutdown(application)


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def session_factory(app):
    return app.state.session_factory
```

`backend/tests/test_health.py`:
```python
from sqlalchemy import select

from forgeops.db.models import Membership, User
from tests.conftest import ADMIN_EMAIL


async def test_health_reports_database_ok(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_startup_creates_admin_and_workspace_once(app, settings, session_factory):
    from forgeops.services.bootstrap import ensure_admin

    async with session_factory() as session:
        user, workspace = await ensure_admin(session, settings)  # second call
        users = (await session.scalars(select(User))).all()
        memberships = (await session.scalars(select(Membership))).all()
    assert [u.email for u in users] == [ADMIN_EMAIL]
    assert len(memberships) == 1 and memberships[0].workspace_id == workspace.id
```

Also create empty `backend/tests/__init__.py` so `from tests.conftest import …` resolves.

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_health.py -v`
Expected: 2 passed (requires `docker compose up -d postgres` from Task 1).

- [ ] **Step 5: Set up Alembic and the initial migration**

Run: `cd backend && uv run alembic init -t async alembic`

Replace `backend/alembic/env.py` with:
```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from forgeops.config import get_settings
from forgeops.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(_url())
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

In `backend/alembic.ini`, leave `sqlalchemy.url` unset (the env.py reads settings).

Run: `cd backend && uv run alembic revision --autogenerate -m "initial"`
Expected: a file `alembic/versions/<rev>_initial.py` whose `upgrade()` creates tables `workspaces, users, memberships, auth_sessions, investigations, events, audit_log`. Open it and confirm all seven `op.create_table` calls and the `events` unique constraint on `(investigation_id, seq)` are present.

Run: `cd backend && uv run alembic upgrade head`
Expected: `Running upgrade  -> <rev>, initial`

- [ ] **Step 6: Commit**

```bash
git add backend/forgeops backend/tests backend/alembic backend/alembic.ini
git commit -m "Add config, data model, app factory, health check and initial migration" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Authentication API

**Files:**
- Create: `backend/forgeops/api/deps.py`, `backend/forgeops/api/auth.py`
- Modify: `backend/forgeops/main.py` (include auth router)
- Modify: `backend/tests/conftest.py` (add `auth_client` fixture)
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `hash_token`, `new_token`, `verify_password`, `LoginLimiter`, ORM models, `app.state.session_factory`.
- Produces: `SESSION_COOKIE = "forgeops_session"`; `CurrentUser(user_id: str, email: str, workspace_id: str, workspace_name: str, csrf_token: str)`; dependencies `current_user(request) -> CurrentUser` (401 if missing/expired) and `require_csrf(request, user) -> CurrentUser` (403 if header `X-CSRF-Token` mismatches on POST/PUT/PATCH/DELETE).
- Produces: routes `POST /api/auth/login` → `MeOut`, `POST /api/auth/logout` → 204, `GET /api/auth/me` → `MeOut`, where `MeOut = {user: {id, email}, workspace: {id, name}, csrf_token}`.
- Produces fixture `auth_client` (logged-in `AsyncClient` with `X-CSRF-Token` header set).

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/conftest.py`:
```python
@pytest.fixture
async def auth_client(client):
    response = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return client
```

`backend/tests/test_auth.py`:
```python
from sqlalchemy import select

from forgeops.db.models import AuditLog
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


async def test_login_sets_cookie_and_returns_me(client):
    response = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL.upper(), "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == ADMIN_EMAIL
    assert body["workspace"]["name"] == "Test workspace"
    assert len(body["csrf_token"]) >= 32
    assert "forgeops_session" in response.cookies
    assert "password" not in response.text


async def test_login_wrong_password_is_401(client):
    response = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": "nope"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email or password is incorrect"


async def test_login_is_rate_limited(client):
    for _ in range(5):
        await client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": "nope"})
    response = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 429


async def test_me_requires_login(client):
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_me_after_login(auth_client):
    response = await auth_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["user"]["email"] == ADMIN_EMAIL


async def test_logout_requires_csrf_then_ends_session(auth_client):
    token = auth_client.headers.pop("X-CSRF-Token")
    assert (await auth_client.post("/api/auth/logout")).status_code == 403
    auth_client.headers["X-CSRF-Token"] = token
    assert (await auth_client.post("/api/auth/logout")).status_code == 204
    assert (await auth_client.get("/api/auth/me")).status_code == 401


async def test_login_is_audited(auth_client, session_factory):
    async with session_factory() as session:
        rows = (await session.scalars(select(AuditLog))).all()
    assert [(r.action, r.actor, r.channel) for r in rows] == [("auth.login", ADMIN_EMAIL, "web")]
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_auth.py -v`
Expected: FAIL (404 on `/api/auth/login`).

- [ ] **Step 3: Implement dependencies and routes**

`backend/forgeops/api/deps.py`:
```python
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
```

`backend/forgeops/api/auth.py`:
```python
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
```

In `backend/forgeops/main.py`, change the import line to `from forgeops.api import auth, health` and add after the health router:
```python
    app.include_router(auth.router, prefix="/api")
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && uv run pytest tests/test_auth.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add backend/forgeops/api backend/forgeops/main.py backend/tests
git commit -m "Add session login, logout, me and CSRF protection" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Event bus

**Files:**
- Already created in Task 3 (verify content matches): `backend/forgeops/events/models.py`, `backend/forgeops/events/bus.py`
- Test: `backend/tests/test_event_bus.py`

**Interfaces:**
- Produces: `EventType` (StrEnum, TRD §6.3 values), `TERMINAL_EVENTS = {investigation_completed, investigation_failed}`, `EventIn(type, agent=None, data={})`, `EventOut(seq, investigation_id, type, agent, ts, data)`.
- Produces: `EventBus(session_factory)` with `async emit(workspace_id, investigation_id, event: EventIn) -> EventOut`, `async history(investigation_id, after_seq=0) -> list[EventOut]`, `async is_terminal(investigation_id) -> bool`, `stream(investigation_id, after_seq=0) -> AsyncIterator[EventOut]` (replays history, then live, ends after a terminal event).

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_event_bus.py`:
```python
import asyncio

from forgeops.db.models import Investigation
from forgeops.events.models import EventIn, EventType


async def _investigation(session_factory, workspace_id: str) -> str:
    async with session_factory() as session:
        inv = Investigation(workspace_id=workspace_id, description="checkout slow")
        session.add(inv)
        await session.commit()
        return inv.id


async def _workspace_id(session_factory) -> str:
    from sqlalchemy import select

    from forgeops.db.models import Workspace

    async with session_factory() as session:
        return (await session.scalars(select(Workspace))).one().id


async def test_emit_assigns_increasing_seq(app, session_factory):
    bus = app.state.event_bus
    ws = await _workspace_id(session_factory)
    inv = await _investigation(session_factory, ws)
    a = await bus.emit(ws, inv, EventIn(type=EventType.investigation_started))
    b = await bus.emit(ws, inv, EventIn(type=EventType.agent_started, agent="code"))
    assert (a.seq, b.seq) == (1, 2)
    assert b.agent == "code"


async def test_concurrent_emits_get_unique_seq(app, session_factory):
    bus = app.state.event_bus
    ws = await _workspace_id(session_factory)
    inv = await _investigation(session_factory, ws)
    results = await asyncio.gather(
        *(bus.emit(ws, inv, EventIn(type=EventType.tool_called, data={"i": i})) for i in range(10))
    )
    assert sorted(e.seq for e in results) == list(range(1, 11))


async def test_history_after_seq(app, session_factory):
    bus = app.state.event_bus
    ws = await _workspace_id(session_factory)
    inv = await _investigation(session_factory, ws)
    for _ in range(3):
        await bus.emit(ws, inv, EventIn(type=EventType.tool_called))
    assert [e.seq for e in await bus.history(inv, after_seq=1)] == [2, 3]


async def test_stream_replays_then_goes_live_then_stops_at_terminal(app, session_factory):
    bus = app.state.event_bus
    ws = await _workspace_id(session_factory)
    inv = await _investigation(session_factory, ws)
    await bus.emit(ws, inv, EventIn(type=EventType.investigation_started))

    received: list[str] = []

    async def consume():
        async for event in bus.stream(inv, after_seq=0):
            received.append(event.type)

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await bus.emit(ws, inv, EventIn(type=EventType.agent_started, agent="code"))
    await bus.emit(ws, inv, EventIn(type=EventType.investigation_completed))
    await asyncio.wait_for(task, timeout=2)
    assert received == ["investigation_started", "agent_started", "investigation_completed"]


async def test_stream_of_finished_investigation_ends_immediately(app, session_factory):
    bus = app.state.event_bus
    ws = await _workspace_id(session_factory)
    inv = await _investigation(session_factory, ws)
    await bus.emit(ws, inv, EventIn(type=EventType.investigation_failed))

    async def drain(after: int) -> list[int]:
        return [e.seq async for e in bus.stream(inv, after_seq=after)]

    assert await asyncio.wait_for(drain(0), timeout=2) == [1]
    assert await asyncio.wait_for(drain(1), timeout=2) == []
```

- [ ] **Step 2: Implement (if not already identical from Task 3)**

`backend/forgeops/events/models.py`:
```python
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    investigation_started = "investigation_started"
    supervisor_started = "supervisor_started"
    plan_created = "plan_created"
    agent_skipped = "agent_skipped"
    agent_started = "agent_started"
    tool_called = "tool_called"
    tool_completed = "tool_completed"
    evidence_added = "evidence_added"
    agent_failed = "agent_failed"
    agent_completed = "agent_completed"
    review_completed = "review_completed"
    rca_started = "rca_started"
    rca_completed = "rca_completed"
    approval_requested = "approval_requested"
    approval_granted = "approval_granted"
    approval_rejected = "approval_rejected"
    action_started = "action_started"
    action_completed = "action_completed"
    report_ready = "report_ready"
    investigation_completed = "investigation_completed"
    investigation_failed = "investigation_failed"


TERMINAL_EVENTS = frozenset({EventType.investigation_completed, EventType.investigation_failed})


class EventIn(BaseModel):
    type: EventType
    agent: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class EventOut(BaseModel):
    seq: int
    investigation_id: str
    type: EventType
    agent: str | None
    ts: datetime
    data: dict[str, Any]
```

`backend/forgeops/events/bus.py`:
```python
"""Persisted, ordered investigation events with in-process live fan-out.

Single-process by design for the MVP: subscribers live in this process's memory.
"""

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import exists, func, select

from forgeops.db.models import Event
from forgeops.db.session import SessionFactory
from forgeops.events.models import TERMINAL_EVENTS, EventIn, EventOut


def _to_out(row: Event) -> EventOut:
    return EventOut(
        seq=row.seq,
        investigation_id=row.investigation_id,
        type=row.type,
        agent=row.agent,
        ts=row.ts,
        data=row.data,
    )


class EventBus:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory
        self._subscribers: dict[str, set[asyncio.Queue[EventOut]]] = defaultdict(set)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def emit(self, workspace_id: str, investigation_id: str, event: EventIn) -> EventOut:
        async with self._locks[investigation_id]:
            async with self._session_factory() as session:
                last = await session.scalar(
                    select(func.max(Event.seq)).where(Event.investigation_id == investigation_id)
                )
                row = Event(
                    investigation_id=investigation_id,
                    workspace_id=workspace_id,
                    seq=(last or 0) + 1,
                    type=event.type.value,
                    agent=event.agent,
                    data=event.data,
                )
                session.add(row)
                await session.commit()
                out = _to_out(row)
        for queue in list(self._subscribers[investigation_id]):
            queue.put_nowait(out)
        return out

    async def history(self, investigation_id: str, after_seq: int = 0) -> list[EventOut]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(Event)
                .where(Event.investigation_id == investigation_id, Event.seq > after_seq)
                .order_by(Event.seq)
            )
            return [_to_out(row) for row in rows]

    async def is_terminal(self, investigation_id: str) -> bool:
        async with self._session_factory() as session:
            return bool(
                await session.scalar(
                    select(
                        exists().where(
                            Event.investigation_id == investigation_id,
                            Event.type.in_([t.value for t in TERMINAL_EVENTS]),
                        )
                    )
                )
            )

    @asynccontextmanager
    async def subscribe(self, investigation_id: str) -> AsyncIterator[asyncio.Queue[EventOut]]:
        queue: asyncio.Queue[EventOut] = asyncio.Queue()
        self._subscribers[investigation_id].add(queue)
        try:
            yield queue
        finally:
            self._subscribers[investigation_id].discard(queue)
            if not self._subscribers[investigation_id]:
                self._subscribers.pop(investigation_id, None)

    async def stream(self, investigation_id: str, after_seq: int = 0) -> AsyncIterator[EventOut]:
        # Subscribe before reading history so nothing emitted in between is lost;
        # duplicates are dropped by sequence number.
        async with self.subscribe(investigation_id) as queue:
            last = after_seq
            for event in await self.history(investigation_id, after_seq):
                yield event
                last = event.seq
                if event.type in TERMINAL_EVENTS:
                    return
            if await self.is_terminal(investigation_id):
                return
            while True:
                event = await queue.get()
                if event.seq <= last:
                    continue
                yield event
                last = event.seq
                if event.type in TERMINAL_EVENTS:
                    return
```

- [ ] **Step 3: Run tests**

Run: `cd backend && uv run pytest tests/test_event_bus.py -v`
Expected: 5 passed

- [ ] **Step 4: Commit**

```bash
git add backend/forgeops/events backend/tests/test_event_bus.py
git commit -m "Add persisted investigation event bus with replay and live streaming" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Investigations API with SSE

**Files:**
- Create: `backend/forgeops/api/investigations.py`
- Modify: `backend/forgeops/main.py` (include router)
- Test: `backend/tests/test_investigations_api.py`

**Interfaces:**
- Consumes: `current_user`, `require_csrf`, `EventBus`, `Investigation`.
- Produces: `POST /api/investigations` body `{description (3..4000 chars), service_id?, window_start?, window_end?}` → 201 `InvestigationOut{id, description, status, source, service_id, window_start, window_end, created_at}` and emits `investigation_started{description}`.
- Produces: `GET /api/investigations` → `list[InvestigationOut]` (newest first, max 50, own workspace); `GET /api/investigations/{id}` → `InvestigationOut` or 404; `GET /api/investigations/{id}/events?after=N` → `text/event-stream`, each message `id: <seq>` and `data: <EventOut JSON>`; honours `Last-Event-ID`.
- M1 hook: `create_investigation` is where M1 starts the engine task.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_investigations_api.py`:
```python
import json

from forgeops.db.models import Investigation, Workspace
from forgeops.events.models import EventIn, EventType


async def test_create_requires_csrf(auth_client):
    auth_client.headers.pop("X-CSRF-Token")
    response = await auth_client.post("/api/investigations", json={"description": "checkout slow"})
    assert response.status_code == 403


async def test_create_and_get(auth_client, app):
    response = await auth_client.post(
        "/api/investigations", json={"description": "Checkout API latency is high"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("inv_")
    assert body["status"] == "queued"
    assert body["source"] == "web"

    fetched = await auth_client.get(f"/api/investigations/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["description"] == "Checkout API latency is high"

    history = await app.state.event_bus.history(body["id"])
    assert [(e.seq, e.type) for e in history] == [(1, "investigation_started")]
    assert history[0].data == {"description": "Checkout API latency is high"}


async def test_description_is_validated(auth_client):
    response = await auth_client.post("/api/investigations", json={"description": "x"})
    assert response.status_code == 422


async def test_list_is_scoped_to_workspace(auth_client, session_factory):
    async with session_factory() as session:
        other = Workspace(name="Other company")
        session.add(other)
        await session.flush()
        session.add(Investigation(workspace_id=other.id, description="not yours"))
        await session.commit()
    await auth_client.post("/api/investigations", json={"description": "mine one"})

    listed = (await auth_client.get("/api/investigations")).json()
    assert [i["description"] for i in listed] == ["mine one"]


async def test_other_workspace_investigation_is_404(auth_client, session_factory):
    async with session_factory() as session:
        other = Workspace(name="Other company")
        session.add(other)
        await session.flush()
        inv = Investigation(workspace_id=other.id, description="not yours")
        session.add(inv)
        await session.commit()
    assert (await auth_client.get(f"/api/investigations/{inv.id}")).status_code == 404
    assert (await auth_client.get(f"/api/investigations/{inv.id}/events")).status_code == 404


def _sse_messages(text: str) -> list[dict]:
    messages, current = [], {}
    for line in text.splitlines():
        if not line:
            if current:
                messages.append(current)
                current = {}
            continue
        field, _, value = line.partition(":")
        current[field] = value.lstrip()
    if current:
        messages.append(current)
    return [m for m in messages if "data" in m]


async def test_events_stream_replays_finished_investigation(auth_client, app):
    created = (
        await auth_client.post("/api/investigations", json={"description": "orders failing"})
    ).json()
    bus = app.state.event_bus
    ws = (await auth_client.get("/api/auth/me")).json()["workspace"]["id"]
    await bus.emit(ws, created["id"], EventIn(type=EventType.investigation_completed))

    response = await auth_client.get(f"/api/investigations/{created['id']}/events")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    messages = _sse_messages(response.text)
    assert [m["id"] for m in messages] == ["1", "2"]
    assert [json.loads(m["data"])["type"] for m in messages] == [
        "investigation_started",
        "investigation_completed",
    ]


async def test_events_stream_honours_last_event_id(auth_client, app):
    created = (
        await auth_client.post("/api/investigations", json={"description": "orders failing"})
    ).json()
    ws = (await auth_client.get("/api/auth/me")).json()["workspace"]["id"]
    await app.state.event_bus.emit(
        ws, created["id"], EventIn(type=EventType.investigation_completed)
    )
    response = await auth_client.get(
        f"/api/investigations/{created['id']}/events", headers={"Last-Event-ID": "1"}
    )
    assert [m["id"] for m in _sse_messages(response.text)] == ["2"]
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_investigations_api.py -v`
Expected: FAIL (404 for `/api/investigations`).

- [ ] **Step 3: Implement**

`backend/forgeops/api/investigations.py`:
```python
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from forgeops.api.deps import CurrentUser, current_user, require_csrf
from forgeops.db.models import Investigation
from forgeops.events.bus import EventBus
from forgeops.events.models import EventIn, EventType

router = APIRouter(prefix="/investigations", tags=["investigations"])


class InvestigationCreate(BaseModel):
    description: str = Field(min_length=3, max_length=4000)
    service_id: str | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None


class InvestigationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    description: str
    status: str
    source: str
    service_id: str | None
    window_start: datetime | None
    window_end: datetime | None
    created_at: datetime


async def _get_owned(request: Request, user: CurrentUser, investigation_id: str) -> Investigation:
    async with request.app.state.session_factory() as session:
        inv = await session.scalar(
            select(Investigation).where(
                Investigation.id == investigation_id,
                Investigation.workspace_id == user.workspace_id,
            )
        )
    if inv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Investigation not found")
    return inv


@router.post("", status_code=status.HTTP_201_CREATED, response_model=InvestigationOut)
async def create_investigation(
    body: InvestigationCreate, request: Request, user: CurrentUser = Depends(require_csrf)
) -> Investigation:
    async with request.app.state.session_factory() as session:
        inv = Investigation(
            workspace_id=user.workspace_id,
            description=body.description.strip(),
            service_id=body.service_id,
            source="web",
            status="queued",
            created_by=user.user_id,
            window_start=body.window_start,
            window_end=body.window_end,
        )
        session.add(inv)
        await session.commit()
    bus: EventBus = request.app.state.event_bus
    await bus.emit(
        user.workspace_id,
        inv.id,
        EventIn(type=EventType.investigation_started, data={"description": inv.description}),
    )
    return inv


@router.get("", response_model=list[InvestigationOut])
async def list_investigations(
    request: Request, user: CurrentUser = Depends(current_user)
) -> list[Investigation]:
    async with request.app.state.session_factory() as session:
        rows = await session.scalars(
            select(Investigation)
            .where(Investigation.workspace_id == user.workspace_id)
            .order_by(Investigation.created_at.desc())
            .limit(50)
        )
        return list(rows)


@router.get("/{investigation_id}", response_model=InvestigationOut)
async def get_investigation(
    investigation_id: str, request: Request, user: CurrentUser = Depends(current_user)
) -> Investigation:
    return await _get_owned(request, user, investigation_id)


@router.get("/{investigation_id}/events")
async def stream_events(
    investigation_id: str,
    request: Request,
    after: int = 0,
    user: CurrentUser = Depends(current_user),
) -> EventSourceResponse:
    inv = await _get_owned(request, user, investigation_id)
    last_event_id = request.headers.get("last-event-id", "")
    after_seq = int(last_event_id) if last_event_id.isdigit() else after
    bus: EventBus = request.app.state.event_bus

    async def messages():
        async for event in bus.stream(inv.id, after_seq):
            yield {"id": str(event.seq), "data": event.model_dump_json()}

    return EventSourceResponse(messages(), ping=15)
```

In `backend/forgeops/main.py`: import line becomes `from forgeops.api import auth, health, investigations` and add:
```python
    app.include_router(investigations.router, prefix="/api")
```

- [ ] **Step 4: Run all backend tests**

Run: `cd backend && uv run pytest -v`
Expected: all tests pass (envfile 5, security 7, health 2, auth 7, event bus 5, investigations 7 = 33).

If the SSE tests hang, the installed `sse-starlette` is waiting on client disconnect under httpx `ASGITransport`; verify the stream ends after the terminal event (it must, per `EventBus.stream`) before changing anything else.

- [ ] **Step 5: Commit**

```bash
git add backend/forgeops/api/investigations.py backend/forgeops/main.py backend/tests/test_investigations_api.py
git commit -m "Add workspace-scoped investigations API with SSE event stream" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: Backend container

**Files:**
- Create: `backend/Dockerfile`, `backend/.dockerignore`
- Modify: `docker-compose.yml` (add `api` service)

**Interfaces:**
- Produces: `docker compose up -d` runs Postgres + API on `http://localhost:8000`, applying migrations on start.

- [ ] **Step 1: Write the Dockerfile**

`backend/Dockerfile`:
```dockerfile
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn forgeops.main:create_app --factory --host 0.0.0.0 --port 8000"]
```

`backend/.dockerignore`:
```text
.venv
__pycache__
.pytest_cache
tests
```

- [ ] **Step 2: Add the api service**

Append under `services:` in `docker-compose.yml`:
```yaml
  api:
    build: ./backend
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "127.0.0.1:8000:8000"
```

- [ ] **Step 3: Build and smoke-test**

Run: `docker compose up -d --build api`
Run: `curl -s http://localhost:8000/api/health`
Expected: `{"status":"ok","database":"ok"}`

Run: `docker compose logs api | tail -5`
Expected: contains `forgeops.started` and no tracebacks.

- [ ] **Step 4: Commit**

```bash
git add backend/Dockerfile backend/.dockerignore docker-compose.yml
git commit -m "Containerize the API with migrations on start" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Frontend shell with login

**Files:**
- Create (scaffold): `frontend/` via Vite `react-ts` template
- Create: `frontend/vite.config.ts` (replace), `src/main.tsx` (replace), `src/app/App.tsx`, `src/styles/tokens.css`, `src/styles/global.css`, `src/api/types.ts`, `src/api/client.ts`, `src/api/auth.ts`, `src/auth/AuthProvider.tsx`, `src/components/Layout.tsx`, `src/pages/LoginPage.tsx`, `src/test/setup.ts`
- Delete: scaffold demo files `src/App.tsx`, `src/App.css`, `src/index.css`, `src/assets/`, `public/vite.svg` (whatever the template generated that is not listed above)
- Test: `frontend/src/pages/LoginPage.test.tsx`

**Interfaces:**
- Consumes: `/api/auth/login`, `/api/auth/me`, `/api/auth/logout`.
- Produces: `api<T>(path, init?)`, `ApiError(status, message)`, `setCsrfToken(token)`; `login(email, password): Promise<Me>`, `fetchMe(): Promise<Me | null>`, `logout()`; `useMe()`, `RequireAuth`, `ME_QUERY_KEY`; `Layout` (renders `<Outlet/>`); types `Me`, `Investigation`, `InvestigationEvent`, `EventType`.

- [ ] **Step 1: Scaffold and install**

Run (repo root): `npm create vite@latest frontend -- --template react-ts`
Run: `cd frontend && npm install && npm install react-router @tanstack/react-query && npm install -D vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event`

Add to `frontend/package.json` `"scripts"`: `"test": "vitest run"`.

- [ ] **Step 2: Config, styles, API layer**

`frontend/vite.config.ts`:
```ts
/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://localhost:8000" } },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
```

`frontend/src/test/setup.ts`:
```ts
import "@testing-library/jest-dom/vitest";
```

`frontend/src/styles/tokens.css`:
```css
:root {
  --bg: #f2f3f0;
  --surface: #ffffff;
  --sunk: #e7e9e4;
  --ink: #16202a;
  --ink-2: #4a5560;
  --line: #d3d7d0;
  --accent: #c8590a;
  --steel: #2f5d8a;
  --ok: #2e7d4f;
  --warn: #a86b00;
  --bad: #b3261e;
  --font: "Source Sans 3", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "JetBrains Mono", ui-monospace, Consolas, monospace;
  color-scheme: light;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f151b;
    --surface: #17202a;
    --sunk: #111920;
    --ink: #e6eaee;
    --ink-2: #9aa6b1;
    --line: #2a3642;
    --accent: #f08a3c;
    --steel: #7faedb;
    --ok: #6bc58e;
    --warn: #e3b04b;
    --bad: #f2837b;
    color-scheme: dark;
  }
}
```

`frontend/src/styles/global.css`:
```css
* { box-sizing: border-box; }
html, body, #root { height: 100%; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.5 var(--font); }
a { color: var(--steel); }
h1, h2, h3 { line-height: 1.15; margin: 0; }
.muted { color: var(--ink-2); }
.mono { font-family: var(--mono); font-size: 0.85em; }
.pad { padding: 24px; }

label { display: block; font-weight: 600; font-size: 0.9rem; margin-bottom: 4px; }
input, textarea {
  width: 100%; font: inherit; color: var(--ink); background: var(--surface);
  border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px;
}
input:focus-visible, textarea:focus-visible, button:focus-visible, a:focus-visible {
  outline: 2px solid var(--steel); outline-offset: 2px;
}
button {
  font: inherit; font-weight: 700; border-radius: 6px; padding: 8px 14px; cursor: pointer;
  border: 1px solid var(--accent); background: var(--accent); color: #fff;
}
button.secondary { background: transparent; color: var(--ink); border-color: var(--line); }
button:disabled { opacity: 0.6; cursor: default; }
.error { color: var(--bad); margin: 0; }

.shell { display: grid; grid-template-rows: auto 1fr; min-height: 100%; }
.topbar {
  display: flex; align-items: center; gap: 20px; padding: 10px 20px;
  background: var(--surface); border-bottom: 1px solid var(--line); flex-wrap: wrap;
}
.brand { font-weight: 800; letter-spacing: 0.02em; }
.topbar nav { display: flex; gap: 14px; flex: 1; }
.topbar nav a { text-decoration: none; color: var(--ink-2); font-weight: 600; }
.topbar nav a.active { color: var(--ink); }
.content { padding: 24px 20px; max-width: 1200px; width: 100%; margin: 0 auto; }

.login { display: grid; place-items: center; min-height: 100%; padding: 16px; }
.login-card {
  width: min(380px, 100%); display: grid; gap: 12px; padding: 28px;
  background: var(--surface); border: 1px solid var(--line); border-radius: 10px;
}

.pill {
  display: inline-block; font-family: var(--mono); font-size: 0.72rem; font-weight: 600;
  padding: 2px 8px; border-radius: 99px; background: var(--sunk); color: var(--ink-2);
}
.pill.running, .pill.queued { color: var(--steel); }
.pill.completed { color: var(--ok); }
.pill.failed, .pill.rejected { color: var(--bad); }
.pill.awaiting_approval { color: var(--warn); }

table { width: 100%; border-collapse: collapse; background: var(--surface); }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); }
th { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--ink-2); }
.table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; }
```

`frontend/src/api/types.ts`:
```ts
export interface Me {
  user: { id: string; email: string };
  workspace: { id: string; name: string };
  csrf_token: string;
}

export type InvestigationStatus =
  | "queued" | "running" | "awaiting_approval" | "acting" | "completed" | "rejected" | "failed";

export interface Investigation {
  id: string;
  description: string;
  status: InvestigationStatus;
  source: "web" | "slack";
  service_id: string | null;
  window_start: string | null;
  window_end: string | null;
  created_at: string;
}

export type EventType =
  | "investigation_started" | "supervisor_started" | "plan_created" | "agent_skipped"
  | "agent_started" | "tool_called" | "tool_completed" | "evidence_added" | "agent_failed"
  | "agent_completed" | "review_completed" | "rca_started" | "rca_completed"
  | "approval_requested" | "approval_granted" | "approval_rejected" | "action_started"
  | "action_completed" | "report_ready" | "investigation_completed" | "investigation_failed";

export interface InvestigationEvent {
  seq: number;
  investigation_id: string;
  type: EventType;
  agent: string | null;
  ts: string;
  data: Record<string, unknown>;
}
```

`frontend/src/api/client.ts`:
```ts
let csrfToken: string | null = null;

export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  if (method !== "GET" && csrfToken) headers.set("X-CSRF-Token", csrfToken);

  const response = await fetch(`/api${path}`, { ...init, method, headers, credentials: "include" });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
```

`frontend/src/api/auth.ts`:
```ts
import { api, ApiError, setCsrfToken } from "./client";
import type { Me } from "./types";

export async function login(email: string, password: string): Promise<Me> {
  const me = await api<Me>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setCsrfToken(me.csrf_token);
  return me;
}

export async function fetchMe(): Promise<Me | null> {
  try {
    const me = await api<Me>("/auth/me");
    setCsrfToken(me.csrf_token);
    return me;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

export async function logout(): Promise<void> {
  await api<void>("/auth/logout", { method: "POST" });
  setCsrfToken(null);
}
```

- [ ] **Step 3: Auth provider, layout, login page, app**

`frontend/src/auth/AuthProvider.tsx`:
```tsx
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate, useLocation } from "react-router";
import { fetchMe } from "../api/auth";

export const ME_QUERY_KEY = ["me"] as const;

export function useMe() {
  return useQuery({ queryKey: ME_QUERY_KEY, queryFn: fetchMe, retry: false, staleTime: 60_000 });
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { data, isPending, isError } = useMe();
  const location = useLocation();
  if (isPending) return <p className="muted pad">Loading…</p>;
  if (isError) return <p className="error pad">Could not reach ForgeOps. Check that the API is running.</p>;
  if (!data) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <>{children}</>;
}
```

`frontend/src/components/Layout.tsx`:
```tsx
import { useQueryClient } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router";
import { logout } from "../api/auth";
import { ME_QUERY_KEY, useMe } from "../auth/AuthProvider";

export function Layout() {
  const { data: me } = useMe();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  async function onSignOut() {
    await logout();
    queryClient.setQueryData(ME_QUERY_KEY, null);
    navigate("/login", { replace: true });
  }

  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">ForgeOps</span>
        <nav aria-label="Main">
          <NavLink to="/" end>Investigations</NavLink>
        </nav>
        <span className="muted">{me?.workspace.name} · {me?.user.email}</span>
        <button className="secondary" onClick={onSignOut}>Sign out</button>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
```

`frontend/src/pages/LoginPage.tsx`:
```tsx
import { useState, type FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router";
import { login } from "../api/auth";
import { ApiError } from "../api/client";
import { ME_QUERY_KEY } from "../auth/AuthProvider";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = await login(email, password);
      queryClient.setQueryData(ME_QUERY_KEY, me);
      const from = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(from, { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) setError("Email or password is incorrect.");
      else if (err instanceof ApiError && err.status === 429)
        setError("Too many attempts. Wait 5 minutes and try again.");
      else setError("Could not reach ForgeOps. Check that the API is running.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login">
      <form className="login-card" onSubmit={onSubmit} aria-labelledby="login-title">
        <h1 id="login-title">ForgeOps</h1>
        <p className="muted">Sign in to your workspace</p>
        <div>
          <label htmlFor="email">Email</label>
          <input id="email" type="email" autoComplete="username" required
            value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete="current-password" required
            value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && <p role="alert" className="error">{error}</p>}
        <button type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </main>
  );
}
```

`frontend/src/app/App.tsx` (Task 9 adds the investigation routes):
```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router";
import { RequireAuth } from "../auth/AuthProvider";
import { Layout } from "../components/Layout";
import { LoginPage } from "../pages/LoginPage";

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireAuth><Layout /></RequireAuth>}>
            <Route index element={<p className="muted">No investigations yet.</p>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

`frontend/src/main.tsx`:
```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import "./styles/tokens.css";
import "./styles/global.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

Set `<title>ForgeOps</title>` in `frontend/index.html`.

- [ ] **Step 4: Write the test**

`frontend/src/pages/LoginPage.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, expect, test, vi } from "vitest";
import { LoginPage } from "./LoginPage";

function renderLogin() {
  const client = new QueryClient();
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<p>home page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

test("signs in and goes to the home page", async () => {
  const me = { user: { id: "usr_1", email: "a@b.c" }, workspace: { id: "ws_1", name: "W" }, csrf_token: "t" };
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(me), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  renderLogin();

  await userEvent.type(screen.getByLabelText("Email"), "a@b.c");
  await userEvent.type(screen.getByLabelText("Password"), "pw");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

  expect(await screen.findByText("home page")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith("/api/auth/login", expect.objectContaining({ method: "POST" }));
});

test("shows an error for a wrong password", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ detail: "Email or password is incorrect" }), { status: 401 }),
  ));
  renderLogin();

  await userEvent.type(screen.getByLabelText("Email"), "a@b.c");
  await userEvent.type(screen.getByLabelText("Password"), "bad");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Email or password is incorrect.");
});
```

- [ ] **Step 5: Run tests and build**

Run: `cd frontend && npm test`
Expected: 2 passed

Run: `cd frontend && npm run build`
Expected: build succeeds with no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend
git commit -m "Add React frontend shell with session login" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Investigations pages with live event stream

**Files:**
- Create: `frontend/src/api/investigations.ts`, `frontend/src/investigations/eventStream.ts`, `frontend/src/pages/InvestigationsPage.tsx`, `frontend/src/pages/InvestigationPage.tsx`
- Modify: `frontend/src/app/App.tsx` (routes)
- Test: `frontend/src/investigations/eventStream.test.ts`

**Interfaces:**
- Consumes: `/api/investigations`, `/api/investigations/{id}`, `/api/investigations/{id}/events`.
- Produces: `listInvestigations()`, `getInvestigation(id)`, `createInvestigation({description})`; `StreamState {events, connected, done}`, `initialStreamState`, `applyEvent(state, event) -> StreamState`, `TERMINAL_EVENT_TYPES`, `useEventStream(id) -> StreamState` (M1's War Room consumes `useEventStream` and `applyEvent`).

- [ ] **Step 1: Write the failing reducer test**

`frontend/src/investigations/eventStream.test.ts`:
```ts
import { expect, test } from "vitest";
import type { InvestigationEvent } from "../api/types";
import { applyEvent, initialStreamState } from "./eventStream";

const ev = (seq: number, type: InvestigationEvent["type"]): InvestigationEvent => ({
  seq, type, investigation_id: "inv_1", agent: null, ts: "2026-09-21T10:00:00Z", data: {},
});

test("appends events in order", () => {
  const s = applyEvent(applyEvent(initialStreamState, ev(1, "investigation_started")), ev(2, "agent_started"));
  expect(s.events.map((e) => e.seq)).toEqual([1, 2]);
  expect(s.done).toBe(false);
});

test("ignores duplicate or older events (replay after reconnect)", () => {
  let s = applyEvent(initialStreamState, ev(1, "investigation_started"));
  s = applyEvent(s, ev(2, "agent_started"));
  s = applyEvent(s, ev(2, "agent_started"));
  s = applyEvent(s, ev(1, "investigation_started"));
  expect(s.events.map((e) => e.seq)).toEqual([1, 2]);
});

test("marks the stream done on a terminal event", () => {
  const s = applyEvent(initialStreamState, ev(1, "investigation_failed"));
  expect(s.done).toBe(true);
});
```

Run: `cd frontend && npm test`
Expected: FAIL (cannot resolve `./eventStream`).

- [ ] **Step 2: Implement the API module and stream**

`frontend/src/api/investigations.ts`:
```ts
import { api } from "./client";
import type { Investigation } from "./types";

export const listInvestigations = () => api<Investigation[]>("/investigations");
export const getInvestigation = (id: string) => api<Investigation>(`/investigations/${id}`);
export const createInvestigation = (body: { description: string }) =>
  api<Investigation>("/investigations", { method: "POST", body: JSON.stringify(body) });
```

`frontend/src/investigations/eventStream.ts`:
```ts
import { useEffect, useReducer } from "react";
import type { EventType, InvestigationEvent } from "../api/types";

export const TERMINAL_EVENT_TYPES: ReadonlySet<EventType> = new Set([
  "investigation_completed",
  "investigation_failed",
]);

export interface StreamState {
  events: InvestigationEvent[];
  connected: boolean;
  done: boolean;
}

export const initialStreamState: StreamState = { events: [], connected: false, done: false };

export function applyEvent(state: StreamState, event: InvestigationEvent): StreamState {
  const lastSeq = state.events.at(-1)?.seq ?? 0;
  if (event.seq <= lastSeq) return state;
  return {
    ...state,
    events: [...state.events, event],
    done: state.done || TERMINAL_EVENT_TYPES.has(event.type),
  };
}

type Action =
  | { kind: "event"; event: InvestigationEvent }
  | { kind: "connected"; value: boolean }
  | { kind: "reset" };

function reducer(state: StreamState, action: Action): StreamState {
  switch (action.kind) {
    case "event":
      return applyEvent(state, action.event);
    case "connected":
      return { ...state, connected: action.value };
    case "reset":
      return initialStreamState;
  }
}

export function useEventStream(investigationId: string): StreamState {
  const [state, dispatch] = useReducer(reducer, initialStreamState);

  useEffect(() => {
    dispatch({ kind: "reset" });
    // The browser resends Last-Event-ID on automatic reconnects; the server replays from there.
    const source = new EventSource(`/api/investigations/${investigationId}/events`, {
      withCredentials: true,
    });
    source.onopen = () => dispatch({ kind: "connected", value: true });
    source.onerror = () => dispatch({ kind: "connected", value: false });
    source.onmessage = (message: MessageEvent<string>) => {
      const event = JSON.parse(message.data) as InvestigationEvent;
      dispatch({ kind: "event", event });
      if (TERMINAL_EVENT_TYPES.has(event.type)) source.close();
    };
    return () => source.close();
  }, [investigationId]);

  return state;
}
```

Run: `cd frontend && npm test`
Expected: 5 passed (2 login + 3 stream).

- [ ] **Step 3: Pages and routes**

`frontend/src/pages/InvestigationsPage.tsx`:
```tsx
import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router";
import { ApiError } from "../api/client";
import { createInvestigation, listInvestigations } from "../api/investigations";

export function InvestigationsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [description, setDescription] = useState("");
  const investigations = useQuery({ queryKey: ["investigations"], queryFn: listInvestigations });
  const create = useMutation({
    mutationFn: createInvestigation,
    onSuccess: (inv) => {
      queryClient.invalidateQueries({ queryKey: ["investigations"] });
      navigate(`/investigations/${inv.id}`);
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    create.mutate({ description });
  }

  return (
    <div style={{ display: "grid", gap: 28 }}>
      <section aria-labelledby="new-title" style={{ display: "grid", gap: 10 }}>
        <h1 id="new-title">New investigation</h1>
        <form onSubmit={onSubmit} style={{ display: "grid", gap: 10 }}>
          <label htmlFor="description">What is happening?</label>
          <textarea id="description" rows={3} required minLength={3} maxLength={4000}
            placeholder="Checkout API latency increased after the last deployment"
            value={description} onChange={(e) => setDescription(e.target.value)} />
          {create.isError && (
            <p role="alert" className="error">
              {create.error instanceof ApiError ? create.error.message : "Could not start the investigation."}
            </p>
          )}
          <div><button type="submit" disabled={create.isPending}>
            {create.isPending ? "Starting…" : "Start investigation"}
          </button></div>
        </form>
      </section>

      <section aria-labelledby="list-title" style={{ display: "grid", gap: 10 }}>
        <h2 id="list-title">Recent investigations</h2>
        {investigations.isPending && <p className="muted">Loading…</p>}
        {investigations.isError && <p className="error">Could not load investigations.</p>}
        {investigations.data?.length === 0 && <p className="muted">No investigations yet.</p>}
        {!!investigations.data?.length && (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Incident</th><th>Status</th><th>Source</th><th>Started</th></tr></thead>
              <tbody>
                {investigations.data.map((inv) => (
                  <tr key={inv.id}>
                    <td><Link to={`/investigations/${inv.id}`}>{inv.description}</Link></td>
                    <td><span className={`pill ${inv.status}`}>{inv.status.replace("_", " ")}</span></td>
                    <td>{inv.source}</td>
                    <td className="mono">{new Date(inv.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
```

`frontend/src/pages/InvestigationPage.tsx` (M1 replaces the event log with the War Room):
```tsx
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router";
import { getInvestigation } from "../api/investigations";
import { useEventStream } from "../investigations/eventStream";

export function InvestigationPage() {
  const { id = "" } = useParams();
  const investigation = useQuery({ queryKey: ["investigation", id], queryFn: () => getInvestigation(id) });
  const stream = useEventStream(id);

  if (investigation.isPending) return <p className="muted">Loading…</p>;
  if (investigation.isError) return <p className="error">Investigation not found.</p>;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <header style={{ display: "grid", gap: 6 }}>
        <h1>{investigation.data.description}</h1>
        <p className="muted">
          {stream.done ? "Finished" : stream.connected ? "Live" : "Connecting…"} · {stream.events.length} events
        </p>
      </header>
      <section aria-labelledby="events-title">
        <h2 id="events-title" style={{ fontSize: "1rem", marginBottom: 8 }}>Event log</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>#</th><th>Time</th><th>Event</th><th>Agent</th><th>Details</th></tr></thead>
            <tbody>
              {stream.events.map((e) => (
                <tr key={e.seq}>
                  <td className="mono">{e.seq}</td>
                  <td className="mono">{new Date(e.ts).toLocaleTimeString()}</td>
                  <td className="mono">{e.type}</td>
                  <td>{e.agent ?? "—"}</td>
                  <td className="mono">{JSON.stringify(e.data)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
```

In `frontend/src/app/App.tsx`, import the two pages and replace the index route:
```tsx
            <Route index element={<InvestigationsPage />} />
            <Route path="investigations/:id" element={<InvestigationPage />} />
```

- [ ] **Step 4: Test and build**

Run: `cd frontend && npm test && npm run build`
Expected: 5 passed; build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "Add investigations list, creation and live event log" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 10: End-to-end verification and setup docs

**Files:**
- Modify: `README.md` (replace "Setup instructions will be added with milestone M0." with the section below)

- [ ] **Step 1: Run the whole stack**

Run: `docker compose up -d --build` (Postgres + API)
Run: `cd frontend && npm run dev`
Open `http://localhost:5173`, sign in with `FORGEOPS_ADMIN_EMAIL` / `FORGEOPS_ADMIN_PASSWORD` from `.env`.
Expected: Investigations page loads with "No investigations yet."

Start an investigation "Checkout API latency increased after the last deployment".
Expected: redirected to its page, status "Live", event log shows `#1 investigation_started` with the description.

Refresh the page. Expected: the same event is shown again (replayed from the database), no duplicates.

Sign out. Expected: redirected to the login page; visiting `/` redirects back to login.

- [ ] **Step 2: Run all tests**

Run: `cd backend && uv run pytest -v` → all pass.
Run: `cd frontend && npm test` → all pass.

- [ ] **Step 3: Document setup in README**

Replace the last line of `README.md` with:
````markdown
## Local setup

Requirements: Docker Desktop, [uv](https://docs.astral.sh/uv/), Node.js 20+.

```bash
cd backend
uv sync
uv run python -m forgeops.devtools.envfile   # creates ../.env with generated secrets
cd ..
docker compose up -d --build                 # Postgres + API on http://localhost:8000
cd frontend
npm install
npm run dev                                  # web app on http://localhost:5173
```

Sign in with `FORGEOPS_ADMIN_EMAIL` and `FORGEOPS_ADMIN_PASSWORD` from `.env`.

Tests:

```bash
cd backend && uv run pytest     # needs the Postgres container running
cd frontend && npm test
```
````

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "Document local setup" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## What comes next (separate plans)

- **M1a – Engine core:** capability registry and tool wrapper, OpenRouter LLM client, shared state, LangGraph graph (plan → specialists → review → RCA → approval interrupt → report), minimal knowledge connector, starting the engine from `create_investigation`.
- **M1b – War Room UI:** top-down SVG office driven by `applyEvent`/`useEventStream`, evidence wall, RCA drawer, approval desk.
