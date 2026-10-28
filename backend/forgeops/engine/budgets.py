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
    tool_output_chars: int = 8000  # default cap; a tool may set its own in the catalog
    empty_results_before_stop: int = 2  # consecutive fruitless searches before a desk gives up
    keep_full_tool_outputs: int = 3  # older tool results collapse to their stored excerpt
    collapsed_output_chars: int = 500
