from typing import Dict, Any
from memory.state import InvestigationState, LogFindings
from tools.logs.tool import LogParserTool

class LogsAgent:
    """
    Logs Agent
    Queries log files to isolate exceptions, timeouts, and anomalous server responses.
    """
    def __init__(self, tool: LogParserTool = None):
        self.tool = tool or LogParserTool()

    def run(self, state: InvestigationState) -> Dict[str, Any]:
        print("[Logs Agent] Parsing server logs...")
        
        # Analyze log file (e.g. checkout.log)
        results = self.tool.analyze_log_file("checkout.log")
        
        log_findings: LogFindings = {
            "raw_anomalies": results.get("raw_anomalies", []),
            "parsed_errors": results.get("parsed_errors", []),
            "redis_timeouts": results.get("redis_timeouts", False),
            "cache_miss_rate": results.get("cache_miss_rate", 0.0),
            "status_500_count": results.get("status_500_count", 0),
            "error": results.get("error")
        }

        logs = state.get("logs_trace", [])
        logs.append(f"Logs Agent found {len(log_findings['parsed_errors'])} unique error events.")

        return {
            "logs": log_findings,
            "logs_trace": logs
        }
