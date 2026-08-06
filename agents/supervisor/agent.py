import os
from typing import Dict, Any
from memory.state import InvestigationState

class SupervisorAgent:
    """
    Supervisor Agent (Engineering Manager)
    Analyzes the incident reports and schedules specialized agents.
    """
    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name

    def run(self, state: InvestigationState) -> Dict[str, Any]:
        """
        Executes supervisor analysis. Determines which tools/agents to dispatch.
        """
        incident = state.get("incident_description", "")
        print(f"[Supervisor] Analyzing incident: '{incident}'")
        
        # In a real environment, we'd query an LLM here to perform structured JSON extraction.
        # Below is a robust template that dynamically resolves targets.
        
        active_agents = []
        plan_steps = []

        # Analyze keywords in description to build plan
        incident_lower = incident.lower()
        if any(w in incident_lower for w in ["commit", "deploy", "pr", "changed", "git", "author", "merge", "push"]):
            active_agents.append("github")
            plan_steps.append("Fetch recent commits and pull requests to isolate code deployments.")
            
        if any(w in incident_lower for w in ["log", "error", "timeout", "exception", "latency", "500", "fail", "slow", "redis"]):
            active_agents.append("logs")
            plan_steps.append("Search and parse system logs for connection issues, HTTP errors, and service spikes.")
            
        if any(w in incident_lower for w in ["runbook", "docs", "how-to", "architecture", "reference", "manual", "fix"]):
            active_agents.append("knowledge")
            plan_steps.append("Query ChromaDB documentation store for corresponding service architecture or troubleshooting runbooks.")

        # Default to all agents if query is general or empty
        if not active_agents:
            active_agents = ["github", "logs", "knowledge"]
            plan_steps = [
                "Scan repository changes to identify recent build/deployment deltas.",
                "Parse service log files to capture any runtime warnings or stack traces.",
                "Perform vector search on internal runbooks for checkout and api issues."
            ]

        logs = state.get("logs_trace", [])
        logs.append(f"Supervisor plan generated. Dispatching agents: {active_agents}")

        return {
            "investigation_plan": {
                "steps": plan_steps,
                "strategy": "Concurrent sub-agent dispatch followed by state synthesis."
            },
            "active_agents": active_agents,
            "current_step": "DispatchingSubagents",
            "logs_trace": logs
        }
