"""Live end-to-end run with the real LLM against the knowledge vault.

    uv run python -m forgeops.devtools.smoke "Checkout is timing out and users see errors"

Starts a real investigation in the admin workspace, prints every event as it happens, prints the
root-cause analysis, and stops when the investigation asks for approval or ends.
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

from sqlalchemy import select

from forgeops.config import get_settings
from forgeops.connectors.knowledge import resolve_vault_path
from forgeops.db.models import ChatMessage, Connection, Investigation, Membership, User
from forgeops.events.models import EventIn, EventType
from forgeops.main import create_app, shutdown, startup

STOP = {EventType.approval_requested, EventType.investigation_completed, EventType.investigation_failed}
VAULT = Path(__file__).resolve().parents[3] / "knowledge-vault"


def _line(event) -> str:
    data = event.data
    detail = (data.get("summary") or data.get("objective") or data.get("finding") or data.get("question")
              or data.get("answer") or data.get("reason") or data.get("text") or data.get("tool") or "")
    if event.type == EventType.plan_created:
        detail = f"{data['summary']} | tasks: " + ", ".join(t["agent"] for t in data["tasks"])
    return f"{event.seq:>3} {event.type.value:<22} {event.agent or '':<17} {str(detail)[:110]}"


async def run(problem: str) -> int:
    settings = get_settings()
    key = settings.openrouter_api_key.get_secret_value() if settings.openrouter_api_key else ""
    if not key.strip():
        print("OPENROUTER_API_KEY is not set in .env. Add it and run again.")
        return 1

    app = create_app(settings)
    await startup(app, settings)
    state = app.state
    try:
        async with state.session_factory() as session:
            user = await session.scalar(select(User).where(User.email == settings.forgeops_admin_email.lower()))
            membership = await session.scalar(select(Membership).where(Membership.user_id == user.id))
            workspace_id = membership.workspace_id
            vault = resolve_vault_path(str(VAULT), settings.knowledge_vault_roots)
            existing = await session.scalar(select(Connection).where(
                Connection.workspace_id == workspace_id, Connection.type == "knowledge"))
            if existing is None:
                session.add(Connection(workspace_id=workspace_id, type="knowledge", name="Starter runbooks",
                                       config={"vault_path": str(vault)}, status="connected"))
            inv = Investigation(workspace_id=workspace_id, description=problem, source="chat",
                                status="queued", created_by=user.id)
            session.add(inv)
            await session.flush()
            session.add(ChatMessage(workspace_id=workspace_id, investigation_id=inv.id, role="user", text=problem))
            await session.commit()

        print(f"Investigation {inv.id}\n")
        started = time.perf_counter()
        await state.event_bus.emit(workspace_id, inv.id, EventIn(
            type=EventType.investigation_started, data={"description": problem}))
        await state.runner.start(inv.id)
        async for event in state.event_bus.stream(inv.id):
            print(_line(event))
            if event.type in STOP:
                break
        await state.runner.wait(inv.id)

        snapshot = await state.runner.snapshot(inv.id) or {}
        rca = snapshot.get("rca")
        print(f"\nDuration: {time.perf_counter() - started:.0f} s | evidence: {len(snapshot.get('evidence', []))}"
              f" | tool calls: {len(snapshot.get('tool_calls', []))} | questions: {len(snapshot.get('questions', []))}")
        if rca:
            print(f"\nROOT CAUSE ({round(rca.confidence * 100)}%): {rca.summary}\nFailure point: {rca.failure_point}")
            for item in rca.missing_information:
                print(f"  not checked: {item}")
            for rec in rca.recommendations:
                print(f"  recommendation {rec.id}: {rec.title} [{rec.action}]")
        return 0
    finally:
        await shutdown(app)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one live ForgeOps investigation")
    parser.add_argument("problem", nargs="?", default="Checkout requests are timing out and users see errors")
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.exit(asyncio.run(run(args.problem)))


if __name__ == "__main__":
    main()
