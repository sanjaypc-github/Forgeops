"""Run the API locally: `uv run python -m forgeops.devtools.serve [--port 8000]`.

On Windows the selector event loop is required by psycopg's async driver (used for LangGraph
checkpoints); uvicorn's own loop setup is skipped so this choice is kept.
"""

import argparse
import asyncio
import sys

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ForgeOps API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run("forgeops.main:create_app", factory=True, host=args.host, port=args.port, loop="none")


if __name__ == "__main__":
    main()
