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
