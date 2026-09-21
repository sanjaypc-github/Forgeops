from dataclasses import dataclass


@dataclass(frozen=True)
class Budgets:
    """Hard limits that keep every investigation bounded in time, cost and chatter."""

    specialist_tool_calls: int = 8
    specialist_seconds: float = 150
    questions_per_agent: int = 2
    questions_total: int = 12
    answer_tool_calls: int = 3
    answer_seconds: float = 45
    tool_timeout_seconds: float = 20
    review_rounds: int = 1
    followup_rounds: int = 2
    run_seconds: float = 1200
    tool_output_chars: int = 8000
