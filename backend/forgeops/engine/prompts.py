"""Load and render the harness prompt templates (engine/prompt_templates/*.md)."""

from functools import cache
from importlib.resources import files

_PACKAGE = "forgeops.engine.prompt_templates"


@cache
def load(name: str) -> str:
    return files(_PACKAGE).joinpath(f"{name}.md").read_text(encoding="utf-8")


def render(name: str, **values: object) -> str:
    """Fill a template; a missing placeholder raises KeyError instead of leaving a gap."""
    return load(name).format_map(values)


def system(role: str, *, now: str, **values: object) -> str:
    """The full system prompt for a role: common ground rules followed by the role instructions."""
    return render("common", now=now) + "\n\n" + render(role, **values)
