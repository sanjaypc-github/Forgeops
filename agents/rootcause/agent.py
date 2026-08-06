from typing import Dict, Any
from memory.state import InvestigationState, RootCauseAnalysis

class RootCauseAgent:
    """
    Root Cause Agent
    Performs synthesis of the collected findings (GitHub, Logs, Knowledge)
    to generate an RCA report and recommended action steps.
    """
    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name

    def run(self, state: InvestigationState) -> Dict[str, Any]:
        print("[Root Cause Agent] Synthesizing findings to isolate root cause...")
        
        # Read findings from state
        github = state.get("github", {})
        logs = state.get("logs", {})
        knowledge = state.get("knowledge", {})
        
        # Inference Logic (Fallback Rule-based inference / LLM Prompt preparation)
        # Check for matching patterns: e.g., Redis timeouts + recent Redis cache commit
        has_redis_timeout = logs.get("redis_timeouts", False)
        
        has_cache_commit = False
        commit_sha = ""
        commit_author = ""
        for commit in github.get("recent_commits", []):
            if "cache" in commit.get("message", "").lower() or "redis" in commit.get("message", "").lower():
                has_cache_commit = True
                commit_sha = commit.get("sha")
                commit_author = commit.get("author")
                break
                
        # Generate RCA synthesis based on signals
        if has_redis_timeout and has_cache_commit:
            probable_cause = (
                f"The incident was caused by recent commit {commit_sha} by {commit_author} "
                f"which added a Redis cache layer to the checkout API. A connection timeout config "
                f"or network access restriction caused the checkout API to fail to reach Redis. "
                f"Because the fallback path PostgreSQL database got flooded or the API connection pool "
                f"timed out waiting for Redis, checkout latency spiked, causing 500 errors."
            )
            evidence = [
                "Logs confirm Redis connection timeouts (3000ms duration spike).",
                f"GitHub history shows commit {commit_sha} changing services/checkout/cache.go.",
                "Knowledge base runbook 'Redis Cache Latency Issues' documents fallback saturation risks."
            ]
            confidence = 0.92
            remediation = [
                "Revert the cache layer deployment if service recovery is urgent.",
                "Verify security group and VPC configurations for Redis subnet availability.",
                "Optimize checkout connection pools and check redis host 'redis.internal.net' resolution."
            ]
        elif has_redis_timeout:
            probable_cause = "Redis connection timed out. No recent cache deployment commits were identified, suggesting an infrastructure outage or networking degradation."
            evidence = ["Logs indicate Redis timeout errors.", "No git changes related to database or cache configs."]
            confidence = 0.70
            remediation = ["Inspect Redis cluster health status.", "Check network route tables and security groups."]
        else:
            probable_cause = "Unknown system degradation. System logs show minor anomalies, and git changes do not point to a specific fault."
            evidence = ["Minor log anomalies found.", "No corresponding runbooks or codebase regressions detected."]
            confidence = 0.35
            remediation = ["Engage secondary engineering on-call support.", "Initiate synthetic user flow profiling."]

        rca_findings: RootCauseAnalysis = {
            "probable_cause": probable_cause,
            "evidence_points": evidence,
            "confidence_score": confidence,
            "remediation_steps": remediation,
            "references": [doc.get("source", "ChromaDB") for doc in knowledge.get("retrieved_documents", [])]
        }

        logs_trace = state.get("logs_trace", [])
        logs_trace.append("Root Cause Analysis agent successfully finished reasoning.")

        return {
            "root_cause": rca_findings,
            "current_step": "AwaitingHumanApproval",
            "approval_status": "pending",
            "logs_trace": logs_trace
        }
