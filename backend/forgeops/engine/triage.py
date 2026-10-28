"""Triage: decide whether a chat message deserves a full investigation.

A measured run showed a platform question — "is all the connectors connected successfully?" — cost
74,850 tokens across 20 model calls, because six specialist desks went looking for the answer in the
customer's tools. ForgeOps already knows which connectors are connected: it is a row in its own
database. Triage answers those questions directly, with no model call at all.

The classifier is deliberately rule-based and biased towards investigating: an ambiguous message is
treated as an incident, because wrongly skipping a real incident is far worse than spending tokens.
"""

import re
from dataclasses import dataclass
from typing import Literal

Intent = Literal["status", "incident"]

def _connector_words() -> str:
    """Provider names from the catalog, so "can you access supabase?" is a platform question."""
    from forgeops.connectors.definitions import CATALOG

    words: set[str] = set()
    for definition in CATALOG.values():
        words.add(definition.type.replace("_", " "))
        words.update(w for w in definition.display_name.lower().split() if len(w) > 3)
    return "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))


# Asked about ForgeOps itself: its connectors, desks, providers and what it can see.
# `connect\w*` deliberately covers connector, connectors, connections, connected — and typos.
_PLATFORM = re.compile(
    r"\b(connect\w*|integrations?|desks?|agents?|tools?|capabilit(?:y|ies)|"
    + _connector_words() + r")\b", re.I)
_PLATFORM_VERB = re.compile(
    r"\b(connected|connect|configured|available|enabled|working|set ?up|"
    r"list|show|which|what|how many|do you have|do we have|can you (?:access|see|use|read)|"
    r"are you|is everything|is all|are all|status|successfully)\b", re.I)

# Words that describe something wrong with the customer's product: always an incident.
_SYMPTOM = re.compile(
    r"\b(error|errors|failing|failed|failure|broken|break|breaks|broke|down|outage|"
    r"crash(?:ed|ing)?|exception|stack ?trace|timeout|timing out|timed out|"
    r"slow|latency|lag|hang(?:s|ing)?|500|502|503|504|40[0-9]|"
    r"not working|does ?n[o']t work|stopped working|regress(?:ion|ed)|"
    r"users? (?:see|report|cannot|can['’]?t)|customers? (?:see|report)|"
    r"since (?:the )?(?:deploy|release|morning|yesterday|update)|"
    r"after (?:the )?(?:deploy|release|update|migration))\b", re.I)

# Asking the platform to go and look at something is an investigation, not a status question.
_INVESTIGATE = re.compile(
    r"\b(investigate|diagnose|debug|root ?cause|why is|why are|why did|"
    r"find out|check (?:the )?(?:logs?|site|website|app|deploy)|what happened)\b", re.I)


@dataclass(frozen=True)
class Decision:
    intent: Intent
    reason: str

    @property
    def needs_investigation(self) -> bool:
        return self.intent == "incident"


def classify(text: str) -> Decision:
    """Rule-based triage. Anything uncertain is treated as an incident."""
    message = text.strip()
    if not message:
        return Decision("incident", "empty message")

    if _SYMPTOM.search(message):
        return Decision("incident", "the message describes a symptom in the customer's system")
    if _INVESTIGATE.search(message):
        return Decision("incident", "the message asks for an investigation")
    if _PLATFORM.search(message) and _PLATFORM_VERB.search(message):
        return Decision("status", "the message asks about ForgeOps' own connectors or desks")
    return Decision("incident", "not recognised as a platform question, so it is investigated")


@dataclass(frozen=True)
class DeskStatus:
    title: str
    connected: bool
    abilities: int
    connectors: list[str]


@dataclass(frozen=True)
class ConnectionStatus:
    name: str
    type_title: str
    ok: bool
    detail: str
    target: str


def render_status(connections: list[ConnectionStatus], desks: list[DeskStatus]) -> str:
    """The answer to a platform question, written from the database. No model is involved."""
    lines: list[str] = []
    healthy = [c for c in connections if c.ok]
    unhealthy = [c for c in connections if not c.ok]

    if not connections:
        lines.append("No tools are connected yet. Open the Connectors page to connect one — "
                     "until then I have nothing to investigate with.")
    else:
        lines.append(f"**{len(healthy)} of {len(connections)} connections are healthy.**")
        lines.append("")
        for c in connections:
            mark = "✅" if c.ok else "⚠️"
            target = f" — `{c.target}`" if c.target else ""
            lines.append(f"{mark} **{c.name}** ({c.type_title}){target}")
            if c.detail:
                lines.append(f"   {c.detail}")

    if unhealthy:
        lines += ["", "Re-test the connections marked with a warning on the Connectors page; "
                      "the message above says what the tool reported."]

    working = [d for d in desks if d.connected]
    idle = [d for d in desks if not d.connected]
    lines += ["", "**Desks**"]
    if working:
        lines.append("Ready: " + ", ".join(
            f"{d.title} ({d.abilities} abilit{'y' if d.abilities == 1 else 'ies'})" for d in working))
    if idle:
        lines.append("No connector: " + ", ".join(d.title for d in idle)
                     + ". Those areas cannot be investigated until a tool is connected.")

    lines += ["", "_Answered from ForgeOps' own records — no agents were run and no tokens were spent._"]
    return "\n".join(lines)
