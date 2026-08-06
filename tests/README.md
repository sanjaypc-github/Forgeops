# EOPS Test Suite

This folder holds unit and integration test scripts.

## Run Tests
Install dev dependencies and execute pytest:

```bash
pip install pytest httpx
pytest tests/
```

## Structure
- `tests/test_agents.py`: Validates Supervisor, GitHub, Logs, and RAG Agents logic.
- `tests/test_graph.py`: Verifies LangGraph state transitions, loops, and parallel executions.
- `tests/test_api.py`: Tests the FastAPI endpoints (`/api/investigate`, `/api/approve`, etc.).
