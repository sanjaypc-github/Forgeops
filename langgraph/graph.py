from typing import Dict, Any, List
import concurrent.futures
from memory.state import InvestigationState, GithubFindings, LogFindings, KnowledgeFindings, RootCauseAnalysis
from agents.supervisor.agent import SupervisorAgent
from agents.github.agent import GitHubAgent
from agents.logs.agent import LogsAgent
from agents.knowledge.agent import KnowledgeAgent
from agents.rootcause.agent import RootCauseAgent

class EOPSInvestigationGraph:
    """
    StateGraph Coordinator for EOPS.
    Orchestrates the lifecycle of incident triage from description to RCA.
    Handles parallel execution of sub-agents and conditional branching.
    """
    def __init__(self):
        self.supervisor = SupervisorAgent()
        self.github_agent = GitHubAgent()
        self.logs_agent = LogsAgent()
        self.knowledge_agent = KnowledgeAgent()
        self.root_cause_agent = RootCauseAgent()

    def get_initial_state(self, incident: str) -> InvestigationState:
        """
        Creates a clean state container for a new investigation.
        """
        return {
            "incident_description": incident,
            "investigation_plan": {"steps": [], "strategy": ""},
            "active_agents": [],
            "github": {
                "recent_commits": [],
                "recent_prs": [],
                "changed_files": [],
                "author": None,
                "timestamp": None,
                "error": None
            },
            "logs": {
                "raw_anomalies": [],
                "parsed_errors": [],
                "redis_timeouts": False,
                "cache_miss_rate": 0.0,
                "status_500_count": 0,
                "error": None
            },
            "knowledge": {
                "retrieved_documents": [],
                "suggested_runbooks": [],
                "architecture_references": [],
                "error": None
            },
            "root_cause": {
                "probable_cause": "",
                "evidence_points": [],
                "confidence_score": 0.0,
                "remediation_steps": [],
                "references": []
            },
            "approval_status": "pending",
            "human_feedback": None,
            "current_step": "init",
            "logs_trace": ["Investigation initiated."]
        }

    def execute_step(self, state: InvestigationState) -> InvestigationState:
        """
        Executes the next node in the graph.
        """
        current = state.get("current_step", "init")

        if current == "init":
            # 1. Supervisor step
            plan_res = self.supervisor.run(state)
            state.update(plan_res)
            return state

        elif current == "DispatchingSubagents":
            # 2. Run active agents in parallel
            active = state.get("active_agents", [])
            print(f"[Graph Orchestrator] Running sub-agents in parallel: {active}")
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {}
                if "github" in active:
                    futures["github"] = executor.submit(self.github_agent.run, state)
                if "logs" in active:
                    futures["logs"] = executor.submit(self.logs_agent.run, state)
                if "knowledge" in active:
                    futures["knowledge"] = executor.submit(self.knowledge_agent.run, state)

                # Wait for threads and merge states
                for key, future in futures.items():
                    try:
                        result = future.result()
                        state.update(result)
                    except Exception as e:
                        state["logs_trace"].append(f"Subagent {key} failed: {str(e)}")
                        
            state["current_step"] = "SynthesizingRCA"
            return state

        elif current == "SynthesizingRCA":
            # 3. Root cause agent synthesis step
            rca_res = self.root_cause_agent.run(state)
            state.update(rca_res)
            return state
            
        return state

    def run_to_approval(self, incident: str) -> InvestigationState:
        """
        Runs the full graph cycle until it reaches the human verification/approval gateway.
        """
        state = self.get_initial_state(incident)
        
        # init -> plan
        state = self.execute_step(state)
        # DispatchingSubagents -> execution
        state = self.execute_step(state)
        # SynthesizingRCA -> RCA completion
        state = self.execute_step(state)
        
        return state
        
    def generate_report(self, state: InvestigationState) -> str:
        """
        Generates a formatted markdown report from the final state.
        """
        rca: RootCauseAnalysis = state.get("root_cause", {})
        github: GithubFindings = state.get("github", {})
        logs: LogFindings = state.get("logs", {})
        
        report = f"""# EOPS Investigation Report
**Incident:** {state.get('incident_description')}
**Approval Status:** {state.get('approval_status').upper()}

---

## 🔍 Root Cause Analysis (RCA) Summary
* **Probable Cause:** {rca.get('probable_cause')}
* **Confidence Level:** {int(rca.get('confidence_score', 0) * 100)}%

### Evidence Gathered
{chr(10).join([f'- {e}' for e in rca.get('evidence_points', [])])}

---

## 🛠️ Recommended Remediation Actions
{chr(10).join([f'{i+1}. {step}' for i, step in enumerate(rca.get('remediation_steps', []))])}

---

## 📊 Supporting Telemetry Data

### Code Modifications (GitHub)
* **Author:** {github.get('author', 'N/A')}
* **Timestamp:** {github.get('timestamp', 'N/A')}
* **Modified Files:**
{chr(10).join([f'  - {f}' for f in github.get('changed_files', [])]) if github.get('changed_files') else '  - None'}

### Log Anomaly Diagnostics
* **Redis Connection Timeouts:** {logs.get('redis_timeouts', False)}
* **500 Status Response Count:** {logs.get('status_500_count', 0)}
* **Cache Miss Rate:** {logs.get('cache_miss_rate', 0.0) * 100}%
* **Error Log Snippets:**
```text
{chr(10).join(logs.get('raw_anomalies', [])[:3])}
```

### Knowledge Base References
{chr(10).join([f'- {ref}' for ref in rca.get('references', [])])}
"""
        return report
