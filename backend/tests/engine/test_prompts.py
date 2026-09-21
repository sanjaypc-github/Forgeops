import pytest

from forgeops.engine import prompts
from forgeops.engine.models import AgentId
from forgeops.engine.roster import PROFILES

NAMES = ["common", "supervisor_plan", "supervisor_review", "supervisor_followup", "specialist", "rca"]


def test_all_prompts_load_and_mention_untrusted_output():
    for name in NAMES:
        assert prompts.load(name).strip()
    assert "<tool_output>" in prompts.load("common")


def test_render_rejects_missing_placeholders():
    with pytest.raises(KeyError):
        prompts.render("specialist", agent_title="x")


def test_system_prompt_is_common_rules_plus_role():
    text = prompts.system("rca", now="2026-09-21T10:00:00Z")
    assert text.startswith(prompts.render("common", now="2026-09-21T10:00:00Z"))
    assert "submit_rca" in text


def test_every_agent_has_a_profile():
    assert set(PROFILES) == set(AgentId)
    assert all(p.focus and p.title and p.area for p in PROFILES.values())
