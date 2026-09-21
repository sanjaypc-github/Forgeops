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
