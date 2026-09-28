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


def system(role: str, **values: object) -> str:
    """The full system prompt for a role: common ground rules followed by the role instructions.

    It must stay identical across a desk's turns so providers can cache the prefix; anything that
    changes per call (the clock, the task) belongs in the first user message instead.
    """
    return render("common") + "\n\n" + render(role, **values)


def now_line(now: str) -> str:
    return f"Current time: {now} (UTC)."
