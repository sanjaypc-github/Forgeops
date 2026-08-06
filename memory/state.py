from typing import TypedDict, List, Dict, Any, Optional

class GithubFindings(TypedDict):
    recent_commits: List[Dict[str, Any]]
    recent_prs: List[Dict[str, Any]]
    changed_files: List[str]
    author: Optional[str]
    timestamp: Optional[str]
    error: Optional[str]

class LogFindings(TypedDict):
    raw_anomalies: List[str]
    parsed_errors: List[Dict[str, Any]]
    redis_timeouts: bool
    cache_miss_rate: Optional[float]
    status_500_count: int
    error: Optional[str]

class KnowledgeFindings(TypedDict):
    retrieved_documents: List[Dict[str, Any]]
    suggested_runbooks: List[str]
    architecture_references: List[str]
    error: Optional[str]

class RootCauseAnalysis(TypedDict):
    probable_cause: str
    evidence_points: List[str]
    confidence_score: float  # 0.0 to 1.0
    remediation_steps: List[str]
    references: List[str]

class InvestigationState(TypedDict):
    # User Input
    incident_description: str
    
    # Supervisor Plan
    investigation_plan: Dict[str, Any]
    active_agents: List[str]
    
    # Sub-agent outputs (populated in parallel)
    github: GithubFindings
    logs: LogFindings
    knowledge: KnowledgeFindings
    
    # Synthesis & Analysis
    root_cause: RootCauseAnalysis
    
    # Human-in-the-loop State
    approval_status: str  # "pending", "approved", "rejected", "needs_more_info"
    human_feedback: Optional[str]
    
    # Execution Tracking
    current_step: str
    logs_trace: List[str]
