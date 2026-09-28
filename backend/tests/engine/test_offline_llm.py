"""The offline stand-in: real tool calls, no pretend analysis, and always labelled."""

import pytest

from forgeops.engine.graph import build_graph
from forgeops.engine.llm.base import LLMNotConfigured
from forgeops.engine.llm.offline import LABEL, OfflineLLM
from forgeops.engine.report import render_report
from tests.engine.graph_fixtures import initial_state, make_deps


def test_it_refuses_to_run_in_production(settings):
    with pytest.raises(LLMNotConfigured, match="refuses to run in production"):
        OfflineLLM.from_settings(settings.model_copy(update={"forgeops_env": "production"}))
    assert OfflineLLM.from_settings(settings.model_copy(update={"forgeops_env": "development"}))


async def test_a_full_run_calls_real_tools_and_labels_every_answer():
    deps, events, _, github = await make_deps({})  # no script: the stand-in drives the whole graph
    deps = type(deps)(**{**deps.__dict__, "llm": OfflineLLM()})
    deps.registry.warnings.append(f"{LABEL}. no model")

    graph = build_graph(deps, None)
    state = await graph.ainvoke(initial_state(), {"configurable": {"thread_id": "inv_offline"}})

    # the desks really called their connectors
    assert github.calls and [c[0] for c in github.calls] == ["github.list_commits"]
    assert [e.type for e in events if e.type == "tool_called"]
    # nothing claims to be analysis
    assert state["plan"].summary.startswith(LABEL)
    assert all(e.confidence == 0.0 for e in state["evidence"])
    assert state["rca"].confidence == 0.0 and state["rca"].failure_point == "unknown (no model connected)"
    assert state["rca"].recommendations == []  # a demo never proposes a write


async def test_the_report_warns_at_the_top():
    deps, _, _, _ = await make_deps({})
    deps = type(deps)(**{**deps.__dict__, "llm": OfflineLLM()})
    deps.registry.warnings.append(f"{LABEL}. no model connected")
    graph = build_graph(deps, None)
    state = await graph.ainvoke(initial_state(), {"configurable": {"thread_id": "inv_offline_2"}})

    report = render_report({**state, "decision": None})
    assert report.splitlines()[2].startswith(f"> ⚠️ **{LABEL}")
    assert "no model connected" in report
