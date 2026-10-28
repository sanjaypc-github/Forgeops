"""Triage keeps platform questions out of the investigation pipeline.

Baseline that motivated this: "is all the connecters connected successfully ?" cost 74,850 tokens
across 20 model calls, 72% of it spent by the Knowledge desk searching a vault with nothing in it.
"""

import pytest

from forgeops.engine.triage import ConnectionStatus, DeskStatus, classify, render_status

PLATFORM_QUESTIONS = [
    "is all the connecters connected successfully ?",     # the real one, typo included
    "which tools do you have?",
    "what connectors are enabled",
    "list my connections",
    "are all the connectors working",
    "can you access supabase?",
    "is the github connector working",
    "how many desks are ready",
    "what can the knowledge vault see",
    "do we have cloudflare connected",
]

INCIDENTS = [
    "Checkout requests are timing out and users see errors since this morning's deploy",
    "the events list shows an error on the live site",
    "why is the site slow",
    "investigate the deploy",
    "site is down",
    "the supabase connection is failing with a 500",          # connector word, but a symptom
    "users cannot see events after the deploy",
    "unable to load events: column events.startTime does not exist",
    "cloudflare pages deploy failed last night",              # provider word, but a symptom
    "the page is blank and the console shows an exception",
]


@pytest.mark.parametrize("text", PLATFORM_QUESTIONS)
def test_platform_questions_are_answered_without_an_investigation(text):
    decision = classify(text)
    assert decision.intent == "status", text
    assert decision.needs_investigation is False
    assert decision.reason


@pytest.mark.parametrize("text", INCIDENTS)
def test_symptoms_always_start_an_investigation(text):
    decision = classify(text)
    assert decision.intent == "incident", text
    assert decision.needs_investigation is True


def test_anything_unrecognised_is_investigated():
    """Wrongly skipping a real incident is far worse than spending tokens."""
    for text in ["", "   ", "hmm", "the thing from yesterday", "look at order 4412"]:
        assert classify(text).intent == "incident"


def test_status_answer_names_every_connection_and_idle_desk():
    answer = render_status(
        connections=[
            ConnectionStatus(name="Site repo", type_title="GitHub", ok=True, detail="15 read tools available",
                             target="acme/web"),
            ConnectionStatus(name="App DB", type_title="Supabase", ok=False, detail="token expired",
                             target="abcdefghijklmnopqrst"),
        ],
        desks=[
            DeskStatus(title="Code", connected=True, abilities=15, connectors=["Site repo"]),
            DeskStatus(title="Observability", connected=False, abilities=0, connectors=[]),
        ],
    )
    assert "1 of 2 connections are healthy" in answer
    assert "Site repo" in answer and "acme/web" in answer
    assert "App DB" in answer and "token expired" in answer
    assert "Code (15 abilities)" in answer
    assert "No connector: Observability" in answer
    assert "no tokens were spent" in answer


def test_status_answer_when_nothing_is_connected():
    answer = render_status(connections=[], desks=[
        DeskStatus(title="Code", connected=False, abilities=0, connectors=[])])
    assert "No tools are connected yet" in answer
    assert "Connectors page" in answer
